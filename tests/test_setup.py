import unittest
from collections.abc import Sequence
from pathlib import Path
from unittest import mock

from tools import setup


class SetupTests(unittest.TestCase):
    def test_macos_default_commands_do_not_require_node(self) -> None:
        root = Path("/repo")
        commands = setup.build_setup_commands(
            root,
            "macos",
            "/runtime/python3",
        )

        self.assertEqual(
            commands[0][1],
            ["/runtime/python3", "-m", "venv", str(root / ".venv")],
        )
        self.assertEqual(
            commands[2][1][-1],
            str(root / "requirements.txt"),
        )
        self.assertEqual(commands[-1][1][-1], "--diagnose")

    def test_tunnel_setup_adds_locked_runtime_install(self) -> None:
        commands = setup.build_setup_commands(
            Path("/repo"),
            "macos",
            "/runtime/python3",
            "/runtime/npm",
            with_tunnel_runtime=True,
        )

        self.assertEqual(
            commands[4][1],
            ["/runtime/npm", "ci", "--omit=dev", "--ignore-scripts"],
        )

    def test_windows_uses_windows_requirements_and_venv_python(self) -> None:
        commands = setup.build_setup_commands(
            Path("C:/repo"),
            "windows",
            "C:/Python/python.exe",
            "C:/Program Files/nodejs/npm.cmd",
        )

        self.assertEqual(
            commands[1][1][0],
            str(Path("C:/repo") / ".venv" / "Scripts" / "python.exe"),
        )
        self.assertEqual(
            commands[2][1][-1],
            str(Path("C:/repo") / "requirements-windows.txt"),
        )

    def test_tunnel_setup_requires_existing_node_runtime(self) -> None:
        with mock.patch.object(setup.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Node.js/npm"):
                setup.run_setup(
                    Path("/repo"),
                    "macos",
                    with_tunnel_runtime=True,
                )

    def test_setup_never_runs_printer_or_calibration_commands(self) -> None:
        executed: list[tuple[str, list[str], Path]] = []

        def record(description: str, command: Sequence[str], cwd: Path) -> None:
            executed.append((description, list(command), cwd))

        setup.run_setup(
            Path("/repo"),
            "macos",
            python_executable="/runtime/python3",
            npm_executable="/runtime/npm",
            runner=record,
        )

        command_text = " ".join(
            argument.lower()
            for _, command, _ in executed
            for argument in command
        )
        self.assertNotIn("--setup-printer", command_text)
        self.assertNotIn("calibrate", command_text)
        self.assertNotIn("print", command_text)
        self.assertIn("--diagnose", command_text)
        self.assertNotIn("npm", command_text)

    def test_unsupported_host_platform_is_rejected(self) -> None:
        with mock.patch.object(setup.sys, "platform", "linux"):
            with self.assertRaisesRegex(RuntimeError, "macOS and Windows"):
                setup.current_platform()


if __name__ == "__main__":
    unittest.main()
