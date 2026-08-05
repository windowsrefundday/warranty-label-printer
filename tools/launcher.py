"""Stable launcher for source checkouts and managed, versioned installs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

SOURCE_ROOT = Path(__file__).resolve().parents[1]
UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60
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
                if not isinstance(state.last_check, str):
                    raise ValueError("last_check is not text")
                elapsed_seconds = (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(state.last_check.replace("Z", "+00:00"))
                ).total_seconds()
                if 0 <= elapsed_seconds < UPDATE_CHECK_INTERVAL_SECONDS:
                    return False
            except (AttributeError, TypeError, ValueError):
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
    except (OSError, updater.UpdateError):
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
    """Start a non-blocking signed check when the six-hour lease expires."""
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


def _background_update_loop(
    paths: updater.UpdatePaths, stop_event: threading.Event
) -> None:
    """Schedule signed checks every six hours while the launched app runs."""
    while not stop_event.wait(UPDATE_CHECK_INTERVAL_SECONDS):
        try:
            _schedule_background_update_check(paths)
        except (OSError, updater.UpdateError):
            # A transient lock or state failure must not terminate the app.
            continue


def _start_background_update_timer(
    paths: updater.UpdatePaths,
) -> tuple[threading.Event, threading.Thread]:
    """Start the lifecycle-bound periodic update checker."""
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_background_update_loop,
        args=(paths, stop_event),
        name="warranty-update-checker",
        daemon=True,
    )
    thread.start()
    return stop_event, thread


def run(arguments: Sequence[str]) -> int:
    """Run the active release, falling back to a source checkout before migration."""
    paths = _managed_root()
    clean_args = [arg for arg in arguments if arg != "--"]
    try:
        paths.ensure()
        _schedule_background_update_check(paths)
        stop_event, timer_thread = _start_background_update_timer(paths)
        try:
            release, _state = _release_for_launch(paths)
            if release is None:
                executable = _source_python()
                command = [str(executable), str(SOURCE_ROOT / "main.py"), *clean_args]
                return subprocess.call(command, cwd=str(SOURCE_ROOT))
            executable = _runtime_python(release)
            return updater.run_child(paths, release, executable, clean_args)
        finally:
            stop_event.set()
            timer_thread.join(timeout=1)
    except (OSError, updater.UpdateError) as exc:
        print(f"Managed update is unavailable; refusing unsafe launch: {exc}", file=sys.stderr)
        return 1


def _load_signed_manifest() -> updater.Manifest:
    url = os.environ.get("WARRANTY_LABEL_UPDATE_MANIFEST_URL", updater.DEFAULT_MANIFEST_URL)
    manifest = updater.Manifest.from_mapping(updater.fetch_manifest(url))
    manifest.verify_signature()
    manifest.validate_time()
    return manifest


def check() -> int:
    """Check the signed update channel and return 0 on success, else 1."""
    paths = _managed_root()
    try:
        paths.ensure()
        state = _mark_checked(paths)
        manifest = _load_signed_manifest()
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
    except OSError as exc:
        print(f"Update check failed safely: {exc}", file=sys.stderr)
        return 1


def download() -> int:
    """Download and stage an eligible update; return 0 on success, else 1."""
    paths = _managed_root()
    try:
        paths.ensure()
        state = _mark_checked(paths)
        manifest = _load_signed_manifest()
        eligible = updater.choose_update(manifest, state, updater.platform_target())
        _clear_error(paths)
        if not eligible:
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
    except OSError as exc:
        print(f"Update failed safely: {exc}", file=sys.stderr)
        return 1


def status() -> int:
    """Print persisted update state; return 0 on success, else 1."""
    paths = _managed_root()
    try:
        state = updater.UpdateState.load(paths)
    except updater.UpdateError as exc:
        print(f"Update status is unavailable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(state.to_mapping(), indent=2, sort_keys=True))
    return 0


def rollback() -> int:
    """Roll back to the previous release; return 0 on success, else 1."""
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
    parser = argparse.ArgumentParser(description="Warranty Label Printer stable launcher")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    # Application arguments intentionally pass through untouched.  Parsing
    # them as launcher options would reject normal flags such as --diagnose.
    run_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    handlers = {"check": check, "download": download, "status": status, "rollback": rollback}
    for command in handlers:
        subparsers.add_parser(command)
    args, passthrough = parser.parse_known_args(raw_arguments)
    command_handlers = {**handlers, "run": lambda: run(args.arguments)}
    if args.command == "run":
        args.arguments.extend(passthrough)
        passthrough = []
    if passthrough:
        parser.error(f"Unrecognized launcher arguments: {' '.join(passthrough)}")
    handler = command_handlers.get(args.command)
    if handler is None:
        parser.error(f"Unsupported launcher command: {args.command}")
    return handler()


if __name__ == "__main__":
    raise SystemExit(main())
