from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from direct.interval.IntervalGlobal import *
from direct.stdpy import threading2
from direct.filter.CommonFilters import CommonFilters
from direct.particles.ParticleEffect import ParticleEffect
import random
import array
import os
import time
import sys

load_prc_file_data("",
"""
sync-video false
fullscreen false
framebuffer-multisample 1
multisamples 4
""")


base = ShowBase()
# load a scene shader
vert_shader = "Assets/Shared/shaders/pbr_shader_v.vert"
frag_shader = "Assets/Shared/shaders/pbr_shader_f.frag"
invert_vert = "Assets/Shared/shaders/pbr_shader_v_invert.vert"
invert_frag = "Assets/Shared/shaders/pbr_shader_f_invert.frag"
metal_shader = Shader.load(Shader.SL_GLSL, invert_vert, invert_frag)
scene_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)
#base.render.set_shader(scene_shader)

scene_filters = CommonFilters(base.win, base.cam)

game_start_time = time.time()

gameController = None

currentSection = None

options = {} # Dictionary of dictionaries of option-values.
# In short: The first key indicates a section, and the section indicates the specific option.
optionCallbacks = {} # Again, a dictionary of dictionaries, this time of callback-pairs.
# The keys are the same as used in "options", above.
optionWidgets = {} # Once again, a dictionary of dictionaries, this time of UI-widgets in a list, and
# a callback ahead of them.
# The keys are the same as used in the two option-dictionaries above.

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
