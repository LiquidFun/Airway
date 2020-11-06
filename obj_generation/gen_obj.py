"""Module to generate .obj file from bronchus coords outer shell

Needs stage-02 (reduced_model.npy) as input.

This file expects the first argument to be a path to the input folder (not including the 
reduced_model.npy). The second argument needs to be a path to the output file.

It does so by going through every bronchus point in the reduced_model.npy and checking
each of the 6 neighboring points whether it is empty. If it is indeed empty then
it adds the points which haven't been added yet on that face and also adds the face.

Then it saves everything into a .obj file with the format of [patient_it].obj. This file can
be imported into blender, 3D printed, visualized and many other nice things.
"""
import os
import sys

import numpy as np
from skimage.morphology import skeletonize

def generate_obj(target, accepted_types, model):
    """Saves a .obj file given the model, the accepted types and a name

    target is a string, this is the full path the file will be saved as

    accepted_types is a list or set which types should be looked for, other
    types will be ignored. If empty set then everything except for 0 will be
    accepted

    model is the 3D numpy array model of the lung or whatever object you
    want to convert to 3D
    """

    if os.path.exists(target):
        print(f"Skipping {target} since it already exists. Manually delete to regenerate.")
        return

    print(f"Generating {target} with accepted types of {accepted_types}")

    vertices = {}
    faces = []

    def check_cell(x, y, z):
        return (accepted_types == set() and model[x][y][z]) or model[x][y][z] in accepted_types

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
                if check_cell(x, y, z):
                    # Checks each neighbor of the coordinate to see
                    # whether a face should be added
                    for x_, y_, z_ in [[-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0], [0, 0, -1], [0, 0, 1]]:

                        # Make sure that the coordinate is empty
                        if not check_cell(x+x_, y+y_, z+z_):
                            d = [-0.5, 0.5]

                            # Face coords is a list of 4 points, these are exactly the points in
                            # the direction of the neighboring point. This is achieved by
                            # iterating over all 8 points with coordinates -0.5 and 0.5,
                            # then guaranteeing that the direction is the same by checking
                            # the direction given in the previous loop.
                            # May be sketchy due to float divison, assert to check for that.
                            face_coords = [[a, b, c] for a in d for b in d for c in d if x_/2 == a or y_/2 == b or z_/2 == c]
                            assert len(face_coords) == 4, "ERROR: Face coord contain more than 4 coordinates"
                            curr_face = []

                            # Iterate over each of the 4 face coordinates, add them
                            # to the vertices if they haven't yet been added
                            for a, b, c in face_coords:
                                key = (-(z+c), -(x+a), y+b)
                                if key not in vertices:
                                    vertices[key] = index
                                    curr_face.append(index)
                                    index += 1
                                else:
                                    curr_face.append(vertices[key])
                            faces.append(curr_face[:2] + curr_face[4:1:-1])
                            assert len(faces[-1]) == 4, "ERROR: Wrong number of points on face"

    print(f"Vertex count : {len(vertices)}")
    print(f"Face count : {len(faces)}")

    vertices = normalize(vertices)

    # Write vertices and faces to file
    with open(target, 'w') as file:
        file.write("# Vertices\n")
        for x, y, z in vertices:
            file.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        file.write("\n# Faces\n")
        for a, b, c, d in faces:
            file.write(f"f {a} {b} {c} {d}\n")

def normalize(vertices):
    """Normalize each coordinate to around -10 to 10, also center them
    """
    vertices = np.array([np.array(v) for v in vertices])
    minimum = np.min(vertices, axis=0)
    vertices -= minimum
    maximum = np.max(vertices)
    maximum_axis0 = np.max(vertices, axis=0)
    # vertices = (vertices - maximum_axis0/2) / maximum
    vertices = (vertices - maximum_axis0/2) / 500
    vertices = vertices * 10
    return vertices


if __name__ == "__main__":
    try:
        SOURCE_DATA_PATH = sys.argv[1]
        TARGET_DATA_PATH = sys.argv[2]
    except IndexError:
        print("ERROR: No source or data path provided, aborting!")
        sys.exit(1)

    MODEL = np.load(os.path.join(SOURCE_DATA_PATH, "reduced_model.npy"))
    print(f"Loaded model with shape {MODEL.shape}")

    if not os.path.exists(TARGET_DATA_PATH):
        os.makedirs(TARGET_DATA_PATH)


    print("Running skeletonize on model")
    # Remove lobe coordinates from model by clipping everything
    # between 0 and 2, then modulo everything by 2 to remove 2s
    SKELETON = skeletonize(np.clip(MODEL, 0, 2) % 2)
    generate_obj(os.path.join(TARGET_DATA_PATH, "skeleton.obj"), set(), SKELETON)
    generate_obj(os.path.join(TARGET_DATA_PATH, "bronchus.obj"), {1}, MODEL)
    generate_obj(os.path.join(TARGET_DATA_PATH, "lung.obj"), {1, 2, 3, 4, 5, 6}, MODEL)

