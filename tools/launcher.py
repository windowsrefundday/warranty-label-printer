"""Stable launcher for source checkouts and managed, versioned installs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from tools import updater  # noqa: E402


def _source_python() -> Path:
    if sys.platform == "win32":
        candidate = SOURCE_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = SOURCE_ROOT / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else Path(sys.executable)


def _managed_root() -> updater.UpdatePaths:
    return updater.UpdatePaths.from_root(updater._data_root())


def _mark_checked(paths: updater.UpdatePaths) -> updater.UpdateState:
    with updater.FileLock(paths.lock):
        state = updater.UpdateState.load(paths)
        state.last_check = datetime.now(timezone.utc).isoformat()
        state.save(paths)
        return state


def _reserve_background_check(paths: updater.UpdatePaths) -> bool:
    with updater.FileLock(paths.lock):
        state = updater.UpdateState.load(paths)
        if state.last_check:
            try:
                elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(
                    state.last_check.replace("Z", "+00:00")
                )
                if elapsed.total_seconds() < 24 * 60 * 60:
                    return False
            except ValueError:
                pass
        state.last_check = datetime.now(timezone.utc).isoformat()
        state.save(paths)
        return True


def _clear_error(paths: updater.UpdatePaths) -> None:
    with updater.FileLock(paths.lock):
        state = updater.UpdateState.load(paths)
        state.last_error = None
        state.save(paths)


def _record_error(paths: updater.UpdatePaths, message: str) -> None:
    try:
        with updater.FileLock(paths.lock):
            state = updater.UpdateState.load(paths)
            state.last_error = message[:500]
            state.save(paths)
    except updater.UpdateError:
        return


def _runtime_python(release: Path) -> Path:
    if sys.platform == "win32":
        executable = release / "runtime" / "Scripts" / "python.exe"
    else:
        executable = release / "runtime" / "bin" / "python"
    if not executable.is_file():
        raise updater.UpdateError(
            f"Managed release {release.name} has no self-contained Python runtime"
        )
    return executable


def _release_for_launch(paths: updater.UpdatePaths) -> tuple[Path | None, updater.UpdateState]:
    state = updater.UpdateState.load(paths)
    version = state.pending_version or state.current_version
    if version is None:
        return None, state
    release = paths.versions / version
    if not release.is_dir():
        raise updater.UpdateError(f"Managed release {version} is missing")
    return release, state


def _schedule_background_update_check(paths: updater.UpdatePaths) -> None:
    """Start a non-blocking signed check at most once per day."""
    if os.environ.get("WARRANTY_LABEL_DISABLE_AUTO_UPDATE") == "1":
        return
    if not _reserve_background_check(paths):
        return
    command = [str(_source_python()), str(Path(__file__).resolve()), "download"]
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                command,
                cwd=str(SOURCE_ROOT),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            subprocess.Popen(
                command,
                cwd=str(SOURCE_ROOT),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except OSError:
        # A failed background check must never prevent the application launch.
        return


def run(arguments: Sequence[str]) -> int:
    """Run the active release, falling back to a source checkout before migration."""
    paths = _managed_root()
    try:
        paths.ensure()
        _schedule_background_update_check(paths)
        release, _state = _release_for_launch(paths)
        if release is None:
            executable = _source_python()
            command = [str(executable), str(SOURCE_ROOT / "main.py"), *arguments]
            return subprocess.call(command, cwd=str(SOURCE_ROOT))
        executable = _runtime_python(release)
        return updater.run_child(paths, release, executable, arguments)
    except (OSError, updater.UpdateError) as exc:
        print(f"Managed update is unavailable; refusing unsafe launch: {exc}", file=sys.stderr)
        return 1


def _load_signed_manifest(paths: updater.UpdatePaths) -> updater.Manifest:
    url = os.environ.get("WARRANTY_LABEL_UPDATE_MANIFEST_URL", updater.DEFAULT_MANIFEST_URL)
    manifest = updater.Manifest.from_mapping(updater.fetch_manifest(url))
    manifest.verify_signature()
    manifest.validate_time()
    return manifest


def check() -> int:
    paths = _managed_root()
    paths.ensure()
    state = _mark_checked(paths)
    try:
        manifest = _load_signed_manifest(paths)
        eligible = updater.choose_update(
            manifest,
            state,
            updater.platform_target(),
        )
        _clear_error(paths)
        if eligible:
            print(f"Update available: {manifest.version} ({manifest.channel})")
        else:
            print("No eligible application update is available.")
        return 0
    except updater.UpdateError as exc:
        _record_error(paths, str(exc))
        print(f"Update check failed safely: {exc}", file=sys.stderr)
        return 1


def download() -> int:
    paths = _managed_root()
    paths.ensure()
    state = _mark_checked(paths)
    try:
        manifest = _load_signed_manifest(paths)
        if not updater.choose_update(manifest, state, updater.platform_target()):
            print("No eligible application update is available.")
            return 0
        updater.prepare_and_install(paths, manifest, updater.platform_target())
        updater.activate(paths, manifest.version)
        print(f"Downloaded and staged {manifest.version}; restart to apply it.")
        return 0
    except updater.UpdateError as exc:
        _record_error(paths, str(exc))
        print(f"Update failed safely: {exc}", file=sys.stderr)
        return 1


def status() -> int:
    paths = _managed_root()
    print(json.dumps(updater.UpdateState.load(paths).to_mapping(), indent=2, sort_keys=True))
    return 0


def rollback() -> int:
    paths = _managed_root()
    try:
        state = updater.rollback(paths, "operator requested rollback")
        print(json.dumps(state.to_mapping(), indent=2, sort_keys=True))
        return 0
    except updater.UpdateError as exc:
        print(f"Rollback unavailable: {exc}", file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    raw_arguments = list(argv if argv is not None else sys.argv[1:])
    # Application arguments intentionally pass through untouched.  Parsing
    # them as launcher options would reject normal flags such as --diagnose.
    if raw_arguments and raw_arguments[0] == "run":
        return run(raw_arguments[1:])
    parser = argparse.ArgumentParser(description="Warranty Label Printer stable launcher")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    for command in ("check", "download", "status", "rollback"):
        subparsers.add_parser(command)
    args = parser.parse_args(raw_arguments)
    if args.command == "check":
        return check()
    if args.command == "download":
        return download()
    if args.command == "status":
        return status()
    return rollback()


if __name__ == "__main__":
    raise SystemExit(main())
