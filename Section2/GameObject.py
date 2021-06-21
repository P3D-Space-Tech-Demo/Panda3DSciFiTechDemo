from panda3d.core import Vec4, Vec3, Vec2, Plane, Point3, BitMask32
from direct.actor.Actor import Actor
from panda3d.core import CollisionSphere, CollisionCapsule, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode
from panda3d.core import AudioSound
from panda3d.core import PointLight
from panda3d.core import NodePath, PandaNode
from panda3d.core import Quat

from Section2.CommonValues import *
from Section2.Common import Common

import math, random

FRICTION = 10.0

class GameObject():
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName, weaponIntoMask, size):
        self.root = Common.framework.showBase.render.attachNewNode(PandaNode("obj"))

        self.colliderName = colliderName

        self.modelName = modelName

        if modelName is None:
            self.actor = NodePath(PandaNode("actor"))
        elif modelAnims is None:
            self.actor = Common.framework.showBase.loader.loadModel(modelName)
        else:
            self.actor = Actor(modelName, modelAnims)
        self.actor.reparentTo(self.root)

        if pos is not None:
            self.root.setPos(pos)

        self.maxHealth = maxHealth
        self.health = maxHealth
        self.healthRechargeRate = 2.0

        self.healthRechargeSuppressionTimer = 0
        self.healthRechargeSuppressionDuration = 0.5

        self.maxSpeed = maxSpeed

        self.terminalVelocity = 50

        self.flinchCounter = 0

        self.velocity = Vec3(0, 0, 0)
        self.acceleration = 300.0

        self.inControl = True
        self.outOfControlTimer = 0

        self.walking = False

        self.size = size

        if colliderName is not None:
            colliderNode = CollisionNode(colliderName)
            colliderNode.addSolid(CollisionSphere(0, 0, 0, size))
            self.colliderNP = self.root.attachNewNode(colliderNode)
            self.colliderNP.setPythonTag(TAG_OWNER, self)
            colliderNode.setFromCollideMask(0)
            colliderNode.setIntoCollideMask(weaponIntoMask)
            #self.colliderNP.show()
        else:
            self.colliderNP = self.root.attachNewNode(PandaNode("stand-in"))

        self.deathSound = None

    def physicalImpact(self, surfaceNormal):
        proj = self.velocity.project(surfaceNormal)
        self.velocity -= proj*2

    def update(self, dt, fluid = False):
        speed = self.velocity.length()

        if self.inControl:
            if self.walking and speed > self.maxSpeed:
                self.velocity.normalize()
                self.velocity *= self.maxSpeed
                speed = self.maxSpeed
        else:
            if speed > self.terminalVelocity:
                self.velocity.normalize()
                self.velocity *= self.terminalVelocity
                speed = self.terminalVelocity

        if Common.useFriction:
            if not self.walking:
                perc = speed/self.maxSpeed
                frictionVal = FRICTION*dt/(max(1, perc*perc))
                if not self.inControl:
                    frictionVal *= 0.8
                if frictionVal > speed:
                    self.velocity.set(0, 0, 0)
                else:
                    frictionVec = -self.velocity
                    frictionVec.normalize()
                    frictionVec *= frictionVal

                    self.velocity += frictionVec

        if not self.inControl:
            if speed < 0.1:
                self.inControl = True
            else:
                self.outOfControlTimer -= dt
                if self.outOfControlTimer <= 0:
                    self.inControl = True

        if fluid:
            self.root.setFluidPos(self.root.getPos() + self.velocity*dt)
        else:
            self.root.setPos(self.root.getPos() + self.velocity*dt)

        if self.healthRechargeSuppressionTimer > 0:
            self.healthRechargeSuppressionTimer -= dt
        else:
            self.alterHealth(self.healthRechargeRate*dt, None, 0, 0)

    def alterHealth(self, dHealth, incomingImpulse, knockback, flinchValue, overcharge = False):
        previousHealth = self.health

        self.health += dHealth

        if incomingImpulse is not None and knockback > 0.1:
            self.velocity += incomingImpulse*knockback
            self.inControl = False
            self.outOfControlTimer = knockback*0.1
            self.walking = False

        if dHealth < 0:
            self.healthRechargeSuppressionTimer = self.healthRechargeSuppressionDuration
            if self.health < 0:
                self.health = 0

        if flinchValue > 0:
            self.flinchCounter -= flinchValue

        if dHealth > 0 and self.health > self.maxHealth and not overcharge:
            self.health = self.maxHealth
        if previousHealth > 0 and self.health <= 0 and self.deathSound is not None:
            self.deathSound.play()

    def turnTowards(self, target, turnRate, dt):
        if isinstance(target, NodePath):
            target = target.getPos(Common.framework.showBase.render)
        elif isinstance(target, GameObject):
            target = target.root.getPos(Common.framework.showBase.render)
        diff = target - self.root.getPos(Common.framework.showBase.render)

        selfQuat = self.root.getQuat(Common.framework.showBase.render)
        selfForward = selfQuat.getForward()

        axis = selfForward.cross(diff.normalized())
        axis.normalize()
        if axis.lengthSquared() < 0.1:
            return

        angle = selfForward.signedAngleDeg(diff.normalized(), axis)
        quat = Quat()
        angle = math.copysign(min(abs(angle), turnRate*dt), angle)
        quat.setFromAxisAngle(angle, axis)
        newQuat = selfQuat*quat
        self.root.setQuat(Common.framework.showBase.render, newQuat)

    def getAngleWithVec(self, vec):
        forward = self.actor.getQuat(Common.framework.showBase.render).getForward()
        forward2D = Vec2(forward.x, forward.y)
        vec = Vec2(vec.x, vec.y)
        vec.normalize()
        angle = forward2D.signedAngleDeg(vec)
        return angle

    def cleanup(self):
        if self.colliderNP is not None and not self.colliderNP.isEmpty():
            self.colliderNP.clearPythonTag(TAG_OWNER)
            self.colliderNP.removeNode()
        self.colliderNP = None

        if self.actor is not None:
            if isinstance(self.actor, Actor):
                self.actor.cleanup()
            self.actor.removeNode()
            self.actor = None

        if self.root is not None:
            self.root.removeNode()
            self.root = None

class ArmedObject():
    def __init__(self):
        self.weaponSets = []

        self.weaponNPs = {}

        self.lockedTarget = None

    def weaponFired(self, weapon):
        pass

    def weaponReset(self, weapon):
        pass

    def addWeapon(self, weapon, setIndex, sourceNP):
        while len(self.weaponSets) <= setIndex:
            self.weaponSets.append([])
        self.weaponSets[setIndex].append(weapon)
        self.weaponNPs[weapon] = sourceNP

    def startFiringSet(self, weaponSet):
        if weaponSet < len(self.weaponSets):
            for weapon in self.weaponSets[weaponSet]:
                if not weapon.active:
                    weapon.triggerPressed(self)

    def ceaseFiringSet(self, weaponSet):
        if weaponSet < len(self.weaponSets):
            for weapon in self.weaponSets[weaponSet]:
                if weapon.active:
                    weapon.triggerReleased(self)

    def update(self, dt):
        for weaponSet in self.weaponSets:
            for weapon in weaponSet:
                weapon.update(dt, self)

    def attackPerformed(self, weapon):
        pass

    def cleanup(self):
        for weaponSet in self.weaponSets:
            for weapon in weaponSet:
                weapon.cleanup()
        self.weaponSets = []

        self.weaponNPs = {}

class Blast():
    def __init__(self, model, minSize, maxSize, duration):
        self.model = model
        self.model.setTwoSided(True)
        self.model.setTransparency(True)
        self.model.setBillboardPointEye()
        self.minSize = minSize
        self.maxSize = maxSize
        self.sizeRange = self.maxSize - self.minSize
        self.duration = duration
        self.timer = duration

    def update(self, dt):
        self.timer -= dt
        if self.timer < 0:
            self.timer = 0
        perc = 1.0 - (self.timer / self.duration)

        self.model.setScale(self.minSize + self.sizeRange*perc)

        self.model.setAlphaScale(math.sin(perc*3.142))

    def cleanup(self):
        if self.model is not None:
            self.model.removeNode()
            self.model = None