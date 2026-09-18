import unittest

from quality_of_life.capabilities import OPERATION_CATALOG
from quality_of_life.neural_advanced import (
    FEATURES,
    LiquidEcology,
    NeuralAdvancedRuntime,
    SpatialWorkspace,
    Vector3,
)


class NeuralAdvancedRuntimeTests(unittest.TestCase):
    def test_advanced_operations_are_in_capability_catalog(self):
        names = {spec.name for spec in OPERATION_CATALOG}
        for required in ("neural.advanced.inspect", "neural.workspace.compose", "neural.cross_application.transfer", "neural.browser.research_wall", "neural.performance.sample", "neural.display.update", "neural.history.snapshot", "neural.planning.dry_run", "neural.reliability.reset", "neural.audio.event", "neural.multiuser.region", "neural.remote.region", "neural.streaming.region", "neural.simulation.run", "neural.accessibility.update"):
            self.assertIn(required, names)

    def test_feature_catalog_contains_requested_domains(self):
        expected = {
            "core_neural", "spatial_windows", "desktop_3d", "cross_application",
            "browser", "games", "performance", "performance_intelligence",
            "hardware_display", "search_navigation", "lifecycle", "memory_history",
            "planning", "reliability", "testing", "developer_tools", "remote",
            "xr", "accessibility", "simulation", "audio", "multi_user",
            "time_machine", "world_streaming", "large_world_proof",
            "advanced_analytics", "optimization_intelligence", "multi_monitor",
            "remote_computing", "xr_full", "accessibility_full", "simulation_world",
            "multi_user_shared",
        }
        self.assertTrue(expected.issubset(FEATURES))

    def test_liquid_ecology_lifecycle_and_fluid_signals(self):
        ecology = LiquidEcology(max_particles=100)
        ecology.seed([
            {"id": "a", "position": (0, 0, 0), "energy": 0.9},
            {"id": "b", "position": (1, 0, 0), "energy": 0.4},
        ])
        children = ecology.mitosis("a")
        self.assertGreaterEqual(len(children), 1)
        self.assertEqual(children[0]["phase"], "complete")
        self.assertTrue(children[0]["animation"])
        satellite = ecology.create_satellite("a")
        self.assertEqual(satellite["kind"], "satellite")
        filament = ecology.filaments(max_edges=8)
        self.assertTrue(filament)
        magnetic = ecology.magnetic_relationship("a", "b", strength=0.8)
        self.assertEqual(magnetic["kind"], "magnetic")
        growth = ecology.growth_sequence("a")
        self.assertGreaterEqual(len(growth), 2)
        event = ecology.reconnect("a", "b", strength=0.8)
        self.assertEqual(event["kind"], "reconnect")
        self.assertEqual(event["phases"][0], "detach")
        step = ecology.step(0.016, activity=0.8)
        self.assertGreater(step["energy_current"], 0.0)
        self.assertIn("ripples", step)
        self.assertIn("waves", step)
        self.assertEqual(step["fluid_environment"], "active")
        death = ecology.apoptosis("b")
        self.assertEqual(death["kind"], "apoptosis")

    def test_core_physics_commands(self):
        from quality_of_life.neural_world import NeuralWorld
        world = NeuralWorld()
        world.advanced.liquid.seed([{"id": "core-a", "position": (0, 0, 0), "energy": 0.9}, {"id": "core-b", "position": (1, 0, 0), "energy": 0.6}])
        reorganized = world.neural_advanced_command("core", "reorganize", {"priorities": {"coding": 0.9, "browser": 0.4}})
        self.assertEqual(reorganized["kind"], "core.reorganization")
        children = world.neural_advanced_command("core", "mitosis", {"id": "core-a"})
        self.assertTrue(children["events"])
        self.assertTrue(world.neural_advanced_command("core", "satellite", {"id": "core-a"})["id"])
        self.assertEqual(world.neural_advanced_command("core", "magnetic", {"source": "core-a", "target": "core-b"})["kind"], "magnetic")
        self.assertEqual(world.neural_advanced_command("fluid", "tick", {"activity": 0.7})["fluid_environment"], "active")

    def test_spatial_workspace_composition(self):
        workspace = SpatialWorkspace()
        for i in range(4):
            workspace.upsert(f"w{i}", f"Window {i}", position=(0, 0, 0))
        workspace.group("g1", ["w0", "w1", "w2"])
        workspace.stack("s1", ["w0", "w1"])
        workspace.tile(["w0", "w1", "w2", "w3"], columns=2)
        workspace.snap("w0", anchor="top-left")
        moved = workspace.move_group("g1", Vector3(10, 5, 1))
        resized = workspace.resize_group("g1", 1.1)
        rotated = workspace.rotate_group("g1", Vector3(0, 0.2, 0))
        hidden = workspace.hide_group("g1", True)
        wall = workspace.giant_wall(["w0", "w1", "w2"])
        workspace.jiggle("w0", impulse=0.2, phase=1.0)
        workspace.elastic_move("w1", Vector3(100, 80, 2), stiffness=0.5)
        workspace.tether("w2", "w0", rest_length=100)
        workspace.freeform("w3", rotation=Vector3(0, 0.2, 0))
        wall_nav = workspace.navigate_wall("display-1", dx=20)
        transition = workspace.transition("3d", preserve_focus=True)
        collision = workspace.collision_report()
        self.assertEqual(len(moved), 3)
        self.assertEqual(len(resized), 3)
        self.assertEqual(len(rotated), 3)
        self.assertEqual(len(hidden), 3)
        self.assertEqual(len(wall), 3)
        self.assertEqual(transition["to"], "3d")
        self.assertEqual(wall_nav["camera_offset"]["x"], 20.0)
        self.assertIn("occlusion_pairs", collision)

    def test_runtime_learning_history_planning_and_recovery(self):
        runtime = NeuralAdvancedRuntime()
        snapshot = {
            "entities": [
                {"id": "n1", "kind": "application", "label": "Opera GX", "source": "browser", "energy": 0.8, "position": [0, 0, 0]},
                {"id": "n2", "kind": "task", "label": "Build", "source": "workflow", "energy": 0.6, "position": [1, 0, 0]},
            ],
            "relations": [{"source": "n1", "target": "n2", "relation_type": "uses", "strength": 0.7}],
        }
        observed = runtime.observe_snapshot(snapshot)
        self.assertIn("physics", observed)
        runtime.history.bookmark("home", {"layout": "home"})
        runtime.history.save_snapshot("t1", snapshot)
        runtime.history.save_snapshot("t2", {"layout": {"mode": "3d"}, "windows": ["n1"]})
        compared = runtime.time_machine(compare=("t1", "t2"))
        self.assertEqual(compared["mode"], "compare")
        dry = runtime.planner.dry_run([{"operation": "window.move"}, {"operation": "file.delete"}], known_good=snapshot)
        self.assertTrue(dry["safe_simulation"])
        self.assertTrue(dry["restorable"])
        runtime.reliability.sleep()
        wake = runtime.reliability.wake()
        self.assertFalse(wake["state"]["sleeping"])
        migrated = runtime.reliability.migrate({"schema_version": 1}, 1)
        self.assertEqual(migrated["schema_version"], 3)

    def test_cross_app_profiles_performance_display_remote_audio_and_streaming(self):
        runtime = NeuralAdvancedRuntime()
        suggestions = runtime.cross_app.suggest("artifact", "build:Jarvis", destinations=["workflow:release", "browser:research", "repository:main"])
        self.assertTrue(suggestions)
        transfer = runtime.cross_app.transfer("artifact", "build:Jarvis", "workflow:release")
        self.assertEqual(transfer["status"], "accepted")
        runtime.profile_learning("browser", "Opera GX", gpu=0.4, ram=0.5)
        runtime.profile_learning("game", "Minecraft", fps=120)
        runtime.performance.sample(cpu=20, ram=35, gpu=40, vram=30, disk=4, network=2, frame_ms=8.3, thermal=0.2, battery=0.9)
        analytics = runtime.performance.analytics()
        self.assertEqual(analytics["frame_time"]["count"], 1)
        self.assertEqual(runtime.performance.resource_heatmap("frame_ms")["count"], 1)
        self.assertEqual(runtime.performance.regression_alerts(frame_limit_ms=40), [])
        display = runtime.displays.upsert("monitor-1", width=3440, height=1440, refresh_hz=165)
        self.assertEqual(display["refresh_hz"], 165)
        runtime.displays.save_arrangement()
        remote = runtime.remote.upsert("pc-2", process_count=14, cpu=22)
        self.assertEqual(remote["id"], "pc-2")
        audio = runtime.audio.emit("search", position=(1, 2, 3), intensity=0.7)
        self.assertTrue(audio["spatial"])
        queued = runtime.streaming.request("region:alpha", priority=0.9)
        self.assertEqual(queued["status"], "queued")
        pumped = runtime.streaming.pump()
        self.assertEqual(pumped["loaded_count"], 1)

    def test_multiuser_accessibility_and_simulation(self):
        runtime = NeuralAdvancedRuntime()
        profile = runtime.multi_user.profile("user-a", accent="blue")
        region = runtime.multi_user.region("brain:team", owner="user-a", shared=True, members=["user-b"])
        settings = runtime.xr_accessibility.update(reduced_motion=True, text_scale=1.2, vr=True)
        benchmark = runtime.simulation_run("neurons", count=200)
        self.assertEqual(profile["workspace"], "workspace:user-a")
        self.assertTrue(region["shared"])
        self.assertTrue(settings["accessibility"]["reduced_motion"])
        self.assertTrue(settings["xr"]["vr"])
        self.assertEqual(benchmark["scenario"], "massive_neurons")

    def test_advanced_snapshot_is_serializable(self):
        runtime = NeuralAdvancedRuntime()
        payload = runtime.snapshot()
        self.assertEqual(payload["schema_version"], 3)
        self.assertIn("features", payload)
        self.assertIn("performance", payload)
        self.assertIn("workspace", payload)


    def test_advanced_runtime_can_be_invoked_through_guarded_runtime_dispatch(self):
        from quality_of_life.permissions import Capability, CapabilityPolicy
        from quality_of_life.runtime import JarvisRuntime
        from quality_of_life.neural_world import NeuralWorld

        runtime = JarvisRuntime(CapabilityPolicy())
        world = NeuralWorld()
        runtime.set_neural_world_service(world)
        result = runtime.dispatch(Capability.SYSTEM_DIAGNOSTICS, "neural.advanced.inspect")
        self.assertIn("performance", result)


if __name__ == "__main__":
    unittest.main()
