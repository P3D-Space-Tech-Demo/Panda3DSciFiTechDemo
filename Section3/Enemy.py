
from panda3d.core import Vec4, Vec3, Vec2, Plane, Point3, BitMask32
from panda3d.core import CollisionSphere, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue
from panda3d.core import Shader

from Section3.GameObject import GameObject, ArmedObject
from Section3.CommonValues import *

from Section3.Common import Common

import random

STEER_LEFT = 0
STEER_RIGHT = 1
STEER_UP = 2
STEER_DOWN = 3

class Enemy(GameObject, ArmedObject):
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName, height):
        GameObject.__init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName, height, MASK_INTO_ENEMY)
        ArmedObject.__init__(self)

        self.setFlinchPool(10, 15)

        self.attackAnimsPerWeapon = {}

        self.flinchAnims = []
        self.flinchTimer = 0

        self.movementNames = ["walk"]

    def setFlinchPool(self, minVal, maxVal):
        self.flinchPoolMin = minVal
        self.flinchPoolMax = maxVal

        self.resetFlinchCounter()

    def resetFlinchCounter(self):
        self.flinchCounter = random.uniform(self.flinchPoolMin, self.flinchPoolMax)

    def alterHealth(self, dHealth, incomingImpulse, flinchValue, overcharge = False):
        GameObject.alterHealth(self, dHealth, incomingImpulse, flinchValue, overcharge)

        self.flinchCounter -= flinchValue
        if self.flinchCounter <= 0:
            self.resetFlinchCounter()
            self.flinch()

    def flinch(self):
        if len(self.flinchAnims) > 0 and self.flinchTimer <= 0:
            anim = random.choice(self.flinchAnims)
            self.actor.play(anim)
            if self.inControl:
                self.velocity.set(0, 0, 0)
            self.inControl = False
            self.walking = False
            self.flinchTimer = self.actor.getDuration(anim)

    def update(self, player, dt):
        GameObject.update(self, dt)
        ArmedObject.update(self, dt)

        if self.flinchTimer > 0:
            self.flinchTimer -= dt

        if self.inControl and self.flinchTimer <= 0:
            self.runLogic(player, dt)

        if self.walking:
            aMovementIsPlaying = False
            for movementName in self.movementNames:
                control = self.actor.getAnimControl(movementName)
                if control.isPlaying():
                    aMovementIsPlaying = True
            if not aMovementIsPlaying:
                self.actor.loop("walk")
        else:
            spawnControl = self.actor.getAnimControl("spawn")
            if spawnControl is None or not spawnControl.isPlaying():
                attackControl = self.actor.getAnimControl("attack")
                if attackControl is None or not attackControl.isPlaying():
                    standControl = self.actor.getAnimControl("stand")
                    if standControl is not None and not standControl.isPlaying():
                        self.actor.loop("stand")

    def runLogic(self, player, dt):
        pass

    def attackPerformed(self, weapon):
        ArmedObject.attackPerformed(self, weapon)

        if weapon in self.attackAnimsPerWeapon:
            self.actor.play(self.attackAnimsPerWeapon[weapon])

        if self.attackSound is not None:
            self.attackSound.play()

    def cleanup(self):
        ArmedObject.cleanup(self)
        GameObject.cleanup(self)

class ChasingEnemy(Enemy):
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName, height,
                 steerDirs = [STEER_LEFT, STEER_RIGHT], steeringFootHeight = 0):
        Enemy.__init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName, height)

        self.steerDirs = steerDirs

        self.acceleration = 100.0

        self.turnRateWalking = 200.0
        self.turnRateStanding = 250.0

        self.yVector = Vec2(0, 1)

        self.steeringRayNPs = []

        self.steeringQueue = CollisionHandlerQueue()

        for i in range(4):
            ray = CollisionSegment(0, 0, 0, 0, 1, 0)

            rayNode = CollisionNode("steering ray")
            rayNode.addSolid(ray)

            rayNode.setFromCollideMask(MASK_WALLS)
            rayNode.setIntoCollideMask(0)

            rayNodePath = self.actor.attachNewNode(rayNode)

            if i % 2 == 0:
                rayNodePath.setX(-0.3)
            else:
                rayNodePath.setX(0.3)
            if i // 2 == 0:
                rayNodePath.setZ(height)
            else:
                rayNodePath.setZ(steeringFootHeight)

            #rayNodePath.show()

            self.steeringRayNPs.append(rayNodePath)

        Common.framework.traverser.addCollider(rayNodePath, self.steeringQueue)

    def runLogic(self, player, dt):
        Enemy.runLogic(self, player, dt)

        selfPos = self.root.getPos(Common.framework.showBase.render)

        vectorToPlayer = player.root.getPos() - selfPos

        vectorToPlayer2D = vectorToPlayer.getXy()
        distanceToPlayer = vectorToPlayer2D.length()

        vectorToPlayer2D.normalize()

        if self.currentWeapon is not None:
            if distanceToPlayer > self.currentWeapon.desiredRange*0.9:
                attackControl = self.actor.getAnimControl("attack")
                if not attackControl.isPlaying():
                    self.walking = True
                    quat = self.root.getQuat(Common.framework.showBase.render)
                    forward = quat.getForward()
                    if vectorToPlayer.dot(forward) > 0 and self.steeringQueue.getNumEntries() > 0:
                        self.steeringQueue.sortEntries()
                        entry = self.steeringQueue.getEntry(0)
                        hitPos = entry.getSurfacePoint(Common.framework.showBase.render)
                        right = quat.getRight()
                        up = quat.getUp()
                        dotRight = vectorToPlayer.dot(right)
                        if STEER_RIGHT in self.steerDirs and dotRight < 0:
                            self.velocity += right*self.acceleration*dt
                            self.root.setH(Common.framework.showBase.render, self.root.getH(Common.framework.showBase.render) + self.turnRateWalking*2*dt)
                        if STEER_LEFT in self.steerDirs and dotRight >= 0:
                            self.velocity -= right*self.acceleration*dt
                            self.root.setH(Common.framework.showBase.render, self.root.getH(Common.framework.showBase.render) - self.turnRateWalking*2*dt)
                        if STEER_UP in self.steerDirs:
                            self.velocity += up*self.acceleration*dt
                        if STEER_DOWN in self.steerDirs:
                            self.velocity -= up*self.acceleration*dt
                    else:
                        self.turnTowards(player, self.turnRateWalking, dt)
                        self.velocity += self.root.getQuat(Common.framework.showBase.render).getForward()*self.acceleration*dt

                self.endAttacking()
            else:
                self.turnTowards(player, self.turnRateStanding, dt)

                self.walking = False
                self.velocity.set(0, 0, 0)

                self.startAttacking()

    def cleanup(self):
        for np in self.steeringRayNPs:
            Common.framework.traverser.removeCollider(np)
            np.removeNode()
        self.steeringRayNPs = []
        self.steeringQueue = None
        Enemy.cleanup(self)

