import subprocess
import unittest
from unittest import mock

from main import launch_https_tunnel


class HttpsTunnelTests(unittest.TestCase):
    def test_accepts_only_https_url_with_hostname_and_pins_package(self):
        process = mock.MagicMock()
        process.stdout = iter(["your url is: https://scanner.example.test\n"])

        with mock.patch("main.subprocess.Popen", return_value=process) as popen:
            returned_process, public_url = launch_https_tunnel(9191)

        self.assertIs(returned_process, process)
        self.assertEqual(public_url, "https://scanner.example.test")
        self.assertEqual(
            popen.call_args.args[0],
            ["npx", "-y", "localtunnel@2.0.2", "--port", "9191"],
        )

    def test_rejects_https_url_without_hostname(self):
        process = mock.MagicMock()
        process.stdout = iter(["your url is: https:///missing-host\n"])

        with mock.patch("main.subprocess.Popen", return_value=process):
            with self.assertRaises(RuntimeError):
                launch_https_tunnel(9191)

        process.terminate.assert_called_once_with()

    def test_waits_after_killing_stuck_process(self):
        process = mock.MagicMock()
        process.stdout = iter(())
        process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="npx", timeout=3),
            0,
        ]

        with mock.patch("main.subprocess.Popen", return_value=process):
            with self.assertRaises(RuntimeError):
                launch_https_tunnel(9191, timeout_seconds=0.0)

        process.kill.assert_called_once_with()
        self.assertEqual(
            process.wait.call_args_list,
            [mock.call(timeout=3), mock.call()],
        )


if __name__ == "__main__":
    unittest.main()
