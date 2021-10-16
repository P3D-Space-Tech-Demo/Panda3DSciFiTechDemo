from common import *
import common


class Intro:

    def __init__(self, data):

        self.data = data
        base.task_mgr.add(self.play, "play_intro")

        KeyBindings.set_handler("start_section2", self.destroy, "section2_intro")
        KeyBindings.activate_all("section2_intro")

        # load in the outside space skybox
        cube_map_name = 'Assets/Section2/tex/main_skybox_#.png'
        self.skybox = create_skybox(cube_map_name)
        self.skybox.reparent_to(base.render)
        self.skybox.set_effect(CompassEffect.make(base.camera, CompassEffect.P_pos))
        self.skybox.node().set_bounds(OmniBoundingVolume())
        self.skybox.node().set_final(True)

        light1 = DirectionalLight("directional light")
        light1.set_color((1., 1., 1., 1.))
        self.light1_np = base.render.attach_new_node(light1)
        self.light1_np.set_hpr(135., -45., 0.)

        light2 = DirectionalLight("directional light")
        light2.set_color((0.15, 0.15, 0.3, 1.))
        self.light2_np = base.render.attach_new_node(light2)
        self.light2_np.set_hpr(-135., 45., 0.)

        base.camera.reparent_to(base.render)
        base.camera.set_pos(150., -200., -50.)
        base.camera.look_at(0., 50., 0.)

        mothership = base.loader.load_model("Assets/Shared/models/player_mothership.gltf")
        mothership.reparent_to(base.render)
        mothership.set_scale(242.895312 * .1)
        mothership.set_shader(metal_shader)
        mothership.set_light(self.light1_np)
        mothership.set_light(self.light2_np)
        self.mothership = mothership

        compartment = mothership.find("**/compartment")
        compartment.set_pos(0, 0, 0)
        compartment_node = mothership.find("**/compartment_node")
        compartment.reparent_to(compartment_node)

        for compartment_node in mothership.find_all_matches("**/compartment_node*"):
            compartment.copy_to(compartment_node)

        wheel = mothership.find("**/wheel")
        wheel.set_pos(0, 0, 0)
        wheel_node = mothership.find("**/wheel_node")
        wheel.reparent_to(wheel_node)

        for wheel_node in mothership.find_all_matches("**/wheel_node*"):
            wheel.copy_to(wheel_node)

    def play(self, task):

        return task.cont

    def destroy(self):

        self.skybox.detach_node()
        self.light1_np.detach_node()
        self.light2_np.detach_node()
        self.mothership.detach_node()
        base.task_mgr.remove("play_intro")

        KeyBindings.deactivateAll("section2_intro")

        common.gameController.startSectionInternal(1, self.data)


KeyBindings.add("start_section2", "escape", "section2_intro")

