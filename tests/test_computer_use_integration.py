import unittest
from unittest.mock import Mock

from quality_of_life.agent_orchestrator import AgentOrchestrator
from quality_of_life.orchestration import RequestProfile


class _Router:
    def complete(self, messages):
        return '{"action":"done","arguments":{}}', "mock"

    def complete_profiled(self, messages, profile):
        return '{"action":"done","arguments":{}}', "mock"


class _Runtime:
    def __init__(self):
        self.confirmation = None
        self.policy = Mock()
        self.policy.needs_confirmation.return_value = False
        self._computer = Mock()
        self._screen = Mock()
        self._screen.capture_png.return_value = b"png"

    def _tool(self, name):
        return self._computer if name == "computer" else self._screen

    def dispatch(self, *args, **kwargs):
        return None


class ComputerUseIntegrationTests(unittest.TestCase):
    def test_general_desktop_goal_uses_goal_agent(self):
        runtime = _Runtime()
        orchestrator = AgentOrchestrator(_Router(), runtime)
        result = orchestrator.execute("open an application and interact with its user interface")
        self.assertEqual(result.profile, RequestProfile.FAST.value)
        self.assertTrue(result.verified)


if __name__ == "__main__":
    unittest.main()
