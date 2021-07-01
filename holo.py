from common import *


def apply_hologram(input_model, pos_adj = Vec3(0, 0, 0), scale_adj = 1):
    # begin holographic distortion setup
    def make_fbo(in_label):
        win_props = WindowProperties()
        props = FrameBufferProperties()
        props.set_rgb_color(1)
        return base.graphicsEngine.makeOutput(base.pipe, str(in_label), -2, props, win_props,
            GraphicsPipe.BFSizeTrackHost | GraphicsPipe.BFRefuseWindow,
            base.win.get_gsg(), base.win)
        
    # make the distortion buffer
    distort_buff = make_fbo("distortion_buffer")
    distort_buff.set_sort(-3)
    distort_buff.set_clear_color((0, 0, 0, 0))

    # add a distortion camera
    distort_cam = base.makeCamera(distort_buff, scene=render, lens=base.cam.node().get_lens(), mask=BitMask32.bit(4))
        
    # the model to be distorted
    input_model.set_pos(pos_adj)
    input_model.set_scale(scale_adj)
    input_model.reparent_to(base.render)
    input_model.set_transparency(TransparencyAttrib.M_dual)
        
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
    noise_tex = loader.loadTexture("Assets/Shared/tex/noise2.png")
    input_model.set_shader_input("waves", noise_tex)

    tex_distort = Texture()
    distort_buff.add_render_texture(tex_distort, GraphicsOutput.RTMBindOrCopy, GraphicsOutput.RTPColor)
    input_model.set_shader_input("screen", tex_distort)
    # distortion setup ends
        
def make_wire(wire_model, pos_adj = Vec3(0, 0, 0), scale_adj = 1):
    # wireframe model
    wire_model.set_pos(pos_adj)
    wire_model.set_scale(scale_adj)
    wire_model.reparent_to(base.render)
    wire_model.set_transparency(TransparencyAttrib.M_dual)
    wire_model.set_render_mode_wireframe()
    wire_model.set_alpha_scale(0.4)
