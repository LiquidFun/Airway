from queue import Queue

import networkx as nx
import numpy as np

from airway.util.util import get_data_paths_from_args
from airway.util.helper_functions import adjacent


def dist_point_to_segment(p: np.ndarray, segment_p1: np.ndarray, segment_p2: np.ndarray):
    """Return distance from point to finite line segment

    >>> def a(a1, a2, a3): return np.array([a1, a2, a3])
    >>> dist_point_to_segment(a(0, 0, 0), a(1, 1, 1), a(10, 10, 10))
    1.7320508075688772
    >>> dist_point_to_segment(a(0, 0, 0), a(-10, 6, 1), a(10, 10, 10))
    8.993626180313887
    >>> dist_point_to_segment(a(0, 0, 0), a(-1, -1, -1), a(1, 1, 1))
    0.0
    >>> round(dist_point_to_segment(a(2, 1, 1), a(-1, -1, -1), a(1, 1, 1)), 6)
    1.0

    Based on Sanya Pushkar's answer: https://stackoverflow.com/a/56467661
    """
    diff = segment_p2 - segment_p1
    tangent_vec = diff / np.linalg.norm(diff)

    # signed parallel distance components. If positive then the point is opposite
    # to the segment point in direction.
    s = np.dot(segment_p1 - p, tangent_vec)
    t = np.dot(p - segment_p2, tangent_vec)

    # clamped parallel distance. If segment is closest, then it will be 0
    h = np.max([s, t, 0])

    # perpendicular distance component
    c = np.cross(p - segment_p1, tangent_vec)
    return np.hypot(h, np.linalg.norm(c))


def fill_line(model: np.ndarray, line_p1: np.ndarray, line_p2: np.ndarray, dist: int):
    queue = Queue()
    queue.put(line_p1)
    visited = set()
    while not queue.empty():
        for adj in adjacent(queue.get()):
            if tuple(adj) not in visited and dist_point_to_segment(adj, line_p1, line_p2) <= dist:
                visited.add(tuple(adj))
                model[tuple(adj)] = 1
                queue.put(adj)


def get_point(node):
    return np.array([int(a) for a in [node["x"], node["y"], node["z"]]])


def main():
    output_data_path, reduced_model_data_path, tree_data_path = get_data_paths_from_args(inputs=2)
    model = np.zeros(np.load(reduced_model_data_path / "reduced_model.npz")["arr_0"].shape)
    tree = nx.read_graphml(tree_data_path / "tree.graphml")
    for parent_id, child_ids in nx.bfs_successors(tree, "0"):
        parent_node = tree.nodes[parent_id]
        parent_point = get_point(parent_node)
        for child_id in child_ids:
            child_point = get_point(tree.nodes[child_id])
            fill_line(model, parent_point, child_point, max(2, parent_node["group_size"] / 2))

    print(*zip(*np.unique(model, return_counts=True)))
    np.savez_compressed(output_data_path / "model.npz", model)


if __name__ == "__main__":
    main()
