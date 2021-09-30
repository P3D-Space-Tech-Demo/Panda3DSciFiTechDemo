from panda3d.core import PandaNode, Vec4, Vec3, Vec2

from Section2.Enemy import FighterEnemy
from Section2.GameObject import ArmedObject, GameObject, FRICTION
from Section2.Weapon import ProjectileWeapon, Projectile
from Section2.Explosion import Explosion

from Section2.CommonValues import *
import common

import random

class BasicEnemyBlaster(ProjectileWeapon):
    def __init__(self):
        projectile = Projectile("Assets/Section2/models/blasterShotEnemy",
                                MASK_INTO_PLAYER,
                                100, 7, 60, 0.5, 0, 0,
                                0, "Assets/Section2/models/blast")
        ProjectileWeapon.__init__(self, projectile)

        self.firingPeriod = 0.5
        self.firingDelayPeriod = -1

class BasicEnemy(FighterEnemy):
    def __init__(self):
        FighterEnemy.__init__(self, Vec3(0, 0, 0),
                       "Assets/Section2/models/enemyFighter",
                              100,
                              20,
                              "enemy",
                              4)
        self.actor.setScale(0.5)

        self.deathSound = common.base.loader.loadSfx("Assets/Section2/sounds/enemyDie.ogg")

        weaponPoint = self.actor.find("**/weaponPoint")
        gun = BasicEnemyBlaster()
        self.addWeapon(gun, 0, weaponPoint)

        engineNPs = self.actor.findAllMatches("**/engineFlame*")
        self.engineData = []
        for np in engineNPs:
            scale = np.getScale().x
            np.setScale(1)
            pos = np.getPos()
            np.removeNode()

            flame = common.base.loader.loadModel("Assets/Shared/models/shipEngineFlame")
            flame.reparentTo(self.actor)
            flame.setPos(pos)
            glow = flame.find("**/glow")
            glow.setScale(scale, 1, scale)
            common.make_engine_flame(flame, Vec3(1, 0.75, 0.2), Vec4(1, 0.4, 0.1, 1))

            self.engineData.append((flame, scale))

        #self.colliderNP.show()

    def setupExplosion(self):
        shaderInputs = {
            "duration" : 1.25,
            "expansionFactor" : 7,
            "rotationRate" : 0.2,
            "fireballBittiness" : 1.8,
            "starDuration" : 0.4
        }

        randomVec1 = Vec2(random.uniform(0, 1), random.uniform(0, 1))
        randomVec2 = Vec2(random.uniform(0, 1), random.uniform(0, 1))

        self.explosion = Explosion(25, "explosion", shaderInputs, "noise", randomVec1, randomVec2)

    def update(self, player, dt):
        FighterEnemy.update(self, player, dt)
        diff = -self.actor.getQuat(render).getForward()
        #diff = fire.getRelativeVector(render, diff)
        for engineFlame, enginePower in self.engineData:
            fire = engineFlame.find("**/flame")
            common.update_engine_flame(fire, diff, enginePower)

    def runLogic(self, player, dt):
        FighterEnemy.runLogic(self, player, dt)

    def destroy(self):
        FighterEnemy.destroy(self)
