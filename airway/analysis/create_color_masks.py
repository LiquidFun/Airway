"""Creates a color mask for lingula and the other

"""
import random
from queue import Queue
from typing import Tuple

import numpy as np
import networkx as nx

from airway.util.helper_functions import adjacent, get_numpy_sphere, get_coords_in_sphere_at_point
from airway.util.util import get_data_paths_from_args


def fill_color_mask_with_bfs(for_point, color_mask, curr_color, model, distance_mask, min_dist):
    # Mark every split interval
    queue = Queue()
    queue.put(for_point)
    dist = distance_mask[for_point]
    visited = {for_point}
    while not queue.empty():
        curr = queue.get()
        for adj in map(tuple, adjacent(curr)):
            not_yet_colored = color_mask[adj] == 0
            is_bronchus = model[adj] == 1
            not_visited = adj not in visited
            below_min_dist = min_dist <= distance_mask[adj]
            # If the current voxel is already closer to root, then only let it propagate upwards, and not downwards
            # This avoids coloring adjacent branches fully
            propagate_upwards_only = dist <= distance_mask[adj] or distance_mask[curr] <= distance_mask[adj]
            if not_yet_colored and is_bronchus and not_visited and below_min_dist and propagate_upwards_only:
                color_mask[adj] = curr_color
                queue.put(adj)
                visited.add(adj)
    print(f"Added {curr_color}")


def find_legal_point(node, distances):
    p = get_point(node)
    queue = Queue()
    queue.put(p)
    visited = {p}
    while not queue.empty():
        for adj in map(tuple, adjacent(queue.get())):
            if adj not in visited:
                if distances[adj] != 0:
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


def color_hex_to_floats(h: str):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def get_color_variation(color, variance=.1):
    def var(h):
        return max(0.0, min(h * (1 + random.uniform(-1, 1) * variance), 1.0))

    return tuple(map(var, color))


def get_point(node):
    return round(node['x']), round(node['y']), round(node['z'])


def main():
    output_data_path, reduced_model_path, distance_mask_path, tree_path, = get_data_paths_from_args(inputs=3)
    model = np.load(reduced_model_path / "reduced_model.npz")['arr_0']
    distance_mask = np.load(distance_mask_path / "distance_mask.npz")['arr_0']
    # np_dist = np.full(model.shape, 0)
    # for (x, y, z), val in distances.items():
    #     np_dist[x, y, z] = val
    # lu_lobe = nx.read_graphml(tree_path / f"lobe-3-{tree_path.name}.graphml")
    tree = nx.read_graphml(tree_path / f"tree.graphml")
    # lu_traversing = nx.bfs_successors(lu_lobe, "5")
    color_mask = np.full(model.shape, 0)

    color_hex_codes = [color_hex_to_floats('ffffff')]

    map_node_id_to_color = {0: color_hex_codes[-1]}

    first_node = list(tree.nodes)[0]
    nodes_visit_order = []
    curr_color = 1
    for (parent_index, successors) in nx.bfs_successors(tree, first_node):
        parent_node = tree.nodes[parent_index]
        parent_dist = distance_mask[find_legal_point(parent_node, distance_mask)] + parent_node['group_size']
        for s in successors:
            succ_node = tree.nodes[s]
            # point = get_point(succ_node)
            point = find_legal_point(succ_node, distance_mask)
            # point = find_legal_point(node, distances, node["group"])
            succ_radius = succ_node['group_size'] / 2
            nodes_visit_order.append((succ_node, point, curr_color, succ_radius, parent_dist))
            if 'color' in succ_node:
                color_hex_codes.append(color_hex_to_floats(succ_node['color']))
            elif parent_index in map_node_id_to_color:
                color_hex_codes.append(get_color_variation(map_node_id_to_color[parent_index]))
            else:
                color_hex_codes.append(color_hex_to_floats("ffffff"))
            map_node_id_to_color[s] = color_hex_codes[-1]
            curr_color += 1
        # fill_sphere_around_point(radius, point, model, color_mask, curr_color)
        # fill_color_mask_with_bfs(point, color_mask, curr_color, model, distance_mask)
    print(color_hex_codes)

    for node, point, curr_color, radius, parent_dist in reversed(nodes_visit_order):
        fill_color_mask_with_bfs(point, color_mask, curr_color, model, distance_mask, parent_dist)

    print("Colors:")
    for color, occ in zip(*np.unique(color_mask, return_counts=True)):
        print(f"Color {color} appears {occ:,} times in color mask")
    np.savez_compressed(output_data_path / "bronchus_color_mask.npz",
                        color_mask=color_mask, color_codes=np.array(color_hex_codes))
    # color_mask
    # output_data_path / "color_mask.npz"


if __name__ == "__main__":
    main()
