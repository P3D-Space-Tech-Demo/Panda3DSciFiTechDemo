from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from direct.actor.Actor import Actor
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

vert_shader = "Assets/Shared/shaders/vertex_glow.vert"
frag_shader = "Assets/Shared/shaders/vertex_glow.frag"
vertex_glow_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)

vert_shader = "Assets/Shared/shaders/flame_glow.vert"
frag_shader = "Assets/Shared/shaders/flame_glow.frag"
flame_glow_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)

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

def make_glowing_np(np, shader_program = vertex_glow_shader):
    np.set_shader(shader_program)
    np.setLightOff(10)
    np.setBin("unsorted", 1)
    np.setDepthWrite(False)
    np.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))

def make_engine_flame(np, flameColourGradients, glowColour, flameScalar = 1.0/0.58957):
    glow = np.find("**/glow")
    flame = np.find("**/flame")

    if glow is not None and not glow.isEmpty():
        make_glowing_np(glow)
        glow.setColorScale(glowColour)
    if flame is not None and not flame.isEmpty():
        make_glowing_np(flame, shader_program = flame_glow_shader)
        flame.setShaderInput("flameColourGradients", flameColourGradients)
        flame.setShaderInput("flameScalar", flameScalar)
        update_engine_flame(flame, Vec2(0, 0), 0)

def update_engine_flame(flame_np, direction_vector, power):
    flame_np.set_shader_input("power", power)
    flame_np.set_shader_input("direction", direction_vector)

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
        particle_interval = ParticleInterval(base.particle_effect, in_model, 0, duration=inter_duration, softStopT=inter_duration/1.5)
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

    def __init__(self, event_id, key, key_str, handler=None, group_id=""):
        self.id = event_id
        self.group_id = group_id
        self.default_key = key
        self.key = key
        self.key_str = key_str
        self._handler = handler if handler else lambda: None

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
    events = {}
    keyboard_map = base.win.get_keyboard_map()

    @classmethod
    def add(cls, event_id, key, group_id="", handler=None):
        raw_key = f"raw-{key}"

        if "mouse" in key or "shift" in key or "control" in key or "alt" in key:
            raw_key = raw_key.replace("raw-", "")
            key_str = key.replace("mouse1", "mouse left")
            key_str = key_str.replace("mouse2", "mouse middle")
            key_str = key_str.replace("mouse3", "mouse right")
        else:
            mapped_key = cls.keyboard_map.get_mapped_button(key)
            key_str = cls.keyboard_map.get_mapped_button_label(key).lower()

        if not key_str:
            if mapped_key:
                key_str = str(mapped_key).lower()
            else:
                key_str = key

        key_str = key_str.replace("_", " ")
        event = Event(event_id, raw_key, key_str, handler, group_id)
        cls.events.setdefault(group_id, {})[event_id] = event

    @classmethod
    def remove(cls, event_id, group_id=""):
        if group_id not in cls.events:
            return False

        events = cls.events[group_id]

        if event_id not in events:
            return False

        del events[event_id]

        if not cls.events[group_id]:
            del cls.events[group_id]

        return True

    @classmethod
    def clear(cls, group_id=""):
        if group_id not in cls.events:
            return False

        del cls.events[group_id]

        return True

    @classmethod
    def set_handler(cls, event_id, handler, group_id=""):
        if group_id not in cls.events:
            return False

        events = cls.events[group_id]

        if event_id not in events:
            return False

        event = events[event_id]
        event.handler = handler

        return True

    @classmethod
    def activate(cls, event_id, group_id="", once=False):
        event = cls.events.get(group_id, {}).get(event_id)

        if not event:
            return False

        if once:
            cls.listener.accept_once(event.key, event.handler)
        else:
            cls.listener.accept(event.key, event.handler)

        return True

    @classmethod
    def activate_all(cls, group_id="", once=False):
        if once:
            for event in cls.events.get(group_id, {}).values():
                cls.listener.accept_once(event.key, event.handler)
        else:
            for event in cls.events.get(group_id, {}).values():
                cls.listener.accept(event.key, event.handler)

    @classmethod
    def deactivate(cls, event_id, group_id=""):
        event = cls.events.get(group_id, {}).get(event_id)

        if not event:
            return False

        cls.listener.ignore(event.key)

        return True

    @classmethod
    def deactivate_all(cls, group_id=""):
        if group_id is None:  # not recommended if cls.listener == base!!!
            cls.listener.ignore_all()
        else:
            for event in cls.events.get(group_id, {}).values():
                cls.listener.ignore(event.key)

    @classmethod
    def rebind(cls, key, event_id, group_id=""):
        if group_id not in cls.events:
            return False

        events = cls.events[group_id]
        event = events[event_id]
        group = {e.key: e for e in events}
        old_key = event.key

        if key == old_key:
            return False

        if key in group:
            group[key].key = ""

        event.key = key

        return True

    @classmethod
    def reset(cls, event_id, group_id=""):
        event = cls.events.get(group_id, {}).get(event_id)

        if not event:
            return False

        event.key = event.default_key

        return True

    @classmethod
    def reset_all(cls, group_id=""):
        if group_id is None:
            for events in cls.events.values():
                for event in events.values():
                    event.key = event.default_key
        elif group_id in cls.events:
            for event in cls.events[group_id].values():
                event.key = event.default_key

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
    text_parts = []  # list of strings
    help_text = ""
    KeyBindings.add("toggle_help", "f1", "text", lambda: TextManager.toggle_text())
    KeyBindings.add("advance_text", "f6", "text", lambda: TextManager.advance_text())
    fade_type = "in"
    fade_ivals = {}
    # define text color for highlighting key-bindings
    props_mgr = TextPropertiesManager.get_global_ptr()
    col_prop = TextProperties()
    col_prop.set_text_color((0, 1, 0, 1))
    props_mgr.set_properties("key", col_prop)

    @classmethod
    def add_text(cls, text_id, text, fade_in=.5):
        if text_id in cls.text_nodes:
            text_np = cls.text_nodes[text_id]
            text_np.detach_node()

        # directly make a text node to display text
        text_node = TextNode(text_id)
        text_node.set_shadow(0.1, 0.1)

        if text_id == "multi_part":
            text_node.set_text(text.pop(0))
            cls.text_parts = text
            key = KeyBindings.events["text"]["advance_text"].key_str
            cls.text_nodes["context_help"].node().set_text(f"\1key\1{key.title()}\2 to advance text")
            z = -.2
        else:
            text_node.set_text(text)
            z = -.1

        if text_id == "context_help":
            cls.help_text = text

        text_np = base.a2dTopLeft.attach_new_node(text_node)
        text_np.set_scale(0.05)
        text_np.set_pos(.05, 0., z)
        display_font = base.loader.load_font("Assets/Shared/fonts/cinema-gothic-nbp-font/CinemaGothicNbpItalic-1ew2.ttf")
        # apply font
        text_node.set_font(display_font)

        cls.text_nodes[text_id] = text_np

        if text_id == "context_help":
            cls.fade_type = "in"

        if fade_in > 0.:
            text_np.set_alpha_scale(0.)
            cls.fade_text(text_id, "in", fade_in)
        else:
            text_np.set_alpha_scale(1.)

        return text_np

    @classmethod
    def remove_text(cls, text_id=None):
        if text_id is not None:
            if text_id in cls.text_nodes:
                text_np = cls.text_nodes[text_id]
                text_np.detach_node()
                del cls.text_nodes[text_id]
            if text_id in cls.fade_ivals:
                ival = cls.fade_ivals[text_id]
                ival.pause()
                del cls.fade_ivals[text_id]
            return

        for text_id, text_np in cls.text_nodes.items():
            text_np.detach_node()

        for text_id, ival in cls.fade_ivals.items():
            ival.pause()

        cls.text_nodes.clear()
        cls.fade_ivals.clear()

    @classmethod
    def advance_text(cls):
        if "multi_part" not in cls.text_nodes:
            return

        old_seq = cls.fade_ivals["multi_part"] if "multi_part" in cls.fade_ivals else None

        if old_seq:
            old_seq.finish()

        text_np = cls.text_nodes["multi_part"]
        seq = Sequence()
        ival = LerpColorScaleInterval(text_np, .5, (1., 1., 1., 0.))
        seq.append(ival)

        if cls.text_parts:
            seq.append(Func(lambda: text_np.node().set_text(cls.text_parts.pop(0))))
            ival = LerpColorScaleInterval(text_np, .5, (1., 1., 1., 1.))
            seq.append(ival)
        else:
            def show_context_help():
                text_np.detach_node()
                del cls.text_nodes["multi_part"]
                cls.text_nodes["context_help"].node().set_text(cls.help_text)
                cls.text_nodes["context_help"].set_alpha_scale(0.)
                cls.fade_text("context_help", "in")

            seq.append(Func(show_context_help))

        seq.start()
        cls.fade_ivals["multi_part"] = seq

    @classmethod
    def fade_text(cls, text_id, fade_type, fade_dur=.5):
        if not text_id in cls.text_nodes:
            return

        text_np = cls.text_nodes[text_id]
        alpha_scale = text_np.get_sa()
        end_alpha_scale = 1. if fade_type == "in" else 0.
        dur = abs(end_alpha_scale - alpha_scale) * fade_dur
        old_ival = cls.fade_ivals[text_id] if text_id in cls.fade_ivals else None

        if old_ival:
            old_ival.pause()

        ival = LerpColorScaleInterval(text_np, dur, (1., 1., 1., end_alpha_scale))
        ival.start()
        cls.fade_ivals[text_id] = ival

    @classmethod
    def toggle_text(cls):
        if not "context_help" in cls.text_nodes:
            return

        cls.fade_type = "out" if cls.fade_type == "in" else "in"
        cls.fade_text("context_help", cls.fade_type)

        # allow keeping the help text on screen until the associated key is released
        if cls.fade_type == "in":
            key = KeyBindings.events["text"]["toggle_help"].key

            def fade_out_help(task):
                base.accept_once(f"{key}-up", lambda: cls.toggle_text())

            # activate the "held down" mode after keeping the key pressed for half
            # a second
            base.task_mgr.add(fade_out_help, "fade_out_help", delay=.5)
            base.accept_once(f"{key}-up", lambda: base.task_mgr.remove("fade_out_help"))

    addText = add_text
    removeText = remove_text


# functional control of a global text alpha scale
def fade_in_text(label, text, screen_pos, color):
    # directly make a text node to display text
    text_1 = TextNode(label)
    text_1.set_text(text)
    text_1_node = base.a2dTopLeft.attach_new_node(text_1)
    text_1_node.set_scale(0.05)
    text_1_node.set_pos(screen_pos)
    text_1_node.set_color(color)
    text_1.set_shadow(0.1, 0.1)
    # text_1.set_shadow_color(color)
    display_font = base.loader.load_font("Assets/Shared/fonts/cinema-gothic-nbp-font/CinemaGothicNbpItalic-1ew2.ttf")
    # apply font
    text_1.set_font(display_font)
    ival = LerpColorScaleInterval(text_1_node, .5, (1., 1., 1., 1.), (1., 1., 1., 0.))
    ival.start()

def dismiss_info_text(text_node):
    try:
        t_node = base.a2dTopLeft.find(text_node)
        ival = LerpColorScaleInterval(t_node, .5, (1., 1., 1., 0.))
        ival.start()
    except:
        print('No info text to dismiss, passing...')

def mirror_ship_parts(model):
    for left_node in model.find_all_matches("**/*_left*"):
        right_node = left_node.copy_to(left_node.parent)
        x, y, z = right_node.get_pos()
        right_node.set_pos(0., 0., 0.)
        right_node.flatten_light()  # bake orientation and scale into vertices
        right_node.set_sx(-1.)
        right_node.flatten_light()  # bake negative scale into vertices
        right_node.set_pos(-x, y, z)
        geom = right_node.children[0].node().modify_geom(0)
        geom.reverse_in_place()

mirrorShipParts = mirror_ship_parts

models = {}
shared_models = {}

def preload_models(model_paths, callback=None):
    async def load_models():
        async for model in base.loader.load_model(model_paths, blocking=False):
            path = model_paths.pop(0)
            _, section_id, _, filename = path.split("/")

            if section_id == "Shared":
                shared_models[filename] = model
            else:
                models[filename] = model
            print("Loaded", path)

        if callback:
            callback()

    base.task_mgr.add(load_models())
