from quality_of_life.hand_control import HandControlBridge, HandEvent


def test_bridge_is_disabled_by_default():
    bridge = HandControlBridge(enabled=False)
    assert bridge.dispatch(HandEvent(kind="move", x=0.2, y=0.4)) is False
