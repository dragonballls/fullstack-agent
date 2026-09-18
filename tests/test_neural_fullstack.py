import json
import time
import unittest

from quality_of_life.neural_advanced import FEATURES
from quality_of_life.neural_fullstack import (
    FULLSTACK_EXECUTION_DOMAINS,
    FULLSTACK_EXECUTOR_BINDINGS,
    FullStackNeuralExperience,
)


class NeuralFullStackTests(unittest.TestCase):
    def test_every_advanced_feature_category_has_a_concrete_executor(self):
        self.assertEqual(set(FEATURES), set(FULLSTACK_EXECUTION_DOMAINS))
        self.assertEqual(set(FEATURES), set(FULLSTACK_EXECUTOR_BINDINGS))
        runtime = FullStackNeuralExperience()
        matrix = runtime.feature_execution_matrix(FEATURES)
        self.assertEqual(matrix["status"], "implemented")
        self.assertEqual(matrix["unbound_domains"], [])
        self.assertEqual(matrix["feature_count"], sum(len(values) for values in FEATURES.values()))
        for domain, values in matrix["domains"].items():
            self.assertEqual(values["status"], "implemented")
            self.assertEqual(values["feature_count"], len(FEATURES[domain]))
            self.assertIn(values["executor_attribute"], set(FULLSTACK_EXECUTOR_BINDINGS.values()))

    def test_audio_voice_directional_and_game_priority_paths(self):
        runtime = FullStackNeuralExperience()
        voice = runtime.command(
            "audio",
            "speak",
            {"text": "Neural systems online", "position": (4, 2, 8)},
        )
        self.assertEqual(voice["event"]["kind"], "voice")
        self.assertGreater(voice["direction"]["azimuth"], 0)
        self.assertEqual(voice["playback"], "queued")
        runtime.command("audio", "configure", {"performance_mode": "low", "game_priority": True})
        game = runtime.command("audio", "event", {"kind": "game", "position": (-2, 0, 4)})
        ambient = runtime.command("audio", "event", {"kind": "ambient", "intensity": 1.0})
        self.assertGreater(game["gain"], ambient["gain"])

    def test_multiuser_regions_layout_pinning_and_resources(self):
        runtime = FullStackNeuralExperience()
        profile = runtime.multi_user.profile("alice", theme="jarvis", voice="spatial")
        runtime.multi_user.set_layout("alice", {"mode": "3d", "workspace": "main"})
        runtime.multi_user.pin_neuron("alice", "neuron:1")
        region = runtime.multi_user.region("brain:shared", owner="alice", shared=True, members=["bob"])
        resource = runtime.multi_user.resource(
            "voice-engine",
            owner="alice",
            shared=True,
            controls={"read": True, "write": False},
        )
        self.assertEqual(profile["user_id"], "alice")
        self.assertIn("neuron:1", runtime.multi_user.snapshot()["profiles"]["alice"]["pinned_neurons"])
        self.assertEqual(set(region["members"]), {"alice", "bob"})
        self.assertFalse(resource["controls"]["write"])

    def test_time_machine_compare_replay_timeline_and_performance(self):
        runtime = FullStackNeuralExperience()
        runtime.history.capture("a", {"performance": {"frame_ms": 20.0}, "neuron": 1})
        runtime.history.capture("b", {"performance": {"frame_ms": 30.0}, "neuron": 2})
        diff = runtime.history.compare("a", "b")
        replay = runtime.history.replay("b")
        ui = runtime.command("time_machine", "interface")
        self.assertTrue(any(change["path"] == "neuron" for change in diff["changes"]))
        self.assertTrue(replay["replay"]["world_restore"])
        self.assertIn("timeline", ui["interface"]["controls"])
        self.assertEqual(runtime.history.performance_analytics()["frame_ms_max"], 30.0)

    def test_world_streaming_index_cache_async_worker_and_unload(self):
        runtime = FullStackNeuralExperience()
        runtime.streaming.index("r1", (64, 0, 96))
        runtime.streaming.request("r1", priority=0.9)
        runtime.command("world_streaming", "pump", {"budget": 1})
        self.assertEqual(runtime.streaming.snapshot()["loaded"][0]["region_id"], "r1")
        runtime.command("world_streaming", "unload", {"id": "r1"})
        self.assertEqual(runtime.streaming.snapshot()["cache"][0]["region_id"], "r1")
        self.assertTrue(runtime.command("world_streaming", "start", {"interval": 0.01})["started"])
        runtime.streaming.request("r2", priority=1.0)
        try:
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                if any(item["region_id"] == "r2" for item in runtime.streaming.snapshot()["loaded"]):
                    break
                time.sleep(0.02)
            self.assertTrue(any(item["region_id"] == "r2" for item in runtime.streaming.snapshot()["loaded"]))
        finally:
            runtime.command("world_streaming", "stop")

    def test_graphics_pipeline_and_adaptive_render_policy(self):
        runtime = FullStackNeuralExperience()
        caps = runtime.graphics.capabilities(zero_copy=True, variable_rate_shading=True)
        self.assertTrue(caps["zero_copy"])
        policy = runtime.graphics.optimize(
            gpu_pressure=0.85, frame_ms=36.0, memory_pressure=0.9, task="windows"
        )
        self.assertEqual(policy["capture"], "on_demand")
        self.assertEqual(policy["vrs"], "enabled")
        runtime.graphics.reserve("vram_mb", 128)
        self.assertEqual(runtime.graphics.frame_policy()["reserved"]["vram_mb"], 128)

    def test_cross_application_browser_game_and_remote_paths(self):
        runtime = FullStackNeuralExperience()
        transfer = runtime.command(
            "cross_application",
            "transfer",
            {"kind": "code", "source": "editor", "destination": "browser", "payload": "print(1)"},
        )
        suggestion = runtime.command(
            "cross_application",
            "suggest",
            {"kind": "artifact", "source": "build", "destinations": ["browser", "release-artifacts"]},
        )
        browser = runtime.command(
            "browser", "research_wall", {"id": "wall", "pages": ["https://a", "https://b"]}
        )
        game = runtime.command(
            "games", "learn", {"name": "Minecraft", "metrics": {"fps": 90}}
        )
        app = runtime.command(
            "remote_computing",
            "application",
            {"id": "app1", "machine_id": "pc2", "state": {"status": "running"}},
        )
        with self.assertRaises(PermissionError):
            runtime.command("remote_computing", "control", {"id": "app1", "confirmed": False})
        controlled = runtime.command(
            "remote_computing", "control", {"id": "app1", "confirmed": True}
        )
        self.assertTrue(transfer["semantic"])
        self.assertTrue(suggestion["suggestions"])
        self.assertTrue(browser["side_by_side"])
        self.assertEqual(game["samples"], 1)
        self.assertEqual(controlled["control"], "authorized")
        self.assertEqual(app["machine_id"], "pc2")

    def test_organism_spatial_performance_optimization_display_xr_and_simulation(self):
        runtime = FullStackNeuralExperience()
        runtime.organism.seed(["n1", "n2", "n3"])
        organism = runtime.command("core_neural", "evolve", {"activity": 0.9})
        self.assertGreaterEqual(organism["cells"], 3)
        self.assertEqual(runtime.command("core_neural", "filaments", {"limit": 10})["filaments"], [])
        runtime.command("spatial_windows", "surface", {"id": "w1", "state": {"position": [0, 0, 0]}})
        runtime.command("desktop_3d", "focus", {"id": "w1"})
        transition = runtime.command(
            "desktop_3d", "transition", {"mode": "3d", "preserve_focus": True}
        )
        self.assertEqual(transition["to"], "3d")
        runtime.performance.sample(frame_ms=18.0, ram_mb=100.0, network_mb=4.0, vram_mb=300.0)
        runtime.performance.sample(frame_ms=20.0, ram_mb=112.0, network_mb=5.0, vram_mb=315.0)
        self.assertTrue(runtime.performance.heatmap("frame_ms")["bins"])
        self.assertEqual(runtime.performance.long_session_profile()["ram_growth"], 12.0)
        opt = runtime.optimization.apply(
            "app", "reduce_glow", before_state={"quality": "high"}, after_state={"quality": "adaptive"}
        )
        self.assertTrue(opt["rollback_available"])
        self.assertTrue(runtime.optimization.rollback("app")["rolled_back"])
        runtime.displays.upsert(
            "main", width=3440, height=1440, dpi=125, refresh_hz=144, x=0, y=0
        )
        runtime.displays.upsert(
            "second", width=1920, height=1080, dpi=100, refresh_hz=60, x=3440, y=0,
            orientation="portrait",
        )
        placement = runtime.displays.placement(
            "main", (1720, 720), target_display="second"
        )
        self.assertEqual(placement["refresh_hz"], 60)
        settings = runtime.xr_accessibility.update(
            reduced_motion=True, text_scale=1.25, eye_gaze=True
        )
        self.assertTrue(settings["reduced_motion"])
        self.assertEqual(settings["text_scale"], 1.25)
        self.assertTrue(settings["eye_gaze"])
        world = runtime.command(
            "simulation_world", "create", {"id": "sandbox", "seed": 11}
        )
        populated = runtime.command(
            "simulation_world",
            "populate",
            {"id": "sandbox", "neurons": 32, "windows": 12, "tasks": 4, "relationships": 64},
        )
        proof = runtime.command(
            "large_world_proof", "benchmark", {"scenario": "neurons", "count": 5000}
        )
        self.assertTrue(world["isolated"])
        self.assertEqual(populated["neurons"], 32)
        self.assertEqual(proof["count"], 5000)

    def test_full_snapshot_is_json_serializable(self):
        runtime = FullStackNeuralExperience()
        runtime.multi_user.profile("alice")
        runtime.audio.speak("hello")
        runtime.history.capture("s1", {"performance": {"frame_ms": 16.6}})
        json.dumps(runtime.snapshot(), sort_keys=True)


if __name__ == "__main__":
    unittest.main()
