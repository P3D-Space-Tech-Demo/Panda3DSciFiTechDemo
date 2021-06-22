#!/usr/bin/env python

from panda3d.core import *
import os
import array
import gltf


loader = Loader.get_global_ptr()
loader_options = LoaderOptions(LoaderOptions.LF_no_cache)
gltf.patch_loader(loader)

# define custom, multi-array vertex format with separate float color column
enums = GeomEnums
float32 = enums.NT_float32
vertex_format = GeomVertexFormat()
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.get_vertex(), 3, float32, enums.C_point)
array_format.add_column(InternalName.get_normal(), 3, float32, enums.C_normal)
array_format.add_column(InternalName.get_texcoord(), 2, float32, enums.C_texcoord)
vertex_format.add_array(array_format)
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.get_color(), 4, float32, enums.C_color)
vertex_format.add_array(array_format)
multi_array_format = GeomVertexFormat.register_format(vertex_format)

def process_geom_node(node_path):

    sorted_indices = []
    geom = node_path.node().modify_geom(0)
    v_data = geom.modify_vertex_data()
    tmp_v_data = GeomVertexData(v_data)
    tmp_v_data.format = multi_array_format
    color_array = tmp_v_data.arrays[1]
    color_view = memoryview(color_array).cast("B").cast("f")
    old_prim = geom.modify_primitive(0)
    old_prim.set_index_type(enums.NT_uint32)
    old_prim_view = memoryview(old_prim.get_vertices()).cast("B").cast("I")

    for j, color in enumerate(color_view[i:i+4] for i in range(0, len(color_view), 4)):
        r, g, b, a = [int(round(encode_sRGB_float(x) * 255.)) for x in color]
        sort = r << 16 | g << 8 | b
        sorted_indices.append((sort, j))

    sorted_indices.sort()
    sort_values = [i[0] for i in sorted_indices]
    sorted_indices = [i[1] for i in sorted_indices]

    sorted_tris = []

    for tri in (old_prim_view[i:i+3] for i in range(0, len(old_prim_view), 3)):
        tri_indices = [sorted_indices.index(i) for i in tri]
        sorted_tris.append((min(tri_indices), tri.tolist()))

    sorted_tris.sort(reverse=True)
    index, tri = sorted_tris.pop()
    sort_val = sort_values[index]
    tris = [tri]
    tris_by_sort = [tris]

    while sorted_tris:

        index, tri = sorted_tris.pop()
        next_sort_val = sort_values[index]

        if next_sort_val == sort_val:
            tris.append(tri)
        else:
            tris = [tri]
            tris_by_sort.append(tris)
            sort_val = next_sort_val

    geom.clear_primitives()

    for tris in tris_by_sort:
        new_prim = GeomTriangles(enums.UH_static)
        new_prim.set_index_type(enums.NT_uint32)
        prim_array = new_prim.modify_vertices()
        tri_rows = sum(tris, [])
        prim_array.set_num_rows(len(tri_rows))
        new_prim_view = memoryview(prim_array).cast("B").cast("I")
        new_prim_view[:] = array.array("I", tri_rows)
        geom.add_primitive(new_prim)


def create_job_schedule(model, starship_id):

    jobs = {}

    def fill_job_data(job_data, node):

        part_count = 0
        worker_pos = []
        job_data["worker_pos"] = worker_pos
        next_job_data = []
        job_data["next_jobs"] = next_job_data
        children = node.children

        while children:

            next_children = None

            for child in children:

                name = child.name

                if name.startswith("job_root"):
                    new_job_data = fill_job_schedule(child)
                    job_index = new_job_data["index"]
                    rel_index = job_index - job_data["index"]
                    next_job_data.append({"rel_index": rel_index, "delay": part_count})
                elif name.startswith("job"):
                    _, job_index, worker_type = name.split("_")
                    job_index = int(job_index) - 1
                    rel_index = job_index - job_data["index"]
                    next_job_data.append({"rel_index": rel_index, "delay": part_count})
                    jobs[job_index] = new_job_data = {}
                    new_job_data["index"] = job_index
                    new_job_data["component_id"] = job_data["component_id"]
                    new_job_data["worker_type"] = worker_type
                    fill_job_data(new_job_data, child)
                elif name.startswith("part"):
                    part_count += 1
                    x, y, z = child.get_net_transform().get_pos()
                    worker_pos.append((x, y, z))
                    next_children = child.children

            children = next_children

        job_data["part_count"] = part_count

    def fill_job_schedule(job_root):

        child = job_root.children[0]
        _, job_index, worker_type = child.name.split("_")
        job_index = int(job_index) - 1
        jobs[job_index] = job_data = {}
        job_data["index"] = job_index
        job_data["component_id"] = job_root.name.replace("job_root_", "")
        job_data["worker_type"] = worker_type
        fill_job_data(job_data, child)

        return job_data

    job_root = model.find("**/job_root_*")
    job_root.detach_node()
    fill_job_schedule(job_root)

    with open(f"jobs_{starship_id}.txt", "w") as job_file:

        for i in range(len(jobs)):

            job_file.write("\n")
            job_data = jobs[i]
            component_id = job_data["component_id"]
            job_file.write(f"component_id {component_id}\n")
            part_count = job_data["part_count"]
            job_file.write(f"part_count {part_count}\n")
            worker_type = job_data["worker_type"]
            job_file.write(f"worker_type {worker_type}\n")
            job_file.write("worker_pos\n")
            worker_pos = job_data["worker_pos"]

            for x, y, z in worker_pos:
                job_file.write(f"    {x} {y} {z}\n")

            job_file.write("next_jobs\n")
            next_job_data = job_data["next_jobs"]

            for data in next_job_data:
                rel_index = data["rel_index"]
                job_file.write(f"    rel_index {rel_index}\n")
                delay = data["delay"]
                job_file.write(f"    delay {delay}\n")


input_model_path = "../Assets/Section1/starship_gltf_models"
output_model_path = "../Assets/Section1/models"

for name in os.listdir(os.path.join(*input_model_path.split("/"))):

    model = NodePath(loader.load_sync(f"{input_model_path}/{name}", loader_options))
    starship_id = os.path.splitext(name)[0]
    create_job_schedule(model, starship_id)

    for node_path in model.find_all_matches("**/+GeomNode"):
        process_geom_node(node_path)

    model.write_bam_file(f"{output_model_path}/{starship_id}.bam")
