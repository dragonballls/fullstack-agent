import os
import unittest
from unittest.mock import patch

from quality_of_life.readiness import CheckStatus, check_readiness, format_report


class ReadinessTests(unittest.TestCase):
    def test_missing_optional_integrations_are_warnings_not_required_failures(self) -> None:
        env = {}
        report = check_readiness(env=env, which=lambda _name: None, importable=lambda _name: False)
        self.assertIn(CheckStatus.WARNING, {check.status for check in report.checks})
        self.assertEqual(CheckStatus.FAIL, report.required_status)

    def test_cloud_key_presence_is_reported_without_exposing_value(self) -> None:
        env = {"OPENAI_API_KEY": "super-secret-value"}
        report = check_readiness(env=env, which=lambda _name: None, importable=lambda _name: True)
        rendered = format_report(report)
        self.assertIn("OPENAI_API_KEY", rendered)
        self.assertNotIn("super-secret-value", rendered)

    def test_present_runtime_prerequisites_can_produce_ready_report(self) -> None:
        env = {
            "OPENAI_API_KEY": "configured",
            "ELEVENLABS_API_KEY": "configured",
        }
        report = check_readiness(env=env, which=lambda _name: "available", importable=lambda _name: True)
        self.assertEqual(CheckStatus.PASS, report.required_status)
        self.assertTrue(report.ready)

    def test_unknown_provider_key_is_not_required(self) -> None:
        env = {"SOME_OTHER_CLOUD_KEY": "configured"}
        report = check_readiness(env=env, which=lambda _name: "available", importable=lambda _name: True)
        self.assertNotEqual(CheckStatus.FAIL, report.required_status)


if __name__ == "__main__":
    unittest.main()
