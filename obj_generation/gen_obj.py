"""Module to generate .obj file from bronchus coords outer shell

Needs stage-02 (reduced_model.npz) as input.

This file expects the first argument to be a path to the input folder (not including the 
reduced_model.npz). The second argument needs to be a path to the output file.

It does so by going through every bronchus point in the reduced_model.npz and checking
each of the 6 neighboring points whether it is empty. If it is indeed empty then
it adds the points which haven't been added yet on that face and also adds the face.

Then it saves everything into a .obj file with the format of [patient_it].obj. This file can
be imported into blender, 3D printed, visualized and many other nice things.
"""
from pathlib import Path
from typing import List, Set
from typing import Dict

import numpy as np
from skimage.morphology import skeletonize

from util.util import get_data_paths_from_args


def generate_obj(output_data_path,
                 accepted_types,
                 model,
                 color_mask=None,
                 rot_mat: np.ndarray = None,
                 num_decimal_digits=2):
    """Saves a .obj obj_file given the model, the accepted types and a name

    output_data_path is a pathlib Path, this is the full path the obj_file will be saved as

    accepted_types is a list or set which types should be looked for, other
    types will be ignored. If empty set then everything except for 0 will be
    accepted

    model is the 3D numpy array model of the lung or whatever object you
    want to convert to 3D

    color_mask is a model with the same shape as model, but its numbers represent
    groups of colors/materials which will be added by this script

    rot_mat is a rotation matrix. Each point p=(x,y,z) is rotated by rot_mat @ p or left unchanged if None
    """

    output_data_path = Path(output_data_path)

    print(f"Generating {output_data_path} with accepted types of {accepted_types}")

    vertices = {}
    faces: Dict[int, List[List[int]]] = {0: []}

    def cell_is_empty(x, y, z):
        return not ((accepted_types == set() and model[x][y][z]) or model[x][y][z] in accepted_types)

    # Go through each point comparing it to all adjacent faces, if one
    # of the blocks is filled and the other is empty then add a face there
    index = 1
    # Iterate over each coordinate in the model
    for x in range(len(model)):
        if x % 50 == 0:
            print(f"Layer {x} of {len(model)}")
        for y in range(len(model[x])):
            for z in range(len(model[x][y])):

                # Check if current coordinate contains bronchus (1) or a lobe (>1)
                if not cell_is_empty(x, y, z):
                    # Checks each neighbor of the coordinate to see
                    # whether a face should be added
                    for x_, y_, z_ in [[-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0], [0, 0, -1], [0, 0, 1]]:

                        # Make sure that the coordinate is empty since otherwise there is no reason to make a face
                        if cell_is_empty(x+x_, y+y_, z+z_):
                            direction = [-0.5, 0.5]

                            # Face coords is a list of 4 points, these are exactly the points in
                            # the direction of the neighboring point. This is achieved by
                            # iterating over all 8 points with coordinates -0.5 and 0.5,
                            # then guaranteeing that the direction is the same by checking
                            # the direction given in the previous loop.
                            # May be sketchy due to float divison, assert to check for that.
                            face_coords = [
                                [a, b, c] for a in direction for b in direction for c in direction
                                if x_/2 == a or y_/2 == b or z_/2 == c
                            ]
                            assert len(face_coords) == 4, "ERROR: Face coords contain more than 4 coordinates"
                            curr_face = []

                            # Iterate over each of the 4 face coordinates, add them
                            # to the vertices if they haven't yet been added
                            for a, b, c in face_coords:
                                key = (a + x, b + y, c + z)
                                if key not in vertices:
                                    vertices[key] = index
                                    curr_face.append(index)
                                    index += 1
                                else:
                                    curr_face.append(vertices[key])
                            material = color_mask[x, y, z] if color_mask is not None else 0
                            if material not in faces:
                                faces[material] = []
                            faces[material].append(curr_face[:2] + curr_face[4:1:-1])
                            assert len(faces[material][-1]) == 4, "ERROR: Wrong number of points on face"

    print(f"Vertex count : {len(vertices)}")
    print(f"Face count : {sum(map(len, faces.values()))}")

    # make to numpy for more easy usage later

    print(model.shape)
    print(vertices)
    vertices = np.array([np.array(v) for v in vertices])
    print(vertices)
    vertices = normalize(vertices, model.shape, rot_mat=rot_mat)

    # Write vertices and faces to obj_file
    material_path = output_data_path.with_suffix(".mtl")
    with open(material_path, 'w') as mat_file:
        import random
        random.seed(output_data_path.parent.name)
        def ran(): return random.uniform(0, 1)
        for material in faces:
            mat_file.write(f"newmtl mat{material}\n")
            mat_file.write("Ns 96.078431\n")
            mat_file.write("Ka 1.000000 1.000000 1.000000\n")
            mat_file.write(f"Kd {ran()} {ran()} {ran()}\n")
            mat_file.write("Ks 0.500000 0.500000 0.500000\n")
            mat_file.write("Ke 0.000000 0.000000 0.000000\n")
            mat_file.write("Ni 1.000000\n")
            mat_file.write("d 1.000000\n")
            mat_file.write("illum 2\n\n")
    with open(output_data_path, 'w') as obj_file:
        obj_file.write("# .obj generated by Airway")
        obj_file.write(f"mtllib {material_path.name}\n")
        obj_file.write("# Vertices\n")
        # original was [[0, 0, -1], [-1, 0, 0], [0, 1, 0]]
        vertexformat = f"v {{:.{num_decimal_digits}f}} {{:.{num_decimal_digits}f}} {{:.{num_decimal_digits}f}}\n"
        for x, y, z in vertices:
            obj_file.write(vertexformat.format(x, y, z))

        obj_file.write("\n# Faces\n")
        for material, faces_with_material in faces.items():
            obj_file.write(f"usemtl mat{material}\n")
            for a, b, c, d in faces_with_material:
                obj_file.write(f"f {a} {b} {c} {d}\n")


def normalize(vertices: np.ndarray, reference_shape: np.ndarray, rot_mat: np.ndarray = None):
    # Shift to middle of the space
    vertices -= np.array(reference_shape) / 2
    # Scale to [-10..10]
    vertices *= 20 / np.max(reference_shape)
    # If available: transform
    # Note: since this is applied afterwards, points can be out of [-10..10]
    if rot_mat is not None:
        vertices = vertices @ np.transpose(rot_mat)
    return vertices


def main():
    output_data_path, input_data_path, color_mask_path  = get_data_paths_from_args(inputs=2)

    model = np.load(input_data_path / "reduced_model.npz")['arr_0']
    print(f"Loaded model with shape {model.shape}")

    bronchus_color_mask = np.load(color_mask_path / "bronchus_color_mask.npz")['arr_0']
    print(f"Loaded color mask with shape {bronchus_color_mask.shape}")

    if not output_data_path.exists():
        output_data_path.mkdir(parents=True, exist_ok=True)

    rot_mat = np.array([[0, 0, -1], [-1, 0, 0], [0, 1, 0]])

    print("Running skeletonize on model")
    # Remove lobe coordinates from model by clipping everything
    # between 0 and 2, then modulo everything by 2 to remove 2s
    skeleton = skeletonize(np.clip(model, 0, 2) % 2)
    generate_obj(output_data_path / "skeleton.obj", set(), skeleton, rot_mat=rot_mat)
    # generate_obj(output_data_path / "bav.obj", {1, 7, 8}, model)
    generate_obj(output_data_path / "bronchus.obj", {1}, model, color_mask=bronchus_color_mask, rot_mat=rot_mat)
    # generate_obj(output_data_path / "veins.obj", {7}, model)
    # generate_obj(output_data_path / "arteries.obj", {8}, model)
    # generate_obj(output_data_path / "lung.obj", {1, 2, 3, 4, 5, 6}, model)


if __name__ == "__main__":
    main()
