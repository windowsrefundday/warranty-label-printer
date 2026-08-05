import base64
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.package_release import build_package
from tools.sign_manifest import create_manifest
from tools.updater import Manifest, UpdateError, platform_target


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingTests(unittest.TestCase):
    def test_package_contains_marker_application_and_runtime(self) -> None:
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

    def test_signed_manifest_round_trips_through_verifier(self) -> None:
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

            document["version"] = "1.2.4"
            tampered = Manifest.from_mapping(document)
            with self.assertRaises(UpdateError):
                tampered.verify_signature({"test-key": public_b64})

            unsafe_asset = root / "release #1.zip"
            unsafe_asset.write_bytes(b"release")
            with self.assertRaises(RuntimeError):
                create_manifest(
                    "1.2.3",
                    "stable",
                    "test-key",
                    private_b64,
                    {"macos-arm64": unsafe_asset},
                    "https://updates.example.test/v1",
                )


if __name__ == "__main__":
    unittest.main()
