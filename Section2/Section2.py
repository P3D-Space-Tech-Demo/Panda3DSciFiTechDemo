from direct.actor.Actor import Actor
from direct.task import Task
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionSphere, CollisionTube, CollisionNode
from panda3d.core import Vec4, Vec3, Vec2
from panda3d.core import WindowProperties
from panda3d.core import Shader
from panda3d.core import ClockObject
from panda3d.core import AmbientLight
from panda3d.core import CompassEffect

from direct.gui.DirectGui import *

from Section2.GameObject import *
from Section2.Player import *
from Section2.Enemy import *
from Section2.Level import Level

import common

import random

class Section2():
    def __init__(self):
        common.currentSection = self

        self.skybox = common.base.loader.load_model('Assets/Section2/models/5k_spacebox.gltf')
        self.skybox.reparent_to(common.base.render)
        self.skybox.setEffect(CompassEffect.make(common.base.camera, CompassEffect.P_pos))
        self.skybox.setBin("background", 1)
        self.skybox.setDepthWrite(False)

        amb_light = AmbientLight('amblight')
        amb_light.setColor((1, 1, 1, 1))
        amb_light_node = self.skybox.attachNewNode(amb_light)

        self.skybox.set_light(amb_light_node)

        self.keyMap = {
            "up" : False,
            "down" : False,
            "left" : False,
            "right" : False,
            "shoot" : False,
            "shootSecondary" : False
        }

        common.base.accept("w", self.updateKeyMap, ["up", True])
        common.base.accept("w-up", self.updateKeyMap, ["up", False])
        common.base.accept("s", self.updateKeyMap, ["down", True])
        common.base.accept("s-up", self.updateKeyMap, ["down", False])
        common.base.accept("mouse1", self.updateKeyMap, ["shoot", True])
        common.base.accept("mouse1-up", self.updateKeyMap, ["shoot", False])
        common.base.accept("mouse3", self.updateKeyMap, ["shootSecondary", True])
        common.base.accept("mouse3-up", self.updateKeyMap, ["shootSecondary", False])

        common.base.accept("\\", self.toggleFriction)

        self.pusher = CollisionHandlerPusher()
        self.traverser = CollisionTraverser()
        self.traverser.setRespectPrevTransform(True)

        self.pusher.add_in_pattern("%fn-into-%in")
        self.pusher.add_in_pattern("%fn-into")
        self.pusher.add_again_pattern("%fn-again-into")
        common.base.accept("projectile-into", self.projectileImpact)
        common.base.accept("projectile-again-into", self.projectileImpact)
        common.base.accept("player-into", self.gameObjectPhysicalImpact)
        common.base.accept("enemy-into", self.gameObjectPhysicalImpact)

        self.updateTask = common.base.taskMgr.add(self.update, "update")

        self.player = None
        self.currentLevel = None

        self.useFriction = False

    def toggleFriction(self):
        self.useFriction = not self.useFriction

    def startGame(self, shipSpec):
        self.cleanupLevel()

        self.currentLevel = Level("spaceLevel")

        self.player = Player(shipSpec)

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

    def gameObjectPhysicalImpact(self, entry):
        fromNP = entry.getFromNodePath()
        if fromNP.hasPythonTag(TAG_OWNER):
            fromNP.getPythonTag(TAG_OWNER).physicalImpact(entry.getSurfaceNormal(common.base.render))

    def triggerActivated(self, entry):
        intoNP = entry.getIntoNodePath()
        trigger = intoNP.getPythonTag(TAG_OWNER)

        if self.currentLevel is not None:
            self.currentLevel.triggerActivated(trigger)

    def cleanupLevel(self):
        if self.currentLevel is not None:
            self.currentLevel.destroy()
            self.currentLevel = None

        if self.player is not None:
            self.player.destroy()
            self.player = None

    def destroy(self):
        if self.skybox is not None:
            self.skybox.removeNode()
            self.skybox = None

        common.base.ignore("w")
        common.base.ignore("w-up")
        common.base.ignore("s")
        common.base.ignore("s-up")
        common.base.ignore("mouse1")
        common.base.ignore("mouse1-up")
        common.base.ignore("mouse3")
        common.base.ignore("mouse3-up")
        common.base.ignore("\\")
        common.base.ignore("projectile-into")
        common.base.ignore("projectile-again-into")
        common.base.ignore("player-into")
        common.base.ignore("enemy-into")

        self.cleanupLevel()
        common.base.taskMgr.remove(self.updateTask)
        self.updateTask = None

        common.currentSection = None

def initialise(shipSpec):
    game = Section2()
    game.startGame(shipSpec)
    return game

def addOptions():
    pass