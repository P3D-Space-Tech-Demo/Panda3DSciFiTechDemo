from panda3d.core import PandaNode, Vec3

from Section3.Enemy import ChasingEnemy
from Section3.GameObject import Walker, ArmedObject, GameObject, FRICTION
from Section3.Weapon import HitscanWeapon, ProjectileWeapon, Projectile

from Section3.CommonValues import *
import common

import random

class MeleeEnemyBasic(ChasingEnemy, Walker):
    def __init__(self):
        ChasingEnemy.__init__(self, Vec3(0, 0, 0),
                       "Assets/Section3/models/EnemyMeleeBasic/enemyMeleeBasic",
                       {
                        "stand" : "Assets/Section3/models/EnemyMeleeBasic/enemyMeleeBasic-stand",
                        "walk" : "Assets/Section3/models/EnemyMeleeBasic/enemyMeleeBasic-walk",
                        "attack" : "Assets/Section3/models/EnemyMeleeBasic/enemyMeleeBasic-attack",
                        "die" : "Assets/Section3/models/EnemyMeleeBasic/enemyMeleeBasic-die",
                        "spawn" : "Assets/Section3/models/EnemyMeleeBasic/enemyMeleeBasic-spawn",
                        "flinch1" : "Assets/Section3/models/EnemyMeleeBasic/enemyMeleeBasic-flinch"
                        },
                       50,
                       7.0,
                       "walkingEnemy",
                       1,
                        steeringFootHeight = 0.5)
        Walker.__init__(self)

        self.actor.setScale(0.6)

        weapon = HitscanWeapon(MASK_INTO_PLAYER, 15, 2.0, 0.75)
        weapon.setAvailable(True)
        self.addWeapon(weapon)
        self.setCurrentWeapon(0)

        self.attackAnimsPerWeapon[self.weapons[0]] = "attack"

        self.flinchAnims = [
            "flinch1"
        ]

        self.deathSound = loader.loadSfx("Assets/Section3/sounds/enemyDie.ogg")
        self.attackSound = loader.loadSfx("Assets/Section3/sounds/enemyAttack.ogg")

        self.weaponNP = self.actor.attachNewNode(PandaNode("weapon"))
        self.weaponNP.setZ(self.height*0.75)

    def update(self, player, dt):
        ChasingEnemy.update(self, player, dt)
        Walker.update(self, dt)

    def runLogic(self, player, dt):
        ChasingEnemy.runLogic(self, player, dt)

        spawnControl = self.actor.getAnimControl("spawn")
        if spawnControl is not None and spawnControl.isPlaying():
            return

    def destroy(self):
        Walker.destroy(self)
        ChasingEnemy.destroy(self)

class RangedEnemyBasic(ChasingEnemy, Walker):
    def __init__(self):
        ChasingEnemy.__init__(self, Vec3(0, 0, 0),
                       "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic",
                       {
                        "stand" : "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic-stand",
                        "walk" : "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic-walk",
                        "attack" : "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic-attack",
                        "die" : "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic-die",
                        "spawn" : "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic-spawn",
                        "strafeLeft" : "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic-strafeLeft",
                        "strafeRight" : "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic-strafeRight",
                        "flinch1" : "Assets/Section3/models/EnemyRangedBasic/enemyRangedBasic-flinch"
                        },
                       20,
                       5.0,
                       "walkingEnemy",
                       1,
                        steeringFootHeight = 0.5)
        Walker.__init__(self)

        self.movementNames.append("strafeLeft")
        self.movementNames.append("strafeRight")

        self.actor.setScale(0.6)

        projectile = Projectile("Assets/Section3/models/EnemyRangedBasic/shot", MASK_INTO_PLAYER, 20, 10, 10, 0.3, 1.0, 0, 0)
        weapon = ProjectileWeapon(projectile)
        weapon.desiredRange = 15
        weapon.setAvailable(True)
        self.addWeapon(weapon)
        self.setCurrentWeapon(0)

        self.attackAnimsPerWeapon[self.weapons[0]] = "attack"

        self.flinchAnims = [
            "flinch1"
        ]

        self.deathSound = loader.loadSfx("Assets/Section3/sounds/enemyDie.ogg")
        self.attackSound = loader.loadSfx("Assets/Section3/sounds/enemyAttack.ogg")

        self.weaponNP = self.actor.attachNewNode(PandaNode("weapon"))
        self.weaponNP.setZ(self.height*0.75)

        self.minStrafeInterval = 3
        self.maxStrafeInterval = 7
        self.strafeSpeed = 10
        self.resetStrafeIntervalTimer()
        self.strafeDuration = 0.2
        self.strafeTimer = 0

    def resetStrafeIntervalTimer(self):
        self.strafeIntervalTimer = random.uniform(self.minStrafeInterval, self.maxStrafeInterval)

    def update(self, player, dt):
        ChasingEnemy.update(self, player, dt)
        Walker.update(self, dt)

        if not self.inControl:
            self.strafeTimer = 0

    def runLogic(self, player, dt):
        spawnControl = self.actor.getAnimControl("spawn")
        if spawnControl is not None and spawnControl.isPlaying():
            return

        if self.strafeTimer > 0:
            self.strafeTimer -= dt
            if self.strafeTimer <= 0:
                self.actor.loop("stand")
        else:
            ChasingEnemy.runLogic(self, player, dt)

            self.strafeIntervalTimer -= dt
            if self.strafeIntervalTimer <= 0:
                self.resetStrafeIntervalTimer()
                if random.choice([True, False]):
                    direction = 1
                    anim = "strafeRight"
                else:
                    direction = -1
                    anim = "strafeLeft"
                self.velocity = self.root.getQuat(common.base.render).getRight()*direction*self.strafeSpeed
                self.actor.loop(anim)
                self.walking = True
                self.strafeTimer = self.strafeDuration

    def destroy(self):
        Walker.destroy(self)
        ChasingEnemy.destroy(self)