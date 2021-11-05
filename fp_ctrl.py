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


# keep track of Panda3D Tasks that are currently running, such that they
# can be paused, resumed and removed
running_tasks = []

def add_running_task(task_func, task_id, *args, **kwargs):
    cleanup = lambda task: running_tasks.remove(task)
    task_obj = ResumableTask(task_func, task_id, uponDeath=cleanup, *args, **kwargs)
    base.task_mgr.add(task_obj)
    running_tasks.append(task_obj)

    return task_obj

base.static_frames = 0
base.static_pos = Vec3()
base.frac_history = []
base.bullet_max_step = 5

paused_cursor_pos = [0,0]

movementSpeedForward = 20
movementSpeedBackward = 20
striveSpeed = 13

base.world = BulletWorld()
base.world.set_gravity(Vec3(0, 0, -9.81))

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

base.accept('f10', toggle_debug)

# 3D player movement system begins
keyMap = {"left": 0, "right": 0, "forward": 0, "backward": 0, "run": 0, "jump": 0}

def setKey(key, value):
    keyMap[key] = value

def reset_key_map():
    for key in keyMap:
        keyMap[key] = 0

def fp_init(target_pos, z_limit = 0, cap_size_x = 2, cap_size_y = 1):
    # initialize player character physics the Bullet way
    shape_1 = BulletCapsuleShape(cap_size_x, cap_size_y, ZUp)
    player_node = BulletCharacterControllerNode(shape_1, 1.5, 'Player')  # (shape, mass, player name)
    player = base.render.attach_new_node(player_node)
    player.set_pos(target_pos)
    player.set_collide_mask(BitMask32.all_on())
    base.world.attach_character(player.node())
    player.node().set_max_slope(0.6)
    cam_pivot = player.attach_new_node("cam_pivot")

    # the effective world-Z limit
    ground_plane = BulletPlaneShape(Vec3(0, 0, 1), 0)
    node = BulletRigidBodyNode('ground')
    node.add_shape(ground_plane)
    node.set_friction(0.1)
    np = base.render.attach_new_node(node)
    np.set_pos(0, 0, z_limit)
    base.world.attach_rigid_body(node)

    # initialize the previous cursor position to be at the center of the window
    paused_cursor_pos[0] = base.win.get_x_size() // 2
    paused_cursor_pos[1] = base.win.get_y_size() // 2

def do_jump(jump_speed = 16, max_height = 1, fall_speed = 150, gravity = 50):
    player = base.render.find('Player')
    player.node().set_jump_speed(jump_speed)
    player.node().set_max_jump_height(max_height)
    player.node().set_fall_speed(fall_speed)
    player.node().set_gravity(gravity)
    player.node().do_jump()

def fp_cleanup():
    try:
        player = base.render.find('Player')
        base.world.remove(player.node())
        player.detach_node()

        ground = base.render.find('ground')
        base.world.remove(ground.node())
        ground.detach_node()

        disable_fp_camera()
        running_tasks.clear()
    except:
        print('fp_cleanup() failed to execute, passing.')

def enable_fp_camera(fp_height = 1):
    base_props = base.win.get_properties()
    bp_hide = base_props.get_cursor_hidden()
    toggle_props = WindowProperties()
    toggle_props.set_cursor_hidden(not bp_hide)
    base.win.request_properties(toggle_props)
    base.win.move_pointer(0, *paused_cursor_pos)

    player = base.render.find('Player')
    cam_pivot = player.find('cam_pivot')
    base.camLens.fov = 80
    base.camLens.set_near_far(0.01, 90000)
    base.camLens.focal_length = 7
    base.camera.reparent_to(cam_pivot)
    base.camera.set_pos_hpr(0., 0., 0., 0., 0., 0.)
    cam_pivot.set_pos(player, 0, 0, fp_height)
    add_running_task(update_cam, "update_fp_cam")
    add_running_task(physics_update, "physics_update")

    KeyBindings.activate_all("fps_controller")

    # disable built-in camera controller
    base.disable_mouse()

def disable_fp_camera():
    base_props = base.win.get_properties()
    bp_hide = base_props.get_cursor_hidden()
    toggle_props = WindowProperties()
    toggle_props.set_cursor_hidden(not bp_hide)
    base.win.request_properties(toggle_props)

    for task_obj in running_tasks[:]:
        base.task_mgr.remove(task_obj)

    running_tasks.clear()

    KeyBindings.deactivate_all("fps_controller")
    reset_key_map()

    pointer = base.win.get_pointer(0)
    paused_cursor_pos[0] = int(pointer.get_x())
    paused_cursor_pos[1] = int(pointer.get_y())

def pause_fp_camera():
    win_props = WindowProperties()
    win_props.set_cursor_hidden(False)
    base.win.request_properties(win_props)
    tmp_tasks = running_tasks[:]

    for task_obj in tmp_tasks:
        task_obj.pause()

    running_tasks[:] = tmp_tasks[:]
    KeyBindings.deactivate_all("fps_controller")
    reset_key_map()

    pointer = base.win.get_pointer(0)
    paused_cursor_pos[0] = int(pointer.get_x())
    paused_cursor_pos[1] = int(pointer.get_y())

def resume_fp_camera():
    win_props = WindowProperties()
    win_props.set_cursor_hidden(True)
    base.win.request_properties(win_props)
    base.win.move_pointer(0, *paused_cursor_pos)

    for task_obj in running_tasks:
        task_obj.resume()

    KeyBindings.activate_all("fps_controller")

def update_cam(task):
    running_tasks[1].resume()

    # the player movement speed

    player = base.render.find('Player')
    cam_pivot = player.find('cam_pivot')
    
    base.static_pos = player.get_pos()

    # get mouse data
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

    if base.win.movePointer(0, window_Xcoord_halved, window_Ycoord_halved):

        # calculate the pitch of the camera pivot
        p = cam_pivot.get_p() - (mouseY - window_Ycoord_halved) * mouseSpeedY

        # sanity checking
        p = max(minPitch, min(maxPitch, p))

        # directly set the camera pivot pitch
        cam_pivot.set_p(p)

        # rotate the player's heading according to the mouse x-axis movement
        h = player.get_h() - (mouseX - window_Xcoord_halved) * mouseSpeedX

        # sanity checking
        h %= 360.

        player.set_h(h)

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

    if not (keyMap["left"] or keyMap["right"] or keyMap["forward"] or keyMap["backward"]):
        if not running_tasks[1].is_paused and player.node().is_on_ground():
            # pause the physics_update if the player isn't in midair
            # and no movement keys are pressed
            temp_tasks = running_tasks[:]
            physics_task = temp_tasks[1]
            physics_task.pause()
            running_tasks[:] = temp_tasks[:]

    return task.cont

def physics_update(task):
    dt = globalClock.get_dt()
    base.world.do_physics(dt, base.bullet_max_step, 1/160)

    if base.static_frames > 60:
        base.static_frames = 0

    return task.cont

def make_collision(rigid_label, input_model, node_number, mass, target_pos = Vec3(), hpr_adj = Vec3(), scale_adj = 1):
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
    np.node().set_friction(1)
    np.set_pos(target_pos)
    np.set_scale(scale_adj)
    np.set_hpr(hpr_adj)
    np.set_collide_mask(BitMask32.allOn())
    base.world.attach_rigid_body(np.node())

def collider_data(pos_1 = Vec3(), pos_2 = Vec3()):
    coll = base.world.ray_test_closest(pos_1, pos_2)
    out_data = [coll.get_hit_pos(), coll.get_hit_normal(), coll.get_hit_fraction(), coll.get_node()]

    return out_data


# define button map
KeyBindings.add("move_left", "a", "fps_controller", lambda: setKey("left", 1))
KeyBindings.add("move_left_done", "a-up", "fps_controller", lambda: setKey("left", 0))
KeyBindings.add("move_right", "d", "fps_controller", lambda: setKey("right", 1))
KeyBindings.add("move_right_done", "d-up", "fps_controller", lambda: setKey("right", 0))
KeyBindings.add("move_forward", "w", "fps_controller", lambda: setKey("forward", 1))
KeyBindings.add("move_forward_done", "w-up", "fps_controller", lambda: setKey("forward", 0))
KeyBindings.add("move_backward", "s", "fps_controller", lambda: setKey("backward", 1))
KeyBindings.add("move_backward_done", "s-up", "fps_controller", lambda: setKey("backward", 0))
KeyBindings.add("run", "shift", "fps_controller", lambda: setKey("run", 1))
KeyBindings.add("run_done", "shift-up", "fps_controller", lambda: setKey("run", 0))
KeyBindings.add("jump", "space", "fps_controller", lambda: setKey("jump", 1))
KeyBindings.add("jump_done", "space-up", "fps_controller", lambda: setKey("jump", 0))
KeyBindings.add("do_jump", "mouse3", "fps_controller", do_jump)
