from panda3d.core import PandaNode, Shader

from Section3.UpdatingEffect import UpdatingEffect

import common

class ItemContents():
    def __init__(self, modelName):
        self.root = common.base.render.attachNewNode(PandaNode("obj"))
        self.actor = common.base.loader.loadModel(modelName)
        self.actor.reparentTo(self.root)
        self.actor.setLightOff(1)

        self.actor.setBillboardAxis()

        self.auraName = None

    def destroy(self):
        if self.root is not None:
            self.root.removeNode()
            self.root = None
        self.actor = None

    def onCollection(self, owner):
        pass

class HealthPotion(ItemContents):
    def __init__(self):
        ItemContents.__init__(self, "Assets/Section3/models/Items/healthPotion")
        self.healthValue = 30

    def onCollection(self, owner):
        if owner.health >= owner.maxHealth:
            return

        owner.alterHealth(self.healthValue, None, 0)

class CumulativeHealingEffect(UpdatingEffect):
    def __init__(self, duration, healthVal):
        UpdatingEffect.__init__(self, duration)

        self.healthVal = healthVal

    def update(self, owner, dt):
        owner.alterHealth(self.healthVal*dt, None, 0)

class RegenerationPotion(ItemContents):
    def __init__(self):
        ItemContents.__init__(self, "Assets/Section3/models/Items/healthPotion")
        self.actor.setColorScale(0.5, 0, 1, 1)

        self.effect = CumulativeHealingEffect(30, 2)

    def onCollection(self, owner):

        owner.addUpdatingEffect(self.effect)

    def destroy(self):
        if self.effect is not None:
            self.effect.destroy()
            self.effect = None

class Ammo(ItemContents):
    def __init__(self, weaponIndex, value, modelName):
        ItemContents.__init__(self, modelName)
        self.weaponIndex = weaponIndex
        self.value = value

        self.auraName = "auraAmmo"

    def onCollection(self, owner):
        if self.weaponIndex >= 0 and self.weaponIndex < len(owner.weapons):
            weapon = owner.weapons[self.weaponIndex]
            weapon.updateAmmoValue(self.value)

class WeaponPickup(ItemContents):
    def __init__(self, weaponIndex, modelName):
        ItemContents.__init__(self, modelName)

        self.weaponIndex = weaponIndex

        self.auraName = "auraWeapon"

    def onCollection(self, owner):
        if self.weaponIndex >= 0 and self.weaponIndex < len(owner.weapons):
            weapon = owner.weapons[self.weaponIndex]
            wasAvailable = weapon.isAvailable
            weapon.setAvailable(True)
            if not wasAvailable:
                owner.setCurrentWeapon(self.weaponIndex)