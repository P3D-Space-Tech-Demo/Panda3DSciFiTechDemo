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

import common

import random

class Section3():
    def __init__(self):
        common.currentSection = self

        common.base.render.setShaderAuto()

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

        common.base.accept("w", self.updateKeyMap, ["up", True])
        common.base.accept("w-up", self.updateKeyMap, ["up", False])
        common.base.accept("s", self.updateKeyMap, ["down", True])
        common.base.accept("s-up", self.updateKeyMap, ["down", False])
        common.base.accept("a", self.updateKeyMap, ["left", True])
        common.base.accept("a-up", self.updateKeyMap, ["left", False])
        common.base.accept("d", self.updateKeyMap, ["right", True])
        common.base.accept("d-up", self.updateKeyMap, ["right", False])
        common.base.accept("mouse1", self.updateKeyMap, ["shoot", True])
        common.base.accept("mouse1-up", self.updateKeyMap, ["shoot", False])
        common.base.accept("wheel_up", self.onMouseWheel, [1])
        common.base.accept("wheel_down", self.onMouseWheel, [-1])
        common.base.accept("space-up", self.interact)
        common.base.accept("1", self.selectWeapon, [0])
        common.base.accept("2", self.selectWeapon, [1])

        self.pusher = CollisionHandlerPusher()
        self.traverser = CollisionTraverser()
        self.traverser.setRespectPrevTransform(True)

        self.pusher.setHorizontal(True)

        self.pusher.add_in_pattern("%fn-into-%in")
        self.pusher.add_in_pattern("%fn-into")
        self.pusher.add_again_pattern("%fn-again-into")
        #self.accept("trapEnemy-into-wall", self.stopTrap)
        common.base.accept("projectile-into", self.projectileImpact)
        common.base.accept("projectile-again-into", self.projectileImpact)
        common.base.accept("playerWallCollider-into-item", self.itemCollected)
        common.base.accept("playerWallCollider-into-trigger", self.triggerActivated)

        self.updateTask = taskMgr.add(self.update, "update")

        self.player = None
        self.currentLevel = None

    def startGame(self):
        self.destroy()

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
                common.gameController.gameOver()
                return Task.done

            self.traverser.traverse(common.base.render)

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

    def destroy(self):
        if self.currentLevel is not None:
            self.currentLevel.destroy()
            self.currentLevel = None

        if self.player is not None:
            self.player.destroy()
            self.player = None

def initialise(data = None):
    game = Section3()
    game.startGame()
    return game