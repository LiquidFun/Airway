"""Module to generate .obj file from splits (places cubes where splits are)
"""
from pathlib import Path

import networkx as nx
import numpy as np

from airway.obj_generation.gen_obj import normalize
from airway.util.util import get_data_paths_from_args


def gen_split_obj(
    target_data_path: Path,
    graph,
    model_shape: np.ndarray,
    rot_mat: np.ndarray = None,
):
    edge_vertices = []

    print(graph.nodes)
    for node, successors in nx.bfs_successors(graph, "0"):
        for succ in successors:
            for curr in [node, succ]:
                n = graph.nodes[curr]
                x, y, z = n["x"], n["y"], n["z"]
                edge_vertices.append(np.array([x, y, z]))
    print(edge_vertices)

    edge_vertices = normalize(edge_vertices, reference_shape=model_shape, rot_mat=rot_mat)

    with open(target_data_path, "w") as file:
        file.write("# Vertices\n")
        file.write("# Edge Vertices\n")
        for x, y, z in edge_vertices:
            file.write(f"v {x:.3f} {y:.3f} {z:.3f}\n")
        file.write("\n# Faces\n")

        file.write("# Edge lines\n")
        for i in range(0, len(edge_vertices), 2):
            j = i + 1
            file.write(f"l {j} {j + 1}\n")


def main():
    (
        output_data_path,
        post_processing_data_path,
        post_composition_data_path,
        reduced_model_data_path,
    ) = get_data_paths_from_args(inputs=3)

    rot_mat = np.array([[0, 0, -1], [-1, 0, 0], [0, 1, 0]])
    model = np.load(reduced_model_data_path / "reduced_model.npz")["arr_0"]

    if not output_data_path.exists():
        output_data_path.mkdir(parents=True, exist_ok=True)

    graph = nx.read_graphml(post_composition_data_path / "tree.graphml")
    gen_split_obj(output_data_path / "splits_no_post_processing.obj", graph, rot_mat=rot_mat, model_shape=model.shape)

    graph = nx.read_graphml(post_processing_data_path / "tree.graphml")
    gen_split_obj(output_data_path / "splits.obj", graph, rot_mat=rot_mat, model_shape=model.shape)


if __name__ == "__main__":
    main()
