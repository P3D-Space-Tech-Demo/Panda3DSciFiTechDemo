
from Section2.CommonValues import *

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
            np.node().setIntoCollideMask(MASK_PLAYER_TRIGGER_DETECTOR)
            np.setName("trigger")
            self.colliderNPs.append(np)
            #np.show()
            #np.ls()
            #if hasattr(np.node(), "getRadius"):
            #    print (np.node().getRadius())

    def destroy(self):
        for np in self.colliderNPs:
            np.clearPythonTag(TAG_OWNER)
        self.colliderNPs = []

        if self.nodePath is not None:
            self.nodePath.removeNode()
            self.nodePath = None