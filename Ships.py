
from panda3d.core import Vec3

from ShipSpec import ShipSpec

shipSpecs = []

# Light fighter
shipSpec = ShipSpec()
shipSpec.gunPositions = [
    (Vec3(-5, 1, -1), 2),
    (Vec3(5, 1, -1), 2),
    (Vec3(-5, 1, 1), 2),
    (Vec3(5, 1, 1), 2),
]
shipSpec.missilePositions = [
    Vec3(0, 1, -2),
]
shipSpec.maxEnergy = 200
shipSpec.shieldRechargeRate = 7
shipSpec.energyRechargeRate = 20
shipSpec.maxShields = 50
shipSpec.numMissiles = 5
shipSpec.maxSpeed = 25
shipSpec.turnRate = 200
shipSpec.acceleration = 60
shipSpec.cockpitModelFile = "STAND_IN/cockpit"
shipSpec.shipModelFileLowPoly = "test_completed_ship_a.gltf"
shipSpec.shipModelScalar = 0.2
shipSpec.shipModelRotation = 180
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
shipSpec.maxEnergy = 100
shipSpec.shieldRechargeRate = 10
shipSpec.energyRechargeRate = 15
shipSpec.maxShields = 100
shipSpec.numMissiles = 15
shipSpec.maxSpeed = 18
shipSpec.turnRate = 150
shipSpec.acceleration = 40
shipSpec.cockpitModelFile = "STAND_IN/cockpit"
shipSpec.shipModelFileLowPoly = "test_completed_ship_a.gltf"
shipSpec.shipModelScalar = 0.2
shipSpec.shipModelRotation = 180
shipSpec.weaponSoundBlastersFileName = "Assets/Section2/sounds/playerAttackBlastersSome.ogg"

shipSpecs.append(shipSpec)

# Heavy missile-platform
shipSpec = ShipSpec()
shipSpec.gunPositions = [
    (Vec3(-33, -25.857, 10.9223), 0),
    (Vec3(33, -25.857, 10.9223), 0),
]
shipSpec.missilePositions = [
    Vec3(-6.88961, -20.92, 17.737),
    Vec3(-3.79584, -20.9288, 18.6035),
    Vec3(6.88961, -20.92, 17.737),
    Vec3(3.79584, -20.9288, 18.6035),
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
shipSpec.weaponSoundBlastersFileName = "Assets/Section2/sounds/playerAttackBlastersOne.ogg"

shipSpecs.append(shipSpec)
