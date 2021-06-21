
from panda3d.core import Vec4, Vec3, Vec2, Plane, Point3, BitMask32
from panda3d.core import CollisionSphere, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue
from panda3d.core import TextureStage
from panda3d.core import ColorBlendAttrib

from Section2.GameObject import GameObject, ArmedObject
from Section2.CommonValues import *
from Section2.Common import Common

import random, math

class Enemy(GameObject, ArmedObject):
    def __init__(self, pos, modelName, maxHealth, maxSpeed, colliderName, size):
        GameObject.__init__(self, pos, modelName, None, maxHealth, maxSpeed, colliderName,
                            MASK_INTO_ENEMY | MASK_FROM_PLAYER | MASK_FROM_ENEMY, size)
        ArmedObject.__init__(self)

        self.colliderNP.node().setFromCollideMask(MASK_WALLS | MASK_FROM_ENEMY)

        Common.framework.pusher.addCollider(self.colliderNP, self.root)
        Common.framework.traverser.addCollider(self.colliderNP, Common.framework.pusher)

        colliderNode = CollisionNode("lock sphere")
        solid = CollisionSphere(0, 0, 0, size*2)
        solid.setTangible(False)
        colliderNode.addSolid(solid)
        self.lockColliderNP = self.root.attachNewNode(colliderNode)
        self.lockColliderNP.setPythonTag(TAG_OWNER, self)
        colliderNode.setFromCollideMask(0)
        colliderNode.setIntoCollideMask(MASK_ENEMY_LOCK_SPHERE)

        self.setFlinchPool(10, 15)

        self.attackAnimsPerWeapon = {}

        self.flinchAnims = []
        self.flinchTimer = 0

        self.shields = []
        self.shieldDuration = 0.5

        self.movementNames = ["walk"]

        self.setupExplosion()

    def setupExplosion(self):
        self.explosion = None

    def setFlinchPool(self, minVal, maxVal):
        self.flinchPoolMin = minVal
        self.flinchPoolMax = maxVal

        self.resetFlinchCounter()

    def resetFlinchCounter(self):
        self.flinchCounter = random.uniform(self.flinchPoolMin, self.flinchPoolMax)

    def alterHealth(self, dHealth, incomingImpulse, knockback, flinchValue, overcharge = False):
        GameObject.alterHealth(self, dHealth, incomingImpulse, knockback, flinchValue, overcharge)

        self.flinchCounter -= flinchValue
        if self.flinchCounter <= 0:
            self.resetFlinchCounter()
            self.flinch()

        if dHealth < 0 and incomingImpulse is not None:
            shield = Common.framework.showBase.loader.loadModel("Assets/Section2/models/shield")
            shield.setScale(self.size)
            shield.reparentTo(self.root)
            shield.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
            shield.lookAt(Common.framework.showBase.render,
                          self.root.getPos(Common.framework.showBase.render) + incomingImpulse)
            shield.setBin("unsorted", 1)
            shield.setDepthWrite(False)
            self.shields.append([shield, 0])

    def flinch(self):
        if len(self.flinchAnims) > 0 and self.flinchTimer <= 0:
            anim = random.choice(self.flinchAnims)
            if self.inControl:
                self.velocity.set(0, 0, 0)
            self.inControl = False
            self.walking = False
            self.flinchTimer = 2

    def update(self, player, dt):
        GameObject.update(self, dt)
        ArmedObject.update(self, dt)

        if self.flinchTimer > 0:
            self.flinchTimer -= dt

        if self.inControl and self.flinchTimer <= 0:
            self.runLogic(player, dt)

        for index, (shield, timer) in enumerate(self.shields):
            timer += dt
            perc = timer / self.shieldDuration
            shield.setTexOffset(TextureStage.getDefault(), perc*3)
            shield.setAlphaScale(1.0 - perc)
            self.shields[index][1] = timer
        self.shields = [[shield, timer] for shield, timer in self.shields if timer < self.shieldDuration]

    def runLogic(self, player, dt):
        pass

    def attackPerformed(self, weapon):
        ArmedObject.attackPerformed(self, weapon)

        if self.attackSound is not None:
            self.attackSound.play()

    def onDeath(self):
        explosion = self.explosion
        self.explosion = None
        explosion.activate(self.velocity, self.root.getPos(Common.framework.showBase.render))
        Common.framework.currentLevel.explosions.append(explosion)
        self.walking = False

    def cleanup(self):
        self.lockColliderNP.clearPythonTag(TAG_OWNER)
        ArmedObject.cleanup(self)
        GameObject.cleanup(self)

class FighterEnemy(Enemy):
    STATE_ATTACK = 0
    STATE_BREAK_AWAY = 1
    STATE_FLEE = 2

    def __init__(self, pos, modelName, maxHealth, maxSpeed, colliderName, size):
        Enemy.__init__(self, pos, modelName, maxHealth, maxSpeed, colliderName, size)

        self.acceleration = 100.0

        self.turnRate = 200.0

        self.yVector = Vec2(0, 1)

        self.steeringRayNPs = []

        self.steeringQueue = CollisionHandlerQueue()

        self.state = FighterEnemy.STATE_ATTACK
        self.breakAwayTimer = 0
        self.breakAwayMaxDuration = 5

        self.evasionDuration = 2
        self.evasionDurationVariability = 0.2
        self.evasionTimer = 0
        self.evasionDirection = (0, 0)

        for i in range(4):
            ray = CollisionSegment(0, 0, 0, 0, 1, 0)

            rayNode = CollisionNode("steering ray")
            rayNode.addSolid(ray)

            rayNode.setFromCollideMask(MASK_WALLS)
            rayNode.setIntoCollideMask(0)

            rayNodePath = self.actor.attachNewNode(rayNode)

            #rayNodePath.show()

            self.steeringRayNPs.append(rayNodePath)

        Common.framework.traverser.addCollider(rayNodePath, self.steeringQueue)

    def runLogic(self, player, dt):
        Enemy.runLogic(self, player, dt)

        selfPos = self.root.getPos(Common.framework.showBase.render)
        playerPos = player.root.getPos()
        playerVel = player.velocity
        playerQuat = player.root.getQuat(Common.framework.showBase.render)
        playerForward = playerQuat.getForward()
        playerUp = playerQuat.getUp()
        playerRight = playerQuat.getRight()

        testWeapon = self.weaponSets[0][0]

        ### With thanks to a post on GameDev.net for this algorithm.
        ### Specifically, the post was by "alvaro", and at time of
        ### writing should be found here:
        ### https://www.gamedev.net/forums/topic/401165-target-prediction-system-target-leading/3662508/
        shotSpeed = testWeapon.projectileTemplate.maxSpeed

        vectorToPlayer = playerPos - selfPos

        quadraticA = shotSpeed*shotSpeed - playerVel.lengthSquared()
        quadraticB = -2*playerVel.dot(vectorToPlayer)
        quadraticC = -vectorToPlayer.lengthSquared()

        quadraticResult = (quadraticB + math.sqrt(quadraticB*quadraticB - 4*quadraticA*quadraticC)) / (2*quadraticA)

        targetPt = playerPos + playerVel*quadraticResult

        ### End of GameDev.net algorithm

        vectorToTargetPt = targetPt - selfPos

        distanceToPlayer = vectorToTargetPt.length()

        quat = self.root.getQuat(Common.framework.showBase.render)
        forward = quat.getForward()
        up = quat.getUp()
        right = quat.getRight()

        angleToPlayer = forward.angleDeg(vectorToTargetPt.normalized())
        angleFromPlayer = playerForward.angleDeg(vectorToPlayer.normalized())

        fireWeapon = False
        if len(self.weaponSets) > 0:
            if distanceToPlayer < testWeapon.desiredRange:
                if angleToPlayer < 30:
                    fireWeapon = True

        if fireWeapon:
            self.startFiringSet(0)
        else:
            self.ceaseFiringSet(0)

        if self.inControl:
            self.walking = True
            if self.state == FighterEnemy.STATE_ATTACK:
                if distanceToPlayer < testWeapon.desiredRange*0.3:
                    self.state = FighterEnemy.STATE_BREAK_AWAY
                    self.breakAwayTimer = self.breakAwayMaxDuration
                else:
                    self.turnTowards(targetPt, self.turnRate, dt)
            elif self.state == FighterEnemy.STATE_BREAK_AWAY:
                self.evasionTimer -= dt
                if self.evasionTimer <= 0:
                    self.evasionTimer = self.evasionDuration + random.uniform(-self.evasionDurationVariability, self.evasionDurationVariability)
                    self.evasionDirection = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
                self.breakAwayTimer -= dt
                if angleFromPlayer > 150:
                    self.turnTowards(selfPos + playerRight*self.evasionDirection[0] + playerUp*self.evasionDirection[1], self.turnRate, dt)
                elif angleToPlayer < 120:
                    self.turnTowards(selfPos - vectorToPlayer, self.turnRate, dt)
                if distanceToPlayer > testWeapon.desiredRange*7 or self.breakAwayTimer <= 0:
                    self.state = FighterEnemy.STATE_ATTACK
            elif self.state == FighterEnemy.STATE_FLEE:
                pass

            self.velocity += forward*self.acceleration*dt

    def cleanup(self):
        if self.explosion is not None:
            self.explosion.cleanup()
            self.explosion = None

        for np in self.steeringRayNPs:
            Common.framework.traverser.removeCollider(np)
            np.removeNode()
        self.steeringRayNPs = []
        self.steeringQueue = None
        Enemy.cleanup(self)

