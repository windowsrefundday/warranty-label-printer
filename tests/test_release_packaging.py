import base64
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr
from unittest import mock
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.package_release import build_package
from tools.sign_manifest import create_manifest
from tools.updater import Manifest, UpdatePaths, UpdateState, platform_target
from tools import launcher


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingTests(unittest.TestCase):
    def test_launcher_passes_application_flags_without_parsing_them(self):
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                "os.environ",
                {
                    "WARRANTY_LABEL_UPDATE_ROOT": temporary,
                    "WARRANTY_LABEL_DISABLE_AUTO_UPDATE": "1",
                },
                clear=False,
            ), mock.patch.object(
                launcher.subprocess, "call", return_value=0
            ) as call:
                self.assertEqual(launcher.main(["run", "--diagnose"]), 0)
                self.assertIn("--diagnose", call.call_args.args[0])

    def test_launcher_schedules_at_most_one_nonblocking_daily_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = UpdatePaths.from_root(Path(temporary))
            paths.ensure()
            state = UpdateState()
            state.save(paths)
            with mock.patch.dict(
                "os.environ", {"WARRANTY_LABEL_DISABLE_AUTO_UPDATE": "0"}, clear=False
            ), mock.patch.object(
                launcher.subprocess, "Popen"
            ) as process:
                launcher._schedule_background_update_check(paths)
                launcher._schedule_background_update_check(paths)
                process.assert_called_once()
                self.assertEqual(process.call_args.args[0][-1], "download")

    def test_launcher_status_fails_safely_when_state_is_corrupt(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = UpdatePaths.from_root(Path(temporary))
            paths.state.parent.mkdir(parents=True, exist_ok=True)
            paths.state.write_text("{", encoding="utf-8")
            with mock.patch.object(launcher, "_managed_root", return_value=paths):
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(launcher.status(), 1)

    def test_package_contains_marker_application_and_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime"
            runtime.mkdir()
            (runtime / "python").write_text("runtime", encoding="utf-8")
            output = root / "release.zip"
            build_package(
                ROOT,
                "1.2.3",
                platform_target(),
                output,
                runtime=runtime,
            )
            with zipfile.ZipFile(output) as bundle:
                names = set(bundle.namelist())
                self.assertIn("release.json", names)
                self.assertIn("app/main.py", names)
                self.assertIn("runtime/python", names)
                marker = json.loads(bundle.read("release.json"))
                self.assertEqual(marker["version"], "1.2.3")
                self.assertEqual(marker["target"], platform_target())
                self.assertEqual(
                    bundle.getinfo("runtime/python").compress_type,
                    zipfile.ZIP_DEFLATED,
                )

    def test_signed_manifest_round_trips_through_verifier(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = root / "release.zip"
            asset.write_bytes(b"release")
            private = Ed25519PrivateKey.generate()
            private_b64 = base64.urlsafe_b64encode(
                private.private_bytes(
                    serialization.Encoding.Raw,
                    serialization.PrivateFormat.Raw,
                    serialization.NoEncryption(),
                )
            ).decode().rstrip("=")
            public_b64 = base64.urlsafe_b64encode(
                private.public_key().public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                )
            ).decode().rstrip("=")
            document = create_manifest(
                "1.2.3",
                "stable",
                "test-key",
                private_b64,
                {"macos-arm64": asset},
                "https://updates.example.test/v1",
            )
            manifest = Manifest.from_mapping(document)
            manifest.verify_signature({"test-key": public_b64})
            self.assertEqual(
                manifest.targets["macos-arm64"].sha256,
                hashlib.sha256(b"release").hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
