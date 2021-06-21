from direct.showbase.ShowBase import ShowBase

from direct.actor.Actor import Actor
from direct.task import Task
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionSphere, CollisionTube, CollisionNode
from panda3d.core import Vec4, Vec3, Vec2
from panda3d.core import WindowProperties
from panda3d.core import Shader
from panda3d.core import ClockObject

from direct.gui.DirectGui import *

from Section2.GameObject import *
from Section2.Player import *
from Section2.Enemy import *
from Section2.Level import Level

from Section2.Common import Common

import random

class Section2():
    def __init__(self, showBase):
        self.showBase = showBase

        Common.initialise()
        Common.framework = self

        showBase.render.setShaderAuto()

        self.keyMap = {
            "up" : False,
            "down" : False,
            "left" : False,
            "right" : False,
            "shoot" : False,
            "shootSecondary" : False
        }

        showBase.accept("w", self.updateKeyMap, ["up", True])
        showBase.accept("w-up", self.updateKeyMap, ["up", False])
        showBase.accept("s", self.updateKeyMap, ["down", True])
        showBase.accept("s-up", self.updateKeyMap, ["down", False])
        showBase.accept("mouse1", self.updateKeyMap, ["shoot", True])
        showBase.accept("mouse1-up", self.updateKeyMap, ["shoot", False])
        showBase.accept("mouse3", self.updateKeyMap, ["shootSecondary", True])
        showBase.accept("mouse3-up", self.updateKeyMap, ["shootSecondary", False])

        showBase.accept("\\", self.toggleFriction)

        self.pusher = CollisionHandlerPusher()
        self.traverser = CollisionTraverser()
        self.traverser.setRespectPrevTransform(True)

        self.pusher.add_in_pattern("%fn-into-%in")
        self.pusher.add_in_pattern("%fn-into")
        self.pusher.add_again_pattern("%fn-again-into")
        showBase.accept("projectile-into", self.projectileImpact)
        showBase.accept("projectile-again-into", self.projectileImpact)
        showBase.accept("player-into", self.gameObjectPhysicalImpact)
        showBase.accept("enemy-into", self.gameObjectPhysicalImpact)

        self.updateTask = showBase.taskMgr.add(self.update, "update")

        self.player = None
        self.currentLevel = None

    def toggleFriction(self):
        Common.useFriction = not Common.useFriction

    def startGame(self, shipSpec):
        self.cleanupLevel()

        self.player = Player(shipSpec)

        self.currentLevel = Level("spaceLevel")

    def updateKeyMap(self, controlName, controlState, callback = None):
        self.keyMap[controlName] = controlState

        if callback is not None:
            callback(controlName, controlState)

    def update(self, task):
        dt = globalClock.getDt()

        if self.currentLevel is not None:
            self.currentLevel.update(self.player, self.keyMap, dt)

            if self.player is not None and self.player.health <= 0:
                self.showBase.gameOver()
                return Task.done

            self.traverser.traverse(self.showBase.render)

            if self.player is not None and self.player.health > 0:
                self.player.postTraversalUpdate(dt)

        return Task.cont

    def projectileImpact(self, entry):
        fromNP = entry.getFromNodePath()
        proj = fromNP.getPythonTag(TAG_OWNER)

        intoNP = entry.getIntoNodePath()
        if intoNP.hasPythonTag(TAG_OWNER):
            intoObj = intoNP.getPythonTag(TAG_OWNER)
            proj.impact(intoObj)
        else:
            proj.impact(None)

    def gameObjectPhysicalImpact(self, entry):
        fromNP = entry.getFromNodePath()
        if fromNP.hasPythonTag(TAG_OWNER):
            fromNP.getPythonTag(TAG_OWNER).physicalImpact(entry.getSurfaceNormal(self.showBase.render))

    def triggerActivated(self, entry):
        intoNP = entry.getIntoNodePath()
        trigger = intoNP.getPythonTag(TAG_OWNER)

        if self.currentLevel is not None:
            self.currentLevel.triggerActivated(trigger)

    def cleanupLevel(self):
        if self.currentLevel is not None:
            self.currentLevel.cleanup()
            self.currentLevel = None

        if self.player is not None:
            self.player.cleanup()
            self.player = None

    def cleanup(self):
        self.showBase.ignore("w")
        self.showBase.ignore("w-up")
        self.showBase.ignore("s")
        self.showBase.ignore("s-up")
        self.showBase.ignore("mouse1")
        self.showBase.ignore("mouse1-up")
        self.showBase.ignore("mouse3")
        self.showBase.ignore("mouse3-up")
        self.showBase.ignore("\\")
        self.showBase.ignore("projectile-into")
        self.showBase.ignore("projectile-again-into")
        self.showBase.ignore("player-into")
        self.showBase.ignore("enemy-into")

        self.cleanupLevel()
        self.showBase.taskMgr.remove(self.updateTask)
        self.showBase = None
        self.updateTask = None

def initialise(showBase, shipSpec):
    game = Section2(showBase)
    game.startGame(shipSpec)
    return game
