import unittest

from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.spatial_windows import SpatialWindowManager


class FakeUser32:
    def __init__(self):
        self.parent = {10: 0, 20: 0}
        self.visible = {10: True, 20: True}
        self.rects = {10: {"x": 100, "y": 100, "width": 800, "height": 600}, 20: {"x": 0, "y": 0, "width": 1200, "height": 800}}
        self.styles = {10: 0x80000000, 20: 0}
        self.exstyles = {10: 0, 20: 0}
    def IsWindow(self, h): return int(h) in self.parent
    def IsWindowVisible(self, h): return self.visible.get(int(h), False)
    def GetParent(self, h): return self.parent[int(h)]
    def GetWindowLongPtrW(self, h, index): return self.styles[int(h)] if index == -16 else self.exstyles[int(h)]
    def SetWindowLongPtrW(self, h, index, value):
        old=self.GetWindowLongPtrW(h,index)
        if index == -16:self.styles[int(h)]=int(value)
        else:self.exstyles[int(h)]=int(value)
        return old
    def SetParent(self, h, parent): self.parent[int(h)]=int(parent); return 1
    def SetWindowPos(self, h, _after, x, y, w, height, _flags):
        self.rects[int(h)]={"x":int(x),"y":int(y),"width":int(w),"height":int(height)}; return 1
    def GetWindowRect(self, h, rect):
        item=self.rects[int(h)]
        rect.left=item["x"];rect.top=item["y"];rect.right=item["x"]+item["width"];rect.bottom=item["y"]+item["height"];return 1


class SpatialEmbeddingTests(unittest.TestCase):
    def test_embed_and_unembed_restore_state(self):
        policy=CapabilityPolicy(allowed=frozenset({Capability.WINDOW_CONTROL}))
        manager=SpatialWindowManager(policy,user32=FakeUser32())
        manager.set_host_handle(20)
        result=manager.embed(10,x=40,y=50,width=500,height=400,confirmed=True)
        self.assertTrue(result["embedded"])
        self.assertEqual(manager.user32.parent[10],20)
        self.assertTrue(manager.embedding_state(10)["embedded"])
        manager.unembed(10,confirmed=True)
        self.assertEqual(manager.user32.parent[10],0)
        self.assertEqual(manager.user32.styles[10],0x80000000)

    def test_embedding_requires_confirmation(self):
        policy=CapabilityPolicy(allowed=frozenset({Capability.WINDOW_CONTROL}))
        manager=SpatialWindowManager(policy,user32=FakeUser32())
        manager.set_host_handle(20)
        with self.assertRaises(PermissionError):
            manager.embed(10)


if __name__=="__main__":
    unittest.main()
