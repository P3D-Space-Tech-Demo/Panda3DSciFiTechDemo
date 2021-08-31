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

vert_shader = "Assets/Shared/shaders/pbr_clip_shader_v.vert"
frag_shader = "Assets/Shared/shaders/pbr_clip_shader_f.frag"
pbr_clip_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)

vert_shader = "Assets/Shared/shaders/portal_sphere.vert"
frag_shader = "Assets/Shared/shaders/portal_sphere.frag"
portal_sphere_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)

base.musicManager.setConcurrentSoundLimit(2)

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

base.particle_effect = ParticleEffect()

def start_particles(target_particle, in_model):
    base.enableParticles()
    base.particle_effect.cleanup()
    base.particle_effect = ParticleEffect()
    # swap .ptf files directly here to load different particle effects
    load_particle_config(target_particle, in_model)

def load_particle_config(filename, in_model, start_pos=Vec3(), inter_duration=1, inter_list=[], use_interval=False):
    if use_interval:
        base.particle_effect.loadConfig(filename)
        base.particle_effect.set_shader_off()
        base.particle_effect.set_pos(start_pos)
        particle_interval = ParticleInterval(base.particle_effect, in_model, 0, duration=inter_duration, softStopT=inter_duration/2)
        base.particle_seq = Sequence()
        base.particle_seq.append(particle_interval)
        base.particle_seq.start()

        inter_list.append(base.particle_seq)

    if not use_interval:
        base.particle_effect.loadConfig(filename)
        base.particle_effect.set_shader_off()

        # sets particles to birth relative to the model
        def sec_particle(duration):
            base.particle_effect.start(in_model)
            base.particle_effect.setPos(start_pos)
            time.sleep(duration)
            base.particle_effect.softStop()

        threading2._start_new_thread(sec_particle, (inter_duration,))

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

def create_sphere(segments):
    from math import pi, sin, cos

    v_format = GeomVertexFormat.get_v3()
    v_data = GeomVertexData("cube_data", v_format, Geom.UH_static)
    prim = GeomTriangles(Geom.UH_static)

    pos_data = array.array("f", [])
    idx_data = array.array("H", [])
    segs_half = max(2, segments // 2)
    segs = segs_half * 2

    angle = pi / segs_half
    angle_v = angle
    pos_data.extend([0., 0., 1.])

    for i in range(segs_half - 1):

        z = cos(angle_v)
        radius_h = sin(angle_v)
        angle_v += angle
        angle_h = 0.

        for j in range(segs):

            x = cos(angle_h) * radius_h
            y = sin(angle_h) * radius_h
            pos_data.extend([x, y, z])
            angle_h += angle

    pos_data.extend([0., 0., -1.])

    for i in range(segs - 1):
        idx_data.extend([0, i + 1, i + 2])

    idx_data.extend([0, segs, 1])

    for i in range(segs_half - 2):

        for j in range(segs - 1):
            k = 1 + i * segs + j
            l = k + segs
            idx_data.extend([k, l, k + 1, l, l + 1, k + 1])

        k = (i + 1) * segs
        l = k + segs
        idx_data.extend([k, l, k + 1 - segs, l, l + 1 - segs, k + 1 - segs])

    vertex_count = 1 + (segs_half - 1) * segs
    k = vertex_count - segs
    vertex_count += 1
    v_data.unclean_set_num_rows(vertex_count)
    view = memoryview(v_data.modify_array(0)).cast("B").cast("f")
    view[:] = pos_data

    for i in range(segs - 1):
        l = k + i
        idx_data.extend([l, vertex_count - 1, l + 1])

    idx_data.extend([vertex_count - 2, vertex_count - 1, vertex_count - 1 - segs])

    idx_array = prim.modify_vertices()
    idx_array.unclean_set_num_rows(len(idx_data))
    view = memoryview(idx_array).cast("B").cast("H")
    view[:] = idx_data

    geom = Geom(v_data)
    geom.add_primitive(prim)
    node = GeomNode("sphere_node")
    node.add_geom(geom)

    return node


# The following class is used to associate event handlers with event IDs.
class Event:

    events = {}

    def __init__(self, event_id, key, handler=None, group_id=""):
        self.id = event_id
        self.group_id = group_id
        self.default_key = key
        self.key = key
        self._handler = handler if handler else lambda: None
        self.events.setdefault(group_id, {})[event_id] = self

    @property
    def handler(self):
        return self._handler

    @handler.setter
    def handler(self, handler=None):
        self._handler = handler if handler else lambda: None


# The following class keeps track of key-bindings, such that they can easily be
# suppressed and restored (e.g. when pausing and resuming the demo, respectively).
# A dedicated DirectObject can be used to listen for key events instead of ShowBase
# by assigning it to `KeyBindings.listener`.
# Key-bindings can be divided into groups for convenience. If no group ID is
# specified in the calls to the class methods, a default ID ("") is used.
class KeyBindings:

    listener = base
    bindings = {}

    @classmethod
    def add(cls, event_id, key, group_id="", handler=None):
        event = Event(event_id, key, handler, group_id)
        cls.bindings.setdefault(group_id, {})[key] = event

    @classmethod
    def remove(cls, key, group_id=""):
        del cls.bindings[group_id][key]

        if not cls.bindings[group_id]:
            del cls.bindings[group_id]

    @classmethod
    def clear(cls, group_id=""):
        del cls.bindings[group_id]

    @classmethod
    def set_handler(cls, event_id, handler, group_id=""):
        if group_id not in Event.events:
            return

        events = Event.events[group_id]

        if event_id not in events:
            return

        event = events[event_id]
        event.handler = handler

    @classmethod
    def activate(cls, key, group_id="", once=False):
        event = cls.bindings.get(group_id, {}).get(key)

        if not event:
            return

        if once:
            cls.listener.accept_once(key, event.handler)
        else:
            cls.listener.accept(key, event.handler)

    @classmethod
    def activate_all(cls, group_id="", once=False):
        if once:
            for key, event in cls.bindings.get(group_id, {}).items():
                cls.listener.accept_once(key, event.handler)
        else:
            for key, event in cls.bindings.get(group_id, {}).items():
                cls.listener.accept(key, event.handler)

    @classmethod
    def deactivate(cls, key):
        cls.listener.ignore(key)

    @classmethod
    def deactivate_all(cls, group_id=""):
        if group_id is None:  # not recommended if cls.listener == base!!!
            cls.listener.ignore_all()
        else:
            for key in cls.bindings.get(group_id, {}):
                cls.listener.ignore(key)

    @classmethod
    def rebind(cls, key, event_id, group_id=""):
        if group_id not in cls.bindings:
            return

        group = cls.bindings[group_id]

        event = Event.events[group_id][event_id]
        old_key = event.key

        if key == old_key:
            return

        if key in group:
            old_event = group[key]
            old_event.key = None

        del group[old_key]
        group[key] = event

    @classmethod
    def reset(cls, event_id, group_id=""):
        if group_id not in cls.bindings:
            return

        group = cls.bindings[group_id]
        events = Event.events[group_id]

        if event_id not in events:
            return

        event = events[event_id]
        del group[event.key]
        event.key = event.default_key
        group[event.default_key] = event

    @classmethod
    def reset_all(cls, group_id=""):
        if group_id is None:
            for group_id, group in Event.events.items():
                for event_id in group:
                    cls.reset(event_id, group_id)
        elif group_id in Event.events:
            for event_id in Event.events[group_id]:
                cls.reset(event_id, group_id)

    setHandler = set_handler
    activateAll = activate_all
    deactivateAll = deactivate_all
    resetAll = reset_all


# The following class is a modification of PythonTask. Its purpose is to
# allow resuming (re-adding) a previously paused (removed) task without its
# internal timers being reset.
# Specifically, since `Task.time` is reset to zero when the task is re-added,
# a new `cont_time` variable adds the previous task duration to this value.
# This variable should therefore be used instead of `Task.time` for code that
# expects the elapsed time to continue increasing from where it left off when
# pausing the task.
# For delayed tasks, no changes to existing code need to be made, as it can
# rely on `Task.delay_time` being decreased by the previously elapsed task time
# upon resumption, as expected.
class ResumableTask(PythonTask):

    def __init__(self, task_func, task_id, delay=None, sort=0, priority=0, uponDeath=None, clock=None):
        def extended_func(task):
            return task_func(self)

        PythonTask.__init__(self, extended_func, task_id)

        self.clock = globalClock if clock is None else clock
        self.delay_time = delay
        self.sort = sort
        self.priority = priority
        self.set_upon_death(uponDeath if uponDeath else lambda task: None)
        self.paused_time = 0.
        self.paused_delay_time = 0.
        self.tmp_time = self.clock.get_real_time()
        self.is_paused = False

    def pause(self):
        if self.is_paused:
            return

        self.paused_time += self.time
        base.task_mgr.remove(self)

        if self.delay_time is None:
            self.paused_delay_time = 0.
        else:
            dt = self.clock.get_real_time() - self.tmp_time
            self.paused_delay_time = max(0., self.delay_time - dt)

        self.is_paused = True

    def resume(self):
        if not self.is_paused:
            return

        if self.delay_time is not None:
            self.delay_time = self.paused_delay_time

        base.task_mgr.add(self)
        self.tmp_time = self.clock.get_real_time()

        self.is_paused = False

    @property
    def cont_time(self):
        return self.time + self.paused_time


class TextManager:

    text_nodes = {}
    text_pages = []  # list of strings
    help_text = ""
    KeyBindings.add("toggle_help", "f1", "text", lambda: TextManager.toggle_text("context_help"))
    KeyBindings.add("advance_text", "f6", "text", lambda: TextManager.advance_text())
    KeyBindings.activate_all("text")
    text_alpha_start = {
        "context_help": 0.01,
        "multi_page": 0.01
    }
    text_alpha = {
        "context_help": 0.01,
        "multi_page": 0.01
    }
    # alpha increment values and scalar (-1. for decrement)
    text_alpha_incr = {
        "context_help": [0.01, 1.],
        "multi_page": [0.01, 1.]
    }

    @classmethod
    def add_text(cls, text_id, text):
        if text_id in cls.text_nodes:
            text_np = cls.text_nodes[text_id]
            text_np.detach_node()

        # directly make a text node to display text
        text_node = TextNode(text_id)

        if text_id == "multi_page":
            text_node.set_text(text.pop(0))
            cls.text_pages = text
            key = Event.events["text"]["advance_text"].key
            cls.text_nodes["context_help"].node().set_text(f"{key.upper()} to advance text")
            z = -.2
        else:
            text_node.set_text(text)
            cls.help_text = text
            z = -.1

        text_np = base.a2dTopLeft.attach_new_node(text_node)
        text_np.set_scale(0.05)
        text_np.set_pos(.05, 0., z)
        display_font = base.loader.loadFont("Assets/Shared/fonts/cinema-gothic-nbp-font/CinemaGothicNbpItalic-1ew2.ttf")
        # apply font
        text_node.set_font(display_font)

        cls.text_alpha_incr[text_id][1] = 1.
        cls.text_alpha[text_id] = cls.text_alpha_start[text_id]
        text_np.set_alpha_scale(cls.text_alpha[text_id])
        cls.text_nodes[text_id] = text_np
        cls.fade_in_text(text_id)

    @classmethod
    def remove_text(cls):
        for text_id in ("context_help", "multi_page"):
            if text_id in cls.text_nodes:
                text_np = cls.text_nodes[text_id]
                text_np.detach_node()
                del cls.text_nodes[text_id]

    @classmethod
    def fade_in_text(cls, text_id):
        if not text_id in cls.text_nodes:
            return

        text_np = cls.text_nodes[text_id]

        def text_alpha():
            for x in range(100):
                cls.text_alpha[text_id] += cls.text_alpha_incr[text_id][0]
                time.sleep(0.01)
                text_np.set_alpha_scale(cls.text_alpha[text_id])

        threading2._start_new_thread(text_alpha, ())

    @classmethod
    def fade_out_text(cls, text_id):
        if not text_id in cls.text_nodes:
            return

        text_np = cls.text_nodes[text_id]
        text_np.set_alpha_scale(cls.text_alpha[text_id])

        def text_alpha():
            for x in range(100):
                cls.text_alpha[text_id] -= cls.text_alpha_incr[text_id][0]
                time.sleep(0.01)
                text_np.set_alpha_scale(cls.text_alpha[text_id])

        threading2._start_new_thread(text_alpha, ())

    @classmethod
    def advance_text(cls):
        if "multi_page" not in cls.text_nodes:
            return

        text_np = cls.text_nodes["multi_page"]

        def text_alpha():
            for x in range(100):
                cls.text_alpha["multi_page"] -= cls.text_alpha_incr["multi_page"][0]
                time.sleep(0.01)
                text_np.set_alpha_scale(cls.text_alpha["multi_page"])

            if cls.text_pages:
                text_np.node().set_text(cls.text_pages.pop(0))
                for x in range(100):
                    cls.text_alpha["multi_page"] += cls.text_alpha_incr["multi_page"][0]
                    time.sleep(0.01)
                    text_np.set_alpha_scale(cls.text_alpha["multi_page"])
            else:
                text_np.detach_node()
                del cls.text_nodes["multi_page"]
                cls.text_nodes["context_help"].node().set_text(cls.help_text)

        threading2._start_new_thread(text_alpha, ())

    @classmethod
    def fade_text(cls, text_id):
        if not text_id in cls.text_nodes:
            return

        text_np = cls.text_nodes[text_id]

        def text_alpha():
            incr = cls.text_alpha_incr[text_id][1]

            while (cls.text_alpha[text_id] < 1.) if incr > 0. else (cls.text_alpha[text_id] > 0.):
                if cls.text_alpha_incr[text_id][1] != incr:
                    break
                cls.text_alpha[text_id] += cls.text_alpha_incr[text_id][0] * incr
                time.sleep(0.01)
                text_np.set_alpha_scale(cls.text_alpha[text_id])

        threading2._start_new_thread(text_alpha, ())

    @classmethod
    def toggle_text(cls, text_id):
        if not text_id in cls.text_nodes:
            return

        cls.text_alpha_incr[text_id][1] *= -1.
        cls.fade_text(text_id)

        # allow keeping the help text on screen until the associated key is released
        if text_id == "context_help" and cls.text_alpha_incr[text_id][1] > 0.:
            key = Event.events["text"]["toggle_help"].key

            def fade_out_help(task):
                base.accept_once(f"{key}-up", lambda: cls.toggle_text(text_id))

            # activate the "held down" mode after keeping the key pressed for half
            # a second
            base.task_mgr.add(fade_out_help, "fade_out_help", delay=.5)
            base.accept_once(f"{key}-up", lambda: base.task_mgr.remove("fade_out_help"))

    addText = add_text
    removeText = remove_text

'''def fade_in_text(label, text, duration):
    # directly make a text node to display text
    text_1 = TextNode(label)
    text_1.set_text(text)
    text_1_node = base.a2dTopLeft.attach_new_node(text_1)
    text_1_node.set_scale(0.05)
    text_1_node.set_pos(.05, 0, -.1)
    display_font = base.loader.loadFont("Assets/Shared/fonts/cinema-gothic-nbp-font/CinemaGothicNbpItalic-1ew2.ttf")
    # apply font
    text_1.set_font(display_font)

    text_1_node.set_alpha_scale(base.text_alpha)

    def text_alpha():
        for x in range(100):
            base.text_alpha += 0.01
            time.sleep(0.01)
            text_1_node.set_alpha_scale(base.text_alpha)

    threading2._start_new_thread(text_alpha, ())

def dismiss_info_text(text_node):
    t_node = base.a2dTopLeft.find(text_node)
    t_node.set_alpha_scale(base.text_alpha)

    def text_alpha():
        for x in range(100):
            base.text_alpha -= 0.01
            time.sleep(0.01)
            t_node.set_alpha_scale(base.text_alpha)

    threading2._start_new_thread(text_alpha, ())'''
