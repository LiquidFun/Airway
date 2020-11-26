"""Creates a color mask for lingula and the other

"""
from queue import Queue
from typing import Tuple

import numpy as np
import networkx as nx

from util.helper_functions import adjacent, get_numpy_sphere, get_coords_in_sphere_at_point
from util.parsing import parse_map_coord_to_distance
from util.util import get_data_paths_from_args


def fill_color_mask_with_bfs(for_point, color_mask, curr_color, model):
    # Mark every split interval
    queue = Queue()
    queue.put(for_point)
    visited = {for_point}
    while not queue.empty():
        for adj in map(tuple, adjacent(queue.get())):
            if color_mask[adj] in {0, curr_color} and model[adj] == 1 and adj not in visited:
                color_mask[adj] = curr_color
                queue.put(adj)
                visited.add(adj)
    print(f"Added {curr_color}")


def find_legal_point(node, distances, target_distance):
    p = (round(node['x']), round(node['y']), round(node['z']))
    queue = Queue()
    queue.put(p)
    visited = {p}
    while not queue.empty():
        for adj in map(tuple, adjacent(queue.get())):
            if adj not in visited:
                if adj in distances:
                    if distances[adj] == target_distance:
                        return adj
                visited.add(adj)
                queue.put(adj)


def fill_sphere_around_point(
            radius: int,
            point: Tuple[int, int, int],
            model: np.ndarray,
            color_mask: np.ndarray,
            curr_color: int,
        ):
    sphere_around_point = get_coords_in_sphere_at_point(radius * 2.5, point)
    color_mask[sphere_around_point] = curr_color
    # for coord in zip(*sphere_around_point):
    #     coord = tuple(map(lambda c: [round(c)], coord))
    #     try:
    #         if model[coord] == 1:
    #             color_mask[coord] = curr_color
    #     except IndexError:
    #         pass


def main():
    output_data_path, reduced_model_path, coord_to_distance_path, tree_path, = get_data_paths_from_args(inputs=3)
    model = np.load(reduced_model_path / "reduced_model.npz")['arr_0']
    # distances = parse_map_coord_to_distance(coord_to_distance_path / "map_coord_to_distance.txt")
    # np_dist = np.full(model.shape, 0)
    # for (x, y, z), val in distances.items():
    #     np_dist[x, y, z] = val
    # lu_lobe = nx.read_graphml(tree_path / f"lobe-3-{tree_path.name}.graphml")
    tree = nx.read_graphml(tree_path / f"tree.graphml")
    # lu_traversing = nx.bfs_successors(lu_lobe, "5")
    color_mask = np.full(model.shape, 0)

    nodes_visit_order = []
    first_node = list(tree.nodes)[0]
    for curr_color, (node_index, successors) in enumerate(nx.bfs_successors(tree, first_node), start=1):
        node = tree.nodes[node_index]
        # point = find_legal_point(node, distances, node["group"])
        point = (round(node['x']), round(node['y']), round(node['z']))
        nodes_visit_order.append((node, point, curr_color))
        radius = node['group_size'] / 2
        fill_sphere_around_point(radius, point, model, color_mask, curr_color)
        # fill_color_mask_with_bfs(point, color_mask, curr_color, distances)

    for node, point, curr_color in reversed(nodes_visit_order):
        fill_color_mask_with_bfs(point, color_mask, curr_color, model)

    print("Colors:")
    for color, occ in zip(*np.unique(color_mask, return_counts=True)):
        print(f"Color {color} appears {occ:,} times in color mask")
    np.savez_compressed(output_data_path / "bronchus_color_mask.npz", color_mask)
    # color_mask
    # output_data_path / "color_mask.npz"


if __name__ == "__main__":
    main()
