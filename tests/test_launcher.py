import io
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tools import launcher
from tools.updater import UpdatePaths, UpdateState


class LauncherTests(unittest.TestCase):
    def test_passes_application_flags_without_parsing_them(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                "os.environ",
                {
                    "WARRANTY_LABEL_UPDATE_ROOT": temporary,
                    "WARRANTY_LABEL_DISABLE_AUTO_UPDATE": "1",
                },
                clear=False,
            ), mock.patch.object(launcher.subprocess, "call", return_value=0) as call:
                self.assertEqual(launcher.main(["run", "--diagnose"]), 0)
                self.assertIn("--diagnose", call.call_args.args[0])

    def test_schedules_at_most_one_nonblocking_six_hour_download(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = UpdatePaths.from_root(Path(temporary))
            paths.ensure()
            state = UpdateState()
            state.save(paths)
            with mock.patch.dict(
                "os.environ", {"WARRANTY_LABEL_DISABLE_AUTO_UPDATE": "0"}, clear=False
            ), mock.patch.object(launcher.subprocess, "Popen") as process:
                launcher._schedule_background_update_check(paths)
                launcher._schedule_background_update_check(paths)
                process.assert_called_once()
                self.assertEqual(process.call_args.args[0][-1], "download")

    def test_waits_six_hours_before_repeating_background_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = UpdatePaths.from_root(Path(temporary))
            paths.ensure()
            state = UpdateState(
                last_check=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
            )
            state.save(paths)
            with mock.patch.dict(
                "os.environ", {"WARRANTY_LABEL_DISABLE_AUTO_UPDATE": "0"}, clear=False
            ), mock.patch.object(launcher.subprocess, "Popen") as process:
                launcher._schedule_background_update_check(paths)
                process.assert_not_called()

                state.last_check = (
                    datetime.now(timezone.utc) - timedelta(hours=6, seconds=1)
                ).isoformat()
                state.save(paths)
                launcher._schedule_background_update_check(paths)
                process.assert_called_once()

    def test_rechecks_while_application_is_running(self) -> None:
        stop_event = mock.Mock()
        stop_event.wait.side_effect = [False, True]
        with mock.patch.object(launcher, "_schedule_background_update_check") as schedule:
            launcher._background_update_loop(mock.sentinel.paths, stop_event)
        schedule.assert_called_once_with(mock.sentinel.paths)
        self.assertEqual(
            stop_event.wait.call_args.args[0], launcher.UPDATE_CHECK_INTERVAL_SECONDS
        )

    def test_status_fails_safely_when_state_is_corrupt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = UpdatePaths.from_root(Path(temporary))
            paths.state.parent.mkdir(parents=True, exist_ok=True)
            paths.state.write_text("{", encoding="utf-8")
            with mock.patch.object(launcher, "_managed_root", return_value=paths):
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(launcher.status(), 1)


if __name__ == "__main__":
    unittest.main()
