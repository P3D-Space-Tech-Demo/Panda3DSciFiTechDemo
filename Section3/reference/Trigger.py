
from Section3.CommonValues import *

class Trigger():
    def __init__(self, callbackName, nodePath, onlyOnce, active):
        self.callbackName = callbackName
        self.nodePath = nodePath
        self.onlyOnce = onlyOnce
        self.active = active

        self.colliderNPs = []

        colliders = nodePath.findAllMatches("**/+CollisionNode")
        for np in colliders:
            np.setPythonTag(TAG_OWNER, self)
            np.node().setFromCollideMask(0)
            np.node().setIntoCollideMask(MASK_FROM_PLAYER)
            np.setName("trigger")
            self.colliderNPs.append(np)

    def destroy(self):
        for np in self.colliderNPs:
            np.clearPythonTag(TAG_OWNER)
        self.colliderNPs = []

        if self.nodePath is not None:
            self.nodePath.removeNode()
            self.nodePath = None