import sys
import math
from pathlib import Path

import re

# Internal import to access blender functionalities
import bpy

# Handle sys args
argv = sys.argv
argv = argv[argv.index("--") + 1:]
print(argv)
bronchus_path = argv[0]
skeleton_path = argv[1]
split_path = argv[2]
tree_path = argv[3]
model_path = argv[4]


def load_obj(path):
    """Loads .obj file and returns the object"""
    name = Path(path).name.replace(".obj", "")
    bpy.ops.import_scene.obj(filepath=path)
    bpy.data.meshes[name].show_double_sided = True
    return bpy.data.objects[name]


def make_obj_smooth(obj, iterations=10, factor=2):
    """Adds smoothing modifier in Blender"""

    # Add smoothing modifier
    smoothing = obj.modifiers.new(name="Smooth", type="SMOOTH")
    smoothing.iterations = iterations
    smoothing.factor = factor

    # Recalculate normals
    bpy.ops.object.select_all(action='DESELECT')
    obj.select = True
    bpy.context.scene.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.editmode_toggle()

    # Since there are no normals in the vertices, add double sided rendering for faces to fix artifacts
    # Update: not needed since normals are now calculated
    # bpy.data.meshes[obj.name].show_double_sided = True

    bpy.ops.object.shade_smooth()


# Delete default cube
bpy.ops.object.delete()
lamp = bpy.data.objects['Lamp']
bpy.context.scene.objects.unlink(lamp)
bpy.data.objects.remove(lamp)

# Import bronchus
bpy.ops.import_scene.obj(filepath=bronchus_path)
bronchus = bpy.data.objects['bronchus']
make_obj_smooth(bronchus) # Smooth before hiding select, as otherwise it doesnt work?
bronchus.hide_select = True


# Define deg to rad function
def rad(degrees):
    return math.pi * degrees / 180


# Move camera
camera = bpy.data.objects['Camera']
camera.location = (0, 16, 0)
camera.rotation_euler = (rad(90), 0, rad(-180))
camera.hide = True

# Set rendering options
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = 128
bpy.context.scene.render.resolution_x = 1600
bpy.context.scene.render.resolution_y = 1600
bpy.context.scene.render.resolution_percentage = 100

# Add lighting plane, move it and hide it
bpy.ops.mesh.primitive_plane_add()
plane = bpy.data.objects['Plane']
plane.hide = True
plane.scale = (16, 16, 1)
plane.location[2] = 20

# Set the material for the lighting plane
mat_name = "LightMat"
mat = bpy.data.materials.new(mat_name)
mat.use_nodes = True
mat.node_tree.nodes.new(type="ShaderNodeEmission")
mat.node_tree.nodes['Emission'].inputs[1].default_value = 5
inp = mat.node_tree.nodes['Material Output'].inputs['Surface']
outp = mat.node_tree.nodes['Emission'].outputs['Emission']
mat.node_tree.links.new(inp, outp)
plane.active_material = mat

# Change default screen
# bpy.context.window.screen = bpy.data.screens['3D View Full']
bpy.context.window.screen = bpy.data.screens['Airway']


def get_areas_by_type(context, type):
    return [a for a in context.screen.areas if a.type == type]


def show_names_in_current_screen():
    for view3d_area in get_areas_by_type(bpy.context, 'VIEW_3D'):
        view_space = view3d_area.spaces[0]
        view_space.show_only_render = False
        view_space.show_floor = False
        view_space.show_axis_x = False
        view_space.show_axis_y = False
        view_space.show_axis_z = False
        view_space.cursor_location = (0, 0, 1000)


# Import skeleton object
skeleton = load_obj(skeleton_path)
make_obj_smooth(skeleton, 2, 2)
skeleton.hide = True
skeleton.hide_render = True
skeleton.hide_select = True

# Import splits object
splits = load_obj(split_path)
splits_no_post_processing = load_obj(split_path.replace("splits.obj", "splits_no_post_processing.obj"))
splits_no_post_processing.hide = True

cubes = []
group_cubes = []
np_model = None
previous_reload_all_cubes = False


def load_tree():
    import networkx as nx
    gt_tree_path = tree_path.replace("tree.graphml", "tree_gt.graphml")
    return nx.read_graphml(gt_tree_path) if Path(gt_tree_path).exists() else nx.read_graphml(tree_path)


def add_to_group(group_name, objects):
    group = bpy.data.groups.get(group_name, bpy.data.groups.new(group_name))
    for obj in objects:
        if obj.name not in group.objects:
            group.objects.link(obj)


def normalize(vertices):
    global np_model
    import numpy as np
    vertices = np.array(vertices)
    if np_model is None:
        np_model = np.load(model_path)['arr_0']
    reference_shape = np.array(np_model.shape)
    rot_mat = np.array([[0, 0, -1], [0, -1, 0], [-1, 0, 0]])
    # Shift to middle of the space
    vertices -= np.array(reference_shape) / 2
    # Scale to [-10..10]
    vertices *= 20 / np.max(reference_shape)
    # If available: transform
    # Note: since this is applied afterwards, points can be out of [-10..10]
    if rot_mat is not None:
        vertices = vertices @ np.transpose(rot_mat)
    return vertices


def reload_cubes(context, show_all_nodes):
    global previous_reload_all_cubes
    previous_reload_all_cubes = show_all_nodes
    show_names_in_current_screen()
    for _, cube in cubes:
        bpy.data.objects.remove(cube, do_unlink=True)
    cubes.clear()
    group_cubes.clear()
    tree = load_tree()
    for node_id in tree.nodes:
        node = tree.nodes[node_id]
        location = tuple(normalize([node['x'], node['y'], node['z']]))
        classification = node['split_classification']
        is_gt_classification = False
        if 'split_classification_gt' in node:
            if node['split_classification_gt'] != "":
                is_gt_classification = True
                classification = node['split_classification_gt']
        if show_all_nodes or not re.match(r"c\d+", classification):
            bpy.ops.mesh.primitive_cube_add(radius=0.02, location=location)
            selected = bpy.context.selected_objects[0]
            selected.name = classification
            if re.match(r"LB\d(\+\d)*[a-c]*i*", selected.name):
                selected.name = selected.name[1:]
            selected.show_name = True
            cubes.append((node_id, selected))
            if is_gt_classification:
                group_cubes.append(selected)
    for _, cube in cubes:
        cube.select = True
    add_to_group("manually_classified", group_cubes)
    bpy.data.objects['splits'].select = True
    return {'FINISHED'}


class ClassificationReloader(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "view3d.airway_reload_classification"
    bl_label = "Airway: reload classification"

    def execute(self, context):
        reload_cubes(context, show_all_nodes=False)
        return {"FINISHED"}


class FullClassificationReloader(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "view3d.airway_reload_full_classification"
    bl_label = "Airway: reload classification and show all nodes"

    def execute(self, context):
        reload_cubes(context, show_all_nodes=True)
        return {"FINISHED"}


class ClassificationSaver(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "view3d.airway_save_classification"
    bl_label = "Airway: save classification"

    def execute(self, context):
        import networkx as nx
        show_names_in_current_screen()
        tree = load_tree()
        for node_id, cube in cubes:
            name = cube.name
            if re.match(r"B\d(\+\d)*[a-c]*i*", cube.name):
                name = "L" + name
            if name == tree.nodes[node_id]["split_classification"]:
                tree.nodes[node_id]["split_classification_gt"] = ""
            else:
                tree.nodes[node_id]["split_classification_gt"] = name
        nx.write_graphml(tree, tree_path.replace("tree.graphml", "tree_gt.graphml"))
        reload_cubes(context, previous_reload_all_cubes)
        return {'FINISHED'}


bpy.utils.register_class(ClassificationReloader)
bpy.utils.register_class(FullClassificationReloader)
bpy.utils.register_class(ClassificationSaver)
# print("Registered class")
