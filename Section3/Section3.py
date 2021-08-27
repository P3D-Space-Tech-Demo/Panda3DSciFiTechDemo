import common
from common import *
import fp_ctrl

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

        # section load order
        # self.loadCutsceneOne()
        self.loadStationSegmentOne()

    def loadStationSegmentOne(self):

        self.intervals = []
        base.static_pos = Vec3(-5.29407, -15.2641, 2.66)

        render.set_shader_off()
        render.set_shader(scene_shader)

        player_start_pos = Vec3(-2.7, 0, 100)
        fp_ctrl.fp_init(player_start_pos, z_limit=-50)
        fp_ctrl.enable_fp_camera()

        # controller info text
        controller_text = 'Jump: Mouse Right' + '\n' + '\n' + 'Forward: W' + '\n'+ 'Left: A' + '\n' + 'Right: D' + '\n' + 'Backward: S' + '\n'  + 'Reload: R' + '\n' + '\n' + 'Dismiss Controller Info: F6'
        fade_in_text('text_1_node', controller_text, 1)

        def hide_info():
            dismiss_info_text('text_1_node')

        base.accept('f6', hide_info)

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

        self.hg_1 = base.loader.load_model(ASSET_PATH_1 + "models/sec3_handgun_1.gltf")
        self.hg_1.reparent_to(render)
        self.hg_1.reparent_to(base.cam)
        self.hg_1.set_y(base.cam, 0.3)
        self.hg_1.set_x(base.cam, 0.1)

        base.drop_clip_toggle = False

        def drop_clip():
            if not base.drop_clip_toggle:
                clip_1 = self.hg_1.find('clip')
                clip_1_pos = clip_1.get_pos()
                clip_1.hide()

                '''def show_clip(t):
                    t = t * 1

                    clip_1.show()

                lf_end = LerpFunc(show_clip, fromData=2.5, toData=4, duration=0)

                def reload_true(t):
                    t = t * 1

                    base.drop_clip_toggle = True

                rl_true = LerpFunc(reload_true, fromData=2.5, toData=4, duration=0)

                def reload_false(t):
                    t = t * 1

                    base.drop_clip_toggle = False

                rl_false = LerpFunc(reload_false, fromData=2.5, toData=4, duration=0)'''

                def show_clip():
                    clip_1.show()

                lf_end = Func(show_clip)

                def reload_true():
                    base.drop_clip_toggle = True

                rl_true = Func(reload_true)

                def reload_false():
                    base.drop_clip_toggle = False
                    section_intervals.remove(reload_hg_1)

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

                start_particles('Assets/Shared/particles/steam.ptf', self.hg_1)
                load_particle_config('Assets/Shared/particles/steam.ptf', self.hg_1, clip_1_pos, 2)

        KeyBindings.set_handler("reload_gun", drop_clip, "section3")

        self.model = base.loader.load_model(ASSET_PATH_1 + "levels/tunnel_drop_1.gltf")
        self.model.reparent_to(base.render)
        self.model.flatten_strong()

        fp_ctrl.make_collision('ramp', self.model, 0, 0, target_pos = Vec3(0, 0, 0), hpr_adj = Vec3(0, 0, 0), scale_adj = 1)

        amb_light = AmbientLight('amblight')
        amb_light.set_priority(50)
        amb_light.set_color((0.5, 0.5, 0.5, 1))
        amb_light_node = render.attach_new_node(amb_light)
        self.model.set_light(amb_light_node)
        section_lights.append(amb_light_node)

        self.hg_1.set_shader(metal_shader)
        self.hg_1.set_light(amb_light_node)

    def pauseGame(self):

        fp_ctrl.pause_fp_camera()

        pause_section_tasks()
        pause_section_intervals()

        KeyBindings.deactivate_all("section3")

    def resumeGame(self):

        resume_section_tasks()
        resume_section_intervals()

        fp_ctrl.resume_fp_camera()

        KeyBindings.activate_all("section3")

    def destroy(self):
        base.static_pos = Vec3(192.383, -0.182223, 2)

        self.hg_1.detach_node()
        self.model.detach_node()
        ramp = base.render.find('ramp')
        base.world.remove(ramp.node())
        ramp.detach_node()

        base.aspect2d.find('text_1_node').detach_node()

        fp_ctrl.fp_cleanup()

        for light in section_lights:
            base.render.set_light_off(light)
            light.detach_node()

        remove_section_tasks()
        section_intervals.clear()
        common.currentSection = None

        if self.intervals and not self.intervals.is_stopped():
            self.intervals.finish()
            self.intervals.clear_intervals()
            if self.intervals in section_intervals:
                section_intervals.remove()

def initialise(data=None):

    base.bullet_max_step = 15

    base.text_alpha = 0.01

    section = Section3()
    common.currentSection = section

    KeyBindings.set_handler("open_pause_menu", common.gameController.openPauseMenu, "section3")
    KeyBindings.activate_all("section3")

    return section


KeyBindings.add("open_pause_menu", "escape", "section3")
KeyBindings.add("reload_gun", "r", "section3")
