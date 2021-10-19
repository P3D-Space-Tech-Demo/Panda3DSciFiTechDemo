from common import *
import common


class Intro:

    def __init__(self, shipSpec):

        self.data = shipSpec
        base.task_mgr.add(self.play, "play_intro")

        KeyBindings.set_handler("start_section2", self.destroy, "section2_intro")
        KeyBindings.activate_all("section2_intro")

        self.scene_root = base.render.attach_new_node("scene_root")

        # load in the outside space skybox
        cube_map_name = 'Assets/Section2/tex/main_skybox_#.png'
        skybox = create_skybox(cube_map_name)
        skybox.reparent_to(self.scene_root)
        skybox.set_effect(CompassEffect.make(base.camera, CompassEffect.P_pos))
        skybox.node().set_bounds(OmniBoundingVolume())
        skybox.node().set_final(True)

        light1 = DirectionalLight("directional light")
        light1.set_color((5., 5., 5., 1.))
        light1_np = self.scene_root.attach_new_node(light1)
        light1_np.set_hpr(135., -45., 0.)

        light2 = DirectionalLight("directional light")
        light2.set_color((4.5, 4.5, 5., 1.))
        light2_np = self.scene_root.attach_new_node(light2)
        light2_np.set_hpr(-135., 45., 0.)

        base.camera.reparent_to(self.scene_root)

        mothership = base.loader.load_model("Assets/Shared/models/player_mothership.gltf")
        mothership.reparent_to(self.scene_root)
        mothership.set_shader(metal_shader)
        mothership.set_light(light1_np)
        mothership.set_light(light2_np)
        self.mothership = mothership

        hangar_exit = mothership.find("**/hangar_door_left_node")

        compartment = mothership.find("**/compartment")
        compartment.set_pos(0, 0, 0)
        compartment_node = mothership.find("**/compartment_node")
        compartment.reparent_to(compartment_node)

        for compartment_node in mothership.find_all_matches("**/compartment_node.*"):
            compartment.copy_to(compartment_node)

        self.wheels = []
        wheel = mothership.find("**/wheel")
        wheel.set_pos(0, 0, 0)
        wheel_node = mothership.find("**/wheel_node")
        wheel.reparent_to(wheel_node)
        self.wheels.append(wheel)

        for wheel_node in mothership.find_all_matches("**/wheel_node.*"):
            wheel_copy = wheel.copy_to(wheel_node)
            self.wheels.append(wheel_copy)

        ship = base.loader.load_model(f"Assets/Shared/models/{shipSpec.shipModelFileLowPoly}")
        common.mirror_ship_parts(ship)
        ship.reparent_to(hangar_exit)
        ship.set_pos(100., -50., 0.)
        ship.set_h(80.)
        self.ship = ship
        self.ship_speed = 180.
        self.ship_rot_speed = 7.
        self.wheel_rot_speed = 1.5

        positions = (
            (6.84507, 11.2454, 0.191199),
            (9.57945, 12.3756, 0.191199),
            (8.85028, 15.7298, 0.191199),
            (1.4063, 14.6871, 2.40655),
            (-2.22233, 10.7603, 3.558),
            (-2.5, 4.3, 5.5)
        )
        start_positions = positions[:-1]
        end_positions = positions[1:]
        durations = (3.5, 3.5, 3.5, 3.5, 7., 8.)

        base.camera.set_pos(positions[0])

        self.intervals = par = Parallel()
        seq = Sequence()
        par.append(seq)

        for start_pos, end_pos, duration in zip(start_positions, end_positions, durations):
            ival = LerpPosInterval(base.camera, duration, end_pos, start_pos, blendType='noBlend')
            seq.append(ival)

        seq.append(Wait(durations[-1]))
        seq.append(Func(self.destroy))

        def zoom_out(fov):
            base.camLens.set_fov(fov)

        def zoom_in(zoom_step):
            base.camera.set_y(base.camera, zoom_step * globalClock.get_dt())

        seq = Sequence()
        par.append(seq)
        zoom_out_dur = 4.
        ival = LerpFunc(zoom_out, fromData=10., toData=50., duration=zoom_out_dur, blendType="easeInOut")
        seq.append(ival)
        zoom_in_dur = 4.
        end_dur = durations[-1] - zoom_in_dur
        seq.append(Wait(sum(durations) - zoom_out_dur - durations[-1]))
        ival = LerpFunc(zoom_in, fromData=5., toData=3., duration=zoom_in_dur, blendType="easeInOut")
        seq.append(ival)
        seq.append(Wait(end_dur))
        par.start()

    def play(self, task):
        dt = globalClock.get_dt()
        d_r = self.wheel_rot_speed * dt

        if self.ship.get_h(self.mothership) > 0.:
            d_h = self.ship_rot_speed * dt
            self.ship.set_h(self.ship, -d_h)

        for wheel in self.wheels:
            wheel.set_r(wheel, d_r)

        d_y = self.ship_speed * dt
        self.ship.set_y(self.ship, -d_y)
        base.camera.look_at(self.ship)

        return task.cont

    def destroy(self):

        self.scene_root.detach_node()
        self.intervals.pause()
        self.intervals = None
        base.task_mgr.remove("play_intro")

        KeyBindings.deactivateAll("section2_intro")

        common.gameController.startSectionInternal(1, self.data)


KeyBindings.add("start_section2", "escape", "section2_intro")
