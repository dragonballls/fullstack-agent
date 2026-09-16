from __future__ import annotations

import unittest

from quality_of_life.planner import PlanError, parse_plan, planning_prompt


class PlannerTests(unittest.TestCase):
    def test_parses_allowlisted_operation(self):
        plan = parse_plan('{"steps":[{"operation":"system.inspect","arguments":{}}]}')
        self.assertEqual(plan.steps[0].operation, "system.inspect")

    def test_normalizes_external_account_write_to_guarded_service_action(self):
        plan = parse_plan(
            '{"steps":[{"operation":"youtube.video.upload","arguments":{"file_path":"clip.mp4","title":"Test","privacy":"private"}}]}'
        )
        self.assertEqual(plan.steps[0].operation, "accounts.service_action")
        self.assertEqual(plan.steps[0].arguments["provider"], "youtube")
        self.assertEqual(plan.steps[0].arguments["operation"], "youtube.video.upload")
        self.assertEqual(plan.steps[0].arguments["payload"]["file_path"], "clip.mp4")

    def test_account_write_rejects_wrong_provider(self):
        with self.assertRaises(PlanError):
            parse_plan(
                '{"steps":[{"operation":"youtube.video.upload","arguments":{"provider":"google","file_path":"clip.mp4","title":"Test"}}]}'
            )

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
