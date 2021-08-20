from direct.actor.Actor import Actor
from direct.task import Task
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionSphere, CollisionTube, CollisionNode
from panda3d.core import Vec4, Vec3, Vec2
from panda3d.core import WindowProperties
from panda3d.core import Shader
from panda3d.core import ClockObject
from panda3d.core import AmbientLight
from panda3d.core import CompassEffect
from panda3d.core import OmniBoundingVolume
from panda3d.core import AudioSound

from direct.gui.DirectGui import *

from Section2.GameObject import *
from Section2.Player import *
from Section2.Enemy import *
from Section2.Level import Level
from Section2.EndPortal import SphericalPortalSystem

import common

import random

class Section2():
    STATE_PLAYING = 0
    STATE_DEATH_CUTSCENE = 1
    STATE_GAME_OVER = 2

    def __init__(self, actionMusic, peaceMusic):
        common.currentSection = self

#        self.skybox = common.base.loader.load_model('Assets/Section2/models/5k_spacebox.gltf')
        cube_map_name = 'Assets/Section2/tex/main_skybox_#.png'
        self.skybox = common.create_skybox(cube_map_name)
        self.skybox.reparentTo(common.base.render)
        self.skybox.setEffect(CompassEffect.make(common.base.camera, CompassEffect.P_pos))
#        self.skybox.setBin("background", 1)
#        self.skybox.setDepthWrite(False)
        self.skybox.node().setBounds(OmniBoundingVolume())
        self.skybox.node().setFinal(True)

        '''amb_light = AmbientLight('amblight')
        amb_light.setColor((1, 1, 1, 1))
        amb_light_node = self.skybox.attachNewNode(amb_light)

        self.skybox.set_light(amb_light_node)'''

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

        common.base.accept("\\", self.toggleThirdPerson)
        common.base.accept("escape", common.gameController.openPauseMenu)

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
        common.base.accept("playerTriggerDetector-into-trigger", self.triggerActivated)

        self.updateTask = common.base.taskMgr.add(self.update, "update")

        self.player = None
        self.currentLevel = None
        self.shipSpec = None

        self.playState = Section2.STATE_PLAYING

        self.paused = False

        self.peaceMusic = common.base.loader.loadMusic(peaceMusic)
        self.actionMusic = common.base.loader.loadMusic(actionMusic)

        self.peaceMusic.setLoop(True)
        self.actionMusic.setLoop(True)

        self.actionMusic.setVolume(0)

        self.peaceMusic.play()
        self.actionMusic.play()

        self.musicFadeSpeedToAction = 1.5
        self.musicFadeSpeedToPeace = 0.5

    def toggleThirdPerson(self):
        self.player.toggleThirdPerson()

    def startGame(self, shipSpec):
        xSize = common.base.win.getXSize()
        ySize = common.base.win.getYSize()

        common.base.win.movePointer(0, xSize//2, ySize//2)

        self.cleanupLevel()

        self.shipSpec = shipSpec

        self.currentLevel = Level("spaceLevel")

        self.player = Player(shipSpec)
        self.player.root.setPos(self.currentLevel.playerSpawnPoint)
        self.player.forceCameraPosition()

        exit_sphere = self.currentLevel.geometry.find("**/=exit").find("**/+GeomNode")
        pos = exit_sphere.get_pos(self.currentLevel.geometry)
        exit_sphere.detach_node()
        lights = [self.currentLevel.lightNP, self.player.lightNP]
        self.portalSys = SphericalPortalSystem(self.currentLevel.geometry, lights, pos)

        self.playState = Section2.STATE_PLAYING

        self.activated()

    def resumeGame(self):
        self.activated()
        self.paused = False

        self.peaceMusic.play()
        self.actionMusic.play()

    def pauseGame(self):
        self.paused = True

        self.peaceMusic.stop()
        self.actionMusic.stop()

    def activated(self):
        properties = WindowProperties()
        properties.setMouseMode(WindowProperties.M_confined)
        properties.setCursorHidden(True)
        #properties.setCursorFilename("Assets/Section2/tex/shipCursor.cur")
        common.base.win.requestProperties(properties)

    def updateKeyMap(self, controlName, controlState, callback = None):
        self.keyMap[controlName] = controlState

        if callback is not None:
            callback(controlName, controlState)

    def update(self, task):
        dt = globalClock.getDt()

        if self.paused:
            return Task.cont

        if self.currentLevel is not None:
            self.currentLevel.update(self.player, self.keyMap, dt)

            if len(self.currentLevel.enemies) == 0:
                if self.peaceMusic.status() != AudioSound.PLAYING:
                    self.peaceMusic.play()
                newVolume = self.peaceMusic.getVolume()
                newVolume += dt*self.musicFadeSpeedToPeace
                if newVolume > 1:
                    newVolume = 1
                self.peaceMusic.setVolume(newVolume)

                newVolume = self.actionMusic.getVolume()
                newVolume -= dt*self.musicFadeSpeedToPeace
                if newVolume < 0:
                    newVolume = 0
                    if self.actionMusic.status() == AudioSound.PLAYING:
                        self.actionMusic.stop()
                self.actionMusic.setVolume(newVolume)
            else:
                newVolume = self.peaceMusic.getVolume()
                newVolume -= dt*self.musicFadeSpeedToAction
                if newVolume < 0:
                    newVolume = 0
                    if self.peaceMusic.status() == AudioSound.PLAYING:
                        self.peaceMusic.stop()
                self.peaceMusic.setVolume(newVolume)

                if self.actionMusic.status() != AudioSound.PLAYING:
                    self.actionMusic.play()
                newVolume = self.actionMusic.getVolume()
                newVolume += dt*self.musicFadeSpeedToAction
                if newVolume > 1:
                    newVolume = 1
                self.actionMusic.setVolume(newVolume)


            if self.player is not None and self.player.health <= 0:
                if self.playState == Section2.STATE_PLAYING:
                    self.playState = Section2.STATE_DEATH_CUTSCENE
                    self.deathTimer = 4.5
                elif self.playState == Section2.STATE_DEATH_CUTSCENE:
                    self.deathTimer -= dt
                    if self.deathTimer <= 0:
                        self.playState = Section2.STATE_GAME_OVER
                        common.gameController.gameOver()
                        return Task.done
                return Task.cont

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

    def exitTriggered(self):
        common.gameController.startSectionInternal(2, self.shipSpec)

    def cleanupLevel(self):
        if self.player is not None:
            self.player.destroy()
            self.player = None

        if self.currentLevel is not None:
            self.currentLevel.destroy()
            self.currentLevel = None

    def destroy(self):
        if self.peaceMusic is not None:
            self.peaceMusic.stop()
            self.peaceMusic = None
        if self.actionMusic is not None:
            self.actionMusic.stop()
            self.actionMusic = None

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
        common.base.ignore("escape")
        common.base.ignore("\\")
        common.base.ignore("projectile-into")
        common.base.ignore("projectile-again-into")
        common.base.ignore("player-into")
        common.base.ignore("enemy-into")

        self.cleanupLevel()
        self.portalSys.destroy()
        self.portalSys = None
        common.base.taskMgr.remove(self.updateTask)
        self.updateTask = None

        common.currentSection = None

def initialise(shipSpec):
    game = Section2("Assets/Section2/music/space_tech_break.mp3",
                    "Assets/Section2/music/space_tech_interlude_full.mp3")
    game.startGame(shipSpec)
    return game

def addOptions():
    gameController = common.gameController

    gameController.addOptionCheck("Use Semi-Newtonian Flight", "useNewtonianFlight", "section2", True)
