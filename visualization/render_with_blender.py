import sys
import math

import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1:]
print(argv)
path = argv[0]

bpy.ops.object.delete()

bpy.ops.import_scene.obj(filepath=path)
bronchus = bpy.data.objects['bronchus']

smoothing = bronchus.modifiers.new(name="Smooth", type="SMOOTH")
smoothing.iterations = 10
smoothing.factor = 2

bpy.data.meshes['bronchus'].show_double_sided = True

camera = bpy.data.objects['Camera']


def rad(degrees):
    return math.pi * degrees / 180


camera.location = (-5, -2, 2)
camera.rotation_euler = (rad(70), 0, rad(-60))

bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = 256
bpy.context.scene.render.resolution_percentage = 100

bpy.ops.mesh.primitive_plane_add()
plane = bpy.data.objects['Plane']
plane.scale = (8, 8, 1)
plane.location[2] = 10
# plane_material = plane.material.new()
mat_name = "LightMat"

mat = bpy.data.materials.new(mat_name)
mat.use_nodes = True

mat.node_tree.nodes.new(type="ShaderNodeEmission")
mat.node_tree.nodes['Emission'].inputs[1].default_value = 5

inp = mat.node_tree.nodes['Material Output'].inputs['Surface']
outp = mat.node_tree.nodes['Emission'].outputs['Emission']

mat.node_tree.links.new(inp, outp)

plane.active_material = mat
