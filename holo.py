from common import *


# keep track of objects that need to be cleaned up after use in a demo section.
objects_to_clean_up = {
    "distort_buff": None,
    "distort_cam": None
}


def apply_hologram(input_model, pos_adj = Vec3(0, 0, 0), scale_adj = 1):
    # begin holographic distortion setup
    def make_fbo(in_label):
        win_props = WindowProperties()
        props = FrameBufferProperties()
        props.set_rgb_color(1)
        return base.graphics_engine.make_output(base.pipe, str(in_label), -2, props, win_props,
            GraphicsPipe.BF_size_track_host | GraphicsPipe.BF_refuse_window,
            base.win.get_gsg(), base.win)

    # make the distortion buffer
    distort_buff = make_fbo("distortion_buffer")
    distort_buff.set_sort(-3)
    distort_buff.set_clear_color((0, 0, 0.3, 0))
    objects_to_clean_up["distort_buff"] = distort_buff

    # add a distortion camera
    distort_cam = base.makeCamera(distort_buff, scene=render, lens=base.camLens, mask=BitMask32.bit(4))
    distort_cam.name = "distort_cam"
    objects_to_clean_up["distort_cam"] = distort_cam

    # the model to be distorted
    input_model.set_pos(pos_adj)
    input_model.set_scale(scale_adj)
    input_model.reparent_to(base.render)

    # load the distortion shader
    distort_shader = Shader.load("Assets/Shared/shaders/holo.sha", Shader.SL_Cg)
    input_model.set_shader(distort_shader)
    input_model.hide(BitMask32.bit(4))
    input_model.set_transparency(TransparencyAttrib.M_dual)

    amb_light = AmbientLight('amblight')
    amb_light.set_color((1, 1, 1, 1))
    amb_light_node = input_model.attach_new_node(amb_light)
    input_model.set_light(amb_light_node)

    # distortion tex
    noise_tex = loader.load_texture("Assets/Shared/tex/noise2.png")
    input_model.set_shader_input("waves", noise_tex)
    # tex timer
    section_1_start_time = time.time()
    t_diff = section_1_start_time - game_start_time
    input_model.set_shader_input("timer", t_diff)

    tex_distort = Texture()
    distort_buff.add_render_texture(tex_distort, GraphicsOutput.RTM_bind_or_copy, GraphicsOutput.RTP_color)
    input_model.set_shader_input("screen", tex_distort)
    # distortion setup ends

def make_wire(wire_model, pos_adj = Vec3(0, 0, 0), scale_adj = 1, alpha = 0.4, render_space = base.render):
    # wireframe model
    wire_model.set_pos(pos_adj)
    wire_model.set_scale(scale_adj)
    wire_model.reparent_to(render_space)
    wire_model.set_transparency(TransparencyAttrib.M_dual)
    wire_model.set_render_mode_wireframe()
    wire_model.set_alpha_scale(alpha)

def holo_cleanup():
    base.graphics_engine.remove_window(objects_to_clean_up["distort_buff"])
    objects_to_clean_up["distort_cam"].detach_node()
