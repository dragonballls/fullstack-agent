import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from quality_of_life.agent_orchestrator import AgentOrchestrator


class _Router:
    def complete(self, messages):
        return '{"action":"done","arguments":{}}', "mock"

    def complete_profiled(self, messages, profile):
        return '{"action":"done","arguments":{}}', "mock"


class _Orchestrator:
    def register(self, action):
        return None


class _Runtime:
    def __init__(self):
        self.confirmation = None
        self.orchestrator = _Orchestrator()
        self._computer = Mock()
        self._screen = Mock()
        self._screen.capture_png.return_value = b"png"
        self._applications = Mock()
        self._applications.list.return_value = (SimpleNamespace(name="Roblox"),)

    def _tool(self, name):
        return {"computer": self._computer, "screen": self._screen, "applications": self._applications}[name]

    def dispatch(self, *args, **kwargs):
        return None


class ComputerUseIntegrationTests(unittest.TestCase):
    def test_general_desktop_goal_uses_goal_agent(self):
        runtime = _Runtime()
        orchestrator = AgentOrchestrator(_Router(), runtime)
        result = orchestrator.execute("play a game using the desktop", confirmed=True)
        self.assertTrue(result.verified)
        self.assertIn("computer-use", result.providers)

    def test_installed_app_open_is_routed_to_computer_use(self):
        runtime = _Runtime()
        orchestrator = AgentOrchestrator(_Router(), runtime)
        result = orchestrator.execute("open Roblox", confirmed=True)
        self.assertTrue(result.verified)
        self.assertIn("computer-use", result.providers)
        runtime._applications.list.assert_called()


if __name__ == "__main__":
    unittest.main()
