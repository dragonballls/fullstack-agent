from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from quality_of_life.prism_gateway import PrismGateway
from quality_of_life.router import CloudModelRouter, ProviderTarget


class PrismGatewayTests(unittest.TestCase):
    def test_default_session_path_is_under_jarvis_prism_home(self) -> None:
        with patch.dict(os.environ, {"JARVIS_PRISM_HOME": str(Path("/tmp/jarvis-prism-test"))}, clear=False):
            gateway = PrismGateway()
        self.assertEqual(gateway.session_file, Path("/tmp/jarvis-prism-test/session.json"))

    def test_missing_session_fails_closed_without_network_or_process(self) -> None:
        with patch.dict(
            os.environ,
            {"JARVIS_PRISM_ENABLED": "1", "JARVIS_PRISM_SESSION": str(Path("/tmp/no-such-prism-session.json"))},
            clear=False,
        ):
            gateway = PrismGateway()
            with patch("quality_of_life.prism_gateway.urllib.request.urlopen") as urlopen:
                self.assertFalse(gateway.ensure_started())
                urlopen.assert_not_called()

    def test_disabled_bridge_fails_closed(self) -> None:
        with patch.dict(os.environ, {"JARVIS_PRISM_ENABLED": "0"}, clear=False):
            gateway = PrismGateway(session_file=Path("/tmp/irrelevant.json"))
            self.assertFalse(gateway.ensure_started())

    def test_status_declares_remote_inference(self) -> None:
        gateway = PrismGateway(session_file=Path("/tmp/no-such-prism-session.json"))
        with patch.object(gateway, "_probe", return_value=False):
            status = gateway.status()
        self.assertFalse(status["configured"])
        self.assertFalse(status["ready"])
        self.assertEqual(status["inference"], "remote")
        self.assertEqual(status["model"], "prism-astra")

    def test_router_has_loopback_prism_target(self) -> None:
        target = CloudModelRouter.prism_target()
        self.assertEqual(target.name, "prism-astra")
        self.assertEqual(target.base_url, "http://127.0.0.1:8319/v1")
        self.assertEqual(target.model, "prism-astra")
        self.assertTrue(target.is_loopback)

    def test_profiled_requests_keep_prism_model_name(self) -> None:
        router = CloudModelRouter(
            (
                CloudModelRouter.prism_target(),
                ProviderTarget("omniroute", "http://127.0.0.1:20128/v1", "OMNIROUTE_API_KEY", "auto"),
            )
        )

        response = unittest.mock.Mock()
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "prism-ready"}}]}
        ).encode()
        response.__enter__ = lambda self: self
        response.__exit__ = lambda self, exc_type, exc, tb: None

        with patch.dict(
            os.environ,
            {
                "JARVIS_PRISM_ENABLED": "1",
                "JARVIS_OMNIROUTE_FAST_MODEL": "auto/fast",
            },
            clear=False,
        ):
            with patch.object(CloudModelRouter, "_ensure_prism", return_value=True):
                with patch("quality_of_life.router.urllib.request.urlopen", return_value=response) as urlopen:
                    text, provider = router.complete_profiled(
                        [{"role": "user", "content": "hello"}], "fast"
                    )

        self.assertEqual((text, provider), ("prism-ready", "prism-astra"))
        request = urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "prism-astra")


if __name__ == "__main__":
    unittest.main()
