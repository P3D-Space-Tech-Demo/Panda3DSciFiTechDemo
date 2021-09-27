
from panda3d.core import Vec3

from ShipSpec import ShipSpec

shipSpecs = []

# Light fighter
shipSpec = ShipSpec()
shipSpec.gunPositions = [
    (Vec3(-6.64267, 30.6346, 6.96551), 2),
    (Vec3(6.64267, 30.6346, 6.96551), 2),
    (Vec3(-8.3686, 27.936, 9.3614), 2),
    (Vec3(8.3686, 27.936, 9.3614), 2),
]
shipSpec.missilePositions = [
    Vec3(-7.57812, -7.58767, 12.1647),
    Vec3(7.57812, -7.58767, 12.1647),
    Vec3(-6.37786, -7.58767, 15.1449),
    Vec3(6.37786, -7.58767, 15.1449)
]
shipSpec.enginePositions = [
    (Vec3(0, -25.4772, 12.6016), 1),
    (Vec3(3.76468, -23.5428, 15.4289), 0),
    (Vec3(-3.76468, -23.5428, 15.4289), 0),
    (Vec3(4.4059, -25.4772, 9.16152), 1),
    (Vec3(-4.4059, -25.4772, 9.16152), 1),
]
shipSpec.maxEnergy = 200
shipSpec.shieldRechargeRate = 7
shipSpec.energyRechargeRate = 20
shipSpec.maxShields = 50
shipSpec.numMissiles = 8
shipSpec.maxSpeed = 25
shipSpec.turnRate = 200
shipSpec.acceleration = 60
shipSpec.cockpitModelFile = "STAND_IN/cockpit"
shipSpec.shipModelFileLowPoly = "test_completed_ship_a.gltf"
shipSpec.shipModelScalar = 0.2
shipSpec.shipModelRotation = 180
shipSpec.shipModelOffset = Vec3(0, 0, -8.4625)
shipSpec.weaponSoundBlastersFileName = "Assets/Section2/sounds/playerAttackBlastersMany.ogg"

shipSpecs.append(shipSpec)

# Medium fighter
shipSpec = ShipSpec()
shipSpec.gunPositions = [
    (Vec3(-2, 1, -2), 1),
    (Vec3(0, 1, -2), 1),
    (Vec3(2, 1, -2), 1)
]
shipSpec.missilePositions = [
    Vec3(-2, 1, -2),
    Vec3(2, 1, -2),
]
shipSpec.enginePositions = [
    (Vec3(0, 51, 11), 1),
    (Vec3(-8.75, 46.5, 11.75), 0.75),
    (Vec3(8.75, 46.5, 11.75), 0.75),
]
shipSpec.maxEnergy = 100
shipSpec.shieldRechargeRate = 10
shipSpec.energyRechargeRate = 15
shipSpec.maxShields = 100
shipSpec.numMissiles = 20
shipSpec.maxSpeed = 18
shipSpec.turnRate = 150
shipSpec.acceleration = 40
shipSpec.cockpitModelFile = "STAND_IN/cockpit"
shipSpec.shipModelFileLowPoly = "test_completed_ship_a.gltf"
shipSpec.shipModelScalar = 0.2
shipSpec.shipModelRotation = 180
shipSpec.shipModelOffset = Vec3(0, 0, 0)
shipSpec.weaponSoundBlastersFileName = "Assets/Section2/sounds/playerAttackBlastersSome.ogg"

shipSpecs.append(shipSpec)

# Heavy missile-platform
shipSpec = ShipSpec()
shipSpec.gunPositions = [
    (Vec3(-33, 25.857, 10.9223), 0),
    (Vec3(33, 25.857, 10.9223), 0),
]
shipSpec.missilePositions = [
    Vec3(-6.88961, 20.92, 17.737),
    Vec3(-3.79584, 20.9288, 18.6035),
    Vec3(6.88961, 20.92, 17.737),
    Vec3(3.79584, 20.9288, 18.6035),
]
shipSpec.enginePositions = [
    (Vec3(0, -22.9886, 10.6874), 1),
    (Vec3(-5.62418, -20.5345, 10.5101), 0.5),
    (Vec3(5.62418, -20.5345, 10.5101), 0.5),
]
shipSpec.maxEnergy = 50
shipSpec.shieldRechargeRate = 20
shipSpec.energyRechargeRate = 7
shipSpec.maxShields = 200
shipSpec.numMissiles = 400
shipSpec.maxSpeed = 14
shipSpec.turnRate = 100
shipSpec.acceleration = 20
shipSpec.cockpitModelFile = "STAND_IN/cockpit"
shipSpec.shipModelFileLowPoly = "test_completed_ship_a.gltf"
shipSpec.shipModelScalar = 0.2
shipSpec.shipModelRotation = 180
shipSpec.shipModelOffset = Vec3(0, -14.421, -10.806)
shipSpec.weaponSoundBlastersFileName = "Assets/Section2/sounds/playerAttackBlastersOne.ogg"

shipSpecs.append(shipSpec)
