from panda3d.core import Shader

from Section3.GameObject import GameObject

from Section3.CommonValues import *
import common

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

        if common.currentSection.currentLevel is not None:
            if self in common.currentSection.currentLevel.items:
                common.currentSection.currentLevel.items.remove(self)

        self.destroy()

    def destroy(self):
        if self.contents is not None:
            self.contents.destroy()
            self.contents = None

        GameObject.destroy(self)
