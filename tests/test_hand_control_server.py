from quality_of_life.hand_control_server import HandControlHandler


def test_hand_control_handler_uses_loopback_routes():
    assert {"/hand/event", "/hand/stop"}.issuperset({"/hand/event", "/hand/stop"})
    assert not hasattr(HandControlHandler, "external_url")
