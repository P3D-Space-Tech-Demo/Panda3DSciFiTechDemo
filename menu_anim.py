from panda3d.core import *
from direct.interval.IntervalGlobal import (
    LerpPosInterval,
    LerpHprInterval,
    LerpColorScaleInterval,
    Func,
    Wait,
    Sequence,
    Parallel
)
from direct.stdpy.file import *
from direct.filter.CommonFilters import CommonFilters
from collections import deque

import random
import common
import holo


class MenuBackdropAnimation:

    def __init__(self, menu_backdrop, anim_type=1):

        # add a render to texture 3D space for the backdrop/background
        ASSET_PATH = "Assets/Section1/"

        self.mirror_buffer = base.win.make_texture_buffer("mirror_buff", 2048, 2048)
        menu_backdrop["frameTexture"] = self.mirror_buffer.get_texture()
        self.mirror_render = NodePath("mirror_render")
        self.mirror_render.set_shader(common.metal_shader)

        mirror_cam = base.make_camera(self.mirror_buffer)
        mirror_cam.reparent_to(self.mirror_render)
        mirror_cam.set_pos(0, -20, 5)
        mirror_cam.set_hpr(0, 25, 0)
        mirror_cam.node().get_lens().set_focal_length(10)
        mirror_cam.node().get_lens().set_fov(90)

        self.mirror_filters = CommonFilters(self.mirror_buffer, mirror_cam)
        self.mirror_filters.set_bloom(intensity=5)
        self.mirror_filters.set_high_dynamic_range()
        self.mirror_filters.set_exposure_adjust(1.8)
        self.mirror_filters.set_gamma_adjust(1.3)

        self.motion_intervals = []

        # mirror scene model load-in
        # reparent to mirror render node
        filenames = (
            'Assets/Shared/models/test_completed_ship_a.gltf',
            'Assets/Shared/models/starship_b_for_wire.gltf',
            'Assets/Shared/models/starship_c_for_wire.gltf'
        )
        self.ships = deque()

        for filename in filenames:
            screen_ship = base.loader.load_model(filename)
            common.mirror_ship_parts(screen_ship)
            holo.make_wire(
                screen_ship,
                scale_adj=0.5,
                alpha=0.2,
                render_space=self.mirror_render
            )
            self.ships.append(screen_ship)

        # load in the space background
        cube_map_name = 'Assets/Section2/tex/main_skybox_#.png'
        self.menu_skybox = common.create_skybox(cube_map_name)
        self.menu_skybox.reparent_to(self.mirror_render)
        self.menu_skybox.set_effect(CompassEffect.make(mirror_cam, CompassEffect.P_pos))
        self.menu_skybox.node().set_bounds(OmniBoundingVolume())
        self.menu_skybox.node().set_final(True)

        nice = LerpHprInterval(self.menu_skybox, 240, (0, 360, 0))
        nice_seq = Sequence()
        nice_seq.append(nice)
        nice_seq.loop()

        # mirror scene lighting
        # point light generator
        for x in range(2):
            plight_1 = PointLight('mirror_light')
            # add plight props here
            plight_1_node = self.mirror_render.attach_new_node(plight_1)
            # group the lights close to each other to create a sun effect
            plight_1_node.set_pos(random.uniform(-21, -20), random.uniform(-21, -20), random.uniform(20, 21))
            self.mirror_render.set_light(plight_1_node)

        if anim_type == 1:
            self.start_animation_type_1()
        elif anim_type == 2:
            self.start_animation_type_2()

    def destroy(self):
        # cleanup for the 3D menu
        print(self.mirror_render.find_all_matches('**'))

        self.mirror_render.children.detach()

        print('remaining objects:')
        print(self.mirror_render.find_all_matches('**'))

        self.mirror_filters.del_bloom()
        self.mirror_filters.del_high_dynamic_range()
        self.mirror_filters.del_exposure_adjust()
        self.mirror_filters.del_gamma_adjust()

        base.task_mgr.remove("move_next_ship")

        for interval in self.motion_intervals:
            interval.pause()

        self.motion_intervals = []
        self.ships = deque()

    def start_animation_type_1(self):
        """ Rotate the wireframe ship models """

        screen_ship_1, screen_ship_2, screen_ship_3 = self.ships

        screen_ship_1.set_pos_hpr(0., 0., 5., 0., 0., 0.)
        screen_ship_1.reparent_to(self.mirror_render)
        nice = LerpHprInterval(screen_ship_1, 120, (-360, 0, 0))
        nice_seq = Sequence()
        nice_seq.append(nice)
        nice_seq.loop()

        screen_ship_2.set_pos_hpr(0., 0., 25., 0., 0., 0.)
        screen_ship_2.reparent_to(self.mirror_render)
        nice = LerpHprInterval(screen_ship_2, 120, (360, 0, 0))
        nice_seq = Sequence()
        nice_seq.append(nice)
        nice_seq.loop()

        screen_ship_3.set_pos_hpr(0., 0., -5., 0., 0., 0.)
        screen_ship_3.reparent_to(self.mirror_render)
        nice = LerpHprInterval(screen_ship_3, 120, (360, 0, 0))
        nice_seq = Sequence()
        nice_seq.append(nice)
        nice_seq.loop()

    def start_animation_type_2(self):
        """ Make the wireframe ship models fly past the camera """

        random_rolls = deque([False] * 3)

        for ship in self.ships:
            ship.set_pos_hpr(0., -100., 0., 180., 0., 0.)
            pivot = self.mirror_render.attach_new_node("ship_pivot")
            ship.reparent_to(pivot)

        def move_ship(ship, random_roll):
            uf = random.uniform
            hpr = (-90., uf(0., 360.), uf(60., 120.))
            quat = Quat()
            quat.set_hpr(hpr)
            dir_vec = quat.get_right() * -1.
            start_pos = quat.xform(Point3(0., 0., uf(-50., -20.)))
            end_pos = start_pos + dir_vec * 200.
            # give the ship a random roll, except on first fly-by
            ship.set_r(uf(-30., 30.) if random_roll else 0.)
            ship.parent.set_pos(start_pos)
            ship.parent.look_at(end_pos)
            ship.set_alpha_scale(0.)
            duration = uf(10., 15.)
            pos_lerp = LerpPosInterval(ship.parent, duration, end_pos)
            fade_in_lerp = LerpColorScaleInterval(ship, 2., (1., 1., 1., .3))
            fade_out_lerp = LerpColorScaleInterval(ship, 2., (1., 1., 1., 0.))
            seq = Sequence()
            par = Parallel()
            seq.append(fade_in_lerp)
            seq.append(Wait(duration - 4.))
            seq.append(fade_out_lerp)
            seq.append(Func(lambda: self.motion_intervals.remove(par)))
            par.append(pos_lerp)
            par.append(seq)
            par.start()
            self.motion_intervals.append(par)

        def move_next_ship(task):
            uf = random.uniform
            delay = random.uniform(5., 10.)
            random_roll = random_rolls[0]
            random_rolls[0] = True
            move_ship(self.ships[0], random_roll)
            self.ships.rotate()
            random_rolls.rotate()
            base.task_mgr.add(move_next_ship, "move_next_ship", delay=delay)

        base.task_mgr.add(move_next_ship, "move_next_ship")
