
import common

def spawnWave1(levelObj):
    levelObj.activateSpawnerGroup("wave1")

def spawnWave2(levelObj):
    levelObj.activateSpawnerGroup("wave2")

def spawnWave3(levelObj):
    levelObj.activateSpawnerGroup("wave3")

def spawnWave4(levelObj):
    levelObj.activateSpawnerGroup("wave4")

def spawnWave5(levelObj):
    levelObj.activateSpawnerGroup("wave5")

def exitTriggered(levelObj):
    common.currentSection.exitTriggered()