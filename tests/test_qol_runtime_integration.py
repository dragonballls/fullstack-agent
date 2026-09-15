import unittest

from quality_of_life.gods_eye import GeoPoint, LocationSnapshot, Place
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


class FakeComputer:
    def __init__(self): self.calls = []
    def move(self, x, y): self.calls.append(("move", x, y))
    def click(self, button="left", clicks=1): self.calls.append(("click", button, clicks))
    def scroll(self, amount): self.calls.append(("scroll", amount))
    def type_text(self, text): self.calls.append(("type_text", text))
    def hotkey(self, *keys): self.calls.append(("hotkey", keys))
    def open_app(self, command, *args): self.calls.append(("open_app", command, args))


class FakeScreen:
    def capture(self, output=None): return b"rgb"


class FakeClipboard:
    def read(self): return "clipboard"
    def write(self, text): return None


class FakeWindows:
    def list_windows(self): return [{"handle": 1, "title": "Jarvis"}]
    def focus_window(self, identifier): return identifier
    def minimize_window(self, identifier): return identifier
    def maximize_window(self, identifier): return identifier
    def close_window(self, identifier): return identifier


class FakeBrowser:
    def open_url(self, url): return url


class FakeBackground:
    def start(self, name, task): return name
    def cancel(self, name): return True
    def active(self): return ()


class FakeRouter:
    def complete(self, messages): return "ok", "fake"


class FakeEye:
    def __init__(self):
        self.place = Place("Tokyo", GeoPoint(35.6762, 139.6503), "tokyo", "fake")
    def search(self, query): return [self.place]
    def locate_me(self): return LocationSnapshot(GeoPoint(34.1, -117.7), 20, True, "fake")
    def open_place(self, place): return {"surface": "gods-eye", "place": place.as_dict()}
    def route(self, origin, destination): return {"origin": origin.as_dict(), "destination": destination.point.as_dict()}


class QoLRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self):
        allowed = frozenset(Capability)
        self.policy = CapabilityPolicy(allowed=allowed)
        self.confirm = lambda *_: True
        self.runtime = JarvisRuntime(
            self.policy,
            confirmation=self.confirm,
            factories={
                "computer": FakeComputer,
                "screen": FakeScreen,
                "clipboard": FakeClipboard,
                "windows": FakeWindows,
                "browser": FakeBrowser,
                "background": FakeBackground,
                "cloud_router": FakeRouter,
                "gods_eye": FakeEye,
            },
        )

    def test_every_runtime_family_has_a_reachable_action(self):
        self.assertEqual(self.runtime.dispatch(Capability.MOUSE_CONTROL, "computer.move", x=3, y=4), None)
        self.assertEqual(self.runtime.dispatch(Capability.SCREEN_READ, "screen.capture"), b"rgb")
        self.assertEqual(self.runtime.dispatch(Capability.CLIPBOARD, "clipboard.read"), "clipboard")
        self.assertEqual(self.runtime.dispatch(Capability.WINDOW_CONTROL, "windows.list"), [{"handle": 1, "title": "Jarvis"}])
        self.assertEqual(self.runtime.dispatch(Capability.BROWSER_CONTROL, "browser.open_url", url="https://example.com"), "https://example.com")
        self.assertEqual(self.runtime.dispatch(Capability.BACKGROUND_JOBS, "background.active"), ())
        self.assertEqual(self.runtime.dispatch(Capability.CLOUD_ROUTING, "cloud_router.complete", messages=[]), ("ok", "fake"))
        self.assertEqual(self.runtime.dispatch(Capability.LOCATION_READ, "gods_eye.open_place", query="Tokyo")["surface"], "gods-eye")
        self.assertEqual(self.runtime.dispatch(Capability.LOCATION_READ, "gods_eye.route_to", query="Tokyo")["origin"], {"latitude": 34.1, "longitude": -117.7})
