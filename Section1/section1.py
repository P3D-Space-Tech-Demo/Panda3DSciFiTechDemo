import common
from common import *
import fp_ctrl
import holo


ASSET_PATH = "Assets/Section1/"
SHADOW_MASK = BitMask32.bit(1)


# Keep track of all tasks that could be running, such that they can be removed
# when this section gets cleaned up.

section_task_ids = set()

def add_section_task(task, task_id, *args, **kwargs):

    base.task_mgr.add(task, task_id, *args, **kwargs)
    section_task_ids.add(task_id)


# Keep track of all lights that have been created, such that they can be removed
# when this section gets cleaned up.

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
        self.interval_seq = None

    def destroy(self):

        self.model.detach_node()
        self.model = None
        self._do_job = lambda: None

        if self.interval_seq and not self.interval_seq.is_stopped():
            self.interval_seq.finish()
            self.interval_seq.clear_intervals()

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
        part = job.generate_part()
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

        def do_job():

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
                do_job()
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
                return

            self.generator.set_z(z)

            return task.cont

        self._do_job = lambda: add_section_task(activate_generator, "activate_generator")

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
        job_func = Func(lambda: self._do_job())
        self.intervals = seq = Sequence()
        seq.append(par)
        seq.append(job_func)
        seq.start()


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

        threading2._start_new_thread(rotor_thread, ())

        self.pivot = NodePath("drone_pivot")
        self.model.reparent_to(self.pivot)

    def destroy(self):

        for interval in self.rotor_intervals:
            interval.finish()

        if self.wobble_intervals:
            self.wobble_intervals.finish()
            self.wobble_intervals.clear_intervals()

        Worker.destroy(self)

        self.pivot.detach_node()

    def wobble(self):

        h, p, r = start_hpr = self.pivot.get_hpr()
        hpr = (random.uniform(h - 2, h + 2), random.uniform(-3, 3), random.uniform(-3, 3))
        hpr_lerp = LerpHprInterval(self.pivot, .5, hpr, start_hpr, blendType='easeInOut')
        self.wobble_intervals = seq = Sequence()

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
            self.wobble_intervals.finish()
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

        job_func = Func(lambda: self._do_job())
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

    def exit_compartment(self):

        delayed_job = self._do_job

        def set_first_part():

            self.released = True
            self._do_job = delayed_job
            self.start_job()

        self._do_job = set_first_part
        self.move()

    def fly_up(self):

        self._do_job = lambda: IdleWorkers.add(self)
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

    def generate_part(self):
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

        t = task.time

        self.model.set_alpha_scale(t / duration)

        if t < duration:
            return task.cont

        self.job.finalizer(self.primitive)
        self.job.notify_part_done()
        self.destroy()

    def reset_size(self, task, node, duration):

        t = task.time
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
    cam_target = None

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

            Elevator.cam_target.look_at(self.model.get_pos())

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

        dt = globalClock.get_dt()
        self.blade_angle += self.blade_speed * dt
        r = task.cont

        if self.blade_angle >= 44.8:
            self.blade_angle = 44.8
            r = task.done
            self.idle = True

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

        for w in self.model.find_all_matches('**/wall*'):
            w.set_shader_off()
            w.set_shader(metal_shader)

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
            fp_ctrl.make_collision(f'stair_{i + 1}_brbn', stair, 0, 0, stair.get_pos())

        self.alcove_toggle = False
        self.door_close_intervals = None

        def hide_corridor():
            if base.camera.get_pos(base.render).x < self.entrance_pos.x:
                self.corridor_model.hide()

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

                seq = Sequence()
                seq.append(para)
                seq.append(Func(hide_corridor))
                self.door_close_intervals = seq
                seq.start()

                return task.done

            return task.cont

        def open_entrance_doors(task=None):
            if not self.alcove_toggle:
                pos = entrance_door_root.get_pos(base.render)
                pd_dist = (pos - base.camera.get_pos(base.render)).length()

                if pd_dist < 30:
                    self.alcove_toggle = True
                    self.corridor_model.show()

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
                        self.door_close_intervals.finish()
                        self.door_close_intervals.clear_intervals()
                        self.door_close_intervals = None

                    func = lambda: add_section_task(close_entrance_doors, "close_entrance_doors")
                    seq = Sequence()
                    seq.append(para)
                    seq.append(Func(func))
                    seq.start()

            if task:
                return task.cont

#        base.accept('o', open_entrance_doors)
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
        # for cameras inside the active force-field, render the latter with
        # set_depth_test(False) and set_two_sided(True) using set_tag_state(_key),
        # such that it gets rendered on top of everything else, giving the
        # impression of it being a volumetric effect
        self.forcefield.tags["render_state"] = "forcefield"

        self.sliding_panel = self.model.find("**/sliding_panel")
        self.sliding_panel_start_pos = self.sliding_panel.get_pos()
        self.sliding_panel.set_pos(0., 0., 0.)
        self.elevator_platform = self.model.find("**/elevator_platform")
        self.elevator_platform_start_z = self.elevator_platform.get_z()
        elevator_root = self.elevator_platform.attach_new_node("elevator_root")
        elevator_root.set_light_off(amb_light_node)

        for i in range(14):
            Elevator(elevator_root, -65. + i * 10.)

        self.job_starter = job_starter
        add_section_task(self.lower_panel, "lower_panel")

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
                stack_root.set_h(random.random() * 360.)

                for i in range(random.randint(1, 5)):
                    container_copy = container.copy_to(stack_root)
                    container_copy.set_h(random.random() * 360.)
                    container_copy.set_z(i * 10.)

        '''
        for root in self.model.find_all_matches("**/container_root_*"):

            for anchor in root.find_all_matches("**/container_b_anchor*"):
                container.copy_to(anchor)
        '''

#            root.flatten_strong()

        container.detach_node()

    def destroy(self):

        self.model.detach_node()
        self.model = None
        del Elevator.instances[:]
        base.ignore("o")

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
        Elevator.cam_target.reparent_to(stair_step)
        Elevator.cam_target.set_pos(74, 0., 4.)
        Elevator.cam_target.look_at(stair_step)
        Elevator.cam_target.children[0].set_y(-50.)
        self.raise_stairs()

    def raise_stairs(self):
        stair_par = Parallel()

        for i in range(len(self.model.find_all_matches("**/platform_stair_step*"))):
            stair = self.model.find(f"**/platform_stair_step{i + 1}")
            start_pos = stair.get_pos()
            end_pos = Point3(start_pos)
            end_pos.z += .55 * (i + 1)
            s_inter = LerpPosInterval(stair, 2., end_pos, start_pos)
            stair_par.append(s_inter)
            stair_brbn = base.render.find(f'**/stair_{i + 1}_brbn')
            s_brbn_inter = LerpPosInterval(stair_brbn, 2., end_pos, start_pos)
            stair_par.append(s_brbn_inter)

        stair_par.start()

class Section1:

    def __init__(self):
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

        self.holo_ship = base.loader.load_model(ASSET_PATH + 'models/holo_starship_a.gltf')
        threading2._start_new_thread(holo.apply_hologram, (self.holo_ship, (0, 0, 0.4), (0.98, 1, 0.95)))

        starship_id = "starship_a"  # should be determined by user
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
            model = model.parent.copy_to(model_root).children[0]
            parent = model.parent
            parent.set_sx(parent, -1.)
            x, y, z = parent.get_pos()
            parent.set_pos(0., 0., 0.)
            parent.flatten_light()  # bake negative scale into vertices
            parent.set_pos(-x, y, z)
            geom = model.node().modify_geom(0)
            geom.reverse_in_place()

            for i in range(geom.get_num_primitives()):
                prim = geom.modify_primitive(i)
                prim.set_index_type(GeomEnums.NT_uint32)

            self.starship_components[component_id] = model
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

        self.hangar = Hangar(self.start_jobs)

        add_section_task(self.check_workers_done, "check_workers_done")

        # set up camera control
        entrance_pos = Point3(self.hangar.entrance_pos)
        entrance_pos.x += 33
        fp_ctrl.fp_init(entrance_pos)
        self.cam_heading = 180.
        self.cam_target = base.render.attach_new_node("cam_target")
        self.cam_target.set_z(4.)
        self.cam_target.set_h(self.cam_heading)
        self.cam_is_fps = False

        def enable_orbital_cam():
            base.camera.reparent_to(self.cam_target)
            base.camera.set_y(-120.)
            base.camLens.fov = 80
            base.camLens.set_near_far(0.01, 90000)
            base.camLens.focal_length = 7
            add_section_task(self.move_camera, "move_camera")

        def cam_switch():
            if self.cam_is_fps:
                fp_ctrl.disable_fp_camera()
                enable_orbital_cam()

            else:
                base.task_mgr.remove("move_camera")
                fp_ctrl.enable_fp_camera()

            self.cam_is_fps = not self.cam_is_fps

        base.accept("\\", cam_switch)
        enable_orbital_cam()

        base.set_background_color(0.1, 0.1, 0.1, 1)
        self.setup_elevator_camera()

    def start_jobs(self):

        job = self.jobs[0]
        worker = IdleWorkers.pop(job.worker_type)
        check_job = lambda task: self.check_job(task, job, worker)
        add_section_task(check_job, "check_job")
        worker.do_job(job, start=True)
        job.is_assigned = True
        self.add_mirror_job(job)

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
        base.camera.look_at(base.render, 0, 0, 15)

        return task.cont

    def setup_elevator_camera(self):

        self.elevator_display_region = dr = base.win.make_display_region(.05, .25, .05, .35)
        dr.sort = 10
        dr.set_clear_color_active(True)
        dr.set_clear_depth_active(True)
        cam_node = Camera("elevator_cam")
        Elevator.cam_target = target = base.render.attach_new_node("elevator_cam_target")
        # target.set_hpr(120., -30., 0.)
        self.elevator_cam = cam = target.attach_new_node(cam_node)
        cam.set_y(-40)
        cam.set_z(2)
        dr.camera = cam

        state_node = NodePath("state")
        state_node.set_depth_test(False)
        state_node.set_two_sided(True)
        state = state_node.get_state()
        cam_node.set_tag_state_key("render_state")
        cam_node.set_tag_state("forcefield", state)

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

    def destroy_holo_ship(self):
        if self.holo_ship:
            self.holo_ship.detach_node()
            self.holo_ship = None
            holo.holo_cleanup()
            p_topper_force_brbn = base.render.find('**/brbn_force')
            base.world.remove(p_topper_force_brbn.node())
            p_topper_force_brbn.detach_node()

    def destroy(self):

        base.ignore("escape")
        base.ignore("\\")

        base.camera.reparent_to(base.render)
        # self.cam_target.detach_node()
        # self.cam_target = None
        base.win.remove_display_region(self.elevator_display_region)
        Elevator.cam_target.detach_node()
        Elevator.cam_target = None
        self.elevator_cam = None

        for tmp_node in base.render.find_all_matches("**/tmp_node"):
            tmp_node.detach_node()

        section_task_ids.add("update_cam")
        section_task_ids.add("physics_update")

        for task_id in section_task_ids:
            base.task_mgr.remove(task_id)

        IdleWorkers.clear()

        while Worker.instances:
            Worker.instances.pop().destroy()

        DroneCompartment.instance.destroy()
        self.hangar.destroy()
        self.hangar = None
        self.model_root.detach_node()
        self.model_root = None
        self.destroy_holo_ship()
        fp_ctrl.fp_cleanup()

        rigid_list = base.render.find_all_matches('**/brbn*')

        for rigid_body in rigid_list:
            base.world.remove(rigid_body.node())
            rigid_body.detach_node()

        rigid_list = base.render.find_all_matches('**/brbn*')

        stair_list = base.render.find_all_matches('**/stair_*')

        for rigid_body in stair_list:
            base.world.remove(rigid_body.node())
            rigid_body.detach_node()

        stair_list = base.render.find_all_matches('**/stair_*')

        for light in section_lights:
            base.render.set_light_off(light)
            light.detach_node()

        scene_filters.del_blur_sharpen()
        scene_filters.del_bloom()

        common.currentSection = None


def initialise(data=None):

    base.render.set_antialias(AntialiasAttrib.MMultisample)

    base.camera.set_pos(0, 0, -2)

    scene_filters.set_blur_sharpen(0.8)
    scene_filters.set_bloom()

    base.accept("escape", common.gameController.gameOver)

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

    return section
