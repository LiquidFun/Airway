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
import numpy as np
from skimage.morphology import skeletonize

from util.util import get_data_paths_from_args


def generate_obj(output_data_path, accepted_types, model):
    """Saves a .obj file given the model, the accepted types and a name

    output_data_path is a string, this is the full path the file will be saved as

    accepted_types is a list or set which types should be looked for, other
    types will be ignored. If empty set then everything except for 0 will be
    accepted

    model is the 3D numpy array model of the lung or whatever object you
    want to convert to 3D
    """

    if output_data_path.exists():
        print(f"Skipping {output_data_path} since it already exists. Manually delete to regenerate.")
        return

    print(f"Generating {output_data_path} with accepted types of {accepted_types}")

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
    with open(output_data_path, 'w') as file:
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


def main():
    output_data_path, input_data_path = get_data_paths_from_args()

    model = np.load(input_data_path / "reduced_model.npy")
    print(f"Loaded model with shape {model.shape}")

    if not output_data_path.exists():
        output_data_path.mkdir(parents=True, exist_ok=True)

    print("Running skeletonize on model")
    # Remove lobe coordinates from model by clipping everything
    # between 0 and 2, then modulo everything by 2 to remove 2s
    skeleton = skeletonize(np.clip(model, 0, 2) % 2)
    generate_obj(output_data_path / "skeleton.obj", set(), skeleton)
    generate_obj(output_data_path / "bronchus.obj", {1}, model)
    generate_obj(output_data_path / "lung.obj", {1, 2, 3, 4, 5, 6}, model)


if __name__ == "__main__":
    main()
