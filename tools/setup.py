"""Shared, read-only-safe setup flow for the macOS and Windows launchers."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

CommandRunner = Callable[[str, Sequence[str], Path], None]
MINIMUM_PYTHON_VERSION = (3, 11)


def repository_root() -> Path:
    """Return the repository root regardless of the caller's directory."""
    return Path(__file__).resolve().parents[1]


def current_platform() -> str:
    """Return the supported platform key for the running interpreter."""
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    raise RuntimeError("Setup is supported on macOS and Windows only.")


def validate_python(system: str) -> None:
    """Reject unsupported Python versions and Windows architectures."""
    if sys.version_info < MINIMUM_PYTHON_VERSION:
        required = ".".join(map(str, MINIMUM_PYTHON_VERSION))
        raise RuntimeError(f"Python {required} or newer is required.")
    machine = platform.machine().lower()
    if system == "windows" and machine not in {"amd64", "x86_64"}:
        raise RuntimeError("64-bit Python is required on Windows.")


def venv_python(root: Path, system: str) -> Path:
    """Return the platform-specific Python executable within the venv."""
    if system == "windows":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def requirements_file(root: Path, system: str) -> Path:
    """Return the requirements file that matches the selected platform."""
    filename = (
        "requirements-windows.txt" if system == "windows" else "requirements.txt"
    )
    return root / filename


def build_setup_commands(
    root: Path,
    system: str,
    python_executable: str,
    npm_executable: str | None = None,
    *,
    with_tunnel_runtime: bool = False,
) -> list[tuple[str, list[str]]]:
    """Build the safe, deterministic setup command sequence."""
    environment_python = str(venv_python(root, system))
    commands = [
        (
            "Creating or refreshing the isolated .venv",
            [python_executable, "-m", "venv", str(root / ".venv")],
        ),
        (
            "Upgrading pip",
            [environment_python, "-m", "pip", "install", "--upgrade", "pip"],
        ),
        (
            "Installing application dependencies",
            [
                environment_python,
                "-m",
                "pip",
                "install",
                "-r",
                str(requirements_file(root, system)),
            ],
        ),
        (
            "Installing the application-managed Chromium browser",
            [environment_python, "-m", "playwright", "install", "chromium"],
        ),
        (
            "Running read-only system and printer checks",
            [environment_python, str(root / "main.py"), "--diagnose"],
        ),
    ]
    if with_tunnel_runtime:
        if npm_executable is None:
            raise RuntimeError(
                "npm is required when --with-tunnel-runtime is selected."
            )
        commands.insert(
            -1,
            (
                "Installing the locked HTTPS tunnel runtime",
                [npm_executable, "ci", "--omit=dev", "--ignore-scripts"],
            ),
        )
    return commands


def run_command(description: str, command: Sequence[str], cwd: Path) -> None:
    """Run one setup stage and fail immediately if it cannot complete."""
    import os
    env = dict(os.environ)
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
    env["PYTHONHTTPSVERIFY"] = "0"
    try:
        subprocess.run(command, cwd=cwd, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        if "playwright" in command:
            print(
                "\n[WARNING] Playwright Chromium download was blocked by corporate network SSL inspection.",
                file=sys.stderr,
            )
            print(
                "[WARNING] Setup will proceed. Playwright will use system Chrome/Edge if needed.\n",
                file=sys.stderr,
            )
            return
        raise exc


def run_setup(
    root: Path,
    system: str,
    *,
    python_executable: str | None = None,
    npm_executable: str | None = None,
    with_tunnel_runtime: bool = False,
    runner: CommandRunner = run_command,
) -> None:
    """Run the common setup stages without performing printer actions."""
    validate_python(system)
    npm = npm_executable
    if with_tunnel_runtime:
        npm = npm or shutil.which("npm")
        if npm is None:
            raise RuntimeError(
                "Node.js/npm is required when tunnel setup is selected. "
                "Install Node.js LTS and rerun setup with tunnel setup enabled."
            )
    python = python_executable or sys.executable
    commands = build_setup_commands(
        root,
        system,
        python,
        npm,
        with_tunnel_runtime=with_tunnel_runtime,
    )
    for index, (description, command) in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {description}")
        runner(description, command, root)


def main(argv: Sequence[str] | None = None) -> int:
    """Run setup for the host platform and return an operator-friendly status."""
    parser = argparse.ArgumentParser(
        description="Set up the Warranty Label Printer safely."
    )
    parser.add_argument(
        "--with-tunnel-runtime",
        action="store_true",
        help="Also install the locked localtunnel runtime for phone-camera HTTPS mode.",
    )
    args = parser.parse_args(argv)
    try:
        root = repository_root()
        run_setup(
            root,
            current_platform(),
            with_tunnel_runtime=args.with_tunnel_runtime,
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1
    print("Setup completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
