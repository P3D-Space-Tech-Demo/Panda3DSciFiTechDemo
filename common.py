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

fancyFont = None
italiciseFont = False

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

def create_skybox(cube_map_name):

    coords = (
        (-1., 1., -1.), (1., 1., -1.), (1., 1., 1.), (-1., 1., 1.),
        (1., -1., -1.), (-1., -1., -1.), (-1., -1., 1.), (1., -1., 1.)
    )
    pos_data = array.array("f", [])

    for coord in coords:
        pos_data.extend(coord * 2)

    idx_data = array.array("H", [
        0, 1, 2,
        0, 2, 3,
        5, 0, 3,
        5, 3, 6,
        1, 4, 7,
        1, 7, 2,
        4, 5, 6,
        4, 6, 7,
        3, 2, 7,
        3, 7, 6,
        5, 4, 1,
        5, 1, 0
    ])

    array_format = GeomVertexArrayFormat()
    array_format.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
    array_format.add_column(InternalName.make("texcoord"), 3, Geom.NT_float32, Geom.C_texcoord)
    vertex_format = GeomVertexFormat()
    vertex_format.add_array(array_format)
    vertex_format = GeomVertexFormat.register_format(vertex_format)

    v_data = GeomVertexData("side_data", vertex_format, Geom.UH_static)
    v_data.unclean_set_num_rows(8)
    view = memoryview(v_data.modify_array(0)).cast("B").cast("f")
    view[:] = pos_data

    prim = GeomTriangles(Geom.UH_static)
    idx_array = prim.modify_vertices()
    idx_array.unclean_set_num_rows(len(idx_data))
    view = memoryview(idx_array).cast("B").cast("H")
    view[:] = idx_data

    geom = Geom(v_data)
    geom.add_primitive(prim)
    node = GeomNode("sky_box")
    node.add_geom(geom)
    skybox = NodePath(node)
    skybox.set_light_off()
    skybox.set_material_off()
    skybox.set_shader_off()
    skybox.set_bin("background", 0)
    skybox.set_depth_write(False)
    skybox.set_scale(10.)
    skybox.set_texture(base.loader.load_cube_map(cube_map_name))

    return skybox
