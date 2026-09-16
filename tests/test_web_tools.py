from __future__ import annotations

import unittest
from unittest.mock import patch

from quality_of_life.web_tools import WebToolAdapter


class WebToolTests(unittest.TestCase):
    def test_rejects_unallowlisted_host(self):
        adapter = WebToolAdapter(allowed_hosts={"example.com"})
        with self.assertRaises(ValueError):
            adapter.fetch("https://not-example.invalid/")

    def test_parse_response_marks_oversized_body(self):
        adapter = WebToolAdapter(allowed_hosts={"example.com"}, max_bytes=10)
        parsed = adapter._parse_response("x" * 25)
        self.assertTrue(parsed["truncated"])
        self.assertEqual(len(parsed["body"]), 10)

    def test_search_requires_configuration(self):
        adapter = WebToolAdapter(allowed_hosts={"example.com"})
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                adapter.search("test")


if __name__ == "__main__":
    unittest.main()
