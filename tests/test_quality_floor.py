from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from quality_of_life.quality_floor import (
    DEFAULT_QUALITY_FLOOR,
    UI_QUALITY_LADDER,
    QualityFloorError,
    compare_to_baseline,
    verify_tree,
)


class QualityFloorTests(unittest.TestCase):
    def test_ladder_is_monotonic_and_current_floor_is_verified(self):
        self.assertEqual(tuple(UI_QUALITY_LADDER), (1, 2, 3, 4, 5))
        self.assertEqual(DEFAULT_QUALITY_FLOOR["product_quality_level"], 4)
        self.assertEqual(DEFAULT_QUALITY_FLOOR["ui_minimum_level"], 4)

    def test_lower_product_floor_is_rejected(self):
        current = json.loads(json.dumps(DEFAULT_QUALITY_FLOOR))
        current["product_quality_level"] = 3
        with self.assertRaisesRegex(QualityFloorError, "Product quality level was lowered"):
            compare_to_baseline(current, DEFAULT_QUALITY_FLOOR)

    def test_lower_ui_floor_is_rejected(self):
        current = json.loads(json.dumps(DEFAULT_QUALITY_FLOOR))
        current["ui_minimum_level"] = 3
        with self.assertRaisesRegex(QualityFloorError, "UI minimum quality level was lowered"):
            compare_to_baseline(current, DEFAULT_QUALITY_FLOOR)

    def test_looser_performance_budget_is_rejected(self):
        current = json.loads(json.dumps(DEFAULT_QUALITY_FLOOR))
        current["performance"]["max_ui_build_bytes"] += 1
        with self.assertRaisesRegex(QualityFloorError, "Performance budget was weakened"):
            compare_to_baseline(current, DEFAULT_QUALITY_FLOOR)

    def test_required_contracts_cannot_be_removed(self):
        current = json.loads(json.dumps(DEFAULT_QUALITY_FLOOR))
        current["required_files"] = current["required_files"][:-1]
        with self.assertRaisesRegex(QualityFloorError, "Required quality-floor files were removed"):
            compare_to_baseline(current, DEFAULT_QUALITY_FLOOR)

    def test_real_repository_meets_the_quality_floor(self):
        result = verify_tree(Path(__file__).resolve().parents[1])
        self.assertTrue(result["ok"])
        self.assertEqual(result["product_quality_level"], 4)
        self.assertEqual(result["ui_minimum_level"], 4)

    def test_quality_floor_cli_passes_from_repository_root(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [__import__("sys").executable, "scripts/verify_quality_floor.py"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
