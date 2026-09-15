import unittest

from quality_of_life.computer_use import ComputerUseAgent, ComputerUseAction


class _FakeComputer:
    def __init__(self):
        self.actions = []

    def execute(self, action):
        self.actions.append(action)
        return {"ok": True, "action": action.kind}


class _FakeObserver:
    def __init__(self):
        self.calls = 0

    def observe(self):
        self.calls += 1
        return {"screen": "Roblox window visible", "focused_app": "Roblox"}


class ComputerUseGoalTests(unittest.TestCase):
    def test_goal_agent_executes_allowlisted_plan_and_reobserves(self):
        computer = _FakeComputer()
        observer = _FakeObserver()
        agent = ComputerUseAgent(
            planner=lambda goal, observation: [
                ComputerUseAction("click", {"x": 100, "y": 200}),
                ComputerUseAction("wait", {"seconds": 0.01}),
            ],
            computer=computer,
            observer=observer,
        )
        result = agent.run("open the game shop")
        self.assertTrue(result.completed)
        self.assertEqual([item.kind for item in computer.actions], ["click", "wait"])
        self.assertEqual(observer.calls, 2)

    def test_goal_agent_rejects_unknown_actions(self):
        agent = ComputerUseAgent(
            planner=lambda goal, observation: [ComputerUseAction("powershell", {"command": "whoami"})],
            computer=_FakeComputer(),
            observer=_FakeObserver(),
        )
        with self.assertRaises(ValueError):
            agent.run("do something")

    def test_goal_agent_bounds_steps(self):
        agent = ComputerUseAgent(
            planner=lambda goal, observation: [ComputerUseAction("wait", {"seconds": 0})] * 11,
            computer=_FakeComputer(),
            observer=_FakeObserver(),
            max_steps=10,
        )
        with self.assertRaises(ValueError):
            agent.run("do lots")
