from __future__ import annotations

import unittest

from quality_of_life.api_tools import ApiEndpoint, ApiToolAdapter


class ApiToolTests(unittest.TestCase):
    def test_unknown_endpoint_is_rejected(self):
        adapter = ApiToolAdapter(())
        result = adapter.invoke("api.request.read", {"endpoint": "missing", "path": "/v1"})
        self.assertFalse(result["ok"])
        self.assertIn("unknown", result["error"])

    def test_path_traversal_is_rejected(self):
        endpoint = ApiEndpoint("fixture", "https://example.com/api", allowed_paths=("/v1",))
        adapter = ApiToolAdapter((endpoint,))
        result = adapter.invoke("api.request.read", {"endpoint": "fixture", "path": "/v1/../secret"})
        self.assertFalse(result["ok"])
        self.assertIn("allowlisted", result["error"])

    def test_endpoint_requires_https(self):
        with self.assertRaises(ValueError):
            ApiToolAdapter((ApiEndpoint("bad", "http://example.com"),))


if __name__ == "__main__":
    unittest.main()
