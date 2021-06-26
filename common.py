from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from direct.interval.IntervalGlobal import *
from direct.stdpy import threading2
from direct.particles.ParticleEffect import ParticleEffect
import random
import array
import os
import time

load_prc_file_data("",
"""
sync-video false
# win-size 1680 1050
# win-size 2560 1440
# fullscreen true
framebuffer-multisample 1
multisamples 4
""")


base = ShowBase()
# load a scene shader
vert_shader = "Assets/Section1/shaders/simplepbr_vert_mod_1.vert"
frag_shader = "Assets/Section1/shaders/simplepbr_frag_mod_1.frag"
scene_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)
base.render.set_shader(scene_shader)

gameController = None

currentSection = None

options = {} # Dictionary of dictionaries of option-values
# In short: The first key indicates a section, and the section indicates the specific option.
optionCallbacks = {} # Again, a dictionary of dictionaries, this time of callback-pairs
# The keys are the same as used in "options", above

def getOption(sectionID, optionID):
    section = options.get(sectionID, None)
    if section is None:
        return None
    optionValue = section.get(optionID, None)
    return optionValue

def setOption(sectionID, optionID, newVal):
    section = options.get(sectionID, None)
    if section is None:
        return
    section[optionID] = newVal

def loadParticles(fileName):
    extension = "ptf"
    directory = "Particles/"
    if not fileName.endswith(".{0}".format(extension)):
        fileName = "{0}.{1}".format(fileName, extension)
    fileName = "{0}{1}".format(directory, fileName)

    particleEffect = ParticleEffect()
    particleEffect.loadConfig(fileName)
    return particleEffect
