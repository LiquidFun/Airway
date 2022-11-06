import sys
import math
import tempfile
from pathlib import Path
import re

# Internal import to access blender functionalities, an editor
# will not know this command, so ignore it:
# noinspection PyUnresolvedReferences,PyPackageRequirements
import bpy

# Careful python version is 3.5 here, no f-strings!

# Check blender version, need to handle <2.80 and >=2.80 differently
is_blender279 = bpy.app.version < (2, 80)

# Handle sys args
argv = sys.argv
argv = argv[argv.index("--") + 1 :]
print(argv)
bronchus_path = argv[0]
skeleton_path = argv[1]
split_path = argv[2]
tree_path = argv[3]
model_path = argv[4]

# classification_config_path = Path(sys.argv[0]).parents[0] / "configs" / "classification.yaml"
classification_config_path = Path(__file__).parents[2] / "configs" / "classification.yaml"
print(classification_config_path)
classification_config = None


def select(obj, active=False):
    if is_blender279:
        obj.select = True
        if active:
            bpy.context.scene.objects.active = obj
    else:
        obj.select_set(True)
        if active:
            bpy.context.view_layer.objects.active = obj


def hide(obj, viewport=False, selection=False, render=False):
    if is_blender279:
        obj.hide = viewport
    else:
        obj.hide_viewport = viewport
    obj.hide_render = render
    obj.hide_select = selection


def load_obj(path):
    """Loads .obj file and returns the object"""
    name = Path(path).name.replace(".obj", "")
    try:
        bpy.ops.import_scene.obj(filepath=path)
    except FileNotFoundError:
        print(f"File {path} does not exist! Skipping it!")
        return None
    if is_blender279:
        bpy.data.meshes[name].show_double_sided = True
    return bpy.data.objects[name]


def make_obj_smooth(obj, iterations=10, factor=2):
    """Adds smoothing modifier in Blender"""

    # Add smoothing modifier
    smoothing = obj.modifiers.new(name="Smooth", type="SMOOTH")
    smoothing.iterations = iterations
    smoothing.factor = factor

    # Recalculate normals
    bpy.ops.object.select_all(action="DESELECT")
    select(obj, True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.editmode_toggle()

    # Since there are no normals in the vertices, add double-sided rendering for faces to fix artifacts
    # Update: not needed since normals are now calculated
    # bpy.data.meshes[obj.name].show_double_sided = True

    bpy.ops.object.shade_smooth()


# Delete default cube
# bpy.ops.object.delete()

for object_name in ["Cube", "Lamp", "Light"]:
    if object_name in bpy.data.objects:
        current_object = bpy.data.objects[object_name]
        if is_blender279:
            bpy.context.scene.objects.unlink(current_object)
        bpy.data.objects.remove(current_object)

# Import bronchus
bpy.ops.import_scene.obj(filepath=bronchus_path)
bronchus = bpy.data.objects["bronchus"]
make_obj_smooth(bronchus)  # Smooth before hiding select, as otherwise it doesn't work?
hide(bronchus, selection=True)


# Define deg to rad function
def rad(degrees):
    return math.pi * degrees / 180


# Move camera
camera = bpy.data.objects["Camera"]
camera.location = (0, 16, 0)
camera.rotation_euler = (rad(90), 0, rad(-180))
if not is_blender279:
    camera.data.lens = 35
hide(camera, viewport=True)

# Set rendering options
bpy.context.scene.render.engine = "CYCLES"
# bpy.context.scene.cycles.samples = 128
bpy.context.scene.cycles.samples = 256
bpy.context.scene.render.resolution_x = 1600
bpy.context.scene.render.resolution_y = 1600
bpy.context.scene.render.resolution_percentage = 100

# Add lighting plane, move it and hide it
bpy.ops.mesh.primitive_plane_add()
plane = bpy.data.objects["Plane"]
hide(plane, viewport=True)
plane.scale = (22, 80, 1)
plane.location = (0, 20, 40)

if is_blender279:
    bpy.context.scene.world.horizon_color = (0, 0, 0)
    bpy.context.scene.cycles.film_transparent = True
else:
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    bpy.context.scene.render.film_transparent = True


# Set the material for the lighting plane
mat_name = "LightMat"
mat = bpy.data.materials.new(mat_name)
mat.use_nodes = True
mat.node_tree.nodes.new(type="ShaderNodeEmission")
mat.node_tree.nodes["Emission"].inputs[1].default_value = 5
inp = mat.node_tree.nodes["Material Output"].inputs["Surface"]
outp = mat.node_tree.nodes["Emission"].outputs["Emission"]
mat.node_tree.links.new(inp, outp)
plane.active_material = mat

# Change default screen
# bpy.context.window.screen = bpy.data.screens['3D View Full']
if "Airway" in bpy.data.screens:
    bpy.context.window.screen = bpy.data.screens["Airway"]


def get_areas_by_type(context, type):
    return [a for a in context.screen.areas if a.type == type]


def show_names_in_current_screen():
    if is_blender279:
        for view3d_area in get_areas_by_type(bpy.context, "VIEW_3D"):
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
# skeleton.hide = True
hide(skeleton, render=True, selection=True)

# Import splits object
splits_no_post_processing = load_obj(split_path.replace("splits.obj", "splits_no_post_processing.obj"))
splits = load_obj(split_path)
hide(splits_no_post_processing, viewport=True)

cubes = []
group_cubes = []
np_model = None
previous_reload_all_cubes = False


def load_tree():
    import networkx as nx

    return nx.read_graphml(tree_path)
    gt_tree_path = tree_path.replace("tree.graphml", "tree_gt.graphml")
    return nx.read_graphml(gt_tree_path) if Path(gt_tree_path).exists() else nx.read_graphml(tree_path)


def add_to_group(group_name, objects):
    if is_blender279:
        group = bpy.data.groups.get(group_name, bpy.data.groups.new(group_name))
        for obj in objects:
            if obj.name not in group.objects:
                group.objects.link(obj)


def normalize(vertices, center=True):
    global np_model
    import numpy as np

    vertices = np.array(vertices)
    if np_model is None:
        np_model = np.load(model_path)["arr_0"]
    reference_shape = np.array(np_model.shape)
    rot_mat = np.array([[0, 0, -1], [0, -1, 0], [-1, 0, 0]])
    # Shift to middle of the space
    if center:
        vertices -= np.array(reference_shape) / 2
    # Scale to [-10..10]
    vertices *= 20 / np.max(reference_shape)
    # If available: transform
    # Note: since this is applied afterwards, points can be out of [-10..10]
    if rot_mat is not None:
        vertices = vertices @ np.transpose(rot_mat)
    return vertices


splits_reference = None


def reload_cubes(context, show_all_nodes, show_reference_nodes=False):
    global previous_reload_all_cubes, splits_reference, classification_config
    import networkx as nx
    import yaml

    previous_reload_all_cubes = show_all_nodes
    reference_locations = []

    # _, tmpfilepath = tempfile.mkstemp(suffix=".obj", prefix="airway_reference_splits")
    # tmpfile = open(tmpfilepath, 'w')

    show_names_in_current_screen()
    for _, cube in cubes:
        bpy.data.objects.remove(cube, do_unlink=True)
    cubes.clear()
    group_cubes.clear()
    tree = load_tree()
    for parent_id, child_ids in nx.bfs_successors(tree, "0"):
        parent_node = tree.nodes[parent_id]
        parent_location = normalize([parent_node["x"], parent_node["y"], parent_node["z"]])
        for child_id in child_ids:
            node = tree.nodes[child_id]
            # print("Node coords:", [node['x'], node['y'], node['z']])
            location = normalize([node["x"], node["y"], node["z"]])
            classification = node["split_classification"]
            is_gt_classification = False
            if "split_classification_gt" in node:
                if node["split_classification_gt"] != "":
                    is_gt_classification = True
                    classification = node["split_classification_gt"]
            if show_all_nodes or not re.match(r"c\d+", classification):
                if is_blender279:
                    bpy.ops.mesh.primitive_cube_add(radius=0.02, location=tuple(location))
                else:
                    bpy.ops.mesh.primitive_cube_add(size=0.02, location=tuple(location))
                selected = bpy.context.selected_objects[0]
                selected.name = classification
                hide(selected, render=True)
                # if re.match(r"LB\d(\+\d)*[a-c]*i*", selected.name):
                #     selected.name = selected.name[1:]
                selected.show_name = True
                cubes.append((child_id, selected))
                if show_reference_nodes:
                    if classification_config is None:
                        with open(classification_config_path, "r") as file:
                            classification_config = yaml.load(file.read(), yaml.FullLoader)
                    try:
                        vec = normalize(classification_config[classification]["vector"], False)
                        target_location = vec + parent_location
                        # print(parent_location, vec, target_location)
                        for loc in [parent_location, target_location]:
                            reference_locations.append("v " + " ".join(map(lambda s: "{:.3f}".format(s), loc)) + "\n")
                    except KeyError:
                        pass
                if is_gt_classification or show_reference_nodes:
                    group_cubes.append(selected)
    if show_reference_nodes:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".obj", prefix="airway_reference_splits") as tmpfile:
            # print(tmpfile.name)
            tmpfile.write("# Vertices\n")
            for reference_location in reference_locations:
                tmpfile.write(reference_location)
            tmpfile.write("\n# Lines\n")
            for index in range(1, len(reference_locations) + 1, 2):
                tmpfile.write("l {} {}\n".format(index, index + 1))
            tmpfile.flush()
            if splits_reference is not None:
                bpy.data.objects.remove(splits_reference)
            splits_reference = load_obj(tmpfile.name)
            splits_reference.rotation_euler = (0, 0, 0)
            splits_reference.name = "splits_reference"
            if is_blender279:
                select(bpy.data.objects["splits_reference"])
            group_cubes.append(splits_reference)
    else:
        if splits_reference is not None:
            hide(splits_reference, viewport=True)
        if is_blender279:
            select(bpy.data.objects["splits"])

    if is_blender279:
        for _, cube in cubes:
            select(cube)
    add_to_group("manually_classified", group_cubes)
    return {"FINISHED"}


class ClassificationReloader(bpy.types.Operator):
    """Tooltip"""

    bl_idname = "view3d.airway_reload_classification"
    bl_label = "Airway: reload classification"

    def execute(self, context):
        reload_cubes(context, show_all_nodes=False)
        return {"FINISHED"}


class GroundTruthReloader(bpy.types.Operator):
    """Tooltip"""

    bl_idname = "view3d.airway_reload_ground_truth"
    bl_label = "Airway: reload ground_truth"

    def execute(self, context):
        reload_cubes(context, show_all_nodes=False, show_reference_nodes=True)
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
            # if re.match(r"B\d(\+\d)*[a-c]*i*", cube.name):
            #     name = "L" + name
            if name == tree.nodes[node_id]["split_classification"]:
                tree.nodes[node_id]["split_classification_gt"] = ""
            else:
                tree.nodes[node_id]["split_classification_gt"] = name
        nx.write_graphml(tree, tree_path.replace("tree.graphml", "tree_gt.graphml"))
        reload_cubes(context, previous_reload_all_cubes)
        return {"FINISHED"}


bpy.utils.register_class(ClassificationReloader)
bpy.utils.register_class(FullClassificationReloader)
bpy.utils.register_class(GroundTruthReloader)
bpy.utils.register_class(ClassificationSaver)
# print("Registered class")
