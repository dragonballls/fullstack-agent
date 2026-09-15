import unittest

from quality_of_life.orchestration import RequestProfile, build_plan, classify_request


class MultiAIOrchestrationContractTests(unittest.TestCase):
    def test_simple_request_uses_fast_profile(self):
        self.assertIs(classify_request("what time is it"), RequestProfile.FAST)

    def test_code_request_uses_coding_profile(self):
        self.assertIs(classify_request("fix the failing pytest and run the tests"), RequestProfile.CODING)

    def test_pc_repair_request_uses_maintenance_profile(self):
        self.assertIs(classify_request("diagnose my PC and safely fix the problems"), RequestProfile.MAINTENANCE)

    def test_screen_understanding_uses_vision_profile(self):
        self.assertIs(classify_request("look at my screen and tell me what is wrong"), RequestProfile.VISION)

    def test_fast_plan_has_one_primary_call(self):
        plan = build_plan("open my browser", RequestProfile.FAST)
        self.assertIs(plan.primary.profile, RequestProfile.FAST)
        self.assertEqual(plan.parallel_tasks, ())

    def test_maintenance_plan_can_parallelize_read_only_inspection(self):
        plan = build_plan("diagnose and fix my PC", RequestProfile.MAINTENANCE)
        self.assertEqual(
            {task.kind for task in plan.parallel_tasks},
            {"pc_diagnostics", "process_snapshot"},
        )


if __name__ == "__main__":
    unittest.main()
