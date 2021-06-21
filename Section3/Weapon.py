from panda3d.core import CollisionSphere, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue, CollisionTraverser
from panda3d.core import BitMask32
from panda3d.core import Vec3

from Section3.CommonValues import *
from Section3.Common import Common

from Section3.GameObject import GameObject

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
                    self.firingTimer = self.firingPeriod

        if self.firingDelay > 0:
            self.firingDelay -= dt
            if self.firingDelay <= 0:
                self.fire(owner, dt)
                self.firingTimer = self.firingPeriod

    def fire(self, owner, dt):
        pass

    def cleanup(self):
        pass

class HitscanWeapon(Weapon):
    def __init__(self, mask, damage, knockback, range = None):
        Weapon.__init__(self, mask, range, damage, knockback)

        if range is None:
            self.ray = CollisionRay(0, 0, 0, 0, 1, 0)
        else:
            self.ray = CollisionSegment(0, 0, 0, 1, 0, 0)

        rayNode = CollisionNode("playerRay")
        rayNode.addSolid(self.ray)

        rayNode.setFromCollideMask(mask)
        rayNode.setIntoCollideMask(0)

        self.rayNodePath = render.attachNewNode(rayNode)
        self.rayQueue = CollisionHandlerQueue()

        self.traverser = CollisionTraverser()
        self.traverser.addCollider(self.rayNodePath, self.rayQueue)

    def performRayCast(self, origin, direction):
        if isinstance(self.ray, CollisionRay):
            self.ray.setOrigin(origin)
            self.ray.setDirection(direction)
        else:
            self.ray.setPointA(origin)
            self.ray.setPointB(origin + direction*self.range)

        self.traverser.traverse(render)

        if self.rayQueue.getNumEntries() > 0:
            self.rayQueue.sortEntries()
            rayHit = self.rayQueue.getEntry(0)

            return True, rayHit
        else:
            return False, None

    def fire(self, owner, dt):
        Weapon.fire(self, owner, dt)
        rayDir = owner.weaponNP.getQuat(render).getForward()
        hit, hitEntry = self.performRayCast(owner.weaponNP.getPos(render), rayDir)

        if hit:
            hitNP = hitEntry.getIntoNodePath()
            if hitNP.hasPythonTag(TAG_OWNER):
                subject = hitNP.getPythonTag(TAG_OWNER)
                subject.alterHealth(-self.damage, rayDir * self.knockback, self.flinchValue)

    def cleanup(self):
        self.traverser.removeCollider(self.rayNodePath)
        self.traverser = None

        if self.rayNodePath is not None:
            self.rayNodePath.removeNode()
            self.rayNodePath = None

        Weapon.cleanup(self)

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

        proj = Projectile.makeRealProjectileFromTemplate(self.projectileTemplate, owner.weaponNP.getPos(Common.framework.showBase.render))
        proj.fly(owner.weaponNP.getQuat(Common.framework.showBase.render).getForward())
        if Common.framework.currentLevel is not None:
            Common.framework.currentLevel.projectiles.append(proj)

        return proj

class Projectile(GameObject):
    def __init__(self, model, mask, range, damage, speed, size, knockback, flinchValue,
                 aoeRadius = 0, blastModel = None,
                 pos = None, damageByTime = False):
        GameObject.__init__(self, pos, model, None, 100, speed, None, 0, mask)
        self.mask = mask
        self.range = range
        if range is None:
            self.rangeSq = 0
        else:
            self.rangeSq = range*range
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

        self.aoeRadius = aoeRadius

        self.collider = None

        self.noZVelocity = False

        if blastModel is None:
            self.blastModel = None
            self.blastModelFile = None
        else:
            self.blastModel = loader.loadModel(blastModel)
            self.blastModelFile = blastModel

    @staticmethod
    def makeRealProjectileFromTemplate(template, projectilePosition):
        result = Projectile(template.modelName, template.mask, template.range,
                            template.damage, template.maxSpeed, template.size,
                            template.knockback, template.flinchValue,
                            template.aoeRadius, template.blastModelFile,
                            pos = projectilePosition, damageByTime = template.damageByTime)

        result.generateCollisionObject()

        return result

    def generateCollisionObject(self):
        colliderNode = CollisionNode("projectile")
        solid = CollisionSphere(0, 0, 0, self.size)
        solid.setTangible(False)
        colliderNode.addSolid(solid)
        self.collider = self.root.attachNewNode(colliderNode)
        self.collider.setPythonTag(TAG_OWNER, self)
        colliderNode.setFromCollideMask(MASK_WALLS | self.mask)
        colliderNode.setIntoCollideMask(0)

        #self.collider.show()

        Common.framework.pusher.addCollider(self.collider, self.root)
        Common.framework.traverser.addCollider(self.collider, Common.framework.pusher)

    def fly(self, direction):
        self.velocity = direction*self.maxSpeed
        self.actor.lookAt(self.velocity)
        self.walking = True

    def update(self, dt):
        GameObject.update(self, dt, fluid = True)
        if self.range is not None:
            diff = self.root.getPos(render) - self.startPos
            if diff.lengthSquared() > self.rangeSq:
                self.health = 0

    def impact(self, impactee):
        selfPos = self.root.getPos(render)
        damageVal = -self.damage
        if self.damageByTime:
            damageVal *= globalClock.getDt()

        if impactee is not None:
            impactee.alterHealth(damageVal, (impactee.root.getPos(render) - selfPos).normalized() * self.knockback,
                              self.flinchValue)

        if self.aoeRadius > 0:
            if self.blastModel is not None:
                Common.framework.currentLevel.addBlast(self.blastModel,
                                                       max(0.01, self.aoeRadius - 0.7),
                                                       self.aoeRadius + 0.2,
                                                       0.15,
                                                       selfPos)
                self.blastModel = None
            aoeRadiusSq = self.aoeRadius*self.aoeRadius
            for other in Common.framework.currentLevel.enemies:
                if other is not impactee:
                    diff = other.root.getPos(render) - selfPos
                    distSq = diff.lengthSquared()
                    if distSq < aoeRadiusSq:
                        perc = distSq/aoeRadiusSq
                        other.alterHealth(damageVal*perc, diff.normalized()*self.knockback*perc,
                                          self.flinchValue*perc)

        if self.maxHealth > 0:
            self.health = 0

    def cleanup(self):
        if self.blastModel is not None:
            self.blastModel.removeNode()
            self.blastModel = None

        if self.collider is not None and not self.collider.isEmpty():
            self.collider.clearPythonTag(TAG_OWNER)
            self.collider.removeNode()
        self.collider = None

        GameObject.cleanup(self)

