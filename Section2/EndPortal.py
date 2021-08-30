from common import *
import common

from panda3d.core import CollisionPolygon, GeomVertexFormat, CollisionNode


class SphericalPortalSystem:

    def __init__(self, level_model, lights, portal_pos):

        loader = base.loader

        self.portal_node_0 = level_model.attach_new_node("portal_node_0")
        self.portal_node_1 = NodePath("portal_node_1")

        for light in lights:
            self.portal_node_1.set_light(light)

        portal_generator = loader.load_model("Assets/Shared/models/portal_generator.gltf")
        portal_generator.set_scale(135.)
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
        self.portal_sphere.set_scale(134.)
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

        self.tunnel_model_0 = loader.load_model("Assets/Shared/models/wrecked_tunnel.gltf")
        self.tunnel_model_0.reparent_to(self.portal_node_0)
        self.tunnel_model_0.set_hpr(-90., -40., 0.)
        self.tunnel_model_0.set_pos(portal_pos)
        self.tunnel_model_0.set_scale(50.)

        self.tunnel_model_1 = self.tunnel_model_0.copy_to(self.portal_node_1)
        self.tunnel_model_1.set_shader(scene_shader)
        plane_np = self.portal_sphere.attach_new_node("clip_plane")
        plane_np.set_hpr(-90., -40., 0.)
        plane_normal = plane_np.get_quat(base.render).get_forward()
        plane_point = plane_np.get_pos(base.render)
        plane_dist = plane_point.dot(plane_normal)
        plane_def = Vec4(*plane_normal, plane_dist)
        self.tunnel_model_0.set_shader(pbr_clip_shader)
        self.tunnel_model_0.set_shader_input("clip_plane_def", plane_def)

        # Create the collision-geometry for the tunnel
        # With thanks to Epihaius for the relevant snippet!
        # Ref: https://discourse.panda3d.org/t/collision-mesh-from-loaded-model-for-built-in-collision-system/27102
        tunnel_collision = loader.load_model("Assets/Section2/models/wrecked_tunnel_collision.gltf")
        tunnel_collision.set_scale(50)
        collision_copy = tunnel_collision.copy_to(common.base.render)
        tunnel_collision.remove_node()
        collision_copy.detach_node()
        collision_copy.flatten_light()

        collision_root = NodePath("tunnel collision root")
        collision_root.reparent_to(level_model)
        collision_root.set_pos(portal_pos + Vec3(5, 0, 0))
        collision_root.set_hpr(-90, -40, 0)

        for np in collision_copy.find_all_matches("**/+GeomNode"):
            node = np.node()
            collision_node = CollisionNode(node.name)
            collision_mesh = collision_root.attach_new_node(collision_node)

            #collision_mesh.show()

            for geom in node.modify_geoms():
                geom.decompose_in_place()
                v_data = geom.modify_vertex_data()
                v_data.format = GeomVertexFormat.get_v3()
                view = memoryview(v_data.arrays[0]).cast("B").cast("f")
                index_list = geom.primitives[0].get_vertex_list()
                index_count = len(index_list)

                for indexList in (index_list[i:i+3] for i in range(0, index_count, 3)):
                    pts = [Point3(*view[index*3:index*3 + 3]) for index in indexList]
                    poly = CollisionPolygon(*pts)
                    collision_node.add_solid(poly)

        collision_copy.remove_node()

        # /Collision-geometry creaction

        cube_map_name = 'Assets/Section3/tex/main_skybox_#.png'
        skybox = common.create_skybox(cube_map_name)
        skybox.reparent_to(self.portal_cam)
        skybox.set_compass()

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
