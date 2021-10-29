import common
from common import *
from .intro_portal import SphericalPortalSystem
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
        tex = base.loader.load_texture("Assets/Section3/tex/loading_screen_section3.png")
        loading_screen.set_texture(tex)

        def start_intro():
            loading_screen.detach_node()
            self.start()

        with open("Section3/models.txt") as model_path_file:
            model_paths = [path.replace("\r", "").replace("\n", "") for path in model_path_file]
        common.models.clear()
        common.preload_models(model_paths, start_intro)

    def start(self):
        events = KeyBindings.events["section3_intro"]
        skip_key = events["start_section3"].key_str
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

        KeyBindings.set_handler("start_section3", self.destroy, "section3_intro")
        KeyBindings.activate_all("section3_intro")

        self.scene_root = base.render.attach_new_node("scene_root")

        # load in the outside space skybox
        cube_map_name = 'Assets/Section3/tex/main_skybox_#.png'
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

        lights = [light1_np, light2_np]
        pos = Point3()
        self.portal_sys = SphericalPortalSystem(self.scene_root, lights, pos)'''

        base.camera.reparent_to(self.scene_root)

    def play(self, task):
        return task.cont

    def destroy(self):
#        self.portal_sys.destroy()
        base.task_mgr.remove("play_intro")

        KeyBindings.deactivate_all("section3_intro")

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

        base.text_alpha = 1.
        fade_in_text('loading', 'Loading...', Vec3(.75, 0, -.1), Vec4(1, 1, 1, 1))

        base.graphics_engine.render_frame()
        base.graphics_engine.render_frame()

        text_node = base.a2dTopLeft.find('loading')
        text_node.detach_node()
        loading_screen.detach_node()

        common.gameController.startSectionInternal(2, None)


KeyBindings.add("start_section3", "escape", "section3_intro")
