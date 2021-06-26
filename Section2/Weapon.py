from panda3d.core import CollisionSphere, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue, CollisionTraverser
from panda3d.core import BitMask32
from panda3d.core import Vec3
from panda3d.core import ColorBlendAttrib

from Section2.CommonValues import *
import common

from Section2.GameObject import GameObject

class Weapon():
    def __init__(self, mask, range, damage, knockback):
        self.active = False
        self.damage = damage
        self.mask = mask
        self.range = range

        self.knockback = knockback

        self.flinchValue = 0

        self.desiredRange = range

        self.particleSystems = []

        self.firingPeriod = 1
        self.firingTimer = 0
        self.firingDelay = 0
        self.firingDelayPeriod = 0.3

        self.isAvailable = False

    def setAvailable(self, state):
        self.isAvailable = state

    def activate(self, owner):
        pass

    def deactivate(self, owner):
        self.firingDelay = 0
        self.firingTimer = 0

    def triggerPressed(self, owner):
        self.active = True

    def triggerReleased(self, owner):
        self.active = False

    def update(self, dt, owner):
        mayFire = False
        if self.firingTimer > 0:
            self.firingTimer -= dt
            if self.firingTimer <= 0:
                mayFire = True
                owner.weaponReset(self)
        else:
            mayFire = True

        if self.active:
            if mayFire:
                if self.firingDelayPeriod > 0:
                    if self.firingDelay <= 0:
                        owner.attackPerformed(self)
                        self.firingDelay = self.firingDelayPeriod
                else:
                    self.fire(owner, dt)

        if self.firingDelay > 0:
            self.firingDelay -= dt
            if self.firingDelay <= 0:
                self.fire(owner, dt)

    def fire(self, owner, dt):
        self.firingTimer = self.firingPeriod
        owner.weaponFired(self)

    def destroy(self):
        pass

class ProjectileWeapon(Weapon):
    def __init__(self, projectileTemplate):
        Weapon.__init__(self, projectileTemplate.mask, projectileTemplate.range, projectileTemplate.damage,
                        projectileTemplate.knockback)

        self.projectileTemplate = projectileTemplate

    def deactivate(self, owner):
        Weapon.deactivate(self, owner)
        self.firingDelay = 0
        self.firingTimer = 0

    def update(self, dt, owner):
        Weapon.update(self, dt, owner)

    def fire(self, owner, dt):
        Weapon.fire(self, owner, dt)

        weaponNP = owner.weaponNPs[self]

        proj = Projectile.makeRealProjectileFromTemplate(self.projectileTemplate,
                                                         weaponNP.getPos(common.base.render))
        proj.fly(weaponNP.getQuat(common.base.render).getForward())
        if common.currentSection.currentLevel is not None:
            common.currentSection.currentLevel.projectiles.append(proj)

        return proj

class Projectile(GameObject):
    def __init__(self, model, isAdditive, mask, range, damage, speed, size, knockback, flinchValue,
                 aoeRadius = 0, blastModel = None,
                 pos = None, damageByTime = False):
        GameObject.__init__(self, pos, model, None, 100, speed, None, mask, 0.5)
        self.mask = mask
        self.range = range
        if range is None:
            self.rangeSq = 0
        else:
            self.rangeSq = range*range
        self.currentDistanceSq = 0
        self.damage = damage
        self.size = size
        self.knockback = knockback
        self.flinchValue = flinchValue
        if pos is None:
            self.root.detachNode()
            self.startPos = Vec3(0, 0, 0)
        else:
            self.startPos = Vec3(pos)
        self.damageByTime = damageByTime

        self.healthRechargeRate = 0

        self.aoeRadius = aoeRadius

        self.colliderNP = None

        self.noZVelocity = False

        self.isAdditive = isAdditive

        if blastModel is None:
            self.blastModel = None
            self.blastModelFile = None
        else:
            self.blastModel = common.base.loader.loadModel(blastModel)
            self.blastModelFile = blastModel

    @staticmethod
    def makeRealProjectileFromTemplate(template, projectilePosition):
        result = template.__class__(template.modelName, template.isAdditive, template.mask, template.range,
                            template.damage, template.maxSpeed, template.size,
                            template.knockback, template.flinchValue,
                            template.aoeRadius, template.blastModelFile,
                            pos = projectilePosition, damageByTime = template.damageByTime)

        if template.isAdditive:
            result.root.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
            result.root.setLightOff(10)
            result.root.setBin("unsorted", 1)
            result.root.setDepthWrite(False)
        result.root.reparentTo(common.currentSection.currentLevel.geometry)

        result.generateCollisionObject()

        return result

    def generateCollisionObject(self):
        colliderNode = CollisionNode("projectile")
        solid = CollisionSphere(0, 0, 0, self.size)
        solid.setTangible(False)
        colliderNode.addSolid(solid)
        self.colliderNP = self.root.attachNewNode(colliderNode)
        self.colliderNP.setPythonTag(TAG_OWNER, self)
        colliderNode.setFromCollideMask(MASK_WALLS | self.mask)
        colliderNode.setIntoCollideMask(0)

        common.currentSection.pusher.addCollider(self.colliderNP, self.root)
        common.currentSection.traverser.addCollider(self.colliderNP, common.currentSection.pusher)

        #self.colliderNP.show()

    def fly(self, direction):
        self.velocity = direction*self.maxSpeed
        self.actor.lookAt(self.velocity)
        self.walking = True

    def update(self, dt):
        GameObject.update(self, dt, fluid = True)
        if self.range is not None:
            diff = self.root.getPos(common.base.render) - self.startPos
            self.currentDistanceSq = diff.lengthSquared()
            if self.currentDistanceSq > self.rangeSq:
                self.health = 0

    def impact(self, impactee):
        selfPos = self.root.getPos(common.base.render)
        damageVal = -self.damage
        if self.damageByTime:
            damageVal *= globalClock.getDt()

        if impactee is not None:
            impactee.alterHealth(damageVal, (impactee.root.getPos(common.base.render) - selfPos).normalized(),  self.knockback,
                              self.flinchValue)

        if self.aoeRadius > 0:
            if self.blastModel is not None:
                common.currentSection.currentLevel.addBlast(self.blastModel,
                                                       max(0.01, self.aoeRadius - 0.7),
                                                       self.aoeRadius + 0.2,
                                                       0.15,
                                                       selfPos)
                self.blastModel = None
            aoeRadiusSq = self.aoeRadius*self.aoeRadius
            for other in common.currentSection.currentLevel.enemies:
                if other is not impactee:
                    diff = other.root.getPos(common.base.render) - selfPos
                    distSq = diff.lengthSquared()
                    if distSq < aoeRadiusSq:
                        perc = distSq/aoeRadiusSq
                        other.alterHealth(damageVal*perc, diff.normalized(), self.knockback*perc,
                                          self.flinchValue*perc)

        if self.maxHealth > 0:
            self.health = 0

    def destroy(self):
        if self.blastModel is not None:
            self.blastModel.removeNode()
            self.blastModel = None

        if self.colliderNP is not None and not self.colliderNP.isEmpty():
            self.colliderNP.clearPythonTag(TAG_OWNER)
            self.colliderNP.removeNode()
        self.colliderNP = None

        GameObject.destroy(self)

class SeekingProjectile(Projectile):
    def __init__(self, model, isAdditive, mask, range, damage, speed, size, knockback, flinchValue,
                 aoeRadius = 0, blastModel = None,
                 pos = None, damageByTime = False):
        Projectile.__init__(self, model, isAdditive, mask, range, damage, speed, size, knockback, flinchValue,
                 aoeRadius, blastModel,
                 pos, damageByTime)

        self.owner = None

    def update(self, dt):
        if self.owner is not None:
            if self.owner.lockedTarget is not None and self.owner.lockedTarget.root is not None:
                diff = self.owner.lockedTarget.root.getPos(common.base.render) - self.root.getPos(common.base.render)
                diff.normalize()
                self.velocity += diff*self.acceleration*dt
                self.actor.lookAt(self.velocity)

        Projectile.update(self, dt)

    def destroy(self):
        self.owner = None
        Projectile.destroy(self)