import sys
import math

# Internal import to access blender functionalities
import bpy

# Handle sys args
argv = sys.argv
argv = argv[argv.index("--") + 1:]
print(argv)
bronchus_path = argv[0]
skeleton_path = argv[1]
split_path = argv[2]

# Delete default cube
bpy.ops.object.delete()

# Import bronchus
bpy.ops.import_scene.obj(filepath=bronchus_path)
bronchus = bpy.data.objects['bronchus']

# Add smoothing modifier
smoothing = bronchus.modifiers.new(name="Smooth", type="SMOOTH")
smoothing.iterations = 10
smoothing.factor = 2

# Since there are no normals in the vertices, add double sided rendering for faces to fix artifacts
bpy.data.meshes['bronchus'].show_double_sided = True


# Define deg to rad function
def rad(degrees):
    return math.pi * degrees / 180


# Move camera
camera = bpy.data.objects['Camera']
camera.location = (-5, -2, 2)
camera.rotation_euler = (rad(70), 0, rad(-60))

# Set rendering options
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = 256
bpy.context.scene.render.resolution_percentage = 100

# Add lighting plane, move it and hide it
bpy.ops.mesh.primitive_plane_add()
plane = bpy.data.objects['Plane']
plane.hide = True
plane.scale = (8, 8, 1)
plane.location[2] = 10

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
bpy.context.window.screen = bpy.data.screens['3D View Full']

# Import skeleton object
bpy.ops.import_scene.obj(filepath=skeleton_path)
bpy.data.meshes['skeleton'].show_double_sided = True
skeleton = bpy.data.objects['skeleton']
skeleton.hide = True
skeleton.hide_render = True

# Import splits object
bpy.ops.import_scene.obj(filepath=split_path)
bpy.data.meshes['splits'].show_double_sided = True
splits = bpy.data.objects['splits']
# splits.select_set = True
