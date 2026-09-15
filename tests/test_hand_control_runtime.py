from quality_of_life.hand_control_runtime import HandControlRuntime


def test_hand_control_runtime_starts_disabled_and_is_idempotent():
    runtime = HandControlRuntime()
    assert runtime.enabled is False
    assert runtime.start() is True
    assert runtime.enabled is True
    assert runtime.start() is True
    runtime.stop()
    assert runtime.enabled is False


def test_hand_control_runtime_reports_local_tracker_url():
    runtime = HandControlRuntime()
    assert runtime.url == "http://127.0.0.1:8795/"
    runtime.stop()
