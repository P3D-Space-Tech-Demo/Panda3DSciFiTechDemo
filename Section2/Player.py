from panda3d.core import PointLight
from panda3d.core import CollisionSphere, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue, CollisionTraverser
from panda3d.core import Vec4, Vec3, Vec2, Plane, Point3, Point2, Quat, BitMask32
from panda3d.core import PandaNode, NodePath
from panda3d.core import Shader
from panda3d.core import TextNode
from panda3d.core import CardMaker
from panda3d.core import TextureStage
from panda3d.core import MeshDrawer
from panda3d.core import ColorBlendAttrib
from direct.actor.Actor import Actor

from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectLabel

from Section2.GameObject import GameObject, ArmedObject
from Section2.PlayerWeapons import BlasterWeapon, RocketWeapon

from Section2.CommonValues import *
from Section2.Common import Common

import math

class Player(GameObject, ArmedObject):
    def __init__(self, shipSpec):
        GameObject.__init__(self,
                            Vec3(0, 0, 0),
                            None,
                            None,
                            shipSpec.maxShields,
                            shipSpec.maxSpeed,
                            "player",
                            MASK_INTO_PLAYER,
                            2)
        ArmedObject.__init__(self)

        self.acceleration = shipSpec.acceleration
        self.turnRate = shipSpec.turnRate

        self.numGuns = len(shipSpec.gunPositions)
        self.numMissiles = shipSpec.numMissiles
        self.maxEnergy = shipSpec.maxEnergy
        self.energyRechargeRate = shipSpec.energyRechargeRate
        self.shieldRechargeRate = shipSpec.shieldRechargeRate

        self.energy = shipSpec.maxEnergy

        for gunPos in shipSpec.gunPositions:
            np = self.actor.attachNewNode(PandaNode("gun node"))
            np.setPos(gunPos)

            gun = BlasterWeapon()
            self.addWeapon(gun, 0, np)

        missileSetCounter = 1
        for missilePos in shipSpec.missilePositions:
            np = self.actor.attachNewNode(PandaNode("missile node"))
            np.setPos(missilePos)

            gun = RocketWeapon()
            self.addWeapon(gun, missileSetCounter, np)
            missileSetCounter += 1

        self.numMissileSets = missileSetCounter - 1
        self.missileSetIndex = 0

        light = PointLight("basic light")
        light.setColor(Vec4(1, 1, 1, 1))
        light.setAttenuation((1, 0.01, 0.001))
        self.lightNP = self.root.attachNewNode(light)
        self.lightNP.setZ(1)
        Common.framework.showBase.render.setLight(self.lightNP)

        self.colliderNP.node().setFromCollideMask(MASK_WALLS | MASK_FROM_PLAYER)

        Common.framework.pusher.addCollider(self.colliderNP, self.root)
        Common.framework.traverser.addCollider(self.colliderNP, Common.framework.pusher)

        Common.framework.showBase.camera.reparentTo(self.actor)
        Common.framework.showBase.camera.setPos(0, 0, 0)
        Common.framework.showBase.camera.setHpr(0, 0, 0)

        lens = Common.framework.showBase.camLens

        lens.setNear(0.03)

        ratio = lens.getAspectRatio()

        lens.setFov(75*ratio)

        self.lastMousePos = Vec2(0, 0)
        self.mouseSpeedHori = 50.0
        self.mouseSpeedVert = 30.0
        self.mouseSensitivity = 1.0

        self.targetingRay = CollisionSegment(0, 0, 0, 0, 100, 0)
        self.targetingRayNode = CollisionNode("lock ray")
        self.targetingRayNode.addSolid(self.targetingRay)
        self.targetingRayNode.setFromCollideMask(MASK_ENEMY_LOCK_SPHERE)
        self.targetingRayNode.setIntoCollideMask(0)
        self.targetingRayNP = self.actor.attachNewNode(self.targetingRayNode)
        self.targetingQueue = CollisionHandlerQueue()

        self.prospectiveLockTarget = None
        self.lockTargetTimer = 0
        self.lockDuration = 1

        Common.framework.traverser.addCollider(self.targetingRayNP, self.targetingQueue)

        #rayNodePath.show()

        self.uiRoot = aspect2d.attachNewNode(PandaNode("player UI"))

        cardMaker = CardMaker("UI maker")
        cardMaker.setFrame(-1, 1, -1, 1)

        self.centreSpot = self.uiRoot.attachNewNode(cardMaker.generate())
        self.centreSpot.setTexture(Common.framework.showBase.loader.loadTexture("Assets/Section2/tex/spot.png"))
        self.centreSpot.setTransparency(True)
        self.centreSpot.setPos(0, 0, 0)
        self.centreSpot.setScale(0.01)
        self.centreSpot.setAlphaScale(0.5)

        self.directionIndicator = self.uiRoot.attachNewNode(cardMaker.generate())
        self.directionIndicator.setTexture(Common.framework.showBase.loader.loadTexture("Assets/Section2/tex/directionIndicator.png"))
        self.directionIndicator.setTransparency(True)
        self.directionIndicator.setScale(0.05)
        self.directionIndicator.hide()

        self.lockMarkerRoot = self.uiRoot.attachNewNode(PandaNode("lock marker root"))
        for i in range(4):
            markerRotationNP = self.lockMarkerRoot.attachNewNode(PandaNode("lock marker rotation"))
            marker = markerRotationNP.attachNewNode(cardMaker.generate())
            marker.setTexture(Common.framework.showBase.loader.loadTexture("Assets/Section2/tex/lockMarker.png"))
            marker.setTransparency(True)
            markerRotationNP.setScale(0.04)
            markerRotationNP.setR(i*90)
        self.lockMarkerRoot.hide()

        self.lockBar = Common.framework.showBase.loader.loadModel("Assets/Section2/models/uiLockBar")
        self.lockBar.reparentTo(self.uiRoot)
        self.lockBar.setScale(0.15)
        #self.lockBar.hide()

        cardMaker.setFrame(-1, 1, 0, 1)

        self.cockpit = Common.framework.showBase.loader.loadModel("Assets/Section2/models/{0}".format(shipSpec.cockpitModelFile))
        self.cockpit.reparentTo(self.actor)

        healthBarRoot = self.cockpit.find("**/healthBar")
        if healthBarRoot is None or healthBarRoot.isEmpty():
            healthBarRoot = self.uiRoot.attachNewNode(PandaNode("health bar root"))
            print ("No health bar root found!")

        energyBarRoot = self.cockpit.find("**/energyBar")
        if energyBarRoot is None or energyBarRoot.isEmpty():
            energyBarRoot = self.uiRoot.attachNewNode(PandaNode("energy bar root"))
            print ("No energy bar root found!")
            
        missileCounterRoot = self.cockpit.find("**/missileCounter")
        if missileCounterRoot is None or missileCounterRoot.isEmpty():
            missileCounterRoot = self.uiRoot.attachNewNode(PandaNode("missile counter root"))
            print ("No missile counter root found!")

        radarRoot = self.cockpit.find("**/radar")
        if radarRoot is None or radarRoot.isEmpty():
            radarRoot = self.uiRoot.attachNewNode(PandaNode("radar root"))
            print ("No radar root found!")
            
        speedometerRoot = self.cockpit.find("**/speedometer")
        if speedometerRoot is None or speedometerRoot.isEmpty():
            speedometerRoot = self.uiRoot.attachNewNode(PandaNode("speedometer root"))
            print ("No speedometer root found!")

        self.radarDrawer = MeshDrawer()
        self.radarDrawer.setBudget(4096)

        self.radarDrawerNP = self.radarDrawer.getRoot()
        self.radarDrawerNP.reparentTo(radarRoot)
        self.radarDrawerNP.setTwoSided(True)
        self.radarDrawerNP.setLightOff()
        self.radarDrawerNP.setDepthWrite(False)
        self.radarDrawerNP.setTransparency(True)

        self.healthBar = healthBarRoot.attachNewNode(cardMaker.generate())
        self.healthBar.setSx(0.05)

        self.energyBar = energyBarRoot.attachNewNode(cardMaker.generate())
        self.energyBar.setSx(0.05)

        self.healthBarScalar = 0.00175
        self.energyBarScalar = 0.00175

        self.missileCounter = DirectLabel(text = "",
                                          text_mayChange = True,
                                          scale = 0.09,
                                          relief = None,
                                          parent = missileCounterRoot)

        self.maxRadarRange = 700
        self.radarSize = 0.3

        self.speedometer = DirectLabel(text = "",
                                       text_mayChange = True,
                                       scale = 0.09,
                                       relief = None,
                                       parent = speedometerRoot)

        self.updateHealthUI()
        self.updateEnergyUI()
        self.updateMissileUI()
        self.updateRadar()
        self.updateSpeedometer()

        self.updatingEffects = []

    def update(self, keys, dt):
        GameObject.update(self, dt)

        self.updateSpeedometer()

        self.walking = False

        quat = self.root.getQuat(Common.framework.showBase.render)
        forward = quat.getForward()
        right = quat.getRight()
        up = quat.getUp()

        if keys["up"]:
            self.walking = True
            self.velocity += forward*self.acceleration*dt
        if keys["down"]:
            self.walking = True
            self.velocity -= forward*self.acceleration*dt
        if keys["left"]:
            self.walking = True
            self.velocity -= right*self.acceleration*dt
        if keys["right"]:
            self.walking = True
            self.velocity += right*self.acceleration*dt
        if self.walking:
            self.inControl = True

        mouseWatcher = base.mouseWatcherNode
        if mouseWatcher.hasMouse():
            xSize = base.win.getXSize()
            ySize = base.win.getYSize()
            xPix = float(xSize % 2)/xSize
            yPix = float(ySize % 2)/ySize
            mousePos = Vec2(base.mouseWatcherNode.getMouse())
            mousePos.addX(-xPix)
            mousePos.addY(-yPix)
            if abs(mousePos.x) < xPix:
                mousePos.x = 0
            if abs(mousePos.y) < yPix:
                mousePos.y = 0

        else:
            mousePos = self.lastMousePos

        if mousePos.length() > 0.01:
            axis = right*(mousePos.y) + up*(-mousePos.x)
            axis.normalize()
            angle = mousePos.length()*self.turnRate*dt

            rotQuat = Quat()
            rotQuat.setFromAxisAngle(angle, axis)

            self.root.setQuat(quat*rotQuat)

        if not self.weaponSets[0][0].active:
            self.alterEnergy(math.sin(1.071*self.energy/self.maxEnergy + 0.5)*self.energyRechargeRate*dt)

        self.updateEnergyUI()
        self.updateHealthUI()
        self.updateRadar()

        #self.root.setH(self.root.getH() - mousePos.x*self.mouseSpeedHori*self.mouseSensitivity)
        #self.actor.setP(self.actor.getP() + mousePos.y*self.mouseSpeedVert*self.mouseSensitivity)

        if keys["shoot"]:
            self.startFiringSet(0)
        else:
            self.ceaseFiringSet(0)

        if keys["shootSecondary"]:
            self.startFiringSet(self.missileSetIndex + 1)
        else:
            for i in range(self.numMissileSets):
                self.ceaseFiringSet(i + 1)

        [effect.update(self, dt) for effect in self.updatingEffects]
        [effect.cleanup() for effect in self.updatingEffects if not effect.active]
        self.updatingEffects = [effect for effect in self.updatingEffects if effect.active]

        if self.targetingQueue.getNumEntries() > 0:
            self.targetingQueue.sortEntries()
            entry = self.targetingQueue.getEntry(0)
            intoNP = entry.getIntoNodePath()
            if intoNP.hasPythonTag(TAG_OWNER):
                other = intoNP.getPythonTag(TAG_OWNER)
                if other is self.prospectiveLockTarget and other is not self.lockedTarget:
                    self.lockTargetTimer += dt
                    if self.lockTargetTimer >= self.lockDuration:
                        self.lockedTarget = other
                else:
                    self.lockTargetTimer = 0
                self.prospectiveLockTarget = other
            else:
                self.lockTargetTimer = 0
        else:
            self.lockTargetTimer = 0

        perc = self.lockTargetTimer / self.lockDuration
        self.lockBar.setTexOffset(TextureStage.getDefault(), 0, -perc*1.1)

        if self.lockedTarget is not None:
            if self.lockedTarget.health <= 0:
                self.lockedTarget = None
            else:
                relPos = self.lockedTarget.root.getPos(self.root)
                planarVec = relPos.getXz()
                relDist = relPos.length()

                if relDist == 0:
                    angle = 0
                else:
                    angle = math.acos(relPos.y/relDist)

                if relDist > 200 or angle > 1.7453:
                    self.lockedTarget = None
                else:

                    if self.lockMarkerRoot.isHidden():
                        self.lockMarkerRoot.show()

                    camPt = Point2()
                    convertedPt = Common.framework.showBase.cam.getRelativePoint(
                                            Common.framework.showBase.render,
                                            self.lockedTarget.root.getPos(Common.framework.showBase.render))
                    if Common.framework.showBase.camLens.project(convertedPt, camPt):
                        self.lockMarkerRoot.setPos(Common.framework.showBase.render2d, camPt.x, 0, camPt.y)
                        if self.lockMarkerRoot.isHidden():
                            self.lockMarkerRoot.show()
                        for child in self.lockMarkerRoot.getChildren():
                            child.getChild(0).setZ((1.0 - min(1, relDist/100))*5 + 0.2)
                    elif not self.lockMarkerRoot.isHidden():
                        self.lockMarkerRoot.hide()

                    if relPos.y < 0 or angle > 0.6:
                        planarVec.normalize()

                        self.directionIndicator.setPos(planarVec.x*0.4, 0, planarVec.y*0.4)

                        angle = math.degrees(math.atan2(planarVec.x, planarVec.y))
                        self.directionIndicator.setR(angle)

                        if self.directionIndicator.isHidden():
                            self.directionIndicator.show()
                    elif not self.directionIndicator.isHidden():
                        self.directionIndicator.hide()
        else:
            if not self.directionIndicator.isHidden():
                self.directionIndicator.hide()
            if not self.lockMarkerRoot.isHidden():
                self.lockMarkerRoot.hide()

    def weaponReset(self, weapon):
        ArmedObject.weaponFired(self, weapon)

        if isinstance(weapon, RocketWeapon):
            self.ceaseFiringSet(self.missileSetIndex + 1)
            self.missileSetIndex += 1
            if self.missileSetIndex >= self.numMissileSets:
                self.missileSetIndex = 0

    def attackPerformed(self, weapon):
        ArmedObject.attackPerformed(self, weapon)

    def postTraversalUpdate(self, dt):
        ArmedObject.update(self, dt)

    def alterHealth(self, dHealth, incomingImpulse, knockback, flinchValue, overcharge = False):
        GameObject.alterHealth(self, dHealth, incomingImpulse, knockback, flinchValue, overcharge)

        self.updateHealthUI()

        #self.hurtSound.play()

    def alterEnergy(self, dEnergy):
        self.energy += dEnergy
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.maxEnergy:
            self.energy = self.maxEnergy

    def alterMissileCount(self, dMissiles):
        self.numMissiles += dMissiles
        if self.numMissiles < 0:
            self.numMissiles = 0
        self.updateMissileUI()

    def updateHealthUI(self):
        perc = self.health/self.maxHealth
        newVal = max(0.01, self.health * self.healthBarScalar)
        self.healthBar.setSz(newVal)
        self.healthBar.setColorScale(1.0 - (perc - 0.5)/0.5, min(1, perc/0.5), 0, 1)
        #self.healthCounter.setText("{0:-.0f}".format(self.health))
        #self.healthCounter.setColorScale(1.0 - (perc - 0.5)/0.5, min(1, perc/0.5), 0, 1)

    def updateEnergyUI(self):
        perc = self.energy/self.maxEnergy
        newVal = max(0.01, self.energy * self.energyBarScalar)
        self.energyBar.setSz(newVal)
        self.energyBar.setColorScale(1.0 - (perc - 0.5)/0.5, min(1, perc/0.5), 0, 1)

    def updateMissileUI(self):
        self.missileCounter["text"] = "Missiles:\n{0}".format(self.numMissiles)
        self.missileCounter.setText()
        self.missileCounter.resetFrameSize()

    def updateSpeedometer(self):
        self.speedometer["text"] = "Speed:\n{0:0=2.0f}m/s".format(self.velocity.length()*2)
        self.speedometer.setText()
        self.speedometer.resetFrameSize()

    def updateRadar(self):
        if Common.framework.currentLevel is not None:
            self.radarDrawer.begin(Common.framework.showBase.cam, Common.framework.showBase.render)

            uvs = Vec2(0, 0)
            
            spotSize = 0.015

            self.radarDrawer.tri(Vec3(-spotSize, 0, -spotSize), Vec4(0, 1, 0, 1), uvs,
                                 Vec3(spotSize, 0, -spotSize), Vec4(0, 1, 0, 1), uvs,
                                 Vec3(-spotSize, 0, spotSize), Vec4(0, 1, 0, 1), uvs)
            self.radarDrawer.tri(Vec3(-spotSize, 0, spotSize), Vec4(0, 1, 0, 1), uvs,
                                 Vec3(spotSize, 0, -spotSize), Vec4(0, 1, 0, 1), uvs,
                                 Vec3(spotSize, 0, spotSize), Vec4(0, 1, 0, 1), uvs)

            selfForward = Vec3(0, 1, 0)

            for enemy in Common.framework.currentLevel.enemies:
                enemyPos = enemy.root.getPos(self.root)
                dist = enemyPos.length()
                if dist < self.maxRadarRange:
                    distPerc = dist / self.maxRadarRange
                    enemyPos.normalize()
                    anglePerc = selfForward.angleDeg(enemyPos) / 180
                    enemyPos.setY(0)
                    enemyPos.normalize()
                    enemyPos *= anglePerc * self.radarSize
                    colour = Vec4(1, 0, 0, math.sin(max(0, 1 - distPerc)*1.571))

                    self.radarDrawer.tri(Vec3(-spotSize, 0, 0) + enemyPos, colour, uvs,
                                         Vec3(spotSize, 0, 0) + enemyPos, colour, uvs,
                                         Vec3(0, 0, spotSize) + enemyPos, colour, uvs)
                    self.radarDrawer.tri(Vec3(spotSize, 0, 0) + enemyPos, colour, uvs,
                                         Vec3(-spotSize, 0, 0) + enemyPos, colour, uvs,
                                         Vec3(0, 0, -spotSize) + enemyPos, colour, uvs)

            self.radarDrawer.end()

    def addUpdatingEffect(self, effect):
        self.updatingEffects.append(effect)
        effect.start(self)

    def cleanup(self):
        if self.uiRoot is not None:
            self.uiRoot.removeNode()
            self.uiRoot = None
        self.healthBar = None

        if self.lightNP is not None:
            Common.framework.showBase.render.clearLight(self.lightNP)
            self.lightNP.removeNode()
            self.lightNP = None

        for effect in self.updatingEffects:
            effect.cleanup()
        self.updatingEffects = []

        ArmedObject.cleanup(self)
        GameObject.cleanup(self)
