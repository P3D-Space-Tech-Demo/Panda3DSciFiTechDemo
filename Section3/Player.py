from panda3d.core import PointLight
from panda3d.core import CollisionSphere, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue, CollisionTraverser
from panda3d.core import Vec4, Vec3, Vec2, Plane, Point3, BitMask32
from panda3d.core import PandaNode, NodePath
from panda3d.core import Shader
from panda3d.core import TextNode
from direct.actor.Actor import Actor

from direct.gui.OnscreenText import OnscreenText

from Section3.GameObject import GameObject, Walker, ArmedObject
from Section3.PlayerWeapons import RapidShotgunWeapon, BlasterWeapon
from Section3.SpecificItems import *

from Section3.CommonValues import *
from Section3.Common import Common

class Player(GameObject, Walker, ArmedObject):
    def __init__(self):
        GameObject.__init__(self,
                            Vec3(0, 0, 0),
                            None,
                            None,
                            100,
                            15,
                            "player",
                            1,
                            MASK_INTO_PLAYER)
        Walker.__init__(self)
        ArmedObject.__init__(self)

        self.weaponNP = self.actor

        light = PointLight("basic light")
        light.setColor(Vec4(1, 1, 1, 1))
        light.setAttenuation((1, 0.01, 0.005))
        self.lightNP = self.root.attachNewNode(light)
        self.lightNP.setZ(1)
        Common.framework.showBase.render.setLight(self.lightNP)

        self.collider.node().setFromCollideMask(MASK_WALLS | MASK_FROM_PLAYER)

        self.actor.setZ(self.height)

        Common.framework.showBase.camera.reparentTo(self.actor)
        Common.framework.showBase.camera.setPos(0, 0, 0)
        Common.framework.showBase.camera.setHpr(0, 0, 0)

        lens = Common.framework.showBase.camLens
        ratio = lens.getAspectRatio()

        lens.setFov(80*ratio)
        lens.setNear(0.03)

        self.lastMousePos = Vec2(0, 0)
        self.mouseSpeedHori = 50.0
        self.mouseSpeedVert = 30.0
        self.mouseSensitivity = 1.0

        self.healthLeft = -0.9
        self.healthRight = 0.9
        self.healthWidth = self.healthRight - self.healthLeft

        self.uiRoot = Common.framework.showBase.a2dBottomCenter.attachNewNode(PandaNode("player UI"))

        self.healthBar = Common.framework.showBase.loader.loadModel("Assets/Section3/models/healthBar")
        self.healthBar.reparentTo(self.uiRoot)
        self.healthBar.setZ(0.05)
        self.healthBar.setX(self.healthLeft)
        self.healthBar.getChild(0).setScale(self.healthWidth/6.0)

        self.weaponUIRoot = self.uiRoot.attachNewNode(PandaNode("player weapon UI"))
        self.weaponUIRoot.setPos(0, 0, 0.1)

        self.addWeapon(RapidShotgunWeapon(self.weaponUIRoot))
        self.addWeapon(BlasterWeapon(self.weaponUIRoot))

        self.weapons[0].setAvailable(True)

        self.setCurrentWeapon(0)

        self.updateHealthUI()

        self.inventory = []

        self.updatingEffects = []

        self.interactionSegment = CollisionSegment(0, 0, 0, 0, 1.5, 0)

        rayNode = CollisionNode("player interaction ray")
        rayNode.addSolid(self.interactionSegment)

        rayNode.setFromCollideMask(MASK_WALLS | MASK_FLOORS | MASK_INTO_ENEMY)
        rayNode.setIntoCollideMask(0)

        self.interactionSegmentNodePath = self.actor.attachNewNode(rayNode)
        #self.interactionSegmentNodePath.show()
        self.interactionSegmentQueue = CollisionHandlerQueue()

        self.interactionSegmentTraverser = CollisionTraverser()
        self.interactionSegmentTraverser.addCollider(self.interactionSegmentNodePath, self.interactionSegmentQueue)

        #self.hurtSound = loader.loadSfx("Sounds/FemaleDmgNoise.ogg")

    def update(self, keys, dt):
        GameObject.update(self, dt)

        self.walking = False

        quat = self.root.getQuat(Common.framework.showBase.render)
        forward = quat.getForward()
        right = quat.getRight()

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

        mouseWatcher = Common.framework.showBase.mouseWatcherNode
        if mouseWatcher.hasMouse():
            xSize = Common.framework.showBase.win.getXSize()
            ySize = Common.framework.showBase.win.getYSize()
            xPix = float(xSize % 2)/xSize
            yPix = float(ySize % 2)/ySize
            mousePos = Vec2(Common.framework.showBase.mouseWatcherNode.getMouse())
            mousePos.addX(-xPix)
            mousePos.addY(-yPix)
            if abs(mousePos.x) < xPix:
                mousePos.x = 0
            if abs(mousePos.y) < yPix:
                mousePos.y = 0

            Common.framework.showBase.win.movePointer(0, xSize//2, ySize//2)
        else:
            mousePos = self.lastMousePos

        self.root.setH(self.root.getH() - mousePos.x*self.mouseSpeedHori*self.mouseSensitivity)
        self.actor.setP(self.actor.getP() + mousePos.y*self.mouseSpeedVert*self.mouseSensitivity)

        if self.currentWeapon is not None:
            if keys["shoot"]:
                self.startAttacking()
            else:
                self.endAttacking()

        [effect.update(self, dt) for effect in self.updatingEffects]
        [effect.cleanup() for effect in self.updatingEffects if not effect.active]
        self.updatingEffects = [effect for effect in self.updatingEffects if effect.active]

    def attackPerformed(self, weapon):
        ArmedObject.attackPerformed(self, weapon)

    def postTraversalUpdate(self, dt):
        Walker.update(self, dt)
        ArmedObject.update(self, dt)

    def alterHealth(self, dHealth, incomingImpulse, flinchValue, overcharge = False):
        GameObject.alterHealth(self, dHealth, incomingImpulse, flinchValue, overcharge)

        self.updateHealthUI()

        #self.hurtSound.play()

    def updateHealthUI(self):
        perc = self.health/self.maxHealth
        self.healthBar.setSx(perc)
        self.healthBar.setColorScale(1.0 - (perc - 0.5)/0.5, min(1, perc/0.5), 0, 1)
        #self.healthCounter.setText("{0:-.0f}".format(self.health))
        #self.healthCounter.setColorScale(1.0 - (perc - 0.5)/0.5, min(1, perc/0.5), 0, 1)

    def scrollWeapons(self, direction):
        newIndex = (self.currentWeaponIndex + direction) % len(self.weapons)
        self.setCurrentWeapon(newIndex)

    def interact(self):
        self.interactionSegmentTraverser.traverse(Common.framework.showBase.render)

        if self.interactionSegmentQueue.getNumEntries() > 0:
            #print ("Hit something:")
            self.interactionSegmentQueue.sortEntries()
            rayHit = self.interactionSegmentQueue.getEntry(0)
            intoNP = rayHit.getIntoNodePath()
            if intoNP.hasPythonTag(TAG_OWNER):
                intoObj = intoNP.getPythonTag(TAG_OWNER)
                if intoObj is not None and hasattr(intoObj, "interact"):
                    intoObj.interact(self)

    def addUpdatingEffect(self, effect):
        self.updatingEffects.append(effect)
        effect.start(self)

    def cleanup(self):
        if self.uiRoot is not None:
            self.uiRoot.removeNode()
            self.uiRoot = None
        self.healthBar = None
        self.weaponUIRoot = None

        if self.lightNP is not None:
            Common.framework.showBase.render.clearLight(self.lightNP)
            self.lightNP.removeNode()
            self.lightNP = None

        for effect in self.updatingEffects:
            effect.cleanup()
        self.updatingEffects = []

        ArmedObject.cleanup(self)
        Walker.cleanup(self)
        GameObject.cleanup(self)
