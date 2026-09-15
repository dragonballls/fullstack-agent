import unittest

from quality_of_life.computer_use import ComputerUseAgent, ComputerUseAction


class _FakeComputer:
    def __init__(self):
        self.actions = []

    def click(self, button="left", clicks=1):
        self.actions.append(ComputerUseAction("click", {"button": button, "clicks": clicks}))

    def scroll(self, amount):
        self.actions.append(ComputerUseAction("scroll", {"amount": amount}))


class _FakeObserver:
    def __init__(self):
        self.calls = 0

    def observe(self):
        self.calls += 1
        return {"screen": "application window visible"}


class ComputerUseGoalTests(unittest.TestCase):
    def test_goal_agent_replans_and_reobserves_until_done(self):
        computer = _FakeComputer()
        observer = _FakeObserver()
        calls = []

        def planner(goal, observation):
            calls.append(observation)
            if len(calls) == 1:
                return [ComputerUseAction("click", {"x": 100, "y": 200})]
            return [ComputerUseAction("done", {})]

        agent = ComputerUseAgent(planner, computer, observer, max_steps=3)
        result = agent.run("open the game shop")
        self.assertTrue(result.completed)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(computer.actions), 1)
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
            planner=lambda goal, observation: [ComputerUseAction("scroll", {"amount": 1})],
            computer=_FakeComputer(),
            observer=_FakeObserver(),
            max_steps=2,
        )
        result = agent.run("keep going")
        self.assertFalse(result.completed)
        self.assertEqual(result.steps_executed, 2)
