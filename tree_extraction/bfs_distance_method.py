import queue

import numpy as np
from skimage.morphology import skeletonize

from util.helper_functions import adjacent
from util.util import get_data_paths_from_args

output_data_path, input_data_path = get_data_paths_from_args()

patient_data_file = input_data_path / "reduced_model.npz"
distance_to_coords_file = output_data_path / "map_distance_to_coords"
coord_to_distance_file = output_data_path / "map_coord_to_distance.txt"
coord_to_previous_file = output_data_path / "map_coord_to_previous.txt"
coord_to_next_count_file = output_data_path / "map_coord_to_next_count.txt"


def find_first_voxel(model):
    """ Find first (highest) voxel in the lung
    """
    for layer in range(len(model)):
        possible_coords = []
        found = False
        for line in range(len(model[layer])):
            for voxel in range(len(model[layer][line])):
                if model[layer][line][voxel] == 1:
                    possible_coords.append(np.array([layer, line, voxel]))
                    found = True
        if found:
            possible_coords = np.array(possible_coords)
            avg = np.sum(possible_coords, axis=0) / len(possible_coords)
            print("Average starting coordinate:", avg)
            best = possible_coords[0]
            for pc in possible_coords:
                if np.sum(np.abs(avg - pc)) < np.sum(np.abs(avg - best)):
                    best = pc
            print("Closest starting coordinate to average:", list(best))
            return list(best)


model = np.load(patient_data_file)['arr_0']
model[model != 1] = 0
# import sys
# print(np.unique(model, return_counts=True))

# Skeletonize model
model = skeletonize(model)
model[model != 0] = 1
# print(np.unique(model, return_counts=True))
# sys.exit(0)
# print(np.count_nonzero(model))

print(f"Model loaded with shape {model.shape}")

first_voxel = find_first_voxel(model)
print(first_voxel)

bfs_queue = queue.Queue()

bfs_queue.put((np.array(first_voxel), 0))
visited = {tuple(first_voxel): 0}

distance_to_coords = []
coord_to_previous = {}
coord_to_next_count = {}

vis_count = 0

# Traverse entire tree to mark each pixels manhattan distance to the first pixel
while not bfs_queue.empty():
    curr, dist = bfs_queue.get()
    if len(distance_to_coords) <= dist:
        distance_to_coords.append([curr])
    else:
        distance_to_coords[dist].append(curr)
    vis_count += 1

    # Print progress
    if vis_count % 10000 == 0:
        print(vis_count)
    next_count = 0
    for adj in adjacent(curr, moore_neighborhood=True):
        x, y, z = adj

        # Iterate over bronchus
        if model[x][y][z] == 1:
            if tuple(adj) not in visited:
                bfs_queue.put((adj, dist + 1))
                coord_to_previous[tuple(adj)] = curr
                visited[tuple(adj)] = dist + 1
                next_count += 1
    coord_to_next_count[tuple(curr)] = next_count

np_dist_to_coords = np.array(distance_to_coords, dtype=object)
np.savez_compressed(distance_to_coords_file, np_dist_to_coords)
print(f"Writing distance to coords with shape: {np_dist_to_coords.shape}")

for dictionary, filename in [(visited, coord_to_distance_file),
                             (coord_to_previous, coord_to_previous_file),
                             (coord_to_next_count, coord_to_next_count_file)]:
    with open(filename, 'w') as curr_file:
        for coord, dist in dictionary.items():
            x, y, z = coord
            curr_file.write(f"{x}, {y}, {z}: {dist}\n")
