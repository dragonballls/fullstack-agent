from __future__ import annotations

import unittest

from quality_of_life.planner import PlanError, parse_plan, planning_prompt


class PlannerTests(unittest.TestCase):
    def test_parses_allowlisted_operation(self):
        plan = parse_plan('{"steps":[{"operation":"system.inspect","arguments":{}}]}')
        self.assertEqual(plan.steps[0].operation, "system.inspect")

    def test_rejects_shell_operations(self):
        with self.assertRaises(PlanError):
            parse_plan('{"steps":[{"operation":"powershell.exec","arguments":{"command":"Get-Process"}}]}')

    def test_rejects_more_than_eight_steps(self):
        raw = '{"steps":[' + ','.join('{"operation":"system.inspect","arguments":{}}' for _ in range(9)) + ']}'
        with self.assertRaises(PlanError):
            parse_plan(raw)

    def test_prompt_forbids_arbitrary_execution(self):
        prompt = planning_prompt("open my browser")
        self.assertIn("Never output shell commands", prompt)
        self.assertIn("browser.open_url", prompt)


if __name__ == "__main__":
    unittest.main()
