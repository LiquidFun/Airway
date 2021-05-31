import math
import queue
from typing import Tuple, Dict

import numpy as np
from skimage.morphology import skeletonize

from airway.util.helper_functions import adjacent
from airway.util.util import get_data_paths_from_args

Coordinate = Tuple[int, int, int]

output_data_path, input_data_path = get_data_paths_from_args()

patient_data_file = input_data_path / "reduced_model.npz"

distance_to_coords_file = output_data_path / "map_distance_to_coords"
coord_to_distance_file = output_data_path / "map_coord_to_distance.txt"
coord_to_previous_file = output_data_path / "map_coord_to_previous.txt"
coord_to_next_count_file = output_data_path / "map_coord_to_next_count.txt"
distance_mask_path = output_data_path / "distance_mask"


def find_first_voxel(model):
    """Find first (highest) voxel in the lung"""
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


model = np.load(patient_data_file)["arr_0"]
model[model != 1] = 0
# import sys
# print(np.unique(model, return_counts=True))

# Skeletonize model
skeleton = skeletonize(model)
skeleton[skeleton != 0] = 1
# print(np.unique(model, return_counts=True))
# sys.exit(0)
# print(np.count_nonzero(model))

print(f"Model loaded with shape {skeleton.shape}")

first_voxel = find_first_voxel(skeleton)


def traverse_skeleton():
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
            if skeleton[x][y][z] == 1:
                if tuple(adj) not in visited:
                    bfs_queue.put((adj, dist + 1))
                    coord_to_previous[tuple(adj)] = curr
                    visited[tuple(adj)] = dist + 1
                    next_count += 1
        coord_to_next_count[tuple(curr)] = next_count

    np_dist_to_coords = np.array(distance_to_coords, dtype=object)
    # print(np_dist_to_coords)
    np.savez_compressed(distance_to_coords_file, np_dist_to_coords)
    print(f"Writing distance to coords with shape: {np_dist_to_coords.shape}")

    for dictionary, filename in [
        (visited, coord_to_distance_file),
        (coord_to_previous, coord_to_previous_file),
        (coord_to_next_count, coord_to_next_count_file),
    ]:
        with open(filename, "w") as curr_file:
            for coord, dist in dictionary.items():
                x, y, z = coord
                curr_file.write(f"{x}, {y}, {z}: {dist}\n")
    return visited


def distance(c1: Coordinate, c2: Coordinate):
    # return math.sqrt(sum(map(lambda a, b: (a-b)*(a-b), zip(c1, c2))))
    return np.linalg.norm(np.array(c1) - np.array(c2))


def get_distance_in_model_from_skeleton(visited: Dict[Coordinate, int]):

    distance_mask: np.ndarray = np.zeros(model.shape)
    origin: Dict[Coordinate, Coordinate] = {}
    bfs_queue = queue.Queue()
    for coord, dist in visited.items():
        bfs_queue.put(coord)
        distance_mask[coord] = dist
        origin[coord] = coord
    while not bfs_queue.empty():
        curr = bfs_queue.get()
        for adj in map(tuple, adjacent(curr)):
            if model[adj] == 1:
                if adj in origin:
                    if distance(origin[curr], adj) >= distance(origin[adj], adj):
                        continue
                # else add point
                bfs_queue.put(adj)
                distance_mask[adj] = distance_mask[curr]
                origin[adj] = origin[curr]
    np.savez_compressed(distance_mask_path, distance_mask)
    print(*map(str, zip(*np.unique(distance_mask, return_counts=True))))
    return distance_mask


def main():
    visited = traverse_skeleton()
    distance_mask = get_distance_in_model_from_skeleton(visited)


if __name__ == "__main__":
    main()
