from direct.actor.Actor import Actor
import common
from common import *
import fp_ctrl
from .intro import Intro

section3_models = common.models["section3"]

ASSET_PATH_1 = "Assets/Section3/"

# keep track of all lights that have been created, such that they can be removed
# when this section gets cleaned up
section_lights = []

section_tasks = []
section_intervals = []

def add_section_task(task_func, task_id, *args, **kwargs):
    cleanup = lambda task_obj: section_tasks.remove(task_obj)
    task_obj = ResumableTask(task_func, task_id, uponDeath=cleanup, *args, **kwargs)
    base.task_mgr.add(task_obj)
    section_tasks.append(task_obj)

    return task_obj

def remove_section_tasks():
    for task_obj in section_tasks[:]:
        base.task_mgr.remove(task_obj)

    section_tasks.clear()

def pause_section_tasks():
    tmp_tasks = section_tasks[:]

    for task_obj in tmp_tasks:
        task_obj.pause()

    section_tasks[:] = tmp_tasks[:]

def resume_section_tasks():
    for task_obj in section_tasks:
        task_obj.resume()

def pause_section_intervals():
    for interval in section_intervals:
        interval.pause()

def resume_section_intervals():
    for interval in section_intervals:
        interval.resume()


class Section3:
    def __init__(self):
        cube_map_name = 'Assets/Section3/tex/main_skybox_#.png'
        self.skybox = common.create_skybox(cube_map_name)
        self.skybox.reparent_to(base.render)
        self.skybox.set_effect(CompassEffect.make(base.camera, CompassEffect.P_pos))
        self.skybox.node().set_bounds(OmniBoundingVolume())
        self.skybox.node().set_final(True)

        # section load order
        # self.loadCutsceneOne()
        self.loadStationSegmentOne()

        '''# Preload the models for Section 4.

        with open("Section4/models.txt") as model_path_file:
            model_paths = [path.replace("\r", "").replace("\n", "") for path in model_path_file]
        common.preload_models(model_paths)'''

    def loadStationSegmentOne(self):
        self.intervals = []
        base.static_pos = Vec3(-5.29407, -15.2641, 2.66)

        render.set_shader_off()
        render.set_shader(metal_shader)

        player_start_pos = Vec3(0.552461, 26.3234, -2.54)
        fp_ctrl.fp_init(player_start_pos, z_limit=-1000)
        fp_ctrl.enable_fp_camera()

        events = KeyBindings.events["section3"]
        reload_key = events["reload_gun"].key_str
        events = KeyBindings.events["fps_controller"]
        jump_key = events["do_jump"].key_str
        forward_key = events["move_forward"].key_str
        backward_key = events["move_backward"].key_str
        left_key = events["move_left"].key_str
        right_key = events["move_right"].key_str
        events = KeyBindings.events["text"]
        help_toggle_key = events["toggle_help"].key_str
        # controller info text
        controller_text = '\n'.join((
            f'Jump: \1key\1{jump_key.title()}\2',
            f'\nForward: \1key\1{forward_key.title()}\2',
            f'Left: \1key\1{left_key.title()}\2',
            f'Right: \1key\1{right_key.title()}\2',
            f'Backward: \1key\1{backward_key.title()}\2',
            f'\nReload: \1key\1{reload_key.title()}\2',
            f'\nToggle This Help: \1key\1{help_toggle_key.title()}\2'
        ))
        TextManager.add_text("context_help", controller_text)
        # narrative text
        narrative = [
            "This is the first part of the narrative"
            " related to the background story of Section 3.",
            "This is the second part of the narrative"
            " related to the background story of Section 3.",
            "This is the third and last part of the narrative"
            " related to the background story of Section 3."
        ]
        TextManager.add_text("multi_part", narrative)

        for x in range(2):
            plight_1 = PointLight('plight_' + str(len(section_lights)))
            plight_1.set_priority(5)
            # add plight props here
            plight_1_node = render.attach_new_node(plight_1)
            plight_1_node.set_pos(-50, -50, 20)
            plight_1_node.node().set_color((1, 1, 1, 1))
            plight_1_node.node().set_attenuation((0.5, 0, 0.005))
            render.set_light(plight_1_node)
            section_lights.append(plight_1_node)

        def print_player_pos():
            print(str(base.render.find('Player').get_pos()))

        base.accept('f4', print_player_pos)

        self.hg_1 = section3_models["sec3_handgun_1.gltf"]

        base.drop_clip_toggle = False

        def drop_clip():
            if not base.drop_clip_toggle:
                clip_1 = self.hg_1.find('clip')
                clip_1_pos = clip_1.get_pos()
                clip_1.hide()

                def show_clip():
                    clip_1.show()

                lf_end = Func(show_clip)

                def reload_true():
                    base.drop_clip_toggle = True

                rl_true = Func(reload_true)

                def reload_false():
                    base.drop_clip_toggle = False
                    section_intervals.remove(reload_hg_1)
                    section_intervals.remove(base.particle_seq)

                rl_false = Func(reload_false)

                clip_container = self.hg_1.find('clip_case')
                clip_container_down = Vec3(clip_container.get_pos()[0], clip_container.get_pos()[1], clip_container.get_pos()[2] - 2)
                clip_container_pos = clip_container.get_pos()
                barrel_1 = self.hg_1.find('barrel')
                front_handle_1 = self.hg_1.find('front_handle_1')
                guard_1 = self.hg_1.find('guard')
                rear_handle_1 = self.hg_1.find('rear_handle')
                trigger_1 = self.hg_1.find('trigger')
                inset_effect_1 = self.hg_1.find('inset_effect')
                chassis_1 = self.hg_1.find('chassis')
                chassis_1_up = Vec3(chassis_1.get_pos()[0], chassis_1.get_pos()[1], chassis_1.get_pos()[2] + 0.005)
                chassis_1_pos = chassis_1.get_pos()

                rhg_inter_1 = LerpPosInterval(chassis_1, 1, chassis_1_up, blendType='easeInOut')
                rhg_inter_2 = LerpPosInterval(chassis_1, 0.5, chassis_1_pos, blendType='easeInOut')
                rhg_inter_1a = LerpPosInterval(inset_effect_1, 1, chassis_1_up, blendType='easeInOut')
                rhg_inter_2a = LerpPosInterval(inset_effect_1, 0.5, chassis_1_pos, blendType='easeInOut')
                rhg_inter_3 = LerpPosInterval(clip_container, 2, clip_container_down, blendType='easeInOut')
                rhg_inter_4 = LerpPosInterval(clip_container, 1, clip_container_pos, blendType='easeInOut')

                rl_par_1 = Parallel()
                rl_par_1.append(rhg_inter_1)
                rl_par_1.append(rhg_inter_1a)

                rl_par_2 = Parallel()
                rl_par_2.append(rhg_inter_2)
                rl_par_2.append(rhg_inter_2a)

                reload_hg_1 = Sequence()
                reload_hg_1.append(rl_true)
                reload_hg_1.append(rl_par_1)
                reload_hg_1.append(rl_par_2)
                reload_hg_1.append(rhg_inter_3)
                reload_hg_1.append(rhg_inter_4)
                reload_hg_1.append(lf_end)
                reload_hg_1.append(rl_false)
                reload_hg_1.start()

                section_intervals.append(reload_hg_1)

                start_particles('Assets/Shared/particles/steam.ptf', self.hg_1, inter_duration=2, inter_list=section_intervals)

        KeyBindings.set_handler("reload_gun", drop_clip, "section3")
        
        self.initial_tunnel = section3_models["sec3_initial_tunnel.gltf"]
        self.initial_tunnel.reparent_to(base.render)
        # self.initial_tunnel.set_pos(0, 0, 25)
        self.initial_tunnel.flatten_strong()
        
        fp_ctrl.make_collision('tunnel', self.initial_tunnel, 0, 0)

        amb_light = AmbientLight('amblight')
        amb_light.set_priority(50)
        amb_light.set_color((0.5, 0.5, 0.5, 1))
        amb_light_node = render.attach_new_node(amb_light)
        render.set_light(amb_light_node)
        section_lights.append(amb_light_node)

        self.hg_1.set_light(amb_light_node)

        self.load_gunhand()
        wrist_joint = self.player_char.expose_joint(None, "modelRoot", "wrist.R")
        self.hg_1.reparent_to(wrist_joint)
        self.hg_1.set_pos_hpr_scale(-1.33718, 0.452767, 5.61854, -90., 81.3, 0., 40., 40., 40.)

    def load_gunhand(self):
        self.player_char = Actor(common.models["shared"]["player_character.gltf"])
        self.player_char.load_anims({
            "squeeze_trigger": ASSET_PATH_1 + "models/player_character_squeeze_trigger.gltf"
        })
        self.player_char.set_play_rate(15., "squeeze_trigger")
        self.player_char.reparent_to(base.camera)
        self.player_char.set_attrib(arm_shader_attrib)
        self.player_char.set_pos(0.125 - .025 * 3., 0.145 - 0.09266, -0.05 + .025 * 6.)
        self.player_char.children[0].set_scale(.025)
        self.player_char.node().set_bounds(OmniBoundingVolume())
        self.player_char.node().set_final(True)

        # initialize armature
        self.player_char.pose("squeeze_trigger", 0)

        KeyBindings.set_handler("fire_gun", lambda: self.player_char.play("squeeze_trigger"), "section3")

        '''def armature_init(wait_period):
            time.sleep(wait_period)
            self.player_char.play("squeeze_trigger")

        threading2._start_new_thread(armature_init, (0.1,))'''

    def pauseGame(self):
        fp_ctrl.pause_fp_camera()

        pause_section_tasks()
        pause_section_intervals()

        KeyBindings.deactivate_all("section3")
        KeyBindings.deactivate_all("text")

    def resumeGame(self):
        resume_section_tasks()
        resume_section_intervals()

        fp_ctrl.resume_fp_camera()

        KeyBindings.activate_all("section3")
        KeyBindings.activate_all("text")

    def destroy(self):
        base.static_pos = Vec3(192.383, -0.182223, 2)

        if self.skybox:
            self.skybox.detach_node()
            self.skybox = None

        self.hg_1.detach_node()
        self.hg_1 = None
        self.initial_tunnel.detach_node()
        self.initial_tunnel = None
        tunnel = base.render.find('tunnel')
        base.world.remove(tunnel.node())
        tunnel.detach_node()
        tunnel = None

        self.player_char.detach_node()
        self.player_char = None

        TextManager.remove_text()

        KeyBindings.deactivate_all("section3")

        fp_ctrl.fp_cleanup()

        for light in section_lights:
            base.render.set_light_off(light)
            light.detach_node()

        remove_section_tasks()
        section_intervals.clear()

        if self.intervals and not self.intervals.is_stopped():
            self.intervals.finish()
            self.intervals.clear_intervals()
            if self.intervals in section_intervals:
                section_intervals.remove()

        section3_models.clear()
        common.currentSection = None


def startIntro(data, show_loading_screen):
    Intro(data, show_loading_screen)


def initialise(data=None):
    base.bullet_max_step = 15

    section = Section3()
    common.currentSection = section

    KeyBindings.set_handler("open_pause_menu", common.gameController.openPauseMenu, "section3")
    KeyBindings.activate_all("section3")
    KeyBindings.activate_all("text")

    return section


KeyBindings.add("open_pause_menu", "escape", "section3")
KeyBindings.add("reload_gun", "r", "section3")
KeyBindings.add("fire_gun", "mouse1", "section3")
