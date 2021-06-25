from common import *


asset_path = "Assets/Section1/"
shadow_mask = BitMask32.bit(1)

# load a scene shader
vert_shader = asset_path + "shaders/simplepbr_vert_mod_1.vert"
frag_shader = asset_path + "shaders/simplepbr_frag_mod_1.frag"
scene_shader = Shader.load(Shader.SL_GLSL, vert_shader, frag_shader)


def make_simple_spotlight(input_pos, look_at, shadows = False, shadow_res = 2048):
    spotlight = Spotlight('random_light')
    if shadows:
        spotlight.set_shadow_caster(True, shadow_res, shadow_res)
        spotlight.camera_mask = shadow_mask

    lens = PerspectiveLens()
    lens.set_near_far(0.5, 5000)
    spotlight.set_lens(lens)
    spotlight.set_attenuation((0.5, 0, 0.0000005))
    spotlight = base.render.attach_new_node(spotlight)
    spotlight.set_pos(input_pos)
    spotlight.look_at(look_at)
    base.render.set_light(spotlight)
    

r_sec = 2.0


pbr_material = Material("pbr_material")
pbr_material.base_color = (0.0049883, 0., 0.8, 1.)
pbr_material.refractive_index = 1.
pbr_material.emission = (0., 0.39676, 0.527723, 0.)
pbr_material.roughness = 0.5


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
    beam.set_material(pbr_material)
    beam.set_transparency(TransparencyAttrib.M_alpha)
    beam.set_shader_off()
    attrib = CBA.make(CBA.M_none, CBA.O_incoming_color, CBA.O_incoming_color,
        CBA.M_add, CBA.O_incoming_alpha, CBA.O_one, (.5, .5, 1., 1.))
    beam.set_attrib(attrib)
    beam.set_bin("unsorted", 0)
    beam.hide(shadow_mask)

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
    beam_connector.set_material(pbr_material)
    beam_connector.set_transparency(TransparencyAttrib.M_alpha)
    beam_connector.set_shader_off()
    attrib = CBA.make(CBA.M_none, CBA.O_incoming_color, CBA.O_incoming_color,
        CBA.M_add, CBA.O_incoming_alpha, CBA.O_one, (.5, .5, 1., 1.))
    beam_connector.set_attrib(attrib)
    beam_connector.set_bin("unsorted", 0)
    beam_connector.hide(shadow_mask)

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


class Worker:

    def __init__(self, worker_type, model, beam, beam_connector, generator_ext_z, pivot_offset=0.):

        self.type = worker_type
        self.model = model
        self.generator = model.find("**/generator")
        self.generator_start_z = self.generator.get_z()
        self.generator_ext_z = generator_ext_z
        self.beam_root = self.generator.attach_new_node("beam_root")
        self.beam_root.hide()
        self.beams = [beam.copy_to(self.beam_root) for _ in range(4)]
        self.beam_connectors = [beam_connector.copy_to(self.beam_root) for _ in range(4)]
        self.part = None
        self.job = None
        self.start_job = lambda: None
        self.pivot_offset = pivot_offset  # pivot offset from model center

        if worker_type == "drone":
            model.reparent_to(base.render)

    def reset_energy_beams(self,):

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
            target_vec = self.target_point - self.model.get_pos()
            self.start_dist = target_vec.length()
            base.task_mgr.add(self.move, "move_bot")
            self._do_job = lambda: elevator.add_request(lambda: elevator.lower_bot(self))
            return

        return task.cont

    def continue_job(self):

        if self.job:
            self.do_job(self.job)
        elif self.type == "bot":
            elevator = self.get_nearest_elevator(self.model.get_y())
            elevator.await_bot(self)
            base.task_mgr.add(lambda task: self.move_to_elevator(task, elevator),
                "move_to_elevator")

    def do_job(self, job, start=False):

        self.job = job
        part = job.generate_part()
        tmp_node = self.generator.attach_new_node("tmp_node")
        ext_z = self.generator_ext_z

        def deactivation_task(task):

            self.beam_root.hide()
            tmp_node.wrt_reparent_to(base.render)
            base.task_mgr.add(deactivate_generator, "deactivate_generator")

            laser_plights = base.render.find_all_matches("**/plight*")
            for l in laser_plights:
                if round(l.get_pos()[0], 0) == round(self.beam_root.get_pos(base.render)[0], 0):
                    l.set_pos(1000, 1000, 1000)

        def do_job():

            if tmp_node.get_pos(base.render)[2] < 3:
                self.part.model.reparent_to(base.render)
                self.part.model.wrt_reparent_to(tmp_node)
                tmp_node.set_scale(.1)
                duration = 1.5
                self.reset_energy_beams()
                self.beam_root.show()
                base.task_mgr.add(self.shoot_energy_beams, "shoot_energy_beams", delay=0.)
                self.part.move_to_ship(tmp_node, duration)
                solidify_task = lambda task: self.part.solidify(task, duration)
                base.task_mgr.add(solidify_task, "solidify")
                base.task_mgr.add(deactivation_task, "deactivate_beams", delay=duration)
                
            if tmp_node.get_pos(base.render)[2] > 3:
                def activate_drone_beam():
                    time.sleep(r_sec)
                    self.part.model.reparent_to(base.render)
                    self.part.model.wrt_reparent_to(tmp_node)
                    tmp_node.set_scale(.1)
                    duration = 1.5
                    self.reset_energy_beams()
                    self.beam_root.show()
                    base.task_mgr.add(self.shoot_energy_beams, "shoot_energy_beams", delay=0.)
                    self.part.move_to_ship(tmp_node, duration)
                    solidify_task = lambda task: self.part.solidify(task, duration)
                    base.task_mgr.add(solidify_task, "solidify")
                    base.task_mgr.add(deactivation_task, "deactivate_beams", delay=duration)
                    
                threading2._start_new_thread(activate_drone_beam, ())
                    
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

        self._do_job = lambda: base.task_mgr.add(activate_generator, "activate_generator")

        if start and self.type == "bot":
            self.start_job = lambda: self.set_part(part)
            elevator = self.get_nearest_elevator(job.start_pos.y)
            elevator.add_request(lambda: elevator.raise_bot(self, job.start_pos))
     
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


class WorkerBot(Worker):

    def __init__(self, beam, beam_connector):
        model = base.loader.load_model(asset_path + "models/worker_bot.gltf")
        model.set_shader_off()

        Worker.__init__(self, "bot", model, beam, beam_connector, .25, -.8875)

        self.turn_speed = 300.
        self.accel = 15.
        self.speed = 0.
        self.speed_max = 5.
        self.speed_vec = Vec3.forward()
        self.target_point = None
        self._do_job = lambda: None

    def set_part(self, part):
        self.part = part
        x, y, z = part.worker_pos
        self.target_point = Point3(x, y, 0.)
        target_vec = self.target_point - self.model.get_pos()
        self.start_dist = target_vec.length()
        base.task_mgr.add(self.move, "move_bot")

    def move(self, task):

        dt = globalClock.get_dt()
        target_vec = self.target_point - self.model.get_pos()
        dist = min(self.start_dist, target_vec.length())
        target_vec.normalize()
        dist_vec = Vec3(target_vec)
        target_vec *= self.start_dist - dist
        dot = self.speed_vec.dot(dist_vec)
        frac = min(1., (.35 + 100 * (1. - (dot + 1.) * .5)) * dt * self.start_dist / dist)

        if dot <= 0.:
            target_vec = dist_vec * 100.
#            print("Course corrected!")

        # to interpolate the speed vector, it is shortened by a small fraction,
        # while that same fraction of the target vector is added to it;
        # this generally changes the length of the speed vector, so to preserve
        # its length (the speed), it is normalized and then multiplied with the
        # current speed value
        speed_vec = self.speed_vec * self.speed * (1. - frac) + target_vec * frac

        if speed_vec.normalize():
            self.speed_vec = speed_vec

        pos = self.model.get_pos()
        old_pos = Point3(pos)
        pos += self.speed_vec * self.speed * dt
        pos.z = 0.
        self.model.set_pos(pos)
        old_h = self.model.get_h()
        quat = Quat()
        look_at(quat, self.speed_vec, Vec3.up())
        h, p, r = quat.get_hpr()
        d_h = h - old_h

        if abs(d_h) > self.turn_speed * dt:
            turn_speed = self.turn_speed * (-1. if d_h < 0. else 1.)
            self.model.set_h(old_h + turn_speed * dt)
        else:
            self.model.set_h(h)

        # accelerate to normal speed
        self.speed = min(self.speed_max, self.speed + self.accel * dt)

        target_vec = self.target_point - pos
        dist = target_vec.length()

        if dist <= self.speed * dt:
            self.speed = 0.
            self._do_job()
            self._do_job = lambda: None
            self.target_point = None

            return task.done

        return task.cont


class WorkerDrone(Worker):

    def __init__(self, beam, beam_connector):

        model = base.loader.load_model(asset_path + "models/worker_drone.gltf")
        model.set_shader_off()
        model.set_pos(0, 0, 20)

        Worker.__init__(self, "drone", model, beam, beam_connector, -.1)

    def set_part(self, part):
        import random

        self.part = part
        x, y, z = part.worker_pos
        drone_inter = LerpPosInterval(self.model, r_sec, (x, y, z), self.model.get_pos(), blendType='easeInOut')
        ran_hpr = Vec3(random.uniform(-10, 10), random.uniform(-10, 10), random.uniform(-15, 15))
        drone_rot = LerpHprInterval(self.model, 0.5, (ran_hpr), self.model.get_hpr(), blendType='easeInOut')
        
        drone_rotors = self.model.find_all_matches("**/propeller*")
        for r in drone_rotors:
            LerpHprInterval(r, 0.1, (360, 0, 0), (0, 0, 0), blendType='easeInOut').loop()
        
        di_par = Parallel()
        di_par.append(drone_inter)
        di_par.append(drone_rot)
        di_par.start()
        
        self._do_job()


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
        self.model.set_material(pbr_material)
        self.model.set_color(0.5, 0.5, 1., 1.)
        self.model.set_alpha_scale(0.)
        self.model.set_transform(job.component.get_net_transform())
        p_min, p_max = self.model.get_tight_bounds()
        self.center = p_min + (p_max - p_min) * .5

    def destroy(self):

        self.model.detach_node()
        self.model = None
#        self.job.notify_part_done()
        self.job = None

    def solidify(self, task, duration):

        self.model.set_alpha_scale(task.time / duration)

        if task.time < duration:
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
        self.model.wrt_reparent_to(base.render)
        node.detach_node()

    def move_to_ship(self, node, duration):

        base.task_mgr.add(lambda task: self.reset_size(task, node, duration), "reset_part_size")


class Elevator:

    instances = []

    def __init__(self, y):

        self.instances.append(self)
        self.model = base.loader.load_model(asset_path + "models/worker_bot_elevator.gltf")
        self.model.reparent_to(base.render)
        self.model.set_y(y)
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
                self.bot.start_job()
                self.bot = None
                base.task_mgr.add(set_ready, "set_ready", delay=1.5)
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
            base.task_mgr.add(self.close_iris, "close_iris")

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
            base.task_mgr.add(self.raise_platform, "raise_platform")

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
                    request = lambda: base.task_mgr.add(self.open_iris, "open_iris")
                    self.add_request(request, index=0)

        for blade in self.blades:
            blade.set_h(self.blade_angle)

        return r

    def await_bot(self, bot):

        self.waiting_bots.append(bot)
        request = lambda: base.task_mgr.add(self.open_iris, "open_iris")
        self.add_request(request)

    def raise_bot(self, bot, start_pos):

        def open_iris():

            self.bot = bot
            bot.model.set_pos_hpr(0., bot.pivot_offset, 0., 0., 0., 0.)
            bot.model.reparent_to(self.platform_connector)
            vec = start_pos - self.model.get_pos()
            quat = Quat()
            look_at(quat, vec, Vec3.up())
            h, p, r = quat.get_hpr()
            self.platform_connector.set_h(h)
            base.task_mgr.add(self.open_iris, "open_iris")

        def raise_if_none_waiting(task):

            if self.waiting_bots:
                return task.cont

            if self.closed:
                self.add_request(open_iris)
            else:
                lower_platform = lambda: base.task_mgr.add(self.lower_platform, "lower_platform")
                self.add_request(lower_platform)
                self.add_request(open_iris)

            self.cam_target.reparent_to(self.model)

        base.task_mgr.add(raise_if_none_waiting, "raise_if_none_waiting")

    def lower_bot(self, bot):

        self.bot = bot
        bot.model.wrt_reparent_to(self.platform_connector)
        base.task_mgr.add(self.lower_platform, "lower_platform")

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


class Section1:

    def __init__(self):
        # set up camera control
        self.cam_heading = 180.
        self.cam_target = base.render.attach_new_node("cam_target")
        self.cam_target.set_z(10.)
        self.cam_target.set_h(self.cam_heading)
        base.camera.reparent_to(self.cam_target)
        base.camera.set_x(-50)
        base.camera.set_y(-125.)
        base.camera.set_z(2)
        base.camera.look_at(0, 0, 0)
        base.task_mgr.add(self.move_camera, "move_camera")

        base.set_background_color(0.1, 0.1, 0.1, 1)
        self.setup_elevator_camera()

        for i in range(20):
            elevator = Elevator(-90. + i * 10.)
            elevator.cam_target = self.elevator_cam_target

        base.task_mgr.add(Elevator.handle_requests, "handle_elevator_requests")

        starship_id = "starship_a"  # should be determined by user
        self.starship_components = {}

        model_root = base.loader.load_model(asset_path + f"models/{starship_id}.bam")
        model_root.reparent_to(base.render)
        model_root.set_shader(scene_shader)
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

        job = self.jobs[0]
        worker = IdleWorkers.pop(job.worker_type)
        check_job = lambda task: self.check_job(task, job, worker)
        base.task_mgr.add(check_job, "check_job")
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
        if base.camera.get_z() < 50:
            base.camera.set_z(base.camera.get_z() + 0.4 * dt)
        base.camera.look_at(0, 0, 5)

        return task.cont

    def setup_elevator_camera(self):

        self.elevator_display_region = dr = base.win.make_display_region(.05, .25, .05, .35)
        dr.sort = 10
        dr.set_clear_color_active(True)
        dr.set_clear_depth_active(True)
        cam_node = Camera("elevator_cam")
        self.elevator_cam_target = target = base.render.attach_new_node("elevator_cam_target")
        target.set_hpr(120., -30., 0.)
        self.elevator_cam = cam = target.attach_new_node(cam_node)
        cam.set_y(-10.)
        dr.camera = cam

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
            base.task_mgr.add(check_job, "check_job")
            worker.do_job(mirror_job, start=True)
            mirror_job.is_assigned = True

        base.task_mgr.add(start_mirror_job, "start_mirror_job", delay=1.5)

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
                base.task_mgr.add(next_check, "check_job")
                self.add_mirror_job(next_job)

        if not job.done:
            return task.cont

        if worker.type == "drone":
            IdleWorkers.add(worker)
            worker.generator.set_z(worker.generator_start_z)


def start(_=None, data=None):

    # we want the mixed graphics pipe for procedural gen so we'll
    # not set the scene_shader on base.render
    # base.render.set_shader(scene_shader)
    base.render.set_antialias(AntialiasAttrib.MMultisample)

    # add a shop floor
    floor = base.loader.load_model(asset_path + "models/shiny_floor.gltf")
    floor.reparent_to(base.render)
    floor.set_shader(scene_shader)
    floor.set_z(-0.3)

    for x in range(6):
        plight_1 = PointLight('plight_1')
        # add plight props here
        plight_1_node = base.render.attach_new_node(plight_1)
        plight_1_node.set_pos(1000, 1000, 1000)
        plight_1_node.node().set_color((0.1, 0.1, 0.9, 0.75))
        plight_1_node.node().set_attenuation((0.5, 0, 0.05))
        base.render.set_light(plight_1_node)

    make_simple_spotlight((200, 100, 900), (0, 5, 10), True)
    make_simple_spotlight((200, 100, 900), (0, 5, 10), False)
    make_simple_spotlight((200, 100, 900), (0, 5, 10), False)
    # make_simple_spotlight((200, 100, 300), (0, 5, 10), False)

    Section1()


initialise = start
