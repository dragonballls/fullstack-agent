from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from quality_of_life.omniroute import OmniRouteConnection, is_loopback_hostname
from quality_of_life.router import CloudModelRouter, ProviderTarget


class OmniRouteConnectionTests(unittest.TestCase):
    def test_default_endpoint_is_loopback_and_autostart_enabled(self) -> None:
        with patch.dict(
            os.environ,
            {
                "JARVIS_OMNIROUTE_BASE_URL": "http://127.0.0.1:20128/v1",
                "JARVIS_OMNIROUTE_API_KEY_ENV": "OMNIROUTE_API_KEY",
                "JARVIS_OMNIROUTE_MODEL": "auto",
            },
            clear=False,
        ):
            target = CloudModelRouter.omniroute_target()
        self.assertEqual(target.base_url, "http://127.0.0.1:20128/v1")
        self.assertTrue(target.is_loopback)
        self.assertEqual(target.model, "auto")

    def test_probe_uses_models_endpoint_and_optional_auth(self) -> None:
        connection = OmniRouteConnection("http://127.0.0.1:20128/v1", "OMNIROUTE_API_KEY")
        with patch.dict(os.environ, {"OMNIROUTE_API_KEY": "test-key"}):
            with patch("quality_of_life.omniroute.urllib.request.urlopen") as urlopen:
                response = urlopen.return_value.__enter__.return_value
                response.status = 200
                response.read.return_value = b"{\"data\":[]}"
                self.assertTrue(connection.probe())
                request = urlopen.call_args.args[0]
                self.assertEqual(request.full_url, "http://127.0.0.1:20128/v1/models")
                self.assertEqual(request.get_header("Authorization"), "Bearer test-key")

    def test_loopback_aliases_are_supported(self) -> None:
        self.assertTrue(is_loopback_hostname("localhost"))
        self.assertTrue(is_loopback_hostname("127.0.0.2"))
        self.assertTrue(is_loopback_hostname("::1"))
        self.assertFalse(is_loopback_hostname("example.com"))

    def test_autostart_overrides_inherited_port(self) -> None:
        connection = OmniRouteConnection("http://127.0.0.1:20129/v1", "OMNIROUTE_API_KEY")
        with patch("quality_of_life.omniroute.shutil.which", return_value="omniroute"):
            with patch("quality_of_life.omniroute.subprocess.Popen") as popen:
                self.assertTrue(connection._start())
                self.assertEqual(popen.call_args.kwargs["env"]["PORT"], "20129")

    def test_non_loopback_http_remains_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ProviderTarget("bad", "http://example.com/v1", "KEY", "auto")


if __name__ == "__main__":
    unittest.main()
