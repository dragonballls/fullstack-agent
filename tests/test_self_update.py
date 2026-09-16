from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from quality_of_life.self_update import (
    GitHubRelease,
    build_windows_handoff_script,
    is_update_available,
    verify_sha256,
)


class SelfUpdateTests(unittest.TestCase):
    def test_release_parser_requires_jarvis_exe_and_digest(self) -> None:
        digest = "a" * 64
        payload = {
            "tag_name": "latest",
            "name": "Jarvis Latest",
            "body": "commit: abc123",
            "assets": [
                {
                    "name": "Jarvis.exe",
                    "browser_download_url": "https://github.com/dragonballls/fullstack-agent/releases/download/latest/Jarvis.exe",
                    "digest": f"sha256:{digest}",
                }
            ],
        }
        release = GitHubRelease.from_payload(payload)
        self.assertEqual(release.tag_name, "latest")
        self.assertEqual(release.commit_sha, "abc123")
        self.assertEqual(release.asset_url.endswith("/Jarvis.exe"), True)
        self.assertEqual(release.sha256, digest)

    def test_update_available_requires_different_known_commit(self) -> None:
        self.assertFalse(is_update_available("abc", "abc"))
        self.assertTrue(is_update_available("abc", "def"))
        self.assertFalse(is_update_available("", "def"))
        self.assertFalse(is_update_available("abc", ""))

    def test_verify_sha256_matches_expected_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Jarvis.exe"
            data = b"verified jarvis build"
            path.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            self.assertTrue(verify_sha256(path, digest))
            self.assertFalse(verify_sha256(path, "0" * 64))

    def test_handoff_script_waits_for_process_then_replaces_and_restarts(self) -> None:
        script = build_windows_handoff_script(
            pid=1234,
            current_exe=Path(r"C:\Jarvis\Jarvis.exe"),
            staged_exe=Path(r"C:\Users\test\AppData\Local\Temp\Jarvis-new.exe"),
        )
        self.assertIn("1234", script)
        self.assertIn("Jarvis-new.exe", script)
        self.assertIn("Jarvis.exe", script)
        self.assertIn("Start-Process", script)
        self.assertIn("Move-Item", script)


if __name__ == "__main__":
    unittest.main()
