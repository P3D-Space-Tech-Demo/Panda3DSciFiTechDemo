from panda3d.core import CollisionSphere, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue, CollisionTraverser
from panda3d.core import BitMask32
from panda3d.core import Vec3
from panda3d.core import OmniBoundingVolume
from panda3d.core import Shader
from panda3d.core import TextNode
from panda3d.core import PandaNode
from direct.actor.Actor import Actor

from direct.gui.OnscreenText import OnscreenText

from Section3.Weapon import Weapon, HitscanWeapon, Projectile, ProjectileWeapon

from Section3.CommonValues import *
import common

import random, math

class PlayerWeapon():
    def __init__(self, handModel, idleAnim, appearAnim, fireAnim, releaseFireAnim, modelScale, uiRoot):
        self.handModel = Actor(handModel,
                               {"idle" : handModel + "-" + idleAnim,
                                "appear" : handModel + "-" + appearAnim,
                                "fire" : handModel + "-" + fireAnim,
                                "releaseFire" : handModel + "-" + releaseFireAnim})
        self.handModel.setBin("fixed", 100)
        self.handModel.setScale(modelScale)
        self.handModel.node().setBounds(OmniBoundingVolume())
        self.handModel.node().setFinal(True)

        self.uiRoot = uiRoot
        #self.handModel.setDepthTest(False)
        #self.handModel.setDepthWrite(False)

        self.ammoCost = 1
        self.startingAmmo = 100
        self.ammoValue = self.startingAmmo

        self.showAmmoDecimals = False

        self.uiRoot = uiRoot.attachNewNode(PandaNode("weapon ui root"))
        self.uiRoot.hide()

        self.ammoCounter = OnscreenText(text = "", parent = self.uiRoot,
                                        mayChange = True,
                                        #font = common.base.font,
                                        fg = (1, 1, 1, 1),
                                        scale = 0.125,
                                        align = TextNode.ACenter)
        self.ammoCounter.setShaderOff(1)

    def activate(self, owner):
        self.handModel.reparentTo(owner.actor)
        self.handModel.setPos(0, 0.075, -0.125)
        self.handModel.play("appear")

        self.updateAmmoValue(0)
        self.uiRoot.show()

    def deactivate(self, owner):
        self.handModel.detachNode()

        self.uiRoot.hide()

    def triggerPressed(self, owner):
        self.handModel.play("fire")

    def triggerReleased(self, owner):
        self.handModel.play("releaseFire")

    def update(self, dt, owner):
        pass

    def updateAmmoValue(self, dAmmo):
        self.ammoValue += dAmmo
        if self.showAmmoDecimals:
            self.ammoCounter.setText("{0:-.1f}".format(max(0, self.ammoValue)))
        else:
            self.ammoCounter.setText("{0:-.0f}".format(max(0, self.ammoValue)))

    def destroy(self):
        if self.handModel is not None:
            self.handModel.cleanup()
            self.handModel.removeNode()
            self.handModel = None
        
class RapidShotgunWeapon(HitscanWeapon, PlayerWeapon):
    def __init__(self, uiRoot):
        HitscanWeapon.__init__(self, MASK_INTO_ENEMY, 1, 2)
        PlayerWeapon.__init__(self, "Assets/Section3/models/WeaponShotgun/playerHand", "idle", "enter", "fire", "releaseFire", 0.03, uiRoot)

        self.flinchValue = 1

        self.ammoCost = 1
        self.startingAmmo = 5
        self.ammoValue = self.startingAmmo

        self.impactPulsePeriod = 0.2

        self.firingPeriod = 0.4
        self.firingDelayPeriod = -1

        self.numShots = 20

        self.spreadSize = 0.4

        self.impactModels = []

        for i in range(self.numShots):
            impactModel = common.base.loader.loadModel("Assets/Section3/models/WeaponShotgun/shotgunImpact")

            impactModel.reparentTo(common.base.render)
            impactModel.hide()
            impactModel.setLightOff(1)

            impactModel.setPythonTag("timer", self.impactPulsePeriod)
            impactModel.setPythonTag("scalar", 0.4)
            impactModel.setPythonTag("scalarSpeed", 0.4)

            impactModel.setBillboardAxis()

            self.impactModels.append(impactModel)

    def activate(self, owner):
        HitscanWeapon.activate(self, owner)
        PlayerWeapon.activate(self, owner)

    def deactivate(self, owner):
        HitscanWeapon.deactivate(self, owner)
        PlayerWeapon.deactivate(self, owner)

        for model in self.impactModels:
            model.hide()

    def triggerPressed(self, owner):
        HitscanWeapon.triggerPressed(self, owner)
        PlayerWeapon.triggerPressed(self, owner)

        if self.firingTimer <= 0:
            self.fire(owner, 0)

    def triggerReleased(self, owner):
        HitscanWeapon.triggerReleased(self, owner)
        PlayerWeapon.triggerReleased(self, owner)

    def update(self, dt, owner):
        HitscanWeapon.update(self, dt, owner)
        PlayerWeapon.update(self, dt, owner)

        for model in self.impactModels:
            if not model.isHidden():
                timer = model.getPythonTag("timer")
                baseScale = model.getPythonTag("scalar")
                timer -= dt
                if timer <= 0:
                    timer = 0
                    model.hide()
                else:
                    perc = timer/self.impactPulsePeriod
                    model.setScale(baseScale*math.sin(((1.0 - perc))*(3.142 - 1.571) + 1.571))
                    #model.setAlphaScale(math.sin(perc*1.571))
                model.setPythonTag("timer", timer)

    def fire(self, owner, dt):
        if self.ammoValue > 0:
            owner.attackPerformed(self)

            self.updateAmmoValue(-self.ammoCost)

            self.firingTimer = self.firingPeriod

            ownerPos = owner.actor.getPos(common.base.render)
            quat = owner.actor.getQuat(common.base.render)
            ownerForward = quat.getForward()
            ownerRight = quat.getRight()
            ownerUp = quat.getUp()

            spreadScalar = self.spreadSize/self.numShots

            for i in range(self.numShots):

                spreadRoll = random.uniform(0, 6.283)
                spreadDist = math.tan(spreadScalar*i)

                spreadOffset = ownerRight*math.sin(spreadRoll) + ownerUp*math.cos(spreadRoll)
                spreadVec = ownerForward + spreadOffset*spreadDist

                spreadVec.normalize()

                hit, hitEntry = self.performRayCast(ownerPos, spreadVec)
                if hit:
                    hitPos = hitEntry.getSurfacePoint(common.base.render)
                    hitNP = hitEntry.getIntoNodePath()
                    hitNormal = hitEntry.getSurfaceNormal(common.base.render)

                    if hit:
                        model = self.impactModels[i]
                        model.show()
                        model.setPos(common.base.render, hitPos)
                        model.setPythonTag("timer", self.impactPulsePeriod)
                        #model.lookAt(hitPos + hitNormal)

                        if hitNP.hasPythonTag(TAG_OWNER):
                            owner = hitNP.getPythonTag(TAG_OWNER)
                            owner.alterHealth(-self.damage, spreadVec * self.knockback, self.flinchValue)
                            model.setScale(0.15)
                            model.setPythonTag("scalar", 0.125)
                        else:
                            model.setScale(0.1)
                            model.setPythonTag("scalar", 0.1125)

    def destroy(self):
        for model in self.impactModels:
            model.removeNode()
        self.impactModels = []
        HitscanWeapon.destroy(self)
        PlayerWeapon.destroy(self)

class BlasterWeapon(ProjectileWeapon, PlayerWeapon):
    def __init__(self, uiRoot):
        projectile = Projectile("Assets/Section3/models/WeaponBlaster/shot", MASK_INTO_ENEMY,
                                20, 10, 10, 0.3, 1.0, 10,
                                0, "Assets/Section3/models/WeaponBlaster/blast")
        ProjectileWeapon.__init__(self, projectile)
        PlayerWeapon.__init__(self, "Assets/Section3/models/WeaponBlaster/playerHand", "idle", "enter", "fire", "releaseFire", 0.03, uiRoot)

        self.ammoCost = 1
        self.startingAmmo = 10
        self.ammoValue = self.startingAmmo

        self.firingPeriod = 0
        self.firingDelayPeriod = -1

        self.numShots = 1

        self.spreadSize = 0

        self.projectileDamageBase = 0
        self.projectileDamageSpread = 50
        self.projectileSizeBase = 0.01
        self.projectileSizeSpread = 0.7
        self.projectileAOESizeBase = 0
        self.projectileAOESizeSpread = 2

        self.charge = 0
        self.chargeRate = 1
        self.ammoDrainTimer = 0
        self.ammoDrainInterval = 0.2

        self.chargeBar = loader.loadModel("Assets/Section3/models/healthBar")
        self.chargeBar.reparentTo(self.uiRoot)
        self.chargeBar.setZ(0.15)
        self.chargeBar.setX(-0.2)
        self.chargeBar.setScale(0.2)
        self.updateChargeBar()

    def updateChargeBar(self):
        chargeVal = max(0.1, self.charge)
        self.chargeBar.setSx(0.02*chargeVal)
        self.chargeBar.setX(-chargeVal*0.06)

    def activate(self, owner):
        ProjectileWeapon.activate(self, owner)
        PlayerWeapon.activate(self, owner)

    def deactivate(self, owner):
        ProjectileWeapon.deactivate(self, owner)
        PlayerWeapon.deactivate(self, owner)

    def triggerPressed(self, owner):
        ProjectileWeapon.triggerPressed(self, owner)
        PlayerWeapon.triggerPressed(self, owner)

        self.charge = 0

    def triggerReleased(self, owner):
        ProjectileWeapon.triggerReleased(self, owner)
        PlayerWeapon.triggerReleased(self, owner)

        self.fire(owner, 0)

        self.charge = 0
        self.updateChargeBar()

    def update(self, dt, owner):
        #ProjectileWeapon.update(self, dt, owner)
        PlayerWeapon.update(self, dt, owner)

        if self.active:
            self.charge += dt*self.chargeRate
            if self.charge > 1:
                self.charge = 1
            self.ammoDrainTimer -= dt
            if self.ammoDrainTimer <= 0:
                self.updateAmmoValue(-self.ammoCost)
                self.ammoDrainTimer = self.ammoDrainInterval

            if self.ammoValue <= 0:
                self.charge = 0

        self.updateChargeBar()

    def fire(self, owner, dt):
        if self.ammoValue > 0:
            owner.attackPerformed(self)

            self.updateAmmoValue(-self.ammoCost)

            size = self.projectileSizeSpread*self.charge

            self.projectileTemplate.damage = self.projectileDamageBase + self.projectileDamageSpread*self.charge
            #self.projectileTemplate.size = self.projectileSizeBase + size
            self.projectileTemplate.aoeRadius = self.projectileAOESizeBase + self.projectileAOESizeSpread*self.charge

            proj = ProjectileWeapon.fire(self, owner, 0)
            proj.actor.setScale(size)

            return proj

    def destroy(self):
        ProjectileWeapon.destroy(self)
        PlayerWeapon.destroy(self)