import common
from common import *
import fp_ctrl
import holo
from panda3d.bullet import BulletBoxShape, BulletRigidBodyNode
from Ships import shipSpecs

ASSET_PATH = "Assets/Section1/"
SHADOW_MASK = BitMask32.bit(1)


# keep track of all tasks and intervals that could be running, such that they
# can be paused, resumed and removed when this section gets cleaned up
section_tasks = []
section_intervals = []

def add_section_task(task_func, task_id, *args, **kwargs):

    cleanup = lambda task_obj: section_tasks.remove(task_obj)
    task_obj = ResumableTask(task_func, task_id, uponDeath=cleanup, *args, **kwargs)
    base.task_mgr.add(task_obj)
    section_tasks.append(task_obj)

    return task_obj

def remove_section_tasks():

    for task_obj in section_tasks[:]:
        base.task_mgr.remove(task_obj)

    section_tasks.clear()

def pause_section_tasks():

    tmp_tasks = section_tasks[:]

    for task_obj in tmp_tasks:
        task_obj.pause()

    section_tasks[:] = tmp_tasks[:]

def resume_section_tasks():

    for task_obj in section_tasks:
        task_obj.resume()

def pause_section_intervals():

    for interval in section_intervals:
        interval.pause()

def resume_section_intervals():

    for interval in section_intervals:
        interval.resume()

def remove_section_intervals():

    for interval in section_intervals:
        interval.pause()

    section_intervals.clear()

# keep track of all lights that have been created, such that they can be removed
# when this section gets cleaned up
section_lights = []

def make_simple_spotlight(input_pos, look_at, shadows = False, shadow_res = 2048, priority = 0):
    spotlight = Spotlight('random_light')
    spotlight.set_priority(priority)

    if shadows:
        spotlight.set_shadow_caster(True, shadow_res, shadow_res)
        spotlight.camera_mask = SHADOW_MASK

    lens = PerspectiveLens()
    lens.set_near_far(0.5, 5000)
    spotlight.set_lens(lens)
    # spotlight.set_attenuation((0.5, 0, 0.005))
    spotlight = base.render.attach_new_node(spotlight)
    spotlight.set_pos(input_pos)
    spotlight.look_at(look_at)
    spotlight.node().get_lens().set_fov(178)
    base.render.set_light(spotlight)
    section_lights.append(spotlight)


# define custom, multi-array vertex format with separate float color column
enums = GeomEnums
float32 = enums.NT_float32
v_format = GeomVertexFormat()
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.get_vertex(), 3, float32, enums.C_point)
v_format.add_array(array_format)
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.get_color(), 4, float32, enums.C_color)
v_format.add_array(array_format)
v_format = GeomVertexFormat.register_format(v_format)


CBA = ColorBlendAttrib
color_blend_attrib = CBA.make(CBA.M_none, CBA.O_incoming_color, CBA.O_incoming_color,
    CBA.M_add, CBA.O_incoming_alpha, CBA.O_one)


def create_beam():

    from math import pi, sin, cos

    pos_data = array.array("f", [])
    col_data = array.array("f", [])
    segs = 6
    vert_count = 0

    for i in range(segs + 1):
        angle = pi * 2 / segs * i
        x = sin(angle)
        z = -cos(angle)
        pos_data.extend((x, 0., z, x, 1., z))
        col_data.extend((.5, .5, 1., 1., .5, .5, 1., .25))
        vert_count += 2

    v_data = GeomVertexData("data", v_format, enums.UH_static)
    v_data.unclean_set_num_rows(vert_count)
    pos_data_array = v_data.modify_array(0)
    pos_view = memoryview(pos_data_array).cast("B").cast("f")
    pos_view[:] = pos_data
    col_data_array = v_data.modify_array(1)
    col_view = memoryview(col_data_array).cast("B").cast("f")
    col_view[:] = col_data

    prim = GeomTriangles(enums.UH_static)

    for i in range(segs):
        i1 = i * 2
        i2 = i1 + 1
        i3 = i2 + 1
        i4 = i3 + 1
        prim.add_vertices(i1, i2, i3)
        prim.add_vertices(i2, i4, i3)

    geom = Geom(v_data)
    geom.add_primitive(prim)

    node = GeomNode("beam")
    node.add_geom(geom)
    beam = NodePath(node)
    beam.set_light_off()
    beam.set_transparency(TransparencyAttrib.M_alpha)
    beam.set_shader_off()
    beam.set_attrib(color_blend_attrib)
    beam.set_depth_write(False)
    beam.set_bin("unsorted", 0)
    beam.hide(SHADOW_MASK)

    return beam


def create_beam_connector():

    col_data = array.array("f", [
        .5, .5, 1., 1.,
        .5, .5, 1., 0.,
        .5, .5, 1., 0.
    ])

    v_data = GeomVertexData("data", v_format, enums.UH_static)
    v_data.set_num_rows(3)
    col_data_array = v_data.modify_array(1)
    col_view = memoryview(col_data_array).cast("B").cast("f")
    col_view[:] = col_data

    prim = GeomTriangles(enums.UH_static)
    prim.add_vertices(0, 1, 2)
    geom = Geom(v_data)
    geom.add_primitive(prim)
    node = GeomNode("beam_connector")
    node.add_geom(geom)
    beam_connector = NodePath(node)
    beam_connector.set_two_sided(True)
    beam_connector.set_light_off()
    beam_connector.set_transparency(TransparencyAttrib.M_alpha)
    beam_connector.set_shader_off()
    beam_connector.set_attrib(color_blend_attrib)
    beam_connector.set_depth_write(False)
    beam_connector.set_bin("unsorted", 0)
    beam_connector.hide(SHADOW_MASK)

    return beam_connector


# The following class wraps a camera that focuses on a particular object which
# it renders to a secondary display region inset within the main view.
# The display region is updated each time the window is resized to maintain its
# aspect ratio and pixel-offset from the window borders.
# The intent is to have the camera focus on a specific object at a moment of
# interest (e.g. a drone starting work on generating a part of the starship's
# hull), for as long as deemed appropriate. During this time, the camera cannot
# focus on a different object if so requested, as this could lead to way too
# fast shifts in focus. Whether the camera can shift focus or not is determined
# by its idle state. Normally this comes down to the idle state of the object
# in focus, although the `idle` class variable can also be used (it is checked
# when the `focus` object is `None`).
class FocusCamera:

    target = None
    cam = None
    display_region = None
    idle = True
    focus = None
    listener = None

    @classmethod
    def setup(cls):
        from direct.showbase.DirectObject import DirectObject
        cls.target = target = base.render.attach_new_node("worker_cam_target")
        cam_node = Camera("worker_focus_cam")
        cam_node.get_lens().fov = (30., 25.)
        cls.cam = cam = target.attach_new_node(cam_node)
        cam.set_y(-20.)
        cls.display_region = dr = base.win.make_display_region(.05, .25, .05, .35)
        dr.sort = 1
        dr.set_clear_color_active(True)
        dr.set_clear_depth_active(True)
        dr.camera = cam

        state_node = NodePath("state")
        state_node.set_depth_test(False)
        state_node.set_two_sided(True)
        state = state_node.get_state()
        cam_node.set_tag_state_key("render_state")
        cam_node.set_tag_state("forcefield", state)

        cls.listener = DirectObject()
        cls.listener.accept("window-event", cls.update_display_region)
        cls.update_display_region(base.win)

        cls.idle = True

    @classmethod
    def destroy(cls):

        base.win.remove_display_region(cls.display_region)
        cls.display_region = None
        cls.target.detach_node()
        cls.target = None
        cls.cam = None
        cls.focus = None
        cls.listener.ignore_all()
        cls.listener = None

    @classmethod
    def update_display_region(cls, window):

        w = window.get_x_size()
        h = window.get_y_size()
        t = .2
        y1 = 20
        y2 = h * t
        x1 = 20
        x2 = x1 + (y2 - y1) * cls.cam.node().get_lens().aspect_ratio
        l = x1 / w
        r = x2 / w
        b = y1 / h
        cls.display_region.dimensions = (l, r, b, t)

    @classmethod
    def is_idle(cls):

        if cls.focus:
            return cls.focus.idle
        else:
            return cls.idle


class IdleWorkers:

    workers = {"bot": [], "drone": []}
    beam = None
    beam_connector = None

    @classmethod
    def pop(cls, worker_type):

        workers = cls.workers[worker_type]

        if workers:
            return workers.pop(0)

        if not cls.beam:
            cls.beam = create_beam()
            cls.beam.set_scale(.1)
            cls.beam_connector = create_beam_connector()

        if worker_type == "bot":
            return WorkerBot(cls.beam, cls.beam_connector)
        elif worker_type == "drone":
            return WorkerDrone(cls.beam, cls.beam_connector)

    @classmethod
    def add(cls, worker):

        cls.workers[worker.type].insert(0, worker)
        worker.job.worker_done = True

    @classmethod
    def clear(cls):

        for workers in cls.workers.values():

            for worker in workers:
                worker.destroy()
                Worker.instances.remove(worker)

            workers.clear()


class Worker:

    instances = []

    def __init__(self, worker_type, model, beam, beam_connector, generator_ext_z, pivot_offset=0.):

        self.instances.append(self)
        self.type = worker_type
        self.model = model
        self.model.set_shader_off()
        self.generator = model.find("**/generator")
        # self.generator.set_transparency(TransparencyAttrib.M_alpha)
        self.generator_start_z = self.generator.get_z()
        self.generator_ext_z = generator_ext_z
        self.beam_root = self.generator.attach_new_node("beam_root")
        self.beam_root.hide()
        self.beams = [beam.copy_to(self.beam_root) for _ in range(4)]
        self.beam_connectors = [beam_connector.copy_to(self.beam_root) for _ in range(4)]
        self.part = None
        self.job = None
        self._do_job = lambda: None
        self.start_job = lambda: None
        self.target_point = None
        self.pivot_offset = pivot_offset  # pivot offset from model center
        self.intervals = None

    def destroy(self):

        self.model.detach_node()
        self.model = None
        self._do_job = lambda: None

        if self.intervals and not self.intervals.is_stopped():
            self.intervals.finish()
            self.intervals.clear_intervals()
            if self.intervals in section_intervals:
                section_intervals.remove(self.intervals)

    @property
    def idle(self):

        return self in IdleWorkers.workers[self.type]

    def reset_energy_beams(self):

        for beam in self.beams:
            beam.set_sy(.01)

        pos_data = array.array("f", [0.] * 9)

        for connector in self.beam_connectors:
            v_data = connector.node().modify_geom(0).modify_vertex_data()
            pos_data_array = v_data.modify_array(0)
            pos_view = memoryview(pos_data_array).cast("B").cast("f")
            pos_view[:] = pos_data

    def shoot_energy_beams(self, task):

        from random import random, randint

        if not self.part:
            return

        model = self.part.model
        prim = self.part.primitive

        if not model:
            return

        v_data = model.node().get_geom(0).get_vertex_data()
        pos_reader = GeomVertexReader(v_data, "vertex")
        tri_count = prim.get_num_primitives()
        beam_root = self.beam_root
        beam_positions = []
        use_randint = True

        for beam in self.beams:
            tri_index = randint(0, tri_count - 1)
            index_offset1 = randint(0, 2)
            index_offset2 = randint(0, 2)
            vert_row1 = prim.get_vertex(tri_index * 3 + index_offset1)
            vert_row2 = prim.get_vertex(tri_index * 3 + index_offset2)
            pos_reader.set_row(vert_row1)
            pos1 = pos_reader.get_data3()
            pos_reader.set_row(vert_row2)
            pos2 = pos_reader.get_data3()
            vec = pos2 - pos1
            rand = randint(0, 1) if use_randint else random()
            use_randint = not use_randint
            pos = pos1 + vec * rand
            pos = beam_root.get_relative_point(model, pos)
            beam_positions.append(pos)
            dist = pos.length()
            beam.set_sy(dist)
            beam.look_at(beam_root, pos)

        beam_positions.append(beam_positions[0])
        positions = zip(beam_positions[:-1], beam_positions[1:])

        for (pos1, pos2), connector in zip(positions, self.beam_connectors):
            v_data = connector.node().modify_geom(0).modify_vertex_data()
            pos_data_array = v_data.modify_array(0)
            pos_view = memoryview(pos_data_array).cast("B").cast("f")
            pos_view[3:6] = array.array("f", [*pos1])
            pos_view[6:9] = array.array("f", [*pos2])

        task.delay_time = .01

        laser_plights = base.render.find_all_matches("**/plight*")
        l_len = len(laser_plights)
        for l in laser_plights:
            laser_plights[randint(0, l_len - 1)].set_pos(beam.get_pos(base.render))

        return task.again

    def move_to_elevator(self, task, elevator):

        if elevator.ready and elevator.waiting_bots[0] is self:
            pos = elevator.model.get_pos()
            model_pos = self.model.get_pos()
            pivot_offset_vec = (pos - model_pos).normalized() * self.pivot_offset
            # make sure the worker model gets centered on the elevator platform
            self.target_point = pos + pivot_offset_vec
            self._do_job = lambda: elevator.add_request(lambda: elevator.lower_bot(self))
            self.move()
            return

        return task.cont

    def continue_job(self):

        if self.job:
            self.do_job(self.job)
        elif self.type == "bot":
            elevator = self.get_nearest_elevator(self.model.get_y())
            elevator.await_bot(self)
            add_section_task(lambda task: self.move_to_elevator(task, elevator), "move_to_elevator")
        else:
            self.fly_up()

    def do_job(self, job, start=False):

        self.job = job
        part = job.get_next_part()
        tmp_node = self.generator.attach_new_node("tmp_node")
        tmp_node.set_compass()
        ext_z = self.generator_ext_z

        def deactivation_task(task):

            self.beam_root.hide()
            add_section_task(deactivate_generator, "deactivate_generator")

            laser_plights = base.render.find_all_matches("**/plight*")
            for l in laser_plights:
                if round(l.get_pos()[0], 0) == round(self.beam_root.get_pos(base.render)[0], 0):
                    l.set_pos(1000, 1000, 1000)

        def generate_part():

            part.model.reparent_to(base.render)
            part.model.wrt_reparent_to(tmp_node)
            tmp_node.set_scale(.1)
            duration = 1.5
            self.reset_energy_beams()
            self.beam_root.show()
            add_section_task(self.shoot_energy_beams, "shoot_energy_beams", delay=0.)
            self.part.move_to_ship(tmp_node, duration)
            solidify_task = lambda task: part.solidify(task, duration)
            add_section_task(solidify_task, "solidify")
            add_section_task(deactivation_task, "deactivate_beams", delay=duration)

        def activate_generator(task):

            dt = globalClock.get_dt()
            z = self.generator.get_z() + ext_z * 2. * dt
            end_z = self.generator_start_z + ext_z

            if (z - end_z) * (-1. if ext_z < 0. else 1.) >= 0.:
                self.generator.set_z(end_z)
                generate_part()
                return

            self.generator.set_z(z)

            return task.cont

        def deactivate_generator(task):

            dt = globalClock.get_dt()
            z = self.generator.get_z() - ext_z * 2. * dt
            end_z = self.generator_start_z

            if (z - end_z) * (-1. if ext_z < 0. else 1.) <= 0.:

                self.generator.set_z(end_z)
                self.continue_job()

                if FocusCamera.focus is self:
                    FocusCamera.focus = None

                return

            self.generator.set_z(z)

            return task.cont

        def activation_job():

            add_section_task(activate_generator, "activate_generator")

            if FocusCamera.is_idle():
                FocusCamera.focus = self
                FocusCamera.target.set_pos(*part.worker_pos)
                h = random.uniform(-135., -45.) if job.start_pos.x < 0. else random.uniform(45., 135.)
                FocusCamera.target.set_hpr(h, -20., 0.)

        self._do_job = activation_job

        if start:
            self.start_job = lambda: self.set_part(part)
            if self.type == "bot":
                elevator = self.get_nearest_elevator(job.start_pos.y)
                elevator.add_request(lambda: elevator.raise_bot(self, job.start_pos))
            elif self.released:
                self.speed_vec = Vec3.down()
                self.set_part(part)
            else:
                DroneCompartment.instance.release_drone(self)
        else:
            self.set_part(part)

    def get_nearest_elevator(self, y):

        shortest_dist = 1000000.

        for elevator in Elevator.instances:

            dist = abs(elevator.y - y)

            if dist < shortest_dist:
                shortest_dist = dist
                nearest_elevator = elevator

        return nearest_elevator

    def set_part(self, part):

        self.part = part
        self.target_point = Point3(*part.worker_pos)
        self.move()


class WorkerBot(Worker):

    def __init__(self, beam, beam_connector):

        model = base.loader.load_model(ASSET_PATH + "models/worker_bot.gltf")

        Worker.__init__(self, "bot", model, beam, beam_connector, .25, -.8875)

    def move(self):

        model_pos = self.model.get_pos()
        quat = Quat()
        vec = self.target_point - model_pos
        dist = max(0., vec.length() - 4.)
        vec.normalize()
        look_at(quat, vec, Vec3.up())
        hpr = quat.get_hpr()
        main_duration = dist * .139
        blend_duration = .5
        end_pos1 = model_pos + vec * 2.
        end_pos2 = end_pos1 + vec * dist
        end_pos3 = end_pos2 + vec * 2.
        ease_in = LerpPosInterval(self.model, blend_duration, end_pos1, model_pos, blendType='easeIn')
        no_blend = LerpPosInterval(self.model, main_duration, end_pos2, end_pos1, blendType='noBlend')
        ease_out = LerpPosInterval(self.model, blend_duration, end_pos3, end_pos2, blendType='easeOut')
        seq = Sequence()
        seq.append(ease_in)
        seq.append(no_blend)
        seq.append(ease_out)
        rot = LerpHprInterval(self.model, 0.5, hpr, self.model.get_hpr(), blendType='easeInOut')
        par = Parallel()
        par.append(seq)
        par.append(rot)

        def job_func():

            if self.intervals in section_intervals:
                section_intervals.remove(self.intervals)

            self._do_job()

        job_func = Func(job_func)
        self.intervals = seq = Sequence()
        seq.append(par)
        seq.append(job_func)
        seq.start()
        section_intervals.append(self.intervals)


class WorkerDrone(Worker):

    def __init__(self, beam, beam_connector):

        model = base.loader.load_model(ASSET_PATH + "models/worker_drone.gltf")

        Worker.__init__(self, "drone", model, beam, beam_connector, -.1)

        self.released = False
        self.wobble_intervals = None
        self.rotor_intervals = []

        def rotor_thread():

            for p in self.model.find_all_matches("**/propeller_*"):
                interval = LerpHprInterval(p, 0.1, (360, 0, 0), (0, 0, 0))
                interval.loop()
                self.rotor_intervals.append(interval)
                section_intervals.append(interval)

        threading2._start_new_thread(rotor_thread, ())

        self.pivot = NodePath("drone_pivot")
        self.model.reparent_to(self.pivot)

    def destroy(self):

        for interval in self.rotor_intervals:
            if interval in section_intervals:
                section_intervals.remove(interval)
            interval.finish()

        if self.wobble_intervals:
            if self.wobble_intervals in section_intervals:
                section_intervals.remove(self.wobble_intervals)
            self.wobble_intervals.pause()
            self.wobble_intervals.clear_intervals()
            self.wobble_intervals = None

        Worker.destroy(self)

        self.pivot.detach_node()

    def wobble(self):

        if self.wobble_intervals:
            self.wobble_intervals.pause()
            if self.wobble_intervals in section_intervals:
                section_intervals.remove(self.wobble_intervals)

        h, p, r = start_hpr = self.pivot.get_hpr()
        hpr = (random.uniform(h - 2, h + 2), random.uniform(-3, 3), random.uniform(-3, 3))
        hpr_lerp = LerpHprInterval(self.pivot, .5, hpr, start_hpr, blendType='easeInOut')
        self.wobble_intervals = seq = Sequence()
        section_intervals.append(self.wobble_intervals)

        if self in IdleWorkers.workers["drone"]:
            d = .5
            pos = (random.uniform(-d, d), random.uniform(-d, d), random.uniform(-d, d))
            pos_lerp = LerpPosInterval(self.model, 1.5, pos, self.model.get_pos(), blendType='easeInOut')
            par = Parallel()
            par.append(pos_lerp)
            par.append(hpr_lerp)
            seq.append(par)
        else:
            seq.append(hpr_lerp)

        seq.append(Func(self.wobble))
        seq.start()

    def stop_wobble(self):

        if self.wobble_intervals:
            pos = self.model.get_pos(base.render)
            hpr = self.pivot.get_hpr()
            if self.wobble_intervals in section_intervals:
                section_intervals.remove(self.wobble_intervals)
            self.wobble_intervals.pause()
            self.wobble_intervals.clear_intervals()
            self.wobble_intervals = None
            self.model.set_pos(0., 0., 0.)
            self.pivot.set_pos(pos)
            self.pivot.set_hpr(hpr)

    def move(self):

        self.stop_wobble()
        pivot_pos = self.pivot.get_pos()
        x1, y1, _ = self.target_point
        x2, y2, _ = pivot_pos
        # tilt the drone by an angle (maximum of e.g. 20 degrees) depending
        # on the travel distance, relative to a reference distance (in this
        # case 20 units)
        f = min(1., (Point3(x1, y1, 0.) - Point3(x2, y2, 0.)).length() / 20.)
        pitch = -20. * f
        vec = self.target_point - pivot_pos
        dist = max(0., vec.length() - 4.)
        vec.normalize()
        quat = Quat()
        look_at(quat, vec, Vec3.up())
        h, p, r = quat.get_hpr()
        hpr_start = (h, pitch, 0.)
        hpr_end = (h, 0., 0.)
        main_duration = dist * .0695
        blend_duration = .25
        level_duration = .5 * f

        end_pos1 = pivot_pos + vec * 2.
        end_pos2 = end_pos1 + vec * dist
        end_pos3 = end_pos2 + vec * 2.
        ease_in = LerpPosInterval(self.pivot, blend_duration, end_pos1, pivot_pos, blendType='easeIn')
        no_blend = LerpPosInterval(self.pivot, main_duration, end_pos2, end_pos1, blendType='noBlend')
        ease_out = LerpPosInterval(self.pivot, blend_duration, end_pos3, end_pos2, blendType='easeOut')

        pos_seq = Sequence()
        pos_seq.append(ease_in)
        pos_seq.append(no_blend)
        pos_seq.append(ease_out)

        def job_func():

            if self.intervals in section_intervals:
                section_intervals.remove(self.intervals)

            self._do_job()

        job_func = Func(job_func)
        pos_seq.append(job_func)
        pos_seq.append(Func(self.wobble))

        pitch_down = LerpHprInterval(self.model, blend_duration, (h, pitch, 0.),
            self.model.get_hpr(), blendType='easeInOut')
        pitch_up = LerpHprInterval(self.model, .5, (h, -pitch * .5, 0.),
            (h, pitch, 0.), blendType='easeInOut')
        level = LerpHprInterval(self.model, level_duration, (h, 0., 0.),
            (h, -pitch * .5, 0.), blendType='easeInOut')

        hpr_seq = Sequence()
        hpr_seq.append(pitch_down)
        hpr_seq.append(Wait(max(0., main_duration - .25)))
        hpr_seq.append(pitch_up)
        hpr_seq.append(level)

        self.intervals = par = Parallel()
        par.append(pos_seq)
        par.append(hpr_seq)
        par.start()
        section_intervals.append(self.intervals)

    def exit_compartment(self):

        delayed_job = self._do_job

        def set_first_part():

            self.released = True
            self._do_job = delayed_job
            self.start_job()

        self._do_job = set_first_part
        self.move()

    def fly_up(self):

        def set_idle():

            IdleWorkers.add(self)

            if FocusCamera.is_idle():
                FocusCamera.focus = self
                FocusCamera.target.set_pos(self.pivot.get_pos())
                h = random.uniform(0., 360.)
                FocusCamera.target.set_hpr(h, 40., 0.)

        self._do_job = set_idle
        x, y, z = self.pivot.get_pos()
        self.target_point = Point3(x, y, z + 20.)
        self.move()


class Job:

    def __init__(self, primitives, component, finalizer, component_id,
                 worker_type, worker_pos, next_jobs):

        self.primitives = primitives
        self.component = component
        self._finalizer_func = finalizer
        self.finalizer = lambda prim: finalizer(component, prim)
        self.component_id = component_id
        self.length = len(primitives)
        self.worker_type = worker_type
        self.worker_pos = worker_pos
        self.start_pos = Point3(*worker_pos[0])
        self.next_jobs = {}
        self.is_assigned = False
        self.worker_done = False

        for next_job in next_jobs:
            self.next_jobs[next_job["delay"]] = next_job["rel_index"]

        self.parts_done = 0

    def __bool__(self):

        return True if self.primitives else False

    def __len__(self):

        return len(self.primitives)

    def create_mirror(self, primitives, component, component_id):
        """
        Create a job that generates parts of a ship component that is a mirrored
        copy of another, relative to the YZ-plane.

        """

        worker_pos = []

        for pos in self.worker_pos:
            x, y, z = pos
            worker_pos.append(Point3(-x, y, z))

        return Job(primitives, component, self._finalizer_func, component_id,
            self.worker_type, worker_pos, [])

    @property
    def done(self):

        return self.parts_done == self.length

    @property
    def next_job_index(self):
        """
        Return the index of the next job in the list of available jobs.
        What this next job is depends on the number of parts currently generated.
        Return -1 if no next job is scheduled at this time (i.e. if there is
        none associated with a delay equal to that number of parts).

        """

        return self.next_jobs.get(self.parts_done, -1)

    def notify_part_done(self):

        self.parts_done += 1

    def get_next_part(self):
        if not self.primitives:
            return

        prim = self.primitives.pop(0)
        worker_pos = self.worker_pos.pop(0)

        return Part(self, prim, worker_pos)


class Part:

    def __init__(self, job, primitive, worker_pos):

        self.job = job
        vertex_data = job.component.node().modify_geom(0).get_vertex_data()
        geom = Geom(vertex_data)
        geom.add_primitive(primitive)
        self.primitive = primitive
        self.worker_pos = worker_pos
        node = GeomNode("part")
        node.add_geom(geom)
        self.model = NodePath(node)
        self.model.set_transparency(TransparencyAttrib.M_alpha)
        self.model.set_light_off()
        self.model.set_color(0.5, 0.5, 1., 1.)
        self.model.set_alpha_scale(0.)
        self.model.set_transform(job.component.get_net_transform())

    def destroy(self):

        self.model.detach_node()
        self.model = None
        self.job = None

    def solidify(self, task, duration):

        t = task.cont_time
        self.model.set_alpha_scale(t / duration)

        if t < duration:
            return task.cont

        self.job.finalizer(self.primitive)
        self.job.notify_part_done()
        self.destroy()

    def reset_size(self, task, node, duration):

        t = task.cont_time
        scale = .1 + (t / duration) * .9

        if t < duration:
            node.set_scale(scale)
            return task.cont

        node.set_scale(1.)
        node.detach_node()

    def move_to_ship(self, node, duration):

        add_section_task(lambda task: self.reset_size(task, node, duration), "reset_part_size")


class Elevator:

    instances = []

    def __init__(self, elevator_root, y):

        self.instances.append(self)
        self.model = base.loader.load_model(ASSET_PATH + "models/worker_bot_elevator.gltf")
        self.model.reparent_to(elevator_root)
        self.model.set_y(y)
        self.model.set_shader_off()
        self.y = y
        self.ready = False
        self.idle = True
        self.closed = True
        self.requests = []
        self.waiting_bots = []
        self.bot = None
        self.platform = self.model.find("**/platform")
        # create a node to attach a bot to, such that the latter ends up
        # being centered on the platform
        self.platform_connector = self.platform.attach_new_node("bot_connector")
        self.platform_z_min = self.platform.get_z()
        self.platform_speed = 5.
        self.blade_angle = 44.8  # controls aperture of shutter
        self.blade_speed = 40.
        self.blades = []

        for blade in self.model.find_all_matches("**/blade.*"):
            blade.set_h(self.blade_angle)
            self.blades.append(blade)

    def raise_platform(self, task):

        dt = globalClock.get_dt()
        z = self.platform.get_z()
        z += self.platform_speed * dt
        r = task.cont

        if z >= 0.:

            z = 0.
            r = task.done

            def set_ready(task=None):

                self.ready = True
                self.idle = True

                if FocusCamera.focus is self:
                    FocusCamera.focus = None

            if self.bot:
                self.bot.model.wrt_reparent_to(base.render)
                self.bot.model.set_z(0.)
                self.bot.start_job()
                self.bot = None
                add_section_task(set_ready, "set_ready", delay=1.5)
            else:
                set_ready()

        self.platform.set_z(z)

        return r

    def lower_platform(self, task):

        self.ready = False
        self.idle = False
        dt = globalClock.get_dt()
        z = self.platform.get_z()
        z -= self.platform_speed * dt
        r = task.cont

        if z <= self.platform_z_min:
            z = self.platform_z_min
            r = task.done
            add_section_task(self.close_iris, "close_iris")

        self.platform.set_z(z)

        return r

    def open_iris(self, task):

        self.idle = False
        self.closed = False
        dt = globalClock.get_dt()
        self.blade_angle -= self.blade_speed * dt
        r = task.cont

        if self.blade_angle <= 0.:
            self.blade_angle = 0.
            r = task.done
            add_section_task(self.raise_platform, "raise_platform")

        for blade in self.blades:
            blade.set_h(self.blade_angle)

        return r

    def close_iris(self, task):

        dt = globalClock.get_dt()
        self.blade_angle += self.blade_speed * dt
        r = task.cont

        if self.blade_angle >= 44.8:

            self.blade_angle = 44.8
            r = task.done
            self.idle = True
            self.closed = True

            if self.bot:

                IdleWorkers.add(self.bot)
                self.waiting_bots.remove(self.bot)
                self.bot.model.detach_node()
                self.bot = None

                if self.waiting_bots:
                    request = lambda: add_section_task(self.open_iris, "open_iris")
                    self.add_request(request, index=0)

        for blade in self.blades:
            blade.set_h(self.blade_angle)

        return r

    def await_bot(self, bot):

        self.waiting_bots.append(bot)
        request = lambda: add_section_task(self.open_iris, "open_iris")
        self.add_request(request)

    def raise_bot(self, bot, start_pos):

        def open_iris():

            self.bot = bot
            bot.model.set_pos_hpr(0., bot.pivot_offset, 0., 0., 0., 0.)
            bot.model.reparent_to(self.platform_connector)
            vec = start_pos - self.model.get_pos(base.render)
            quat = Quat()
            look_at(quat, vec, Vec3.up())
            h, p, r = quat.get_hpr()
            self.platform_connector.set_h(base.render, h)
            add_section_task(self.open_iris, "open_iris")

        def raise_if_none_waiting(task):

            if self.waiting_bots:
                return task.cont

            if self.closed:
                self.add_request(open_iris)
            else:
                lower_platform = lambda: add_section_task(self.lower_platform, "lower_platform")
                self.add_request(lower_platform)
                self.add_request(open_iris)

            if FocusCamera.is_idle():
                FocusCamera.target.set_pos(self.model.get_pos())
                h = random.uniform(-135., -45.)
                FocusCamera.target.set_hpr(h, -20., 0.)
                FocusCamera.focus = self

        add_section_task(raise_if_none_waiting, "raise_if_none_waiting")

    def lower_bot(self, bot):

        self.bot = bot
        bot.model.wrt_reparent_to(self.platform_connector)
        add_section_task(self.lower_platform, "lower_platform")

    def add_request(self, request, index=None):

        if index is None:
            self.requests.append(request)
        else:
            self.requests.insert(index, request)

    def handle_next_request(self):

        if self.idle and self.requests:
            self.requests.pop(0)()

    @classmethod
    def handle_requests(cls, task):

        for inst in cls.instances:
            inst.handle_next_request()

        return task.cont


class DroneCompartment:

    instance = None

    def __init__(self):

        DroneCompartment.instance = self
        self.model = base.loader.load_model(ASSET_PATH + "models/worker_drone_compartment.gltf")
        self.model.reparent_to(base.render)
        self.model.set_shader_off()
        self.idle = True
        self.closed = True
        self.requests = []
        self.drone = None
        self.blade_angle = 44.8  # controls aperture of shutter
        self.blade_speed = 40.
        self.blades = []

        for blade in self.model.find_all_matches("**/blade.*"):
            blade.set_h(self.blade_angle)
            self.blades.append(blade)

    def destroy(self):

        DroneCompartment.instance = None
        self.model.detach_node()
        self.model = None
        self.requests.clear()

    def open_iris(self, task):

        self.idle = False
        dt = globalClock.get_dt()
        self.blade_angle -= self.blade_speed * dt
        r = task.cont

        if self.blade_angle <= 0.:
            self.blade_angle = 0.
            r = task.done
            self.drone.exit_compartment()
            add_section_task(self.close_iris, "close_iris", delay=2.)

        for blade in self.blades:
            blade.set_h(self.blade_angle)

        return r

    def close_iris(self, task):

        # the delay needs to be set to zero explicitly, or resumption of the
        # task will use the initial delay of 2.0, despite the return value of
        # `task.cont` instead of `task.again`
        task.delay_time = 0.
        dt = globalClock.get_dt()
        self.blade_angle += self.blade_speed * dt
        r = task.cont

        if self.blade_angle >= 44.8:

            self.blade_angle = 44.8
            r = task.done
            self.idle = True

            if FocusCamera.focus is self:
                FocusCamera.focus = None

        for blade in self.blades:
            blade.set_h(self.blade_angle)

        return r

    def release_drone(self, drone):

        def request():

            self.drone = drone
            x, y, z = self.model.get_pos()
            drone.pivot.reparent_to(base.render)
            drone.pivot.set_pos(x, y, z + 1.)
            drone.target_point = Point3(x, y, z - 5.)
            add_section_task(self.open_iris, "open_iris")

            if FocusCamera.is_idle():
                FocusCamera.focus = self
                FocusCamera.target.set_pos(self.model.get_pos(base.render))
                h = random.uniform(0., 360.)
                FocusCamera.target.set_hpr(h, 30., 0.)

        self.add_request(request)

    def add_request(self, request, index=None):

        if index is None:
            self.requests.append(request)
        else:
            self.requests.insert(index, request)

    def handle_next_request(self, task):

        if self.idle and self.requests:
            self.requests.pop(0)()

        return task.cont


class Hangar:

    def __init__(self, job_starter):

        self.model = base.loader.load_model(ASSET_PATH + "models/hangar.gltf")
        self.model.reparent_to(base.render)
        ceiling = self.model.find('**/ceiling')
        ceiling.set_light_off()

        # apply metalness effect shader
        alcove = self.model.find('**/alcove')
        alcove.set_shader_off()
        alcove.set_shader(metal_shader)
        fp_ctrl.make_collision('alcove_brbn', alcove, 0, 0, alcove.get_pos())

        # make a light for the corridor interior
        plight_1 = PointLight('scene_light_3')
        # add plight props here
        plight_1.set_priority(10)
        plight_1_node = base.render.attach_new_node(plight_1)
        plight_1_node.set_pos(180, 0, 7)
        plight_1_node.node().set_color((0.9, 0.9, 1, 1))
        # plight_1_node.node().set_attenuation((0.5, 0, 0.05))
        base.render.set_light(plight_1_node)
        section_lights.append(plight_1_node)

        # this prevents the corridor light from reflecting overmuch
        p_topper_actual = self.model.find('p_topper')
        p_topper_actual.set_light_off(plight_1_node)
        floor = self.model.find('floor')
        floor.set_light_off(plight_1_node)

        corridor_coll_pos = [(180.83, -12.099, 3.46),  (179.901, 11.5889, 3.46), (199.222, -0.22609, 3.46), (156.69, 6.82736, 3.46), (156.522, -6.79245, 3.46)]
        shape_sizes = [(25, 1, 10), (25, 1, 10), (1, 25, 10), (2, 2, 10), (2, 2, 10)]

        for p, s in zip(corridor_coll_pos, shape_sizes):
            coll_shape = BulletBoxShape(Vec3(s))
            body = BulletRigidBodyNode('corridor_brbn_1')
            d_coll = base.render.attach_new_node(body)
            d_coll.node().add_shape(coll_shape)
            d_coll.node().set_mass(0)
            d_coll.node().set_friction(0.5)
            d_coll.set_collide_mask(BitMask32.allOn())
            d_coll.set_pos(p)
            base.world.attach_rigid_body(d_coll.node())

        for w in self.model.find_all_matches('**/wall*'):
            w.set_shader_off()
            w.set_shader(metal_shader)
            fp_ctrl.make_collision('wall_brbn', w, 0, 0, w.get_pos())

        entrance_doors = list(self.model.find_all_matches("**/entrance_door*"))
        entrance_door_root = self.model.attach_new_node("entrance_door_root")
        self.entrance_pos = Point3(157., 0., -4.)
        entrance_door_root.set_pos(self.entrance_pos)

        for d in entrance_doors:
            d.set_shader_off()
            d.set_shader(metal_shader)
            d.reparent_to(entrance_door_root)

        for d in self.model.find_all_matches("**/door_*"):
            d.set_shader_off()
            d.set_shader(metal_shader)
            fp_ctrl.make_collision('alcove_brbn', d, 0, 0, d.get_pos())

        for s in self.model.find_all_matches("**/support_anchor*"):
            s.set_shader_off()
            s.set_shader(metal_shader)

        for s in self.model.find_all_matches("**/platform_stair*"):
            s.set_shader_off()
            s.set_shader(metal_shader)

        amb_light = AmbientLight('amblight')
        amb_light.set_priority(50)
        amb_light.set_color((0.8, 0.8, 0.8, 1))
        amb_light_node = self.model.attach_new_node(amb_light)
        self.model.set_light(amb_light_node)
        section_lights.append(amb_light_node)

        # make initial stair collision
        for i in range(len(self.model.find_all_matches("**/platform_stair_step*"))):
            stair = self.model.find(f"**/platform_stair_step{i + 1}")
            z = -4.55 + i * .15
            stair.set_z(z)
            stair.flatten_strong()
            fp_ctrl.make_collision(f'stair_{i + 1}_brbn', stair, 0, 0, stair.get_pos())

        self.alcove_toggle = False
        self.door_open_intervals = None
        self.door_close_intervals = None

        def remove_door_open_intervals():
            if self.door_open_intervals and self.door_open_intervals in section_intervals:
                section_intervals.remove(self.door_open_intervals)

        def remove_door_close_intervals():
            if self.door_close_intervals and self.door_close_intervals in section_intervals:
                section_intervals.remove(self.door_close_intervals)

        def hide_corridor():
            if base.camera.get_pos(base.render).x < self.entrance_pos.x:
                self.corridor_model.hide()
                corridor_light = base.render.find('scene_light_3')
                base.render.set_light_off(corridor_light)

        def close_entrance_doors(task):
            pos = entrance_door_root.get_pos(base.render)
            pd_dist = (pos - base.camera.get_pos(base.render)).length()

            if pd_dist > 30:
                self.alcove_toggle = False

                doors_right = self.model.find_all_matches('**/entrance_door_right*')
                doors_left = self.model.find_all_matches('**/entrance_door_left*')
                origin = (0., 0., 0.)

                para = Parallel()

                for door in doors_right:
                    dr_inter = LerpPosInterval(door, 1.5, origin, (0., -6., 0.), blendType='easeInOut')
                    para.append(dr_inter)

                for door in doors_left:
                    dl_inter = LerpPosInterval(door, 1.5, origin, (0., 6., 0.), blendType='easeInOut')
                    para.append(dl_inter)

                if self.door_close_intervals and self.door_close_intervals in section_intervals:
                    section_intervals.remove(self.door_close_intervals)

                seq = Sequence()
                seq.append(para)
                seq.append(Func(hide_corridor))
                seq.append(Func(remove_door_close_intervals))
                self.door_close_intervals = seq
                seq.start()
                section_intervals.append(self.door_close_intervals)

                return task.done

            return task.cont

        def open_entrance_doors(task=None):
            if not self.alcove_toggle:
                pos = entrance_door_root.get_pos(base.render)
                pd_dist = (pos - base.camera.get_pos(base.render)).length()

                if pd_dist < 30:
                    self.alcove_toggle = True

                    doors_right = self.model.find_all_matches('**/entrance_door_right*')
                    doors_left = self.model.find_all_matches('**/entrance_door_left*')

                    para = Parallel()
                    pos_r = doors_right.get_path(0).get_pos()
                    pos_l = doors_left.get_path(0).get_pos()
                    d = 6. - abs(pos_r.y)
                    dur = 1.5 * d / 6.

                    for door in doors_right:
                        dr_inter = LerpPosInterval(door, dur, (0., -6., 0.), pos_r, blendType='easeInOut')
                        para.append(dr_inter)

                    for door in doors_left:
                        dl_inter = LerpPosInterval(door, dur, (0., 6., 0.), pos_l, blendType='easeInOut')
                        para.append(dl_inter)

                    if self.door_close_intervals and self.door_close_intervals.is_playing():
                        if self.door_close_intervals in section_intervals:
                            section_intervals.remove(self.door_close_intervals)
                        self.door_close_intervals.finish()
                        self.door_close_intervals.clear_intervals()
                        self.door_close_intervals = None

                    if self.door_open_intervals and self.door_open_intervals in section_intervals:
                        section_intervals.remove(self.door_open_intervals)

                    func = lambda: add_section_task(close_entrance_doors, "close_entrance_doors")
                    seq = Sequence()
                    seq.append(para)
                    seq.append(Func(func))
                    seq.append(Func(remove_door_open_intervals))
                    self.door_open_intervals = seq
                    seq.start()
                    section_intervals.append(self.door_open_intervals)
                    self.corridor_model.show()
                    corridor_light = base.render.find('scene_light_3')
                    base.render.set_light(corridor_light)

            if task:
                return task.cont

        add_section_task(open_entrance_doors, "open_entrance_doors")

        self.create_support_structure()
        self.create_corridor()
        self.add_containers()
        self.lights = self.model.find_all_matches("**/forcefield_light*")

        for light in self.lights:
            light.set_light_off()
            light.set_color(1., 0., 0., 1.)

        self.emission = 0.
        self.emission_incr = 1.
        self.emitters = self.model.find_all_matches("**/forcefield_emitter*")

        for emitter in self.emitters:
            emitter.set_light_off()

        add_section_task(self.pulsate_emitters, "pulsate_emitters")

        self.forcefield = self.model.find("**/forcefield")
        self.forcefield.set_light_off()
        self.forcefield.set_color(.2, .2, 1., .1)
        self.forcefield.set_transparency(TransparencyAttrib.M_alpha)
        self.forcefield.set_attrib(color_blend_attrib)
        self.forcefield.set_depth_write(False)
        self.forcefield.set_shader_off()
        # for cameras inside the active force-field, render the latter with
        # set_depth_test(False) and set_two_sided(True) using set_tag_state(_key),
        # such that it gets rendered on top of everything else, giving the
        # impression of it being a volumetric effect
        self.forcefield.tags["render_state"] = "forcefield"

        self.sliding_panel = self.model.find("**/sliding_panel")
        self.sliding_panel_start_pos = self.sliding_panel.get_pos()
        fp_ctrl.make_collision('panel_brbn', self.sliding_panel, 0, 0, Vec3())
        self.sliding_panel.set_pos(0., 0., 0.)
        self.elevator_platform = self.model.find("**/elevator_platform")
        self.elevator_platform_start_z = self.elevator_platform.get_z()
        elevator_root = self.elevator_platform.attach_new_node("elevator_root")
        elevator_root.set_light_off(amb_light_node)

        for i in range(14):
            Elevator(elevator_root, -65. + i * 10.)

        self.job_starter = job_starter
        add_section_task(self.lower_panel, "lower_panel")
        FocusCamera.target.set_pos(Elevator.instances[-3].model.get_pos(base.render))
        FocusCamera.target.set_z(0.)
        FocusCamera.target.set_hpr(180., -5., 0.)

    def create_support_structure(self):

        corner_beam = self.model.find("**/support_corner")
        vertical_beam = self.model.find("**/support_vertical")
        horizontal_beam = self.model.find("**/support_horizontal")
        roots = []
        roots.append(self.model.find("**/support_anchor_root_back"))
        roots.append(self.model.find("**/support_anchor_root_front"))
        roots.append(self.model.find("**/support_anchor_root_left"))
        roots.append(self.model.find("**/support_anchor_root_right"))
        roots.extend(self.model.find_all_matches("**/support_anchor_root_ceiling*"))

        anchor = self.model.find("**/support_anchor_front_left")
        beam_left = corner_beam.copy_to(anchor)
        anchor = self.model.find("**/support_anchor_front_right")
        beam_right = corner_beam.find("**/+GeomNode").copy_to(anchor)
        beam_right.set_sx(-1.)
        beam_right.node().modify_geom(0).reverse_in_place()
        anchor = self.model.find("**/support_anchor_back_left")
        beam = beam_right.copy_to(anchor)
        beam.set_h(180.)
        anchor = self.model.find("**/support_anchor_back_right")
        beam = beam_left.copy_to(anchor)
        beam.set_h(180.)

        for anchor in self.model.find_all_matches("**/support_anchor_vertical*"):
            vertical_beam.copy_to(anchor)

        for anchor in self.model.find_all_matches("**/support_anchor_horizontal*"):
            horizontal_beam.copy_to(anchor)

        corner_beam.detach_node()
        vertical_beam.detach_node()
        horizontal_beam.detach_node()

        for root in roots:
            root.flatten_strong()

    def create_corridor(self):

        model = base.loader.load_model(ASSET_PATH + "models/hangar_corridor.gltf")

        # apply metalness effect shader
        model.set_shader_off()
        model.set_shader(metal_shader)

        door_frame = model.find("**/corridor_door_frame")
        door_left = self.model.find("**/entrance_door_left")
        door_right = self.model.find("**/entrance_door_right")
        doors = (door_left, door_right)
        entrance_floor = self.model.find("**/entrance_floor")
        segment_a = model.find("**/corridor_segment_a")
        segment_b = model.find("**/corridor_segment_b")
        anchor1 = model.find("**/door_frame_anchor_01")
        anchor2 = model.find("**/door_frame_anchor_02")
        entrance_floor.copy_to(anchor1)
        entrance_floor.copy_to(anchor2)
        door_frame.copy_to(anchor1)
        door_frame.copy_to(anchor2)

        for door in doors:
            door_copy = door.copy_to(anchor1)
            door_copy.name = door.name + "_copy"

        for door in doors:
            door_copy = door.copy_to(anchor2)
            door_copy.name = door.name.replace("entrance", "corridor")

        for anchor in model.find_all_matches("**/segment_a_anchor*"):
            segment_a.copy_to(anchor)

        for anchor in model.find_all_matches("**/segment_b_anchor*"):
            segment_b.copy_to(anchor)

        entrance_floor.hide()
        door_frame.detach_node()
        segment_a.detach_node()
        segment_b.detach_node()
        model.set_pos(self.entrance_pos)
        model.reparent_to(self.model)
        self.corridor_model = model

    def add_containers(self):

        container = self.model.find("**/container_type_b")
        container.set_shader_off()
        container.set_shader(metal_shader)

        stack_dist = 18. + random.random() * 2.

        for root in self.model.find_all_matches("**/container_root_*"):

            stack_count = random.randint(2, 4)
            max_angle = 360. - 90. * stack_count
            angle = 0.
            root.set_h(random.random() * 360.)

            for _ in range(stack_count):

                stack_pivot = root.attach_new_node("stack_pivot")
                angle = random.uniform(angle, max_angle)
                stack_pivot.set_h(angle)
                angle += 90.
                max_angle += 90.
                stack_root = stack_pivot.attach_new_node("stack_root")
                stack_root.set_x(stack_dist)

                for i in range(random.randint(1, 5)):
                    container_copy = container.copy_to(stack_root)
                    container_copy.set_h(random.random() * 360.)
                    container_copy.set_z(i * 10.)

                container_shape = BulletBoxShape(Vec3(10, 10, 10))
                body = BulletRigidBodyNode('container_brbn')
                d_coll = base.render.attach_new_node(body)
                d_coll.node().add_shape(container_shape)
                d_coll.node().set_mass(0)
                d_coll.node().set_friction(0.5)
                d_coll.set_collide_mask(BitMask32.allOn())
                d_coll.set_pos(stack_root.get_pos(base.render))
                d_coll.set_h(stack_root.children[0].get_h(base.render))
                base.world.attach_rigid_body(d_coll.node())

        container.detach_node()

    def destroy(self):

        if self.door_open_intervals:
            if self.door_open_intervals.is_playing():
                self.door_open_intervals.finish()
                self.door_open_intervals.clear_intervals()
            if self.door_open_intervals in section_intervals:
                section_intervals.remove(self.door_open_intervals)
            self.door_open_intervals = None

        if self.door_close_intervals:
            if self.door_close_intervals.is_playing():
                self.door_close_intervals.finish()
                self.door_close_intervals.clear_intervals()
            if self.door_close_intervals in section_intervals:
                section_intervals.remove(self.door_close_intervals)
            self.door_close_intervals = None

        self.model.detach_node()
        self.model = None
        Elevator.instances.clear()

    def pulsate_emitters(self, task):

        from math import pi, sin

        dt = globalClock.get_dt()
        self.emission += 5. * self.emission_incr * dt

        if self.emission_incr > 0. and self.emission >= pi * .5:
            value = 1.
            self.emission = pi * .5
            self.emission_incr = -1.
        elif self.emission_incr < 0. and self.emission <= 0.:
            value = 0.
            self.emission = 0.
            self.emission_incr = 1.
        else:
            value = sin(self.emission)

        for emitter in self.emitters:
            emitter.set_color(value, value, 1., 1.)

        return task.cont

    def lower_panel(self, task):

        dt = globalClock.get_dt()
        start_z = self.sliding_panel_start_pos.z
        z = self.sliding_panel.get_z() - 5. * dt
        cont = True

        if z <= start_z:
            z = start_z
            cont = False

        self.sliding_panel.set_z(z)

        if cont:
            return task.cont

        add_section_task(lambda task: self.slide_panel(task, -1.), "slide_panel")

    def slide_panel(self, task, direction):

        dt = globalClock.get_dt()
        dest_x = self.sliding_panel_start_pos.x if direction < 0. else 0.
        x = self.sliding_panel.get_x() + 5. * direction * dt
        cont = True

        if (direction < 0. and x <= dest_x) or (direction > 0. and x >= dest_x):
            x = dest_x
            cont = False

        self.sliding_panel.set_x(x)

        if cont:
            return task.cont

        if direction < 0.:
            add_section_task(self.raise_elevator_platform, "raise_elevator_platform")
        else:
            add_section_task(self.raise_panel, "raise_panel")

    def raise_elevator_platform(self, task):

        dt = globalClock.get_dt()
        z = self.elevator_platform.get_z() + 5. * dt
        cont = True

        if z >= 0.:
            z = 0.
            cont = False

        self.elevator_platform.set_z(z)

        if cont:
            return task.cont

        self.job_starter()

    def deactivate_forcefield(self):

        add_section_task(self.lower_elevator_platform, "lower_elevator_platform")
        FocusCamera.target.set_pos(Elevator.instances[-3].model.get_pos(base.render))
        FocusCamera.target.set_hpr(-180, -5., 0.)
        FocusCamera.idle = False

        self.replace_procedural_ship()

    def lower_elevator_platform(self, task):

        dt = globalClock.get_dt()
        start_z = self.elevator_platform_start_z
        z = self.elevator_platform.get_z() - 5. * dt
        cont = True

        if z <= start_z:
            z = start_z
            cont = False

        self.elevator_platform.set_z(z)

        if cont:
            return task.cont

        add_section_task(lambda task: self.slide_panel(task, 1.), "slide_panel")

    def raise_panel(self, task):

        dt = globalClock.get_dt()
        z = self.sliding_panel.get_z() + 5. * dt
        cont = True

        if z >= 0.:
            z = 0.
            cont = False

        self.sliding_panel.set_z(z)

        if cont:
            return task.cont

        for light in self.lights:
            light.set_color(0., 1., 0., 1.)

        base.task_mgr.remove("pulsate_emitters")

        for emitter in self.emitters:
            emitter.set_color(0., 0., 0., 1.)

        self.forcefield.hide()

        stair_step = self.model.find("**/platform_stair_step1*")
        cam_target = FocusCamera.target
        cam_target.reparent_to(stair_step)
        cam_target.set_pos(120., 35., 5.)
        cam_target.look_at(74., 0., 0.)
        self.raise_stairs()

    def raise_stairs(self):

        p_topper_force_brbn = base.render.find('**/brbn_force')
        base.world.remove(p_topper_force_brbn.node())
        p_topper_force_brbn.detach_node()

        stair_seq = Sequence()
        stair_par = Parallel()

        def remove_intervals():

            if stair_seq in section_intervals:
                section_intervals.remove(stair_seq)

        for i in range(len(self.model.find_all_matches("**/platform_stair_step*"))):
            stair = self.model.find(f"**/platform_stair_step{i + 1}")
            start_pos = stair.get_pos()
            end_pos = Point3(start_pos)
            end_pos.z += .34 * (i + 1)
            s_inter = LerpPosInterval(stair, 2., end_pos, start_pos)
            stair_par.append(s_inter)
            stair_brbn = base.render.find(f'**/stair_{i + 1}_brbn')
            s_brbn_inter = LerpPosInterval(stair_brbn, 2., end_pos, start_pos)
            stair_par.append(s_brbn_inter)

        stair_seq.append(stair_par)
        stair_seq.append(Func(remove_intervals))
        stair_seq.start()
        section_intervals.append(stair_seq)

    def replace_procedural_ship(self):
        # this is a hack to make progress on the section
        # before the final ship model goes through the
        # procedural generation scripts

        # manually remove the generated ship
        for x in base.render.find_all_matches('**/tire*'):
            x.detach_node()

        for x in base.render.find_all_matches('**/rocket*'):
            x.detach_node()

        for x in base.render.find_all_matches('**/mirror*'):
            x.detach_node()

        for x in base.render.find_all_matches('**/outer*'):
            x.detach_node()

        for x in base.render.find_all_matches('**/front*'):
            x.detach_node()

        for x in base.render.find_all_matches('**/main/Cylinder*'):
            x.detach_node()

        for x in base.render.find_all_matches('**/back_wing*'):
            x.detach_node()

        # load in the playable ship
        finished_ship = base.loader.load_model('Assets/Shared/models/test_completed_ship_a.gltf')
        finished_ship.reparent_to(base.render)
        finished_ship.set_shader_off()
        finished_ship.set_shader(scene_shader)
        
        # mirror the ship parts
        mirror_ship_parts(finished_ship)

        for x in finished_ship.find_all_matches('*rocket*'):
            x.set_shader(metal_shader)

        for x in finished_ship.find_all_matches('*wing*'):
            x.set_shader(metal_shader)

        for x in finished_ship.find_all_matches('*d_*'):
            x.set_shader(metal_shader)
            
        for x in finished_ship.find_all_matches('*thruster*'):
            x.set_shader(metal_shader)
            
        for x in finished_ship.find_all_matches('*blaster*'):
            x.set_shader(metal_shader)

        interior_coll = finished_ship.find('interior')
        interior_coll.set_shader(metal_shader)
        interior_coll.flatten_strong()
        fp_ctrl.make_collision('interior_coll_brbn', interior_coll, 0, 0, interior_coll.get_pos(base.render))

        self.slide = finished_ship.find('ramp_actual')
        self.slide.flatten_strong()
        fp_ctrl.make_collision('slide_brbn', self.slide, 0, 0, self.slide.get_pos(base.render))

        slide_coll = base.render.find('slide_brbn')

        def ramp_seq():
            self.up_door = finished_ship.find('d_upper')
            self.down_door = finished_ship.find('d_lower')

            self.up_door_pos = self.up_door.get_pos(base.render)
            self.up_door_hpr = self.up_door.get_hpr()
            up_door_pos_adj = Vec3(self.up_door_pos[0], self.up_door_pos[1], self.up_door_pos[2] + 5)
            up_door_hpr_adj = Vec3(self.up_door_hpr[0], self.up_door_hpr[1], self.up_door_hpr[2] - 50)
            
            self.down_door_pos = self.down_door.get_pos(base.render)
            self.down_door_hpr = self.down_door.get_hpr()
            down_door_pos_adj = Vec3(self.down_door_pos[0], self.down_door_pos[1], self.down_door_pos[2] - 8)
            down_door_hpr_adj = Vec3(self.down_door_hpr[0], self.down_door_hpr[1], self.down_door_hpr[2] + 50)

            up_door_lerp = LerpHprInterval(self.up_door, 1, up_door_hpr_adj)
            down_door_lerp = LerpHprInterval(self.down_door, 1, down_door_hpr_adj)

            door_par = Parallel()
            door_par.append(up_door_lerp)
            door_par.append(down_door_lerp)

            ramp_1_pos = self.slide.get_pos(base.render)
            ramp_1_pos = Vec3(ramp_1_pos[0] + 13, ramp_1_pos[1], ramp_1_pos[2] - 2.4)

            slide_coll_pos = slide_coll.get_pos(base.render)
            slide_coll_pos = Vec3(slide_coll_pos[0] + 13, slide_coll_pos[1], slide_coll_pos[2] - 2.4)

            ramp_lerp = LerpPosHprInterval(self.slide, 2, ramp_1_pos, (0, 0, 22))
            ramp_lerp_2 = LerpPosHprInterval(slide_coll, 2, slide_coll_pos, (0, 0, 22))

            ramp_par = Parallel()
            ramp_par.append(ramp_lerp)
            ramp_par.append(ramp_lerp_2)

            door_ramp_seq = Sequence()
            door_ramp_seq.append(door_par)
            door_ramp_seq.append(ramp_par)
            door_ramp_seq.start()

        self.finished_ship_ready = False

        def ship_ready():
            while not self.finished_ship_ready:
                time.sleep(0.1)
                target = Vec3(30.7101, -15.3108, 7.21)
                p_dist = (target - base.camera.get_pos(base.render)).length()

                if p_dist < 20:
                    self.finished_ship_ready = True

                    ramp_seq()

        threading2._start_new_thread(ship_ready, ())

        cockpit = base.loader.load_model('Assets/Shared/models/test_cockpit.gltf')
        cockpit.reparent_to(base.render)
        cockpit.set_pos(0, -32, 9)
        cockpit.set_scale(1)
        cockpit.set_h(90)
        cockpit.set_light(base.render.find_all_matches('**/amblight*')[1])

        for a in cockpit.find_all_matches('**/*accent*'):
            a.set_shader_off()

        for t in cockpit.find_all_matches('**/*track*'):
            t.set_shader_off()

        joystick = base.loader.load_model('Assets/Shared/models/joystick.gltf')
        joystick.reparent_to(base.render)
        joystick.set_h(90)
        joystick.set_pos(0, 0, 10)
        joy_pos = joystick.get_pos()
        joystick.set_shader_off()
        joystick.hide()

        def animate_cockpit():
            c_1 = cockpit.find('**/chair')
            c_2 = cockpit.find('**/accent_rot')
            c_3 = cockpit.find('**/chair_bottom_accent')
            c_4 = cockpit.find('**/chair_cyl')

            c_1_rot = LerpHprInterval(c_1, 3.5, Vec3(), blendType='easeInOut')
            c_2_rot = LerpHprInterval(c_2, 3.5, Vec3(), blendType='easeInOut')

            c_1_inter = LerpPosInterval(c_1, 1.5, (-2, -0.002, 0), blendType='easeInOut')
            c_2_inter = LerpPosInterval(c_2, 1.5, (-2, -0.002, 0), blendType='easeInOut')
            c_3_inter = LerpPosInterval(c_3, 1.5, (-2, -0.002, -0.464), blendType='easeInOut')
            c_4_inter = LerpPosInterval(c_4, 1.5, (-2, 0, 0), blendType='easeInOut')

            joystick_inter = LerpPosInterval(joystick, 1.5, (joy_pos[0], joy_pos[1], joy_pos[2] + 0.75), joy_pos, blendType='easeInOut')

            def initiate_transition():
                fp_ctrl.fp_cleanup()

                base.camera.set_pos_hpr(0., 0., 0., 0., 0., 0.)
                base.camera.reparent_to(c_1)
                base.camLens.fov = 110
                base.camLens.set_near_far(0.01, 90000)
                base.camLens.focal_length = 7
                base.camera.set_h(90)
                base.camera.set_pos(1.2, 0, 2.9)

                right_arm = base.render.find_all_matches('**/Armature*')[0]
                right_arm.set_h(-15)
                r_pos = right_arm.get_pos()
                right_arm.set_pos(r_pos[0] + 2, r_pos[1], r_pos[2])
                right_arm.hide()

                left_arm = base.render.find_all_matches('**/Armature*')[1]
                left_arm.set_h(15)
                l_pos = left_arm.get_pos()
                left_arm.set_pos(l_pos[0] - 2, l_pos[1], l_pos[2] - 0.5)
                left_arm.hide()

                arm_screen = base.render.find('**/wide_screen_video_display.egg/Plane')
                as_pos = arm_screen.get_pos()
                arm_screen.set_pos(as_pos[0] - 2, as_pos[1], as_pos[2] - 0.5)
                arm_screen.hide()

                # make the blue laser lights white scene lights
                laser_plights = base.render.find_all_matches("**/plight*")
                for l in laser_plights:
                    l.node().set_color(Vec4(1, 1, 1, 1))
                    l.set_pos(0, 0, 30)

                # load in the outside space skybox
                cube_map_name = 'Assets/Section2/tex/main_skybox_#.png'
                self.skybox = common.create_skybox(cube_map_name)
                self.skybox.reparent_to(base.render)
                self.skybox.set_effect(CompassEffect.make(base.camera, CompassEffect.P_pos))
                self.skybox.node().set_bounds(OmniBoundingVolume())
                self.skybox.node().set_final(True)

                door_left = base.render.find('**/door_left')
                dl_pos = door_left.get_pos()
                dl_pos = Vec3(dl_pos[0] + 40, dl_pos[1], dl_pos[2])
                door_right = base.render.find('**/door_right')
                dr_pos = door_right.get_pos()
                dr_pos = Vec3(dr_pos[0] - 40, dr_pos[1], dr_pos[2])

                dl_inter = LerpPosInterval(door_left, 10, dl_pos, blendType='easeInOut')
                dr_inter = LerpPosInterval(door_right, 10, dr_pos, blendType='easeInOut')

                pit_pos = cockpit.get_pos()
                pit_pos = Vec3(pit_pos[0], pit_pos[1] - 400, pit_pos[2])
                joy_pos = joystick.get_pos()
                joy_pos = Vec3(joy_pos[0], joy_pos[1], joy_pos[2] - 1)
                ship_pos = finished_ship.get_pos()
                ship_pos = Vec3(ship_pos[0], ship_pos[1] - 400, ship_pos[2])

                pit_inter = LerpPosInterval(cockpit, 4, pit_pos, blendType='easeIn')
                joy_inter = LerpPosInterval(joystick, 0.3, joy_pos, blendType='easeInOut')
                ship_inter = LerpPosInterval(finished_ship, 4, ship_pos, blendType='easeIn')

                def exit_triggered():
                    '''def end_seq_1():
                        fade_in_text('loading', 'Loading...', Vec3(.75, 0, -.1), Vec4(1, 1, 1, 1))
                        # dismiss_info_text('loading')
                        
                    def end_seq_2():
                        self.skybox.detach_node()
                        common.gameController.startSectionIntro(1, shipSpecs[1])
                        
                    seq = Sequence()
                    seq.append(Func(end_seq_1))
                    seq.append(Func(end_seq_2))
                    seq.start()'''
                    self.skybox.detach_node()
                    common.gameController.startSectionIntro(1, shipSpecs[1])

                load_sec_2 = Func(exit_triggered)

                door_par = Parallel()
                door_par.append(dl_inter)
                door_par.append(dr_inter)

                pit_par = Parallel()
                pit_par.append(pit_inter)
                pit_par.append(joy_inter)
                pit_par.append(ship_inter)

                exit_seq = Sequence()
                exit_seq.append(door_par)
                exit_seq.append(pit_par)
                exit_seq.append(load_sec_2)
                exit_seq.start()

                section_intervals.append(exit_seq)

                def close_ship_doors():
                    up_door_lerp = LerpHprInterval(self.up_door, 1, self.up_door_hpr)
                    down_door_lerp = LerpHprInterval(self.down_door, 1, self.down_door_hpr)
                    ramp_lerp = LerpPosHprInterval(self.slide, 0.5, Vec3(), Vec3())

                    door_par = Parallel()
                    door_par.append(up_door_lerp)
                    door_par.append(down_door_lerp)
                    door_par.append(ramp_lerp)

                    door_ramp_seq = Sequence()
                    door_ramp_seq.append(door_par)
                    door_ramp_seq.start()

                close_ship_doors()

            initiate = Func(initiate_transition)

            def show_joy(t):
                t = t * 1

                joystick.show()

            lf_end = LerpFunc(show_joy, fromData=2.5, toData=4, duration=0)

            chair_par_1 = Parallel()
            chair_par_1.append(c_1_rot)
            chair_par_1.append(c_2_rot)

            chair_par_2 = Parallel()
            chair_par_2.append(c_1_inter)
            chair_par_2.append(c_2_inter)
            chair_par_2.append(c_3_inter)
            chair_par_2.append(c_4_inter)

            chair_seq = Sequence()
            chair_seq.append(initiate)
            chair_seq.append(chair_par_1)
            chair_seq.append(chair_par_2)
            chair_seq.append(lf_end)
            chair_seq.append(joystick_inter)
            chair_seq.start()

            section_intervals.append(chair_seq)

        self.cockpit_engaged = False

        def cockpit_check():
            while not self.cockpit_engaged:
                time.sleep(0.1)
                target = Vec3(0.204692, -26.4711, 14.0199)
                p_dist = (target - base.camera.get_pos(base.render)).length()

                if p_dist < 1:
                    self.cockpit_engaged = True

                    animate_cockpit()

        threading2._start_new_thread(cockpit_check, ())

class Section1:

    def __init__(self):

        events = KeyBindings.events["section1"]
        cam_toggle_key = events["cam_switch"].key_str
        music_toggle_key = events["toggle_music"].key_str
        events = KeyBindings.events["fps_controller"]
        jump_key = events["do_jump"].key_str
        forward_key = events["move_forward"].key_str
        backward_key = events["move_backward"].key_str
        left_key = events["move_left"].key_str
        right_key = events["move_right"].key_str
        events = KeyBindings.events["text"]
        help_toggle_key = events["toggle_help"].key_str
        # controller info text
        controller_text = '\n'.join((
            f'Toggle First-Person Mode: \1key\1{cam_toggle_key.title()}\2',
            f'\nJump: \1key\1{jump_key.title()}\2',
            f'\nForward: \1key\1{forward_key.title()}\2',
            f'Left: \1key\1{left_key.title()}\2',
            f'Right: \1key\1{right_key.title()}\2',
            f'Backward: \1key\1{backward_key.title()}\2',
            f'\nPlay/Pause Music: \1key\1{music_toggle_key.title()}\2',
            f'\nToggle This Help: \1key\1{help_toggle_key.title()}\2'
        ))
        TextManager.add_text("context_help", controller_text)

        self.jobs_started = False
        self.await_build_init = False
        self.arms_instantiated = False

        music_path = ASSET_PATH + 'music/space_tech_next_short.mp3'
        self.music = common.base.loader.load_music(music_path)
        self.music.set_loop(False)
        self.music_time = self.music.get_time()
        self.music_paused_while_playing = False
        # self.music.play()

        KeyBindings.set_handler("toggle_music", self.toggle_music, "section1")

        # initial collision
        p_topper = base.loader.load_model(ASSET_PATH + "models/p_topper.gltf")
        fp_ctrl.make_collision('brbn', p_topper, 0, 0)

        p_topper_out = base.loader.load_model(ASSET_PATH + "models/p_topper_out.gltf")
        pto_p = p_topper_out.get_pos()
        fp_ctrl.make_collision('brbn', p_topper_out, 0, 0, target_pos=(pto_p[0], pto_p[1], pto_p[2] -0.5))

        p_topper_force = base.loader.load_model(ASSET_PATH + "models/p_topper_force.gltf")
        fp_ctrl.make_collision('brbn_force', p_topper_force, 0, 0)

        add_section_task(Elevator.handle_requests, "handle_elevator_requests")

        compartment = DroneCompartment()
        compartment.model.set_pos(0., 0., 50.)
        add_section_task(compartment.handle_next_request, "handle_compartment_requests")

        def build_starship(ship = "starship_a"):
            if self.arms_instantiated:
                if not self.jobs_started:
                    if self.music.status() == 1:
                        self.music.set_time(self.music_time)
                        self.music.play()

                    print('Starship instantiation triggered.')
                    # starship instantiation begins
                    self.jobs_started = True
                    add_section_task(self.check_workers_done, "check_workers_done")

                    self.holo_ship.show()

                    if self.right_taps == 1:
                        ship = "starship_a"

                    elif self.right_taps == 2:
                        ship = "starship_b"

                    elif self.right_taps == 3:
                        ship = "starship_c"

                    starship_id = ship  # should be determined by user
                    self.starship_components = {}

                    self.model_root = model_root = base.loader.load_model(f"{ASSET_PATH}models/{starship_id}.bam")
                    model_root.reparent_to(base.render)
                    # model_root.set_two_sided(True)
                    model_root.set_color(1., 1., 1., 1.)

                    for model in model_root.find_all_matches("**/+GeomNode"):
                        component_id = model.parent.name
                        self.starship_components[component_id] = model

                    for mirror_node in model_root.find_all_matches("**/mirror_*"):

                        component_id = mirror_node.name
                        model = self.starship_components[component_id.replace("mirror_", "")]
                        mirror_parent = model.parent.copy_to(model.parent.parent)
                        x, y, z = mirror_parent.get_pos()
                        mirror_parent.set_pos(0., 0., 0.)
                        mirror_parent.flatten_light()  # bake orientation and scale into vertices
                        mirror_parent.set_sx(-1.)
                        mirror_parent.flatten_light()  # bake negative scale into vertices
                        mirror_parent.set_pos(-x, y, z)
                        mirror_model = mirror_parent.children[0]
                        geom = mirror_model.node().modify_geom(0)
                        geom.reverse_in_place()

                        for i in range(geom.get_num_primitives()):
                            prim = geom.modify_primitive(i)
                            prim.set_index_type(GeomEnums.NT_uint32)

                        self.starship_components[component_id] = mirror_model
                        mirror_node.detach_node()

                    self.jobs = []
                    self.mirror_jobs = {}
                    primitives = {}
                    finalizer = self.add_primitive

                    for component_id, component in self.starship_components.items():
                        node = component.node()
                        bounds = node.get_bounds()
                        geom = node.modify_geom(0)
                        vertex_data = geom.get_vertex_data()
                        new_prim = GeomTriangles(GeomEnums.UH_static)
                        new_prim.set_index_type(GeomEnums.NT_uint32)
                        primitives[component_id] = [prim for prim in geom.primitives]
                        geom.clear_primitives()
                        geom.add_primitive(new_prim)
                        node.set_bounds(bounds)
                        node.set_final(True)

                    for job_data in self.parse_job_schedule(starship_id):

                        part_count = job_data["part_count"]
                        del job_data["part_count"]
                        component_id = job_data["component_id"]
                        component = self.starship_components[component_id]
                        prims = primitives[component_id][:part_count]
                        job = Job(prims, component, finalizer, **job_data)
                        self.jobs.append(job)
                        del primitives[component_id][:part_count]
                        mirror_component_id = "mirror_" + component_id

                        if mirror_component_id in self.starship_components:
                            component = self.starship_components[mirror_component_id]
                            prims = primitives[mirror_component_id][:part_count]
                            mirror_job = job.create_mirror(prims, component, component_id)
                            self.mirror_jobs[component_id] = mirror_job
                            del primitives[mirror_component_id][:part_count]

                    # prune any invalid jobs
                    self.jobs = [j for j in self.jobs if j]

        KeyBindings.set_handler("build_starship", build_starship, "section1")

        self.holo_ship = base.loader.load_model(ASSET_PATH + 'models/holo_starship_a.gltf')
        threading2._start_new_thread(holo.apply_hologram, (self.holo_ship, (0, 0, 0.4), (0.98, 1, 0.95)))
        self.holo_ship.hide()

        FocusCamera.setup()

        self.hangar = Hangar(self.start_jobs)

        self.right_taps = 1
        # base.accept('arrow_right', self.arrow_arm_screen)
        KeyBindings.set_handler("arrow_arm_screen", self.arrow_arm_screen, "section1")

        # set up camera control
        entrance_pos = Point3(self.hangar.entrance_pos)
        entrance_pos.x += 33
        base.static_pos = Vec3(192.383, -0.182223, -0.5)

        self.cam_heading = 180.
        self.cam_target = base.render.attach_new_node("cam_target")
        self.cam_target.set_z(4.)
        self.cam_target.set_h(self.cam_heading)
        self.cam_pivot = self.cam_target.attach_new_node("cam_pivot")
        self.cam_pivot.set_y(-115.)
        self.cam_is_fps = False

        def enable_orbital_cam():
            base.camera.set_pos_hpr(0., 0., 0., 0., 0., 0.)
            base.camera.reparent_to(self.cam_pivot)
            base.camLens.fov = 80
            base.camLens.set_near_far(0.01, 90000)
            base.camLens.focal_length = 7

        def cam_switch():
            events = KeyBindings.events["fps_controller"]
            forward_key = events["move_forward"].key_str
            backward_key = events["move_backward"].key_str
            left_key = events["move_left"].key_str
            right_key = events["move_right"].key_str
            is_down = base.mouseWatcherNode.is_button_down
            moving = is_down(forward_key) or is_down(backward_key) or is_down(left_key) or is_down(right_key)

            if self.cam_is_fps:
                if moving:
                    return

                self.right_arm.hide()
                self.left_arm.hide()
                fp_ctrl.disable_fp_camera()
                enable_orbital_cam()
            else:
                if not self.arms_instantiated:
                    fp_ctrl.fp_init(Vec3(192.383, -0.182223, -0.5), z_limit=-4)

                fp_ctrl.enable_fp_camera(fp_height = 4.75)

                if not self.arms_instantiated:
                    self.arms_instantiated = True
                    # instantiate arms the normal way
                    # space suit arms setup begins
                    self.right_arm = base.loader.load_model("Assets/Shared/models/player_right_arm_restpose_2021_08_28.gltf")
                    self.right_arm.reparent_to(base.camera)
                    self.right_arm.set_pos(0.5, 1, -0.5)
                    self.right_arm.set_h(10)
                    self.right_arm.set_scale(0.2)

                    self.left_arm = base.loader.load_model("Assets/Shared/models/player_left_arm_restpose_2021_08_29.gltf")
                    self.left_arm.reparent_to(base.camera)
                    self.left_arm.set_pos(-0.5, 1, -0.5)
                    self.left_arm.set_h(-10)
                    self.left_arm.set_scale(0.2)

                    # the spacesuit arm holo-display begins
                    # make a new texture buffer, render node, and attach a camera
                    mirror_buffer = base.win.make_texture_buffer("mirror_buff", 512, 512)
                    self.mirror_render = NodePath("mirror_render")
                    self.mirror_render.set_shader(metal_shader)

                    mirror_cam = base.make_camera(mirror_buffer)
                    mirror_cam.reparent_to(self.mirror_render)
                    mirror_cam.set_pos(0, -20, 5)
                    mirror_cam.set_hpr(0, 25, 0)
                    mirror_cam.node().get_lens().set_focal_length(10)
                    mirror_cam.node().get_lens().set_fov(90)

                    mirror_filters = CommonFilters(mirror_buffer, mirror_cam)
                    # mirror_filters.set_high_dynamic_range()
                    mirror_filters.set_exposure_adjust(1.1)
                    # mirror_filters.set_gamma_adjust(1.3)

                    # load in a mirror/display object model in normal render space
                    mirror_model = base.loader.loadModel(ASSET_PATH + 'models/wide_screen_video_display.egg')
                    mirror_model.reparent_to(base.render)
                    mirror_model.set_pos(119.466, 4.90663, 3.46)
                    mirror_model.look_at(79.4992, 3.56733, 4.35998)
                    mirror_model.set_shader_off()
                    mirror_model.set_transparency(TransparencyAttrib.M_dual)
                    mirror_model.reparent_to(self.left_arm)
                    # mirror_model.set_h(90)
                    mirror_model.set_scale(0.5)
                    mirror_model.set_pos(-0.5, -0.3, 1)

                    amb_light = AmbientLight('amblight_2')
                    amb_light.set_priority(50)
                    amb_light.set_color((1, 1, 1, 1))
                    amb_light_node = mirror_model.attach_new_node(amb_light)
                    mirror_model.set_light(amb_light_node)
                    section_lights.append(amb_light_node)

                    # mirror scene model load-in
                    # reparent to mirror render node
                    self.screen_ship_1 = base.loader.load_model(ASSET_PATH + "models/starship_a_screen_select.gltf")
                    self.screen_ship_1.reparent_to(self.mirror_render)
                    self.screen_ship_1.set_pos(0, 0, 10)
                    self.screen_ship_1.set_scale(7)
                    nice = LerpHprInterval(self.screen_ship_1, 5, (360, 360, 360))
                    nice_seq = Sequence()
                    nice_seq.append(nice)
                    nice_seq.loop()
                    section_intervals.append(nice_seq)

                    # reparent to mirror render node
                    self.screen_ship_2 = base.loader.load_model(ASSET_PATH + "models/light_spec_screen_select.gltf")
                    self.screen_ship_2.reparent_to(self.mirror_render)
                    self.screen_ship_2.set_pos(-15, 0, 10)
                    self.screen_ship_2.set_scale(2)
                    mirror_ship_parts(self.screen_ship_2)
                    nice = LerpHprInterval(self.screen_ship_2, 5, (360, 360, 360))
                    nice_seq = Sequence()
                    nice_seq.append(nice)
                    nice_seq.loop()
                    section_intervals.append(nice_seq)

                    # reparent to mirror render node
                    self.screen_ship_3 = base.loader.load_model(ASSET_PATH + "models/heavy_spec_screen_select.gltf")
                    self.screen_ship_3.reparent_to(self.mirror_render)
                    self.screen_ship_3.set_pos(15, 0, 10)
                    self.screen_ship_3.set_scale(2)
                    mirror_ship_parts(self.screen_ship_3)
                    nice = LerpHprInterval(self.screen_ship_3, 5, (360, 360, 360))
                    nice_seq = Sequence()
                    nice_seq.append(nice)
                    nice_seq.loop()
                    section_intervals.append(nice_seq)

                    # mirror scene lighting
                    # point light generator
                    for x in range(3):
                        plight_1 = PointLight('mirror_light')
                        # add plight props here
                        plight_1_node = self.mirror_render.attach_new_node(plight_1)
                        # group the lights close to each other to create a sun effect
                        plight_1_node.set_pos(random.uniform(-21, -20), random.uniform(-21, -20), random.uniform(20, 21))
                        self.mirror_render.set_light(plight_1_node)
                        section_lights.append(plight_1_node)

                    # set the live buffer texture to the mirror/display model in normal render space
                    mirror_model.set_texture(mirror_buffer.get_texture())

                else:
                    self.right_arm.show()
                    self.left_arm.show()

            self.cam_is_fps = not self.cam_is_fps

        KeyBindings.set_handler("cam_switch", cam_switch, "section1")
        enable_orbital_cam()
        add_section_task(self.move_camera, "move_camera")

        base.set_background_color(0.1, 0.1, 0.1, 1)

    def arrow_arm_screen(self):

        if self.right_taps == 1:

            self.right_taps = 2
            # screen_ship_1 was the first to be shown at a scale of 7
            # so we'll give it a special scale check to prevent overscaling
            if self.screen_ship_1.get_scale() > 2:
                def make_smaller():
                    model_current_scale = self.screen_ship_1.get_scale()
                    for x in range(50):
                        model_current_scale -= 0.1
                        self.screen_ship_1.set_scale(model_current_scale)
                        time.sleep(0.001)

                threading2._start_new_thread(make_smaller, ())

            def make_bigger():
                model_current_scale = self.screen_ship_3.get_scale()
                for x in range(50):
                    model_current_scale += 0.1
                    self.screen_ship_3.set_scale(model_current_scale)
                    time.sleep(0.001)

            threading2._start_new_thread(make_bigger, ())

        elif self.right_taps == 2:

            self.right_taps = 3

            def make_smaller():
                model_current_scale = self.screen_ship_3.get_scale()
                for x in range(50):
                    model_current_scale -= 0.1
                    self.screen_ship_3.set_scale(model_current_scale)
                    time.sleep(0.001)

            threading2._start_new_thread(make_smaller, ())

            def make_bigger():
                model_current_scale = self.screen_ship_2.get_scale()
                for x in range(50):
                    model_current_scale += 0.1
                    self.screen_ship_2.set_scale(model_current_scale)
                    time.sleep(0.001)

            threading2._start_new_thread(make_bigger, ())

        elif self.right_taps == 3:

            self.right_taps = 1

            def make_smaller():
                model_current_scale = self.screen_ship_2.get_scale()
                for x in range(50):
                    model_current_scale -= 0.1
                    self.screen_ship_2.set_scale(model_current_scale)
                    time.sleep(0.001)

            threading2._start_new_thread(make_smaller, ())

            def make_bigger():
                model_current_scale = self.screen_ship_1.get_scale()
                for x in range(50):
                    model_current_scale += 0.1
                    self.screen_ship_1.set_scale(model_current_scale)
                    time.sleep(0.001)

            threading2._start_new_thread(make_bigger, ())

    def toggle_music(self):
        if self.music.status() == 2:
            self.music_time = self.music.get_time()
            self.music.stop()

        elif self.music.status() == 1:
            self.music.set_time(self.music_time)
            self.music.play()

    def start_jobs(self):

        if self.jobs_started:
            job = self.jobs[0]
            worker = IdleWorkers.pop(job.worker_type)
            check_job = lambda task: self.check_job(task, job, worker)
            add_section_task(check_job, "check_job")
            worker.do_job(job, start=True)
            job.is_assigned = True
            self.add_mirror_job(job)

            try:
                dismiss_info_text('bay_ready_text')
            except:
                print('No info text present.')

        else:
            events = KeyBindings.events["section1"]
            build_start_key = events["build_starship"].key_str.title()
            arrow_key = events["arrow_arm_screen"].key_str.title()
            bay_ready_text = '\n\n'.join((
                'Construction bay is ready and awaiting job input.',
                f'Tap \1key\1{arrow_key}\2 in First-Person Mode to hover-select your spacecraft.',
                f'Press \1key\1{build_start_key}\2 to begin building your selected spacecraft.'
            ))
            fade_in_text('bay_ready_text', bay_ready_text, Vec3(.75, 0, -.1), Vec4(1, 1, 1, 1))

            add_section_task(self.await_build_command, "await_build_command")

    def await_build_command(self, task):

        if self.jobs_started and not self.await_build_init:
            self.await_build_init = True
            self.start_jobs()

        return task.cont

    def parse_job_schedule(self, starship_id):

        job_schedule = []
        read_coords = False
        read_next_jobs = False
        path = os.path.join("Section1", f"jobs_{starship_id}.txt")

        with open(path) as job_file:

            for line in job_file:

                line = line.strip("\n")

                if line.startswith("#"):
                    continue
                elif not line:
                    job_data = {}
                    job_schedule.append(job_data)
                    continue
                elif line.startswith("worker_pos"):
                    read_coords = True
                    worker_pos = []
                    job_data["worker_pos"] = worker_pos
                    continue
                elif line.startswith("next_jobs"):
                    read_coords = False
                    read_next_jobs = True
                    next_jobs_data = []
                    job_data["next_jobs"] = next_jobs_data
                    continue
                elif not line.startswith(" "):
                    read_coords = False
                    read_next_jobs = False

                if read_coords:
                    coords = [float(x.strip()) for x in line.split()]
                else:
                    prop, val = [x.strip() for x in line.split()]
                    if prop == "part_count":
                        val = int(val)

                if read_coords:
                    worker_pos.append(coords)
                elif read_next_jobs:
                    val = int(val)
                    if prop == "rel_index":
                        next_job_data = {prop: val}
                        next_jobs_data.append(next_job_data)
                    else:
                        next_job_data[prop] = val
                else:
                    job_data[prop] = val

        return job_schedule

    def move_camera(self, task):

        dt = globalClock.get_dt()
        self.cam_heading -= 1.75 * dt
        self.cam_target.set_h(self.cam_heading)
        if self.cam_target.get_z() < 40:
            self.cam_target.set_z(self.cam_target.get_z() + 0.15 * dt)
        self.cam_pivot.look_at(base.render, 0, 0, 15)

        return task.cont

    def add_primitive(self, component, prim):

        prim_array = prim.get_vertices()
        prim_view = memoryview(prim_array).cast("B").cast("I")
        geom = component.node().modify_geom(0)
        new_prim = geom.modify_primitive(0)
        new_prim_array = new_prim.modify_vertices()
        old_size = new_prim_array.get_num_rows()
        new_prim_array.set_num_rows(old_size + len(prim_view))
        new_prim_view = memoryview(new_prim_array).cast("B").cast("I")
        new_prim_view[old_size:] = prim_view[:]

    def add_mirror_job(self, job):

        if job.component_id not in self.mirror_jobs:
            return

        mirror_job = self.mirror_jobs[job.component_id]

        def start_mirror_job(task):

            worker = IdleWorkers.pop(mirror_job.worker_type)
            check_job = lambda task: self.check_job(task, mirror_job, worker)
            add_section_task(check_job, "check_job")
            worker.do_job(mirror_job, start=True)
            mirror_job.is_assigned = True

        add_section_task(start_mirror_job, "start_mirror_job", delay=1.5)

    def check_job(self, task, job, worker):

        next_job_index = job.next_job_index

        if next_job_index > 0:

            index = self.jobs.index(job)
            next_job = self.jobs[index + next_job_index]

            if not next_job.is_assigned:
                next_worker = IdleWorkers.pop(next_job.worker_type)
                next_worker.do_job(next_job, start=True)
                next_job.is_assigned = True
                next_check = lambda task: self.check_job(task, next_job, next_worker)
                add_section_task(next_check, "check_job")
                self.add_mirror_job(next_job)

        if not job.done:
            return task.cont

    def check_workers_done(self, task):

        for job in self.jobs + list(self.mirror_jobs.values()):
            if not job.worker_done:
                return task.cont

        self.hangar.deactivate_forcefield()
        self.destroy_holo_ship()

    def pauseGame(self):

        if self.cam_is_fps:
            fp_ctrl.pause_fp_camera()

        pause_section_tasks()
        pause_section_intervals()

        if self.music.status() == 2:
            self.music_paused_while_playing = True

        self.music_time = self.music.get_time()
        self.music.stop()

        KeyBindings.deactivate_all("section1")
        KeyBindings.deactivate_all("text")

    def resumeGame(self):

        resume_section_tasks()
        resume_section_intervals()

        if self.music_paused_while_playing:
            self.music.set_time(self.music_time)
            self.music.play()

            self.music_paused_while_playing = False

        if self.cam_is_fps:
            fp_ctrl.resume_fp_camera()

        KeyBindings.activate_all("section1")
        KeyBindings.activate_all("text")

    def destroy_holo_ship(self):
        if self.holo_ship:
            self.holo_ship.detach_node()
            self.holo_ship = None
            holo.holo_cleanup()

    def destroy(self):

        # clean up the stand-in finished ship
        base.render.find('**/d_*').get_parent().detach_node()

        text_node = base.a2dTopLeft.find('bay_ready_text')

        if not text_node.is_empty():
            text_node.detach_node()

        if self.arms_instantiated:
            self.left_arm.detach_node()
            self.right_arm.detach_node()
            fp_ctrl.fp_cleanup()

        arm_screen = base.render.find('**/wide_screen_video_display.egg/Plane')
        arm_screen.get_parent().detach_node()

        if 'not' not in str(base.render.find('**/joystick')):
            joystick = base.render.find('**/joystick')
            joystick.get_parent().detach_node()
            cockpit = base.render.find('**/dashboard')
            cockpit.get_parent().detach_node()

        base.static_pos = Vec3(-5.29407, -15.2641, 2.66)

        TextManager.remove_text()

        KeyBindings.deactivate_all("section1")

        base.camera.reparent_to(base.render)
        self.cam_target.detach_node()
        self.cam_target = None
        FocusCamera.destroy()

        for tmp_node in base.render.find_all_matches("**/tmp_node"):
            tmp_node.detach_node()

        IdleWorkers.clear()

        while Worker.instances:
            Worker.instances.pop().destroy()

        DroneCompartment.instance.destroy()
        self.hangar.destroy()
        self.hangar = None

        if self.jobs_started:
            self.model_root.detach_node()
            self.model_root = None
            self.destroy_holo_ship()

        remove_section_tasks()
        remove_section_intervals()

        rigid_list = base.render.find_all_matches('**/*brbn*')

        for rigid_body in rigid_list:
            base.world.remove(rigid_body.node())
            rigid_body.detach_node()

        stair_list = base.render.find_all_matches('**/stair_*')

        for rigid_body in stair_list:
            base.world.remove(rigid_body.node())
            rigid_body.detach_node()

        for light in section_lights:
            base.render.set_light_off(light)
            light.detach_node()

        scene_filters.del_blur_sharpen()
        scene_filters.del_bloom()

        common.currentSection = None


def initialise(data=None):

    base.render.set_antialias(AntialiasAttrib.M_multisample)

    base.bullet_max_step = 1

    base.text_alpha = 0.01

    scene_filters.set_blur_sharpen(0.8)
    scene_filters.set_bloom()

    KeyBindings.set_handler("open_pause_menu", common.gameController.openPauseMenu, "section1")

    def print_player_pos():
        print(base.camera.get_pos(base.render))

    base.accept('f4', print_player_pos)

    for x in range(5):
        plight_1 = PointLight('plight_1')
        plight_1.set_priority(5)
        # add plight props here
        plight_1_node = base.render.attach_new_node(plight_1)
        plight_1_node.set_pos(1000, 1000, 1000)
        plight_1_node.node().set_color((0.1, 0.1, 0.9, 1.0))
        plight_1_node.node().set_attenuation((0.5, 0, 0.005))
        # plight_1_node.node().set_shadow_caster(True, 1024, 1024)
        base.render.set_light(plight_1_node)
        section_lights.append(plight_1_node)

    plight_1 = PointLight('scene_light_1')
    # add plight props here
    plight_1.set_priority(10)
    plight_1_node = base.render.attach_new_node(plight_1)
    plight_1_node.set_pos(0, 0, 30)
    plight_1_node.node().set_color((1, 1, 1, 1))
    # plight_1_node.node().set_attenuation((0.5, 0, 0.05))
    base.render.set_light(plight_1_node)
    section_lights.append(plight_1_node)

    plight_2 = PointLight('scene_light_2')
    plight_2.set_priority(10)
    # add plight props here
    plight_2_node = base.render.attach_new_node(plight_2)
    plight_2_node.set_pos(0, 0, 5)
    plight_2_node.node().set_color((1, 1, 1, 1))
    # plight_2_node.node().set_attenuation((0.5, 0, 0.05))
    base.render.set_light(plight_2_node)
    section_lights.append(plight_2_node)

    make_simple_spotlight((200, 100, 900), (0, 5, 10), False, 15)
    make_simple_spotlight((-200, 0, 2000), (146.4, -3.3, 5.7), False, 15)
    make_simple_spotlight((0, 0, 2000), (-90, 108, 10), False, 15)
    # make_simple_spotlight((0, 0, 1300), (-90, -120, 10), False)
    # make_simple_spotlight((0, 0, 1300), (102, -145, 10), False)
    # make_simple_spotlight((0, 0, 1300), (94, 120, 10), False)

    section = Section1()
    common.currentSection = section
    KeyBindings.activate_all("section1")
    KeyBindings.activate_all("text")

    return section


KeyBindings.add("open_pause_menu", "escape", "section1")
KeyBindings.add("cam_switch", "\\", "section1")
KeyBindings.add("toggle_music", "p", "section1")
KeyBindings.add("build_starship", "enter", "section1")
KeyBindings.add("arrow_arm_screen", "arrow_right", "section1")
