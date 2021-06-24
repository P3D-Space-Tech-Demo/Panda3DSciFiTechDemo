from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from direct.interval.IntervalGlobal import *
from direct.particles.ParticleEffect import ParticleEffect
import random
import array
import os

load_prc_file_data("",
"""
sync-video false
# win-size 1680 1050
# win-size 2560 1440
# fullscreen true
framebuffer-multisample 1
multisamples 4
""")

import simplepbr

base = ShowBase()
base.pipeline = simplepbr.init()

gameController = None

currentSection = None

def loadParticles(fileName):
    extension = "ptf"
    directory = "Particles/"
    if not fileName.endswith(".{0}".format(extension)):
        fileName = "{0}.{1}".format(fileName, extension)
    fileName = "{0}{1}".format(directory, fileName)

    particleEffect = ParticleEffect()
    particleEffect.loadConfig(fileName)
    return particleEffect
