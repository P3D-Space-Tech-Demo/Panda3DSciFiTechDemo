from common import *
import common
from direct.stdpy.file import *


class Intro:

    def __init__(self, data=None, show_loading_screen=True):
        if show_loading_screen:
            self.show_loading_screen()
        else:
            self.start()

    def show_loading_screen(self):
        cm = CardMaker("loading_screen")
        cm.set_frame_fullscreen_quad()
        loading_screen = base.render2d.attach_new_node(cm.generate())
        tex = base.loader.load_texture("Assets/Section1/tex/loading_screen_section1.png")
        loading_screen.set_texture(tex)

        def start_intro():
            loading_screen.detach_node()
            self.start()

        with open("Section1/models.txt") as model_path_file:
            model_paths = [path.replace("\r", "").replace("\n", "") for path in model_path_file]
        common.models.clear()
        common.preload_models(model_paths, start_intro)

    def start(self):
        events = KeyBindings.events["section1_intro"]
        skip_key = events["start_section1"].key_str
        events = KeyBindings.events["text"]
        help_toggle_key = events["toggle_help"].key_str
        # info text
        info_text = '\n'.join((
            f'Press \1key\1{skip_key.title()}\2 to skip',
            f'\nToggle This Help: \1key\1{help_toggle_key.title()}\2'
        ))
        TextManager.add_text("context_help", info_text)

        base.task_mgr.add(lambda t: self.destroy(), "exit", delay=.5)
#        base.task_mgr.add(self.play, "play_intro")

        KeyBindings.set_handler("start_section1", self.destroy, "section1_intro")
        KeyBindings.activate_all("section1_intro")
        KeyBindings.activate_all("text")

        self.scene_root = base.render.attach_new_node("scene_root")

        # load in the outside space skybox
        cube_map_name = 'Assets/Section2/tex/main_skybox_#.png'
        skybox = create_skybox(cube_map_name)
        skybox.reparent_to(self.scene_root)
        skybox.set_effect(CompassEffect.make(base.camera, CompassEffect.P_pos))
        skybox.node().set_bounds(OmniBoundingVolume())
        skybox.node().set_final(True)

        '''light1 = DirectionalLight("directional light")
        light1.set_color((5., 5., 5., 1.))
        light1_np = self.scene_root.attach_new_node(light1)
        light1_np.set_hpr(135., -45., 0.)

        light2 = DirectionalLight("directional light")
        light2.set_color((4.5, 4.5, 5., 1.))
        light2_np = self.scene_root.attach_new_node(light2)
        light2_np.set_hpr(-135., 45., 0.)
        self.scene_root.set_light(light1_np)
        self.scene_root.set_light(light2_np)
        self.scene_root.set_shader(metal_shader)

        base.camera.reparent_to(self.scene_root)

        mothership = common.shared_models["player_mothership.gltf"]
        mothership.reparent_to(self.scene_root)
        self.mothership = mothership

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

        # The following code is borrowed from `Player.py`; it implements rocket engine flames.

        light = PointLight("basic light")
        light.setColor(Vec4(1, 1, 1, 1))
        light.setAttenuation((1, 0.1, 0.01))
        self.lightNP = self.scene_root.attachNewNode(light)
        self.lightNP.setZ(1)
        self.scene_root.setLight(self.lightNP)'''

    def play(self, task):
        dt = globalClock.get_dt()
        d_r = self.wheel_rot_speed * dt

        for wheel in self.wheels:
            wheel.set_r(wheel, d_r)

        return task.cont

    def destroy(self):
        self.scene_root.detach_node()
        self.scene_root = None
#        self.intervals.pause()
#        self.intervals = None
        base.task_mgr.remove("play_intro")

        KeyBindings.deactivate_all("section1_intro")

        TextManager.remove_text()

        base.graphics_engine.render_frame()

        img = PNMImage()
        base.win.get_screenshot(img)
        img.gaussian_filter(5.)
        img *= (.3, .3, .3, 1.)
        cm = CardMaker("loading_screen")
        cm.set_frame_fullscreen_quad()
        loading_screen = base.render2d.attach_new_node(cm.generate())
        tex = Texture()
        tex.load(img)
        loading_screen.set_texture(tex)

        text_np = TextManager.add_text("loading", "Loading...", fade_in=0.)
        text_np.set_pos(.75, 0, -.1)

        base.graphics_engine.render_frame()
        base.graphics_engine.render_frame()

        TextManager.remove_text()
        loading_screen.detach_node()

        common.gameController.startSectionInternal(0, None)


KeyBindings.add("start_section1", "escape", "section1_intro")
