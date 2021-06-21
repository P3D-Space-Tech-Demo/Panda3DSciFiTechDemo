from panda3d.core import Shader

from Section3.GameObject import GameObject

from Section3.CommonValues import *
from Section3.Common import Common

class Item(GameObject):
    def __init__(self, pos, auraModel, contents):
        GameObject.__init__(self, pos, auraModel, None, 100, 0, "item", 1, 0)

        self.actor.setBillboardAxis()
        self.actor.setTransparency(True)
        self.actor.setLightOff(1)

        self.weaponCollider.node().setFromCollideMask(0)
        self.weaponCollider.node().setIntoCollideMask(MASK_FROM_PLAYER)
        self.weaponCollider.node().modifySolid(0).setTangible(False)
        self.weaponCollider.setZ(-self.height*0.5)

        self.contents = contents
        self.contents.root.setPos(pos)

    def collected(self, collector):
        self.contents.root.detachNode()

        if hasattr(self.contents, "onCollection"):
            self.contents.onCollection(collector)

        self.health = 0

        if Common.framework.currentLevel is not None:
            if self in Common.framework.currentLevel.items:
                Common.framework.currentLevel.items.remove(self)

        self.cleanup()

    def cleanup(self):
        if self.contents is not None:
            self.contents.cleanup()
            self.contents = None

        GameObject.cleanup(self)
