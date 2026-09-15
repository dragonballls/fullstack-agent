from quality_of_life.capabilities import operation
from quality_of_life.manifest import default_registry


def test_hand_control_operations_are_cataloged():
    assert operation("hand_control.start").capability.value == "mouse.control"
    assert operation("hand_control.stop").capability.value == "mouse.control"


def test_hand_control_tool_is_discoverable():
    registry = default_registry()
    assert "hand_control" in registry.names()
