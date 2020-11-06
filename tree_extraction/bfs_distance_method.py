import os
import sys
import queue
import numpy as np
from helper_functions import adjacent

try:
    source_path_dir = sys.argv[1]
    target_path_dir = sys.argv[2]
except IndexError:
    print("ERROR: No data or target folder found, aborting")
    sys.exit(1)

patient_data_file = os.path.join(source_path_dir, "reduced_model.npy")
distance_to_coords_file = os.path.join(target_path_dir, "map_distance_to_coords")
coord_to_distance_file = os.path.join(target_path_dir, "map_coord_to_distance.txt")
coord_to_previous_file = os.path.join(target_path_dir, "map_coord_to_previous.txt")
coord_to_next_count_file = os.path.join(target_path_dir, "map_coord_to_next_count.txt")

# Find first (highest) voxel in the lung
def find_first_voxel(model):
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

model = np.load(patient_data_file)
print(f"Model loaded with shape {model.shape}") 

first_voxel = find_first_voxel(model)

bfs_queue = queue.Queue()

bfs_queue.put((np.array(first_voxel), 0))
visited = {tuple(first_voxel) : 0}

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
    for adj in adjacent(curr):
        x, y, z = adj

        # Iterate over bronchus
        if model[x][y][z] == 1:
            if tuple(adj) not in visited:
                bfs_queue.put((adj, dist+1))
                coord_to_previous[tuple(adj)] = curr
                visited[tuple(adj)] = dist+1
                next_count += 1
    coord_to_next_count[tuple(curr)] = next_count

np.save(distance_to_coords_file, np.array(distance_to_coords))
print(f"Writing distance to coords with shape: {np.array(distance_to_coords).shape}")

for dictionary, filename in [(visited, coord_to_distance_file),
                             (coord_to_previous, coord_to_previous_file),
                             (coord_to_next_count, coord_to_next_count_file)]:
    with open(filename, 'w') as curr_file:
        for coord, dist in dictionary.items():
            x,y,z = coord
            curr_file.write("{}, {}, {}: {}\n".format(x, y, z, dist))

