from common import *
import common

vert_shader = "Assets/Shared/shaders/portal_sphere.vert"
frag_shader = "Assets/Shared/shaders/portal_sphere.frag"
portal_sphere_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)

vert_shader = "Assets/Shared/shaders/pbr_clip_shader_v.vert"
frag_shader = "Assets/Shared/shaders/pbr_clip_shader_f.frag"
pbr_clip_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)


def create_sphere(segments):
    from math import pi, sin, cos

    v_format = GeomVertexFormat.get_v3()
    v_data = GeomVertexData("cube_data", v_format, Geom.UH_static)
    prim = GeomTriangles(Geom.UH_static)

    pos_data = array.array("f", [])
    idx_data = array.array("H", [])
    segs_half = max(2, segments // 2)
    segs = segs_half * 2

    angle = pi / segs_half
    angle_v = angle
    pos_data.extend([0., 0., 1.])

    for i in range(segs_half - 1):

        z = cos(angle_v)
        radius_h = sin(angle_v)
        angle_v += angle
        angle_h = 0.

        for j in range(segs):

            x = cos(angle_h) * radius_h
            y = sin(angle_h) * radius_h
            pos_data.extend([x, y, z])
            angle_h += angle

    pos_data.extend([0., 0., -1.])

    for i in range(segs - 1):
        idx_data.extend([0, i + 1, i + 2])

    idx_data.extend([0, segs, 1])

    for i in range(segs_half - 2):

        for j in range(segs - 1):
            k = 1 + i * segs + j
            l = k + segs
            idx_data.extend([k, l, k + 1, l, l + 1, k + 1])

        k = (i + 1) * segs
        l = k + segs
        idx_data.extend([k, l, k + 1 - segs, l, l + 1 - segs, k + 1 - segs])

    vertex_count = 1 + (segs_half - 1) * segs
    k = vertex_count - segs
    vertex_count += 1
    v_data.unclean_set_num_rows(vertex_count)
    view = memoryview(v_data.modify_array(0)).cast("B").cast("f")
    view[:] = pos_data

    for i in range(segs - 1):
        l = k + i
        idx_data.extend([l, vertex_count - 1, l + 1])

    idx_data.extend([vertex_count - 2, vertex_count - 1, vertex_count - 1 - segs])

    idx_array = prim.modify_vertices()
    idx_array.unclean_set_num_rows(len(idx_data))
    view = memoryview(idx_array).cast("B").cast("H")
    view[:] = idx_data

    geom = Geom(v_data)
    geom.add_primitive(prim)
    node = GeomNode("sphere_node")
    node.add_geom(geom)

    return node


class SphericalPortalSystem:

    def __init__(self, level_model, lights, portal_pos):

        loader = base.loader

        self.portal_node_0 = level_model.attach_new_node("portal_node_0")
        self.portal_node_1 = NodePath("portal_node_1")
#        self.portal_node_1.set_shader_auto()

        for light in lights:
            self.portal_node_1.set_light(light)

        portal_generator = loader.load_model("Assets/Section2/models/portal_generator.gltf")
        portal_generator.set_scale(27.)
        portal_generator.set_shader(scene_shader)
        portal_generator.reparent_to(self.portal_node_0)
        portal_generator.set_pos(portal_pos)
        portal_generator.set_hpr(-90., -130., 0.)

        # apply blue light to portal sphere
        light = PointLight("point_light")
        light.set_color((.5, .5, 1., 1.))
        self.light_np = portal_generator.attach_new_node(light)
        self.light_np.set_pos(0., 0., 50.)
        portal_generator.set_light(self.light_np)

        self.portal_sphere = self.portal_node_0.attach_new_node(create_sphere(segments=48))
        self.portal_sphere.set_scale(26.8)
        self.portal_sphere.set_transparency(TransparencyAttrib.M_alpha)
        self.portal_sphere.set_light_off()
        self.portal_sphere.set_material_off()
        self.portal_sphere.set_shader(portal_sphere_shader)
        self.portal_sphere.set_pos(portal_pos)

        props = FrameBufferProperties()
        props.set_rgba_bits(8, 8, 8, 0)
        props.set_depth_bits(8)
        portal_buffer = base.win.make_texture_buffer("portal", 1024, 1024, fbp=props)
        self.portal_buffer = portal_buffer
        self.portal_cam = base.make_camera(portal_buffer)
        self.portal_cam.reparent_to(self.portal_node_1)
        self.portal_cam.node().set_lens(base.camLens)
        portal_texture = portal_buffer.get_texture()
        portal_texture.minfilter = Texture.FT_linear_mipmap_linear
        self.portal_sphere.set_texture(TextureStage("portal"), portal_texture)

        self.tunnel_model_0 = loader.load_model("Assets/Section2/models/wrecked_tunnel.gltf")
        self.tunnel_model_0.reparent_to(self.portal_node_0)
        self.tunnel_model_0.set_hpr(-90., -40., 0.)
        self.tunnel_model_0.set_pos(portal_pos)
        self.tunnel_model_0.set_scale(10.)

        self.tunnel_model_1 = self.tunnel_model_0.copy_to(self.portal_node_1)
        self.tunnel_model_1.set_shader(scene_shader)
        plane = Plane(Vec3(0., -1., 0.), Point3(0., 0., 0.))
#        plane_np = self.portal_sphere.attach_new_node(PlaneNode("plane", plane))
        plane_np = self.portal_sphere.attach_new_node("clip_plane")
        plane_np.set_hpr(-90., -40., 0.)
#        self.tunnel_model_0.set_clip_plane(plane_np)
        plane_normal = plane_np.get_quat(base.render).get_forward()
        plane_point = plane_np.get_pos(base.render)
        plane_dist = plane_point.dot(plane_normal)
        plane_def = Vec4(*plane_normal, plane_dist)
        self.tunnel_model_0.set_shader(pbr_clip_shader)
        self.tunnel_model_0.set_shader_input("clip_plane_def", plane_def)

#        skybox = loader.load_model("Assets/Section2/models/portal_skybox.gltf")
        cube_map_name = 'Assets/Section2/tex/portal_skybox_#.png'
        skybox = common.create_skybox(cube_map_name)
        skybox.reparent_to(self.portal_cam)
        skybox.set_compass()
        '''
        skybox.set_scale(50.)
        skybox.set_light_off()
        skybox.set_shader_off()
        skybox.set_bin("background", 0)
        skybox.set_depth_write(False)
        '''

        base.task_mgr.add(self.update_portal_cam, "update_portal_cam", sort=45)

    def update_portal_cam(self, task):

        mat = base.camera.get_mat(common.currentSection.currentLevel.geometry)
        self.portal_cam.set_mat(mat)

        return task.cont

    def destroy(self):

        base.task_mgr.remove("update_portal_cam")
        base.graphics_engine.remove_window(self.portal_buffer)
        self.portal_buffer = None
        self.portal_node_0.detach_node()
        self.portal_node_0 = None
        self.portal_node_1 = None