import unittest

from quality_of_life.readiness import CheckStatus, check_readiness, format_report


class ReadinessTests(unittest.TestCase):
    def test_missing_optional_integrations_are_warnings_not_required_failures(self) -> None:
        report = check_readiness(env={}, which=lambda _name: None, importable=lambda _name: False)
        self.assertIn(CheckStatus.WARNING, {check.status for check in report.checks})
        self.assertEqual(CheckStatus.FAIL, report.required_status)

    def test_cloud_key_presence_is_reported_without_exposing_value(self) -> None:
        report = check_readiness(env={"OPENAI_API_KEY": "super-secret-value"}, which=lambda _name: None, importable=lambda _name: True)
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

    def test_unknown_provider_key_does_not_satisfy_cloud_requirement(self) -> None:
        env = {"SOME_OTHER_CLOUD_KEY": "configured"}
        report = check_readiness(env=env, which=lambda _name: "available", importable=lambda _name: True)
        self.assertEqual(CheckStatus.FAIL, report.required_status)

    def test_custom_omniroute_key_environment_is_recognized(self) -> None:
        """Recognize a credential variable selected by the OmniRoute configuration."""
        env = {
            "JARVIS_OMNIROUTE_API_KEY_ENV": "MY_LOCAL_OMNI_KEY",
            "MY_LOCAL_OMNI_KEY": "configured",
        }
        report = check_readiness(env=env, which=lambda _name: "available", importable=lambda _name: True)
        self.assertEqual(CheckStatus.PASS, report.required_status)
        self.assertIn("MY_LOCAL_OMNI_KEY", format_report(report))

    def test_custom_cloud_key_environment_is_recognized(self) -> None:
        """Recognize a credential variable selected by explicit cloud configuration."""
        env = {
            "JARVIS_CLOUD_BASE_URL": "https://example.com/v1",
            "JARVIS_CLOUD_API_KEY_ENV": "MY_CLOUD_KEY",
            "MY_CLOUD_KEY": "configured",
        }
        report = check_readiness(env=env, which=lambda _name: "available", importable=lambda _name: True)
        self.assertEqual(CheckStatus.PASS, report.required_status)


if __name__ == "__main__":
    unittest.main()
