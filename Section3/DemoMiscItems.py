from panda3d.core import PandaNode

from Section3.CommonValues import *
from Section3.Common import Common

import math

class Door():
    def __init__(self, modelNP = None):
        self.root = Common.framework.showBase.render.attachNewNode(PandaNode("obj"))

        self.isOpen = False
        self.movementTimer = 0
        self.movementDuration = 0
        self.movementSpeed = 1.5
        self.wobbleDuration = 0.3
        self.wobbleSize = 0.05

        self.height = 1.0

        self.lastZ = 0
        self.zVec = 0

        self.collisionNPs = []

        self.model = None
        self.setModel(modelNP)

    def alterHealth(self, dHealth, incomingImpulse, flinchValue, overcharge = False):
        pass

    def interact(self, interactor):
        if self.isOpen:
            self.close()
        else:
            self.open()

    def update(self, dt):
        if self.movementDuration > 0:
            self.movementTimer += dt
            if self.movementTimer < self.wobbleDuration:
                perc = math.sin(self.movementTimer * 3.142 / self.wobbleDuration)*self.wobbleSize
            else:
                perc = (self.movementTimer - self.wobbleDuration) / self.movementDuration
            if perc >= 1:
                self.movementDuration = 0
                perc = 1
            self.model.setZ(perc*self.zVec + self.lastZ)

    def open(self):
        self.isOpen = True
        self.movementTimer = 0
        self.lastZ = self.model.getZ(Common.framework.showBase.render)
        self.zVec = -self.height - self.lastZ
        self.movementDuration = abs(abs(self.lastZ) - self.height)/self.movementSpeed

    def close(self):
        self.isOpen = False
        self.movementTimer = 0
        self.lastZ = self.model.getZ(Common.framework.showBase.render)
        self.zVec = abs(self.lastZ)
        self.movementDuration = abs(self.lastZ)/self.movementSpeed

    def setModel(self, modelNP):
        self.cleanupModel()

        self.model = self.root.attachNewNode(PandaNode("model"))

        if modelNP is not None:
            modelNP.wrtReparentTo(self.model)
            bottomPt, topPt = modelNP.getTightBounds()
            self.height = abs(topPt.z - bottomPt.z) - 0.1

            collisionNPs = modelNP.findAllMatches("**/+CollisionNode")
            for np in collisionNPs:
                np.setPythonTag(TAG_OWNER, self)
                self.collisionNPs.append(np)

    def cleanupModel(self):
        for np in self.collisionNPs:
            np.clearPythonTag(TAG_OWNER)

        if self.model is not None:
            self.model.removeNode()
            self.model = None

        self.collisionNPs = []
        self.height = 0

    def cleanup(self):
        self.cleanupModel()
        if self.root is not None:
            self.root.removeNode()
            self.root = None

def buildDoors(level, doors):
    for doorNP in doors:
        doorObj = Door(doorNP)
        level.passiveObjects.append(doorObj)

