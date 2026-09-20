from pathlib import Path
import tempfile
import unittest

from quality_of_life.personas import (
    PersonaConversation,
    PersonaStore,
    PersonaVoice,
    extract_addressed_persona,
    extract_group_start,
)


class FakeController:
    class Result:
        def __init__(self, text="Jarvis reply", needs_confirmation=False):
            self.text = text
            self.needs_confirmation = needs_confirmation

    def __init__(self):
        self.calls = []

    def execute_request(self, text, confirmed=False):
        self.calls.append((text, confirmed))
        return self.Result(f"Jarvis heard: {text}")


class FakeRouter:
    def __init__(self):
        self.calls = []

    def complete_profiled(self, messages, profile):
        self.calls.append((messages, profile))
        system = messages[0]["content"]
        persona = system.split("\n", 1)[0].removeprefix("You are ").rstrip(".")
        return (f"{persona} response", "fake")


class PersonaTests(unittest.TestCase):
    def make_store(self):
        self.tmp = tempfile.TemporaryDirectory()
        return PersonaStore(Path(self.tmp.name) / "personas.json")

    def tearDown(self):
        if hasattr(self, "tmp"):
            self.tmp.cleanup()

    def test_create_persists_locked_rules_and_voice(self):
        store = self.make_store()
        created = store.create_or_update(
            name="Nova",
            description="Analytical and concise.",
            locked_rules=["Always be analytical.", "Never claim an unverified action."],
            voice=PersonaVoice(provider="kokoro", voice_id="af_sarah", speed=1.1, description="Clear and measured."),
        )
        reopened = PersonaStore(store.path).get("nova")
        self.assertEqual(created.locked_rules, reopened.locked_rules)
        self.assertEqual(reopened.voice.voice_id, "af_sarah")
        self.assertEqual(reopened.voice.speed, 1.1)

    def test_jarvis_is_protected(self):
        store = self.make_store()
        with self.assertRaises(ValueError):
            store.create_or_update(name="Jarvis", description="replacement")
        with self.assertRaises(ValueError):
            store.delete("Jarvis")

    def test_addressed_persona_and_switch_parser(self):
        store = self.make_store()
        store.create_or_update(name="Nova", description="Analytical")
        addressed, body = extract_addressed_persona("Hey Nova, summarize this.", store.list())
        self.assertEqual(addressed, "Nova")
        self.assertEqual(body, "summarize this.")
        addressed, body = extract_addressed_persona("Jarvis, hello.", store.list())
        self.assertEqual(addressed, "Jarvis")
        self.assertEqual(body, "hello.")

    def test_group_parser_requires_multiple_known_names_and_dialogue_word(self):
        store = self.make_store()
        store.create_or_update(name="Nova", description="Analytical")
        store.create_or_update(name="Echo", description="Creative")
        names, topic = extract_group_start("Have Jarvis and Nova chat with Echo about reliability.", store.list())
        self.assertEqual(names, ["Jarvis", "Nova", "Echo"])
        self.assertEqual(topic, "reliability")

    def test_custom_persona_uses_router_and_keeps_locked_rules_in_system_message(self):
        store = self.make_store()
        store.create_or_update(
            name="Nova",
            description="Calm analyst.",
            locked_rules=["Never omit uncertainty."],
        )
        controller = FakeController()
        router = FakeRouter()
        service = PersonaConversation(controller, router=router, store=store)
        response = service.respond("Nova, explain the issue.")
        self.assertEqual(response.speaker, "Nova")
        self.assertIn("Never omit uncertainty.", router.calls[0][0][0]["content"])
        self.assertEqual(controller.calls, [])

    def test_active_jarvis_preserves_existing_controller(self):
        store = self.make_store()
        controller = FakeController()
        service = PersonaConversation(controller, router=FakeRouter(), store=store)
        response = service.respond("do the normal Jarvis thing")
        self.assertEqual(response.speaker, "Jarvis")
        self.assertEqual(controller.calls, [("do the normal Jarvis thing", False)])

    def test_group_session_gives_each_participant_a_turn(self):
        store = self.make_store()
        store.create_or_update(name="Nova", description="Analytical")
        store.create_or_update(name="Echo", description="Creative")
        service = PersonaConversation(FakeController(), router=FakeRouter(), store=store)
        service.start_group(["Jarvis", "Nova", "Echo"], "reliability")
        response = service.respond("What matters most?")
        self.assertTrue(response.group_active)
        self.assertEqual([turn.persona for turn in response.turns], ["Jarvis", "Nova", "Echo"])

    def test_group_session_can_stop(self):
        store = self.make_store()
        store.create_or_update(name="Nova", description="Analytical")
        service = PersonaConversation(FakeController(), router=FakeRouter(), store=store)
        service.start_group(["Jarvis", "Nova"], "testing")
        self.assertTrue(service.state()["group_active"])
        service.stop_group()
        self.assertFalse(service.state()["group_active"])


if __name__ == "__main__":
    unittest.main()
