from panda3d.core import WindowProperties, CardMaker
from direct.stdpy.file import *
import common


class TitleScreen:

    def __init__(self, demo_class, window_updater, option_dir, option_filename):
        try:
            with open(f"{option_dir}/{option_filename}") as option_file:
                for line in option_file:
                    _, option_id, option_value = line.split("|")
                    option_id = option_id.strip()
                    if option_id == "resolution":
                        w, h = option_value.split(" x ")
                        properties = WindowProperties()
                        properties.set_size(int(w), int(h))
                        common.base.win.request_properties(properties)
                        break
        except FileNotFoundError as e:
            pass

        cm = CardMaker("loading_screen")
        cm.set_frame_fullscreen_quad()
        screen = base.render2d.attach_new_node(cm.generate())
        tex = base.loader.load_texture("Assets/Shared/tex/title_screen.png")
        screen.set_texture(tex)

        def start_demo():
            screen.detach_node()
            demo = demo_class()
            window_updater(demo, common.base.win)

        with open("models.txt") as model_path_file:
            model_paths = [path.replace("\r", "").replace("\n", "") for path in model_path_file]
        common.preload_models(model_paths, start_demo)
