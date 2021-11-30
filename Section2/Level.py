
from panda3d.core import Vec3, Vec4, DirectionalLight, Filename, VirtualFileSystem

from Section2.GameObject import *
from Section2.Trigger import Trigger
from Section2.Spawner import Spawner
import Section2.SpecificEnemies as SpecificEnemies

from Section2 import TagHandler
import common

import importlib

from panda3d.core import TextNode

class Level():
    def __init__(self, levelFile):
        self.levelFile = levelFile

        self.geometry = NodePath(PandaNode("level root"))
        for index in range(5):
            loadedNP = common.models["{0}_{1}.egg.pz".format(levelFile, index)]
            del common.models["{0}_{1}.egg.pz".format(levelFile, index)]
            loadedNP.reparentTo(self.geometry)

        '''foundPartwiseFile = False
        index = 0
        fName = "Assets/Section2/levels/{0}_{1}".format(levelFile, index)
        virtualFS = VirtualFileSystem.getGlobalPtr()
        while virtualFS.exists(Filename("{0}.egg".format(fName))):
            foundPartwiseFile = True
            loadedNP = common.base.loader.loadModel(fName)
            loadedNP.reparentTo(self.geometry)
            index += 1
            fName = "Assets/Section2/levels/{0}_{1}".format(levelFile, index)
        if not foundPartwiseFile:
            loadedNP = common.base.loader.loadModel("Assets/Section2/levels/{0}".format(levelFile))
            loadedNP.reparentTo(self.geometry)'''
        self.geometry.reparentTo(common.base.render)
        #self.geometry.setShaderAuto()
        self.geometry.setShader(common.metal_shader)
        #mats = self.geometry.findAllMaterials()
        #for mat in mats:
        #    print (mat.getRoughness())
        #    mat.setRoughness(0.8)

        TagHandler.handleGeometryTags(self.geometry)

        try:
            self.scriptObj = importlib.import_module("Assets.Section2.levels.scripts.{0}".format(levelFile))
        except ImportError as e:
            print ("Error importing script-file " + levelFile)
            print (e)

        self.enemies = []

        self.deadEnemies = []

        self.particleSystems = []

        self.blasts = []

        self.projectiles = []

        self.passiveObjects = []

        self.items = []

        self.triggers = []

        self.explosions = []

        self.spawners = {}
        self.spawnerGroups = {}

        self.registeredSpawnables = {}

        if hasattr(SpecificEnemies, "spawnableDict"):
            for name, data in SpecificEnemies.spawnableDict.items():
                self.registeredSpawnables[name] = (data, True)

        self.geometryInterpreters = {
            "spawner" : self.buildSpawners,
            "trigger" : self.buildTriggers,
            "playerSpawnPoint" : self.setPlayerSpawnPoint,
            "exit" : self.setExit
        }

        if hasattr(SpecificEnemies, "buildDict"):
            for name, callback in SpecificEnemies.buildDict.items():
                self.geometryInterpreters[name] = callback

        self.spawnersToActivate = []

        self.interpretGeometry()

        light = DirectionalLight("directional light")
        light.setColor(Vec4(1, 1, 1, 1))
        self.lightNP = self.geometry.attachNewNode(light)
        self.lightNP.setHpr(135, -45, 0)
        self.geometry.setLight(self.lightNP)

        light2 = DirectionalLight("directional light")
        light2.setColor(Vec4(0.15, 0.15, 0.3, 1))
        self.light2NP = self.geometry.attachNewNode(light2)
        self.light2NP.setHpr(-135, 45, 0)
        self.geometry.setLight(self.light2NP)

        for spawnerName in self.spawnersToActivate:
            self.activateSpawner(spawnerName)

        self.spawnersToActivate = []

    def interpretGeometry(self):
        for key, callback in self.geometryInterpreters.items():
            nps = self.geometry.findAllMatches("**/={0}".format(key))
            callback(self, nps)

    def setPlayerSpawnPoint(self, level, spawnPtNPs):
        np = spawnPtNPs[0]
        self.playerSpawnPoint = np.getPos(common.base.render)

        for np in spawnPtNPs:
            np.removeNode()

    def setExit(self, level, exitNPs):
        np = exitNPs[0]
        exit = Trigger("exitTriggered", np, True, True)
        self.exit = exit

    def buildSpawners(self, level, spawnerNPs):
        for np in spawnerNPs:
            id = np.getTag("id")
            spawnerIsActive = np.getTag("active") == "True"
            spawnerGroupName = np.getTag("groupName")
            pos = np.getPos(common.base.render)
            h = np.getH(common.base.render)
            spawnerName = np.getName()

            np.removeNode()

            spawnableData, isEnemy = self.registeredSpawnables[id]
            spawner = Spawner(spawnableData, pos, h, isEnemy)

            self.spawners[spawnerName] = spawner
            if spawnerGroupName is not None and len(spawnerGroupName) > 0:
                if spawnerGroupName not in self.spawnerGroups:
                    self.spawnerGroups[spawnerGroupName] = []
                self.spawnerGroups[spawnerGroupName].append(spawner)

            if spawnerIsActive:
                self.spawnersToActivate.append(spawnerName)

    def activateSpawner(self, spawnerName):
        spawner = self.spawners.get(spawnerName, None)
        if spawner is not None:
            self.activateSpawnerInternal(spawner)

    def activateSpawnerInternal(self, spawner):
        if not spawner.isReady:
            return

        obj = spawner.spawnObj
        spawner.spawnObj = None
        spawner.isReady = False

        if spawner.objIsEnemy:
            self.enemies.append(obj)
            #obj.actor.play("spawn")
        else:
            if obj.auraName is not None:
                auraPath = obj.auraName
            else:
                auraPath = None
            item = Item(obj.root.getPos() + Vec3(0, 0, 1), auraPath, obj)
            self.items.append(item)
        obj.root.wrtReparentTo(self.geometry)

    def activateSpawnerGroup(self, groupName):
        spawnerList = self.spawnerGroups.get(groupName, None)
        if spawnerList is not None:
            for spawner in spawnerList:
                self.activateSpawnerInternal(spawner)

    def buildTriggers(self, level, triggerNPs):
        for np in triggerNPs:
            callbackName = np.getTag("callback")
            onlyOnce = np.getTag("onlyOnce") == "True"
            active = np.getTag("active") == "True"
            trigger = Trigger(callbackName, np, onlyOnce, active)
            self.triggers.append(trigger)

    def triggerActivated(self, trigger):
        if hasattr(self.scriptObj, trigger.callbackName):
            getattr(self.scriptObj, trigger.callbackName)(self)
        if trigger.onlyOnce:
            trigger.active = False

    def addBlast(self, model, minSize, maxSize, duration, pos):
        blast = Blast(model, minSize, maxSize, duration)
        blast.model.reparentTo(self.geometry.render)
        blast.model.setPos(pos)
        self.blasts.append(blast)
        blast.update(0)

    def update(self, player, keyMap, dt):
        if player is not None:
            # Player update

            player.update(keyMap, dt)

            # Enemy update

            [enemy.update(player, dt) for enemy in self.enemies]

            newlyDeadEnemies = [enemy for enemy in self.enemies if enemy.health <= 0]
            self.enemies = [enemy for enemy in self.enemies if enemy.health > 0]

            for enemy in newlyDeadEnemies:
                enemy.onDeath()

            self.deadEnemies += newlyDeadEnemies

            enemiesAnimatingDeaths = []
            for enemy in self.deadEnemies:
                GameObject.update(enemy, dt)
                enemy.destroy()
            self.deadEnemies = enemiesAnimatingDeaths

            # Projectile update

            [proj.update(dt) for proj in self.projectiles]

            [proj.destroy() for proj in self.projectiles if proj.maxHealth > 0 and proj.health <= 0]
            self.projectiles = [proj for proj in self.projectiles if proj.maxHealth <= 0 or proj.health > 0]

            # Passive object update

            [obj.update(dt) for obj in self.passiveObjects]

            [blast.update(dt) for blast in self.blasts]

            [blast.destroy() for blast in self.blasts if blast.timer <= 0]
            self.blasts = [blast for blast in self.blasts if blast.timer > 0]

            [explosion.update(dt) for explosion in self.explosions]
            [explosion.destroy() for explosion in self.explosions if not explosion.isAlive()]
            self.explosions = [explosion for explosion in self.explosions if explosion.isAlive()]

        [system.update(dt) for system in self.particleSystems]

    def destroy(self):
        for explosion in self.explosions:
            explosion.destroy()
        self.explosions = []

        if self.lightNP is not None:
            if self.geometry is not None:
                self.geometry.clearLight(self.lightNP)
            self.lightNP.removeNode()
            self.lightNP = None

        if self.geometry is not None:
#            self.geometry.removeNode()
            self.geometry.detachNode()
            self.geometry = None

        if self.exit is not None:
            self.exit.destroy()
            self.exit = None

        for blast in self.blasts:
            blast.destroy()
        self.blasts = []

        for trigger in self.triggers:
            trigger.destroy()
        self.triggers = []

        for spawner in self.spawners.values():
            spawner.destroy()
        self.spawners = {}
        self.spawnerGroups = {}

        for enemy in self.enemies:
            enemy.destroy()
        self.enemies = []

        for enemy in self.deadEnemies:
            enemy.destroy()
        self.deadEnemies = []

        for passive in self.passiveObjects:
            passive.destroy()
        self.passiveObjects = []

        for projectile in self.projectiles:
            projectile.destroy()
        self.projectiles = []
