from panda3d.core import Vec4, Vec3, Vec2, Plane, Point3, BitMask32
from direct.actor.Actor import Actor
from panda3d.core import CollisionSphere, CollisionCapsule, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode
from panda3d.core import AudioSound
from panda3d.core import PointLight
from panda3d.core import NodePath, PandaNode

from Section3.CommonValues import *
import common

import math, random

FRICTION = 150.0

class GameObject():
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName, height, weaponIntoMask):
        self.root = common.base.render.attachNewNode(PandaNode("obj"))

        self.colliderName = colliderName

        self.modelName = modelName

        if modelName is None:
            self.actor = NodePath(PandaNode("actor"))
        elif modelAnims is None:
            self.actor = common.base.loader.loadModel(modelName)
        else:
            self.actor = Actor(modelName, modelAnims)
        self.actor.reparentTo(self.root)

        if pos is not None:
            self.root.setPos(pos)

        self.height = height

        self.maxHealth = maxHealth
        self.health = maxHealth

        self.maxSpeed = maxSpeed

        self.terminalVelocity = 15

        self.flinchCounter = 0

        self.velocity = Vec3(0, 0, 0)
        self.acceleration = 300.0

        self.inControl = True

        self.walking = False

        self.noZVelocity = True

        if colliderName is not None:
            colliderNode = CollisionNode(colliderName)
            colliderNode.addSolid(CollisionCapsule(0, 0, 0, 0, 0, height, 0.3))
            self.weaponCollider = self.root.attachNewNode(colliderNode)
            self.weaponCollider.setPythonTag(TAG_OWNER, self)
            colliderNode.setFromCollideMask(0)
            colliderNode.setIntoCollideMask(weaponIntoMask)
            #self.weaponCollider.show()
        else:
            self.weaponCollider = self.root.attachNewNode(PandaNode("stand-in"))

        self.deathSound = None

        self.currentWeapon = None

    def update(self, dt, fluid = False):
        speed = self.velocity.length()
        if self.noZVelocity:
            self.velocity.setZ(0)

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

        if not self.inControl and speed < 0.1:
            self.inControl = True

        if fluid:
            self.root.setFluidPos(self.root.getPos() + self.velocity*dt)
        else:
            self.root.setPos(self.root.getPos() + self.velocity*dt)

    def alterHealth(self, dHealth, incomingImpulse, flinchValue, overcharge = False):
        previousHealth = self.health

        self.health += dHealth

        if incomingImpulse is not None and incomingImpulse.lengthSquared() > 0.1:
            self.velocity += incomingImpulse
            self.inControl = False
            self.walking = False

        if flinchValue > 0:
            self.flinchCounter -= flinchValue

        if dHealth > 0 and self.health > self.maxHealth and not overcharge:
            self.health = self.maxHealth
        if previousHealth > 0 and self.health <= 0 and self.deathSound is not None:
            self.deathSound.play()

    def turnTowards(self, target, turnRate, dt):
        if isinstance(target, NodePath):
            target = target.getPos(common.base.render)
        elif isinstance(target, GameObject):
            target = target.root.getPos(common.base.render)
        diff = target - self.root.getPos(common.base.render)

        angle = self.getAngleWithVec(diff)

        if abs(angle) < 1:
            return angle

        maxTurn = turnRate*dt
        if angle < 0:
            maxTurn = -maxTurn
            if angle > maxTurn:
                self.root.setH(self.root, angle)
                return 0
            else:
                self.root.setH(self.root, maxTurn)
                return angle-maxTurn
        else:
            if angle < maxTurn:
                self.root.setH(self.root, angle)
                return 0
            else:
                self.root.setH(self.root, maxTurn)
                return angle-maxTurn

    def getAngleWithVec(self, vec):
        forward = self.actor.getQuat(common.base.render).getForward()
        forward2D = Vec2(forward.x, forward.y)
        vec = Vec2(vec.x, vec.y)
        vec.normalize()
        angle = forward2D.signedAngleDeg(vec)
        return angle

    def destroy(self):
        if self.weaponCollider is not None and not self.weaponCollider.isEmpty():
            self.weaponCollider.clearPythonTag(TAG_OWNER)
            self.weaponCollider.removeNode()
        self.weaponCollider = None

        if self.actor is not None:
            if isinstance(self.actor, Actor):
                self.actor.cleanup()
            self.actor.removeNode()
            self.actor = None

        if self.root is not None:
            self.root.removeNode()
            self.root = None

class Walker():
    def __init__(self):

        colliderNode = CollisionNode(self.colliderName + "WallCollider")
        colliderNode.addSolid(CollisionSphere(0, 0, 0, 0.3))
        self.collider = self.root.attachNewNode(colliderNode)
        self.collider.setPythonTag(TAG_OWNER, self)
        colliderNode.setFromCollideMask(MASK_WALLS)
        colliderNode.setIntoCollideMask(0)

        self.collider.setZ(self.height*0.5)

        common.currentSection.pusher.addCollider(self.collider, self.root)
        common.currentSection.traverser.addCollider(self.collider, common.currentSection.pusher)

        self.ray = CollisionRay(0, 0, self.height/2, 0, 0, -1)

        rayNode = CollisionNode(self.colliderName + "Ray")
        rayNode.addSolid(self.ray)

        rayNode.setFromCollideMask(MASK_FLOORS)
        rayNode.setIntoCollideMask(0)

        self.rayNodePath = self.root.attachNewNode(rayNode)
        self.rayQueue = CollisionHandlerQueue()

        common.currentSection.traverser.addCollider(self.rayNodePath, self.rayQueue)

    def update(self, dt):
        if self.rayQueue.getNumEntries() > 0:
            self.rayQueue.sortEntries()
            rayHit = self.rayQueue.getEntry(0)
            hitPos = rayHit.getSurfacePoint(common.base.render)
            self.root.setZ(hitPos.z)

    def destroy(self):
        if self.collider is not None and not self.collider.isEmpty():
            self.collider.clearPythonTag(TAG_OWNER)
            common.currentSection.traverser.removeCollider(self.collider)
            common.currentSection.pusher.removeCollider(self.collider)

        common.currentSection.traverser.removeCollider(self.rayNodePath)

class ArmedObject():
    def __init__(self):

        self.currentWeapon = None
        self.currentWeaponIndex = -1

        self.weapons = []

        self.weaponNP = None

    def addWeapon(self, weapon):
        self.weapons.append(weapon)

    def setCurrentWeapon(self, index):
        if not self.weapons[index].isAvailable:
            return

        prevWasActive = False
        if self.currentWeapon is not None:
            prevWasActive = self.currentWeapon.active
            if prevWasActive:
                self.currentWeapon.triggerReleased(self)
            self.currentWeapon.deactivate(self)

        self.currentWeaponIndex = index
        self.currentWeapon = self.weapons[index]

        if self.currentWeapon is not None:
            self.currentWeapon.activate(self)
            if prevWasActive:
                self.currentWeapon.triggerPressed(self)

    def startAttacking(self):
        if self.currentWeapon is not None:
            if not self.currentWeapon.active:
                self.currentWeapon.triggerPressed(self)

    def endAttacking(self):
        if self.currentWeapon is not None:
            if self.currentWeapon.active:
                self.currentWeapon.triggerReleased(self)

    def update(self, dt):
        if self.currentWeapon is not None:
            self.currentWeapon.update(dt, self)

    def attackPerformed(self, weapon):
        pass

    def destroy(self):
        for weapon in self.weapons:
            weapon.destroy()
        self.weapons = []

        self.currentWeapon = None
        self.currentWeaponIndex = -1

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

    def destroy(self):
        if self.model is not None:
            self.model.removeNode()
            self.model = None