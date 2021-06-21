from direct.showbase.ShowBase import ShowBase

from direct.actor.Actor import Actor
from direct.task import Task
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionSphere, CollisionTube, CollisionNode
from panda3d.core import Vec4, Vec3, Vec2
from panda3d.core import WindowProperties
from panda3d.core import Shader
from panda3d.core import ClockObject

from direct.gui.DirectGui import *

from Section3.GameObject import *
from Section3.Player import *
from Section3.Enemy import *
from Section3.Level import Level

from Section3.Common import Common

import random

class Section3():
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
            "activateItem" : False,
            "invLeft" : False,
            "invRight" : False
        }

        showBase.accept("w", self.updateKeyMap, ["up", True])
        showBase.accept("w-up", self.updateKeyMap, ["up", False])
        showBase.accept("s", self.updateKeyMap, ["down", True])
        showBase.accept("s-up", self.updateKeyMap, ["down", False])
        showBase.accept("a", self.updateKeyMap, ["left", True])
        showBase.accept("a-up", self.updateKeyMap, ["left", False])
        showBase.accept("d", self.updateKeyMap, ["right", True])
        showBase.accept("d-up", self.updateKeyMap, ["right", False])
        showBase.accept("mouse1", self.updateKeyMap, ["shoot", True])
        showBase.accept("mouse1-up", self.updateKeyMap, ["shoot", False])
        showBase.accept("wheel_up", self.onMouseWheel, [1])
        showBase.accept("wheel_down", self.onMouseWheel, [-1])
        showBase.accept("space-up", self.interact)
        showBase.accept("1", self.selectWeapon, [0])
        showBase.accept("2", self.selectWeapon, [1])

        self.pusher = CollisionHandlerPusher()
        self.traverser = CollisionTraverser()
        self.traverser.setRespectPrevTransform(True)

        self.pusher.setHorizontal(True)

        self.pusher.add_in_pattern("%fn-into-%in")
        self.pusher.add_in_pattern("%fn-into")
        self.pusher.add_again_pattern("%fn-again-into")
        #self.accept("trapEnemy-into-wall", self.stopTrap)
        showBase.accept("projectile-into", self.projectileImpact)
        showBase.accept("projectile-again-into", self.projectileImpact)
        showBase.accept("playerWallCollider-into-item", self.itemCollected)
        showBase.accept("playerWallCollider-into-trigger", self.triggerActivated)

        self.updateTask = taskMgr.add(self.update, "update")

        self.player = None
        self.currentLevel = None

    def startGame(self):
        self.cleanup()

        self.player = Player()

        self.currentLevel = Level("testLevel")

    def selectWeapon(self, index):
        if self.player is not None:
            self.player.setCurrentWeapon(index)

    def interact(self):
        if self.player is not None:
            self.player.interact()

    def onMouseWheel(self, dir):
        if self.player is not None:
            self.player.scrollWeapons(dir)

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

    def itemCollected(self, entry):
        fromNP = entry.getFromNodePath()
        player = fromNP.getPythonTag(TAG_OWNER)

        intoNP = entry.getIntoNodePath()
        item = intoNP.getPythonTag(TAG_OWNER)

        item.collected(player)

    def triggerActivated(self, entry):
        intoNP = entry.getIntoNodePath()
        trigger = intoNP.getPythonTag(TAG_OWNER)

        if self.currentLevel is not None:
            self.currentLevel.triggerActivated(trigger)

    def cleanup(self):
        if self.currentLevel is not None:
            self.currentLevel.cleanup()
            self.currentLevel = None

        if self.player is not None:
            self.player.cleanup()
            self.player = None

def initialise(showBase, data = None):
    game = Section3(showBase)
    game.startGame()
    return game