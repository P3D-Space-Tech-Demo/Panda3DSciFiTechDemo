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


world = BulletWorld()
world.set_gravity(Vec3(0, 0, -9.81))
# the effective world-Z limit
ground_plane = BulletPlaneShape(Vec3(0, 0, 1), 0)
node = BulletRigidBodyNode('ground')
node.add_shape(ground_plane)
node.set_friction(0.1)
np = base.render.attach_new_node(node)
np.set_pos(0, 0, -0.3)
world.attach_rigid_body(node)

# 3D player movement system begins
keyMap = {"left": 0, "right": 0, "forward": 0, "backward": 0, "run": 0, "jump": 0}

def setKey(key, value):
    keyMap[key] = value

def fp_init():
    # initialize player character physics the Bullet way
    shape_1 = BulletCapsuleShape(0.75, 0.5, ZUp)
    player_node = BulletCharacterControllerNode(shape_1, 0.1, 'Player')  # (shape, mass, player name)
    player = base.render.attach_new_node(player_node)
    player.set_pos(150, 10, 15)
    player.set_collide_mask(BitMask32.all_on())
    world.attach_character(player.node())
    
def fp_cleanup():
    player = base.render.find('Player')
    world.remove(player.node())

def use_fp_camera():
    player = base.render.find('Player')
    base.camera.reparent_to(player)
    base.camera.set_y(player, 0.03)
    base.camera.set_z(player, 3.0)
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

    # disable mouse
    base.disable_mouse()

def update_cam(Task):
    # the player movement speed
    movementSpeedForward = 5
    movementSpeedBackward = 5
    striveSpeed = 6
    static_pos_bool = False
    static_pos = Vec3()

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
        if static_pos_bool:
            static_pos_bool = False

        player.set_x(player, -striveSpeed * globalClock.get_dt())

    if not keyMap["left"]:
        if not static_pos_bool:
            static_pos_bool = True
            static_pos = player.get_pos()

        player.set_x(static_pos[0])
        player.set_y(static_pos[1])

    if keyMap["right"]:
        if static_pos_bool:
            static_pos_bool = False

        player.set_x(player, striveSpeed * globalClock.get_dt())

    if not keyMap["right"]:
        if not static_pos_bool:
            static_pos_bool = True
            static_pos = player.get_pos()

        player.set_x(static_pos[0])
        player.set_y(static_pos[1])

    if keyMap["forward"]:
        if static_pos_bool:
            static_pos_bool = False

        player.set_y(player, movementSpeedForward * globalClock.get_dt())

    if keyMap["forward"] != 1:
        if not static_pos_bool:
            static_pos_bool = True
            static_pos = player.get_pos()

        player.set_x(static_pos[0])
        player.set_y(static_pos[1])

    if keyMap["backward"]:
        if static_pos_bool:
            static_pos_bool = False

        player.set_y(player, -movementSpeedBackward * globalClock.get_dt())

    return Task.cont

def physics_update(Task):
    dt = globalClock.get_dt()
    world.do_physics(dt)

    return Task.cont
