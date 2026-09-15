import os
import unittest

from quality_of_life.router import CloudModelRouter, ProviderTarget


class RouterTests(unittest.TestCase):
    def test_missing_keys_report_names_not_secret_values(self):
        router = CloudModelRouter((ProviderTarget("one", "https://one.invalid", "ONE_KEY", "m1"),))
        old = os.environ.pop("ONE_KEY", None)
        try:
            with self.assertRaisesRegex(RuntimeError, "one: missing ONE_KEY") as ctx:
                router.complete([{"role": "user", "content": "hi"}])
            self.assertNotIn("secret-value", str(ctx.exception))
        finally:
            if old is not None:
                os.environ["ONE_KEY"] = old

    def test_router_never_mentions_local_backend_as_implicit_fallback(self):
        with open("quality_of_life/router.py", encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("ollama", source.lower())

    def test_provider_order_is_preserved(self):
        router = CloudModelRouter(
            (
                ProviderTarget("first", "https://first.invalid", "FIRST_KEY", "m1"),
                ProviderTarget("second", "https://second.invalid", "SECOND_KEY", "m2"),
            )
        )
        self.assertEqual([target.name for target in router.targets], ["first", "second"])

    def test_omniroute_defaults_are_explicit_and_openai_compatible(self):
        self.assertEqual(CloudModelRouter.omniroute_base_url(), "http://127.0.0.1:20128/v1")
        self.assertEqual(CloudModelRouter.omniroute_model(), "auto")
        self.assertEqual(CloudModelRouter.omniroute_api_key_env(), "OMNIROUTE_API_KEY")

    def test_custom_system_prompt_is_injected_once_without_overwriting_existing_system_message(self):
        router = CloudModelRouter((ProviderTarget("test", "https://example.invalid", "TEST_KEY", "m1"),))
        messages = [{"role": "system", "content": "base"}, {"role": "user", "content": "hi"}]
        result = router.prepare_messages(messages, "jarvis rules")
        self.assertEqual(
            result,
            [
                {"role": "system", "content": "base\n\njarvis rules"},
                {"role": "user", "content": "hi"},
            ],
        )

    def test_provider_target_rejects_insecure_remote_http(self):
        with self.assertRaisesRegex(ValueError, "HTTPS is required for non-loopback cloud targets"):
            ProviderTarget("remote", "http://example.com/v1", "KEY", "m1")

    def test_provider_target_rejects_invalid_configuration(self):
        with self.assertRaisesRegex(ValueError, "base_url must be an absolute HTTP(S) URL"):
            ProviderTarget("bad-url", "not-a-url", "KEY", "m1")
        with self.assertRaisesRegex(ValueError, "model must be non-empty"):
            ProviderTarget("bad-model", "https://example.com/v1", "KEY", " ")

    def test_local_omniroute_does_not_require_a_bearer_key(self):
        router = CloudModelRouter((ProviderTarget("local", "http://127.0.0.1:20128/v1", "MISSING_KEY", "auto"),))
        old = os.environ.pop("MISSING_KEY", None)
        try:
            with self.assertRaisesRegex(RuntimeError, "All configured cloud targets failed: local: provider request failed"):
                router.complete([{"role": "user", "content": "hi"}])
        finally:
            if old is not None:
                os.environ["MISSING_KEY"] = old


if __name__ == "__main__":
    unittest.main()
