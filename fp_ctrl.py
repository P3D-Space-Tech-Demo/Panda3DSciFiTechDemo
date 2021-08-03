from common import *
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.bullet import ZUp
from panda3d.bullet import BulletCapsuleShape
from panda3d.bullet import BulletTriangleMesh
from panda3d.bullet import BulletTriangleMeshShape
from panda3d.bullet import BulletBoxShape
from panda3d.bullet import BulletGhostNode
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletPlaneShape
from panda3d.bullet import BulletDebugNode


base.static_frames = 0
base.static_pos = Vec3()

base.world = BulletWorld()
base.world.set_gravity(Vec3(0, 0, -9.81))
# the effective world-Z limit
ground_plane = BulletPlaneShape(Vec3(0, 0, 1), 0)
node = BulletRigidBodyNode('ground')
node.add_shape(ground_plane)
node.set_friction(0.1)
np = base.render.attach_new_node(node)
np.set_pos(0, 0, -4)
base.world.attach_rigid_body(node)

# Bullet debugger
debug_node = BulletDebugNode('bullet_debug')
debug_node.show_wireframe(True)
debug_node.show_constraints(True)
debug_node.show_bounding_boxes(False)
debug_node.show_normals(False)
debug_np = base.render.attach_new_node(debug_node)
base.world.set_debug_node(debug_np.node())

# debug toggle function
def toggle_debug():
    if debug_np.is_hidden():
        debug_np.show()
    else:
        debug_np.hide()

# base.accept('f1', toggle_debug)

# 3D player movement system begins
keyMap = {"left": 0, "right": 0, "forward": 0, "backward": 0, "run": 0, "jump": 0}

def setKey(key, value):
    keyMap[key] = value

def fp_init(target_pos):
    # initialize player character physics the Bullet way
    shape_1 = BulletCapsuleShape(2, 1, ZUp)
    player_node = BulletCharacterControllerNode(shape_1, 1.5, 'Player')  # (shape, mass, player name)
    player = base.render.attach_new_node(player_node)
    player.set_pos(target_pos)
    player.set_collide_mask(BitMask32.all_on())
    base.world.attach_character(player.node())

def do_jump(jump_speed = 16, max_height = 1, fall_speed = 150, gravity = 50):
    player = base.render.find('Player')
    player.node().set_jump_speed(jump_speed)
    player.node().set_max_jump_height(max_height)
    player.node().set_fall_speed(fall_speed)
    player.node().set_gravity(gravity)
    player.node().do_jump()

def fp_cleanup():
    player = base.render.find('Player')
    base.world.remove(player.node())
    player.detach_node()
    disable_fp_camera()

def enable_fp_camera(fp_height = 1):
    player = base.render.find('Player')
    base.camLens.fov = 80
    base.camLens.set_near_far(0.01, 90000)
    base.camLens.focal_length = 7
    base.camera.reparent_to(player)
    base.camera.set_pos(player, 0, 0, fp_height)
    base.camera.set_hpr(0., 0., 0.)
    base.task_mgr.add(update_cam, "update_cam")
    base.task_mgr.add(physics_update, "physics_update")

    # define button map
    base.accept("a", setKey, ["left", 1])
    base.accept("a-up", setKey, ["left", 0])
    base.accept("d", setKey, ["right", 1])
    base.accept("d-up", setKey, ["right", 0])
    base.accept("w", setKey, ["forward", 1])
    base.accept("w-up", setKey, ["forward", 0])
    base.accept("s", setKey, ["backward", 1])
    base.accept("s-up", setKey, ["backward", 0])
    base.accept("shift", setKey, ["run", 1])
    base.accept("shift-up", setKey, ["run", 0])
    base.accept("space", setKey, ["jump", 1])
    base.accept("space-up", setKey, ["jump", 0])

    base.accept('mouse3', do_jump)

    # disable mouse
    base.disable_mouse()

def disable_fp_camera():
    base.task_mgr.remove("update_cam")
    base.task_mgr.remove("physics_update")
    base.ignore("mouse3")

    for key_id in ("w", "a", "s", "d", "shift", "space"):
        base.ignore(key_id)
        base.ignore(key_id + "-up")

def update_cam(Task):
    # the player movement speed
    movementSpeedForward = 15
    movementSpeedBackward = 15
    striveSpeed = 11
    
    player = base.render.find('Player')

    # get mouse data
    mouse_watch = base.mouseWatcherNode
    if mouse_watch.has_mouse():
        pointer = base.win.get_pointer(0)
        mouseX = pointer.get_x()
        mouseY = pointer.get_y()

    # screen sizes
    window_Xcoord_halved = base.win.get_x_size() // 2
    window_Ycoord_halved = base.win.get_y_size() // 2
    # mouse speed
    mouseSpeedX = 0.2
    mouseSpeedY = 0.2
    # maximum and minimum pitch
    maxPitch = 90
    minPitch = -50
    # cam view target initialization
    camViewTarget = LVecBase3f()

    if base.win.movePointer(0, window_Xcoord_halved, window_Ycoord_halved):
        p = 0

        if mouse_watch.has_mouse():
            # calculate the pitch of camera
            p = base.camera.get_p() - (mouseY - window_Ycoord_halved) * mouseSpeedY

        # sanity checking
        if p < minPitch:
            p = minPitch
        elif p > maxPitch:
            p = maxPitch

        if mouse_watch.has_mouse():
            # directly set the camera pitch
            base.camera.set_p(p)
            camViewTarget.set_y(p)

        # rotate the player's heading according to the mouse x-axis movement
        if mouse_watch.has_mouse():
            h = player.get_h() - (mouseX - window_Xcoord_halved) * mouseSpeedX

        if mouse_watch.has_mouse():
            # sanity checking
            if h < -360:
                h += 360

            elif h > 360:
                h -= 360

            player.set_h(h)
            camViewTarget.set_x(h)

    if keyMap["left"]:
        base.static_frames = 0
        player.set_x(player, -striveSpeed * globalClock.get_dt())

    if keyMap["right"]:
        base.static_frames = 0
        player.set_x(player, striveSpeed * globalClock.get_dt())

    if keyMap["forward"]:
        base.static_frames = 0
        player.set_y(player, movementSpeedForward * globalClock.get_dt())

    if keyMap["backward"]:
        base.static_frames = 0
        player.set_y(player, -movementSpeedBackward * globalClock.get_dt())
        
    if not keyMap["left"]:
        if not keyMap["right"]:
            if not keyMap["forward"]:
                if not keyMap["backward"]:
                    if player.node().is_on_ground():
                        base.static_frames += 1
                    
                        if base.static_frames == 1:
                            base.static_pos = player.get_pos()

                        player.set_pos(base.static_pos)

    return Task.cont

def physics_update(Task):
    dt = globalClock.get_dt()
    base.world.do_physics(dt)
    
    if base.static_frames > 60:
        base.static_frames = 0

    return Task.cont
    
def make_collision(rigid_label, input_model, node_number, mass, target_pos = Vec3(0, 0, 0), hpr_adj = Vec3(0, 0, 0), scale_adj = 1):
    # generic tristrip collision generator begins
    geom_nodes = input_model.find_all_matches('**/+GeomNode')
    geom_nodes = geom_nodes.get_path(node_number).node()
    geom_target = geom_nodes.get_geom(0)
    output_bullet_mesh = BulletTriangleMesh()
    output_bullet_mesh.add_geom(geom_target)
    tri_shape = BulletTriangleMeshShape(output_bullet_mesh, dynamic=False)

    body = BulletRigidBodyNode(str(rigid_label))
    np = base.render.attach_new_node(body)
    np.node().add_shape(tri_shape)
    np.node().set_mass(mass)
    np.node().set_friction(0.01)
    np.set_pos(target_pos)
    np.set_scale(scale_adj)
    np.set_hpr(hpr_adj)
    np.set_collide_mask(BitMask32.allOn())
    base.world.attach_rigid_body(np.node())

