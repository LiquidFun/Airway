"""Creates list of nodes and edges which represent the splits in the bronchus

Input: stage-03 

This script creates a list of edges and nodes which represent the splits in the tree. 
Each node has a coordinates describing them, the edges denote which coordinates are connected
with each other.

This is done by using the groups created by the previous script. By going through each group
this script now checks whenever a group splits in 2 (there is no path between them), whenever this
happens it marks this as a split and saves it later on.

After doing that it backtracks all nodes and creates all the edges. 
"""

import queue
import math
from typing import Tuple, Set

import numpy as np

from airway.util.helper_functions import adjacent, find_radius_via_sphere
from airway.util.util import get_data_paths_from_args

output_data_path, input_data_path, reduced_model_data_path = get_data_paths_from_args(inputs=2)

REDUCED_MODEL = reduced_model_data_path / "reduced_model.npz"
DISTANCE_TO_COORDS_FILE = input_data_path / "map_distance_to_coords.npz"
MAP_COORD_TO_PREVIOUS_FILE = input_data_path / "map_coord_to_previous.txt"
MAP_COORD_TO_NEXT_COUNT_FILE = input_data_path / "map_coord_to_next_count.txt"

FINAL_COORDS_FILE = output_data_path / "final_coords"
FINAL_EDGES_FILE = output_data_path / "final_edges"
EDGE_ATTRIBUTES_FILE = output_data_path / "edge_attributes"
COORD_ATTRIBUTES_FILE = output_data_path / "coord_attributes"

model = np.load(REDUCED_MODEL)["arr_0"]
print(model.shape)


def parse_coord(coord, split_on):
    text = coord.replace("[", "").replace("]", "").strip().split(split_on)
    if len(text) == 1:
        return int(text[0])
    else:
        return tuple([int(a) for a in text if a != ""])


coord_to_previous = {}
coord_to_next_count = {}
for dictionary, filename in [
    (coord_to_previous, MAP_COORD_TO_PREVIOUS_FILE),
    (coord_to_next_count, MAP_COORD_TO_NEXT_COUNT_FILE),
]:
    with open(filename, "r") as dist_file:
        for line in dist_file.read().split("\n"):
            if line != "":
                [first_half, second_half] = line.split(":")
                coord = parse_coord(first_half, ",")
                prev = parse_coord(second_half, " ")
                dictionary[coord] = prev

# Maps group id (1, 0) to group_id (0, 0) to show the predecessor
prev_group = {}

# A list of all groups, where each entry corresponds to a list with all the groups in the distance
all_groups = []

# Maps group to average coordinate of the group
group_to_avg_coord = {}


def distance(coord1, coord2):
    return np.linalg.norm(coord1 - coord2)


def calc_diameter(area):
    return math.sqrt(4 * area / math.pi)


DISTANCE_TO_COORDS = np.load(DISTANCE_TO_COORDS_FILE, allow_pickle=True)["arr_0"]

group_diameter = {}
group_area = {}

# Each iteration corresponds to 1 depth level from the start point
for curr_dist, coords in enumerate(DISTANCE_TO_COORDS):
    coords_set = {tuple(coord) for coord in coords}
    print("Current manhattan distance: {}".format(curr_dist), end=" -> ")

    # Groups is a dictionary where each coordinate maps to an integer which stands for it's group
    # number.  A group in this project is regarded as a set of coordinates which have the same
    # manhattan distance from the start point and are moore connected.
    groups = {}
    group_index = 0

    # Iterate over each coord in the current depth level. Later on this coordinate will be added
    # to a bfs queue and each adjacent coordinate will be marked as belonging to this group.
    # The loop will not iterate over visited coords, therefore this loop will only visit as many
    # coords as there are groups
    for coord in coords:

        # Convert coord to tuple since arrays can't be hashed in dictionaries
        coord = tuple(coord)

        # Make sure the coordinate has not been visited yet
        if coord not in groups:
            groups[coord] = group_index
            group_coords_sum = np.array(coord)
            group_size = 1
            bfs_queue = queue.Queue()
            bfs_queue.put(coord)

            # Count any adjacent coords to the current group
            while not bfs_queue.empty():
                curr = bfs_queue.get()

                # Iterate over adjacent coords
                for adj in adjacent(curr, moore_neighborhood=True):
                    adj = tuple(adj)

                    # If the adjacent is an actual coordinate (not empty space) and has not yet
                    # been visited then mark it as belonging to this group
                    if adj in coords_set and adj not in groups.keys():
                        bfs_queue.put(adj)
                        groups[adj] = group_index
                        group_coords_sum += np.array(adj)
                        group_size += 1

            # Group_id is the unique identifier for each group; this one will be used in dicts
            # to access them
            group_id = (curr_dist, group_index)

            # Remember the previous group for each group. Used to build the tree
            if curr_dist != 0:
                prev_group[group_id] = all_groups[(curr_dist - 1)][coord_to_previous[coord]]

            # Add the information about the group for saving as attribute
            group_area[group_id] = group_size
            group_diameter[group_id] = calc_diameter(group_size)

            # Count the average coordinate for each group, this will be the split location
            group_to_avg_coord[group_id] = group_coords_sum / group_size
            group_index += 1

    all_groups.append(groups)
    print("{} group count".format(group_index))
    # if curr_dist == 10:
    #     break

# Create successor count for each node
# Will be used to determine groups which only connect 2 other groups if there are only
successor_count = {(0, 0): 0}
for group, prev_group_index in prev_group.items():
    curr_dist, group_index = group
    key = (curr_dist - 1, prev_group_index)
    if key not in successor_count:
        successor_count[key] = 0
    successor_count[key] += 1

# Build minimal tree
minimal_tree = {(0, 0): (0, 0)}
edge_area_per_group_id = {(0, 0): [1]}

# print("="*50)
# print("succesor_count: ", successor_count)
# print("="*50)

not_skip_groups = {(0, 0)}


for group, prev_group_index in prev_group.items():
    curr_dist, group_index = group
    prev = (curr_dist - 1, prev_group_index)

    # print(f"Prev: {prev}, curr: {group}")
    # Propagates prev until node with succesor_count of not 1 appears, i.e. either 0 (end node),
    # or >1 which is a split
    if prev in successor_count:
        if prev not in edge_area_per_group_id:
            edge_area_per_group_id[prev] = []
        if successor_count[prev] == 1:
            minimal_tree[group] = minimal_tree[prev]
            if group not in edge_area_per_group_id:
                edge_area_per_group_id[group] = edge_area_per_group_id[prev].copy()
            # Use this if not skeletonize
            edge_area_per_group_id[group].append(group_area[group])

        else:
            minimal_tree[group] = prev
            not_skip_groups.add(prev)
            # print(f"Trying to find {prev} in temp_edge for group: {group}")
            edge_area_per_group_id[group] = [group_area[group]]


# Remove nodes which add no information
for group, successors in successor_count.items():
    # Filter nodes, make sure not to filter start node
    if group not in not_skip_groups:
        minimal_tree.pop(group, None)

# print(prev_group)
# print(successor_count)
# print(minimal_tree)

# print("="*50)
# print("edge_area_per_group_id: ", edge_area_per_group_id)

# Save nodes
xs = []
ys = []
zs = []
group_attr = []

# Calculate final coordinates and group coordinates
for group_id in minimal_tree:
    c = group_to_avg_coord[group_id]
    xs.append(c[0])
    ys.append(c[1])
    zs.append(c[2])
    group_area[group_id] = find_radius_via_sphere(c, {1}, model) * 2
    group_diameter[group_id] = (group_area[group_id] / 2) ** 2 * math.pi
    group_attr.append(np.array([group_diameter[group_id], group_area[group_id], group_id[0]], dtype=object))

final_coords = np.array([xs, ys, zs])

xs = []
ys = []
zs = []
edge_attr = []

# Calculate edge and coord attributes
for group_id in minimal_tree:
    # Skip first node
    if group_id != (0, 0):
        # Get coordinates for previous nodes
        c = group_to_avg_coord[group_id]
        prev_group_id = minimal_tree[group_id]
        prev_c = group_to_avg_coord[prev_group_id]
        xs.append([c[0], prev_c[0]])
        ys.append([c[1], prev_c[1]])
        zs.append([c[2], prev_c[2]])

        # Add edge attributes
        area1 = group_diameter[group_id]
        area2 = group_diameter[prev_group_id]
        curr_edge_areas = [round((area1 + area2) / 2)] * len(edge_area_per_group_id[group_id])
        print(group_id, curr_edge_areas)
        # avg_area = sum(curr_edge_areas) / len(curr_edge_areas)
        # avg_diameter = sum([calc_diameter(a) for a in curr_edge_areas]) / len(curr_edge_areas)
        # edge_attr.append(np.array([avg_diameter, avg_area]))
        edge_attr.append(np.array(curr_edge_areas))


final_edges = np.array([xs, ys, zs])
# print(final_edges)
# print(final_coords)

np.savez_compressed(FINAL_COORDS_FILE, np.array(final_coords))
np.savez_compressed(FINAL_EDGES_FILE, np.array(final_edges))
np.savez_compressed(COORD_ATTRIBUTES_FILE, np.array(group_attr))
np.savez_compressed(EDGE_ATTRIBUTES_FILE, np.array(edge_attr, dtype=object))
# print(group_to_avg_coord)
