import json
from pathlib import Path
import plistlib
import unittest
from unittest.mock import patch
from nexum.identity import APP_ID, VERSION, artifact_name
from nexum.paths import data_dir, cache_dir


class DistributionTests(unittest.TestCase):
    def test_consistent_artifact_names(self):
        self.assertEqual(artifact_name("source"), f"Nexum-{VERSION}-source.zip")
        self.assertEqual(
            artifact_name("macos", "aarch64"), f"Nexum-{VERSION}-macos-arm64.dmg"
        )
        self.assertEqual(
            artifact_name("linux", "arm64"), f"Nexum-{VERSION}-linux-aarch64.flatpak"
        )
        with self.assertRaises(ValueError):
            artifact_name("windows", "arm64")

    def test_native_macos_paths(self):
        with patch("nexum.paths.sys.platform", "darwin"):
            self.assertEqual(
                data_dir(), Path.home() / "Library/Application Support/Nexum"
            )
            self.assertEqual(cache_dir(), Path.home() / "Library/Caches/Nexum")

    def test_flatpak_desktop_and_metadata_identity_match(self):
        import xml.etree.ElementTree as ET

        root = Path(__file__).resolve().parents[1]
        folder = root / "packaging/flatpak"
        manifest = json.loads((folder / (APP_ID + ".json")).read_text())
        self.assertEqual(manifest["app-id"], APP_ID)
        meta = ET.parse(folder / (APP_ID + ".metainfo.xml")).getroot()
        self.assertEqual(meta.findtext("id"), APP_ID)
        self.assertEqual(meta.findtext("launchable"), APP_ID + ".desktop")
        self.assertIn("Name=Nexum\n", (folder / (APP_ID + ".desktop")).read_text())
        self.assertNotIn("--filesystem=host", manifest["finish-args"])

    def test_macos_entitlements_do_not_disable_runtime_protection(self):
        p = Path(__file__).resolve().parents[1] / "packaging/macos/entitlements.plist"
        with p.open("rb") as f:
            self.assertEqual(plistlib.load(f), {})
