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
from panda3d.core import CompassEffect
from direct.actor.Actor import Actor

from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectLabel

from Section2.GameObject import GameObject, ArmedObject
from Section2.PlayerWeapons import BlasterWeapon, RocketWeapon
from Section2.Explosion import Explosion

from Section2.CommonValues import *
import common

import math, random

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

        self.root.reparentTo(common.currentSection.currentLevel.geometry)

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

        self.maxRadarRange = 700

        light = PointLight("basic light")
        light.setColor(Vec4(1, 1, 1, 1))
        light.setAttenuation((1, 0.1, 0.01))
        self.lightNP = self.root.attachNewNode(light)
        self.lightNP.setZ(1)
        common.currentSection.currentLevel.geometry.setLight(self.lightNP)

        self.colliderNP.node().setFromCollideMask(MASK_WALLS | MASK_FROM_PLAYER)

        solid = CollisionSphere(0, 0, 0, self.size)
        solid.setTangible(False)
        triggerDetectorNode = CollisionNode("playerTriggerDetector")
        triggerDetectorNode.addSolid(solid)
        self.triggerDetectorNP = self.root.attachNewNode(triggerDetectorNode)
        self.triggerDetectorNP.setPythonTag(TAG_OWNER, self)
        triggerDetectorNode.setFromCollideMask(MASK_PLAYER_TRIGGER_DETECTOR)
        triggerDetectorNode.setIntoCollideMask(0)

        common.currentSection.pusher.addCollider(self.colliderNP, self.root)
        common.currentSection.traverser.addCollider(self.colliderNP, common.currentSection.pusher)
        common.currentSection.pusher.addCollider(self.triggerDetectorNP, self.root)
        common.currentSection.traverser.addCollider(self.triggerDetectorNP, common.currentSection.pusher)

        self.cameraTarget = self.actor.attachNewNode(PandaNode("camera target"))
        self.cameraTarget.setPos(0, 0, 0)
        self.cameraTarget.setHpr(0, 0, 0)

        self.thirdPersonCameraPos = Vec3(0, -7.5, 2.5)

        self.cameraSpeedScalar = 80

        common.base.camera.reparentTo(common.currentSection.currentLevel.geometry)

        lens = common.base.camLens

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

        common.currentSection.traverser.addCollider(self.targetingRayNP, self.targetingQueue)

        self.radarSize = 0.3

        self.uiRoot = common.base.aspect2d.attachNewNode(PandaNode("player UI"))

        cardMaker = CardMaker("UI maker")
        cardMaker.setFrame(-1, 1, -1, 1)

        self.centreSpot = self.uiRoot.attachNewNode(cardMaker.generate())
        self.centreSpot.setTexture(common.base.loader.loadTexture("Assets/Section2/tex/spot.png"))
        self.centreSpot.setTransparency(True)
        self.centreSpot.setPos(0, 0, 0)
        self.centreSpot.setScale(0.01)
        self.centreSpot.setAlphaScale(0.5)

        self.directionIndicator = self.uiRoot.attachNewNode(cardMaker.generate())
        self.directionIndicator.setTexture(common.base.loader.loadTexture("Assets/Section2/tex/directionIndicator.png"))
        self.directionIndicator.setTransparency(True)
        self.directionIndicator.setScale(0.05)
        self.directionIndicator.hide()

        self.lockMarkerRoot = self.uiRoot.attachNewNode(PandaNode("lock marker root"))
        for i in range(4):
            markerRotationNP = self.lockMarkerRoot.attachNewNode(PandaNode("lock marker rotation"))
            marker = markerRotationNP.attachNewNode(cardMaker.generate())
            marker.setTexture(common.base.loader.loadTexture("Assets/Section2/tex/lockMarker.png"))
            marker.setTransparency(True)
            markerRotationNP.setScale(0.04)
            markerRotationNP.setR(i*90)
        self.lockMarkerRoot.hide()

        self.lockBar = common.base.loader.loadModel("Assets/Section2/models/uiLockBar")
        self.lockBar.reparentTo(self.uiRoot)
        self.lockBar.setScale(0.15)
        #self.lockBar.hide()

        cardMaker.setFrame(-1, 1, 0, 1)

        self.cockpit = common.base.loader.loadModel("Assets/Section2/models/{0}".format(shipSpec.cockpitModelFile))
        self.cockpit.reparentTo(self.actor)

        self.thirdPersonShip = common.base.loader.loadModel("Assets/Section2/models/{0}".format(shipSpec.shipModelFileLowPoly))
        self.thirdPersonShip.setScale(0.5)
        self.thirdPersonShip.reparentTo(self.actor)

        bounds = self.thirdPersonShip.getTightBounds()
        self.thirdPersonWidth = bounds[1][1] - bounds[0][1]
        self.thirdPersonHeight = bounds[1][2] - bounds[0][2]
        self.thirdPersonLength = bounds[1][0] - bounds[0][0]

        self.thirdPersonShip.hide()

        self.healthBarScalar = 0.00175
        self.energyBarScalar = 0.00175

        self.healthBarRoot = self.cockpit.find("**/healthBar")
        if self.healthBarRoot is None or self.healthBarRoot.isEmpty():
            self.healthBarRoot = self.uiRoot.attachNewNode(PandaNode("health bar root"))
            print ("No health bar root found!")

        self.energyBarRoot = self.cockpit.find("**/energyBar")
        if self.energyBarRoot is None or self.energyBarRoot.isEmpty():
            self.energyBarRoot = self.uiRoot.attachNewNode(PandaNode("energy bar root"))
            print ("No energy bar root found!")
            
        self.missileCounterRoot = self.cockpit.find("**/missileCounter")
        if self.missileCounterRoot is None or self.missileCounterRoot.isEmpty():
            self.missileCounterRoot = self.uiRoot.attachNewNode(PandaNode("missile counter root"))
            print ("No missile counter root found!")

        self.radarRoot = self.cockpit.find("**/radar")
        if self.radarRoot is None or self.radarRoot.isEmpty():
            self.radarRoot = self.uiRoot.attachNewNode(PandaNode("radar root"))
            print ("No radar root found!")
            
        self.speedometerRoot = self.cockpit.find("**/speedometer")
        if self.speedometerRoot is None or self.speedometerRoot.isEmpty():
            self.speedometerRoot = self.uiRoot.attachNewNode(PandaNode("speedometer root"))
            print ("No speedometer root found!")

        self.healthBarRootThirdPerson = common.base.aspect2d.attachNewNode(PandaNode("health bar root 3rd person"))
        self.healthBarRootThirdPerson.setPos(0.5, 0, -1)
        barBacking = self.healthBarRootThirdPerson.attachNewNode(cardMaker.generate())
        barBacking.setSz(self.maxHealth * self.healthBarScalar + 0.01)
        barBacking.setSx(0.06)
        barBacking.setColorScale(0.3, 0.3, 0.3, 1)
        self.healthBarRootThirdPerson.hide()

        self.energyBarRootThirdPerson = common.base.aspect2d.attachNewNode(PandaNode("energy bar root 3rd person"))
        self.energyBarRootThirdPerson.setPos(-0.5, 0, -1)
        barBacking = self.energyBarRootThirdPerson.attachNewNode(cardMaker.generate())
        barBacking.setSz(self.maxEnergy * self.healthBarScalar + 0.01)
        barBacking.setSx(0.06)
        barBacking.setColorScale(0.3, 0.3, 0.3, 1)
        self.energyBarRootThirdPerson.hide()

        self.radarRootThirdPerson = common.base.aspect2d.attachNewNode(PandaNode("radar root 3rd person"))
        self.radarRootThirdPerson.setPos(0, 0, -1 + self.radarSize)
        radarBacking = common.base.loader.loadModel("Assets/Section2/models/uiRadar")
        radarBacking.reparentTo(self.radarRootThirdPerson)
        radarBacking.setColorScale(0.3, 0.3, 0.3, 0.5)
        radarBacking.setScale(self.radarSize)
        radarBacking.setTransparency(True)
        self.radarRootThirdPerson.hide()

        self.speedometerRootThirdPerson = common.base.aspect2d.attachNewNode(PandaNode("speedometer root 3rd person"))
        self.speedometerRootThirdPerson.setPos(0.85, 0, -0.9)
        barBacking = self.speedometerRootThirdPerson.attachNewNode(cardMaker.generate())
        barBacking.setSz(0.18)
        barBacking.setSx(0.2)
        barBacking.setZ(-0.1)
        barBacking.setColorScale(0.7, 0.7, 0.7, 1)
        self.speedometerRootThirdPerson.hide()

        self.missileCounterRootThirdPerson = common.base.aspect2d.attachNewNode(PandaNode("missile counter root 3rd person"))
        self.missileCounterRootThirdPerson.setPos(-0.85, 0, -0.9)
        barBacking = self.missileCounterRootThirdPerson.attachNewNode(cardMaker.generate())
        barBacking.setSz(0.18)
        barBacking.setSx(0.2)
        barBacking.setZ(-0.1)
        barBacking.setColorScale(0.7, 0.7, 0.7, 1)
        self.missileCounterRootThirdPerson.hide()

        self.radarDrawer = MeshDrawer()
        self.radarDrawer.setBudget(4096)

        self.radarDrawerNP = self.radarDrawer.getRoot()
        self.radarDrawerNP.reparentTo(self.radarRoot)
        self.radarDrawerNP.setTwoSided(True)
        self.radarDrawerNP.setLightOff()
        self.radarDrawerNP.setDepthWrite(False)
        self.radarDrawerNP.setTransparency(True)

        self.healthBar = self.healthBarRoot.attachNewNode(cardMaker.generate())
        self.healthBar.setSx(0.05)

        self.energyBar = self.energyBarRoot.attachNewNode(cardMaker.generate())
        self.energyBar.setSx(0.05)

        self.missileCounter = DirectLabel(text = "",
                                          text_mayChange = True,
                                          scale = 0.09,
                                          relief = None,
                                          parent = self.missileCounterRoot)

        self.speedometer = DirectLabel(text = "",
                                       text_mayChange = True,
                                       scale = 0.09,
                                       relief = None,
                                       parent = self.speedometerRoot)

        self.updateHealthUI()
        self.updateEnergyUI()
        self.updateMissileUI()
        self.updateRadar()
        self.updateSpeedometer()

        self.setThirdPerson(False)

        self.updatingEffects = []

        self.deathFireTimer = 2.5
        self.deathFlameTimer = 0

    def toggleThirdPerson(self):
        self.setThirdPerson(not self.isThirdPerson)

    def setThirdPerson(self, shouldBeThirdPerson):
        self.isThirdPerson = shouldBeThirdPerson

        if shouldBeThirdPerson:
            self.cameraTarget.setPos(self.thirdPersonCameraPos)
            common.base.camera.setPos(self.actor, -self.thirdPersonCameraPos*0.5)
            self.cameraSpeedScalar = 10
            self.thirdPersonShip.show()
            self.cockpit.hide()

            self.radarRootThirdPerson.show()
            self.healthBarRootThirdPerson.show()
            self.energyBarRootThirdPerson.show()
            self.missileCounterRootThirdPerson.show()
            self.speedometerRootThirdPerson.show()

            self.radarDrawerNP.reparentTo(self.radarRootThirdPerson)
            self.healthBar.reparentTo(self.healthBarRootThirdPerson)
            self.energyBar.reparentTo(self.energyBarRootThirdPerson)
            self.missileCounter.reparentTo(self.missileCounterRootThirdPerson)
            self.speedometer.reparentTo(self.speedometerRootThirdPerson)
        else:
            self.cameraTarget.setY(0)
            self.cameraTarget.setZ(0)
            common.base.camera.setPos(self.actor, -self.thirdPersonCameraPos*0.5)
            self.cameraSpeedScalar = 90
            self.cockpit.show()
            self.thirdPersonShip.hide()

            self.radarRootThirdPerson.hide()
            self.healthBarRootThirdPerson.hide()
            self.energyBarRootThirdPerson.hide()
            self.missileCounterRootThirdPerson.hide()
            self.speedometerRootThirdPerson.hide()

            self.radarDrawerNP.reparentTo(self.radarRoot)
            self.healthBar.reparentTo(self.healthBarRoot)
            self.energyBar.reparentTo(self.energyBarRoot)
            self.missileCounter.reparentTo(self.missileCounterRoot)
            self.speedometer.reparentTo(self.speedometerRoot)

    def forceCameraPosition(self):
        common.base.camera.setPos(self.cameraTarget, 0, 0, 0)
        common.base.camera.setHpr(self.cameraTarget, 0, 0, 0)

    def updateDeathCutscene(self, dt):
        if not self.isThirdPerson:
            self.setThirdPerson(True)
        self.cameraTarget.setPos(self.thirdPersonCameraPos*3)

        self.updateCamera(dt)

        if self.deathFireTimer > 0:
            self.deathFlameTimer -= dt
            if self.deathFlameTimer <= 0:
                self.deathFlameTimer = 0.1
                shaderInputs = {
                    "duration" : 0.8,
                    "expansionFactor" : 2,
                    "rotationRate" : 0.2,
                    "fireballBittiness" : 0.01,
                    "starDuration" : 0
                }

                randomVec1 = Vec2(random.uniform(0, 1), random.uniform(0, 1))
                randomVec2 = Vec2(random.uniform(0, 1), random.uniform(0, 1))

                explosion = Explosion(2, "explosion", shaderInputs, "noise", randomVec1, randomVec2)

                dir = Vec3(random.uniform(-1, 1),
                           random.uniform(-1, 1),
                           random.uniform(-1, 1))
                dir.normalize()
                dir.x *= self.thirdPersonWidth*0.5
                dir.y *= self.thirdPersonLength*0.5
                dir.z *= self.thirdPersonHeight*0.5

                explosion.activate(self.velocity, self.root.getPos(common.base.render) + dir)
                common.currentSection.currentLevel.explosions.append(explosion)

            self.deathFireTimer -= dt
            if self.deathFireTimer <= 0:
                self.thirdPersonShip.hide()

                shaderInputs = {
                    "duration" : 1.125,
                    "expansionFactor" : 7,
                    "rotationRate" : 0.2,
                    "fireballBittiness" : 1.0,
                    "starDuration" : 0
                }

                randomVec1 = Vec2(random.uniform(0, 1), random.uniform(0, 1))
                randomVec2 = Vec2(random.uniform(0, 1), random.uniform(0, 1))

                explosion = Explosion(20, "explosion", shaderInputs, "noise", randomVec1, randomVec2)

                explosion.activate(self.velocity, self.root.getPos(common.base.render))
                common.currentSection.currentLevel.explosions.append(explosion)


                shaderInputs = {
                    "duration" : 2,
                    "expansionFactor" : 0,
                    "rotationRate" : 0.2,
                    "fireballBittiness" : 0.01,
                    "starDuration" : 0
                }

                for i in range(20):
                    randomVec1 = Vec2(random.uniform(0, 1), random.uniform(0, 1))
                    randomVec2 = Vec2(random.uniform(0, 1), random.uniform(0, 1))

                    dir = Vec3(random.uniform(-1, 1),
                               random.uniform(-1, 1),
                               random.uniform(-1, 1))
                    dir.normalize()
                    dir.x *= self.thirdPersonWidth
                    dir.y *= self.thirdPersonLength
                    dir.z *= self.thirdPersonHeight
                    dir.normalize()
                    dir *= 15

                    explosion = Explosion(2.5, "explosion", shaderInputs, "noise", randomVec1, randomVec2)

                    explosion.activate(self.velocity + dir, self.root.getPos(common.base.render))
                    common.currentSection.currentLevel.explosions.append(explosion)

    def updateCamera(self, dt):
        camera = common.base.camera
        cameraPos = camera.getPos(common.base.render)
        diff = self.cameraTarget.getPos(common.base.render) - cameraPos
        camera.setPos(common.base.render, cameraPos + diff*dt*self.cameraSpeedScalar)
        camera.setHpr(self.cameraTarget, 0, 0, 0)

    def update(self, keys, dt):
        if self.health <= 0:
            self.updateDeathCutscene(dt)
            GameObject.update(self, dt)
            return

        self.updateSpeedometer()

        self.walking = False

        quat = self.root.getQuat(common.base.render)
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

        mouseWatcher = common.base.mouseWatcherNode
        if mouseWatcher.hasMouse():
            xSize = common.base.win.getXSize()
            ySize = common.base.win.getYSize()
            xPix = float(xSize % 2)/xSize
            yPix = float(ySize % 2)/ySize
            mousePos = Vec2(common.base.mouseWatcherNode.getMouse())
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
        [effect.destroy() for effect in self.updatingEffects if not effect.active]
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
                    convertedPt = common.base.cam.getRelativePoint(
                                            common.base.render,
                                            self.lockedTarget.root.getPos(common.base.render))
                    if common.base.camLens.project(convertedPt, camPt):
                        self.lockMarkerRoot.setPos(common.base.render2d, camPt.x, 0, camPt.y)
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

        self.updateCamera(dt)

        GameObject.update(self, dt)

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
        if common.currentSection.currentLevel is not None:
            selfForward = Vec3(0, 1, 0)

            self.radarDrawer.begin(common.base.cam, common.base.render)

            uvs = Vec2(0, 0)
            
            spotSize = 0.015

            self.radarDrawer.tri(Vec3(-spotSize, 0, -spotSize), Vec4(0, 1, 0, 1), uvs,
                                 Vec3(spotSize, 0, -spotSize), Vec4(0, 1, 0, 1), uvs,
                                 Vec3(-spotSize, 0, spotSize), Vec4(0, 1, 0, 1), uvs)
            self.radarDrawer.tri(Vec3(-spotSize, 0, spotSize), Vec4(0, 1, 0, 1), uvs,
                                 Vec3(spotSize, 0, -spotSize), Vec4(0, 1, 0, 1), uvs,
                                 Vec3(spotSize, 0, spotSize), Vec4(0, 1, 0, 1), uvs)

            exitPos = common.currentSection.currentLevel.exit.nodePath.getPos(self.root)
            exitPos.normalize()
            anglePerc = selfForward.angleDeg(exitPos) / 180
            exitPos.setY(0)
            exitPos.normalize()
            exitPos *= anglePerc * self.radarSize
            
            self.radarDrawer.tri(Vec3(-spotSize, 0, -spotSize) + exitPos, Vec4(0, 0, 1, 1), uvs,
                                 Vec3(spotSize, 0, -spotSize) + exitPos, Vec4(0, 0, 1, 1), uvs,
                                 Vec3(-spotSize, 0, spotSize) + exitPos, Vec4(0, 0, 1, 1), uvs)
            self.radarDrawer.tri(Vec3(-spotSize, 0, spotSize) + exitPos, Vec4(0, 0, 1, 1), uvs,
                                 Vec3(spotSize, 0, -spotSize) + exitPos, Vec4(0, 0, 1, 1), uvs,
                                 Vec3(spotSize, 0, spotSize) + exitPos, Vec4(0, 0, 1, 1), uvs)

            for enemy in common.currentSection.currentLevel.enemies:
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

    def destroy(self):
        if self.triggerDetectorNP is not None:
            self.triggerDetectorNP.clearPythonTag(TAG_OWNER)
            self.triggerDetectorNP.removeNode()
            self.triggerDetectorNP = None

        if self.uiRoot is not None:
            self.uiRoot.removeNode()
            self.uiRoot = None
        self.healthBar = None

        if self.lightNP is not None:
            common.currentSection.currentLevel.geometry.clearLight(self.lightNP)
            self.lightNP.removeNode()
            self.lightNP = None

        for effect in self.updatingEffects:
            effect.destroy()
        self.updatingEffects = []

        ArmedObject.destroy(self)
        GameObject.destroy(self)
