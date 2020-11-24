"""Creates a color mask for lingula and the other

"""
from queue import Queue

import numpy as np
import networkx as nx

from tree_extraction.helper_functions import adjacent
from util.parsing import parse_map_coord_to_distance
from util.util import get_data_paths_from_args


def fill_color_mask_with_bfs(for_point, color_mask, curr_color, distances):
    # Mark every split interval
    queue = Queue()
    queue.put(for_point)
    visited = set(for_point)
    node_dist = distances[for_point]
    while not queue.empty():
        for adj in map(tuple, adjacent(queue.get())):
            if adj in distances and adj not in visited:
                if distances[adj] >= node_dist-3:
                    if distances[adj] > node_dist:
                        color_mask[adj] = curr_color
                    queue.put(adj)
                    visited.add(adj)
    print(f"Added {curr_color}")


def find_legal_point(node, distances, target_distance):
    p = (round(node['x']), round(node['y']), round(node['z']))
    queue = Queue()
    queue.put(p)
    visited = set(p)
    while not queue.empty():
        for adj in map(tuple, adjacent(queue.get())):
            if adj not in visited:
                if adj in distances:
                    if distances[adj] == target_distance:
                        return adj
                visited.add(adj)
                queue.put(adj)


def main():
    output_data_path, reduced_model_path, coord_to_distance_path, tree_path, = get_data_paths_from_args(inputs=3)
    model = np.load(reduced_model_path / "reduced_model.npz")['arr_0']
    distances = parse_map_coord_to_distance(coord_to_distance_path / "map_coord_to_distance.txt")
    np_dist = np.full(model.shape, 0)
    for (x, y, z), val in distances.items():
        np_dist[x, y, z] = val
    # lu_lobe = nx.read_graphml(tree_path / f"lobe-3-{tree_path.name}.graphml")
    lu_lobe = nx.read_graphml(tree_path / f"tree.graphml")
    # lu_traversing = nx.bfs_successors(lu_lobe, "5")
    color_mask = np.full(model.shape, 0)
    first_node = list(lu_lobe.nodes)[0]
    for curr_color, (node_index, successors) in enumerate(nx.bfs_successors(lu_lobe, first_node), start=1):
        node = lu_lobe.nodes[node_index]
        point = find_legal_point(node, distances, node["group"])
        fill_color_mask_with_bfs(point, color_mask, curr_color, distances)
        # color_mask[np_dist >= node_dist] = curr_color
    print(np.unique(model))
    np.savez_compressed(output_data_path / "bronchus_color_mask.npz", color_mask)
    # color_mask
    # output_data_path / "color_mask.npz"


if __name__ == "__main__":
    main()
