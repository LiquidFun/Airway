from collections import defaultdict
from pathlib import Path
from typing import List

import networkx as nx
import yaml
import numpy as np

from airway.classification.split_classification import cost_exponential_diff_function
from airway.util.config_parsers import parse_classification_config
from airway.util.util import get_data_paths_from_args, get_ignored_patients
from airway.util.color import Color

col = Color()


def get_input():
    output_data_path, tree_input_path = get_data_paths_from_args(inputs=1)
    classification_config = parse_classification_config()
    trees: List[nx.Graph] = []
    ignored_patients = get_ignored_patients()
    print(ignored_patients)
    for tree_path in Path(tree_input_path).glob("*/tree.graphml"):
        if tree_path.parent.name not in ignored_patients:
            trees.append(nx.read_graphml(tree_path))
    return output_data_path, trees, classification_config


def get_point(node):
    return np.array([node["x"], node["y"], node["z"]])


def analyse_angles(trees, classification_config):
    map_classification_to_vectors = defaultdict(lambda: [])
    for tree in trees:
        successors = dict(nx.bfs_successors(tree, "0"))
        for parent_id, child_ids in successors.items():
            parent_node = tree.nodes[parent_id]
            parent_point = get_point(parent_node)
            for child_id in child_ids:
                child_node = tree.nodes[child_id]
                child_point = get_point(child_node)
                vec = child_point - parent_point
                try:
                    child_classification = child_node["split_classification"]
                    target_vec = classification_config[child_classification]["vector"]
                    map_classification_to_vectors[child_classification].append(vec)
                except KeyError:
                    pass
    return map_classification_to_vectors


def format_vec(vec):
    return "[" + ", ".join(map(lambda x: f"{x:8.2f}", vec)) + "]"


def get_angle(vec, ref_vec):
    pre_arccos_angle = np.clip((vec @ ref_vec) / (np.linalg.norm(vec) * np.linalg.norm(ref_vec)), -1, 1)
    return np.arccos(pre_arccos_angle)


def get_formatted_angle(vec, ref_vec):
    a = get_angle(vec, ref_vec)
    c = cost_exponential_diff_function(vec, ref_vec)
    return col.yellow(f"{a/np.pi*180:6.2f}°") + f"   ({a:4.2f} -> {c:4.2f})"


def main():
    output_path, trees, classification_config = get_input()
    map_classification_to_vectors = analyse_angles(trees, classification_config)
    summary_list = []
    for classification, vectors in map_classification_to_vectors.items():
        avg = np.average(vectors, axis=0)
        print(f"{col.red(classification)}:")
        try:
            ref_vec = classification_config[classification]["vector"]
            summary_list.append((get_angle(avg, ref_vec), classification, len(vectors)))
            print(f"angle avg to ref:\t{get_formatted_angle(avg, ref_vec)}")
            print(f"ref:\t{format_vec(ref_vec)}")
        except KeyError:
            ref_vec = None
        print(f"avg:\t{format_vec(avg)}")
        for vector in sorted(vectors, key=lambda x: get_angle(x, ref_vec)):
            print(f'\t{format_vec(vector)} {"" if ref_vec is None else get_formatted_angle(vector, ref_vec)}')
        print()
    print("Summary list:")
    print("\n".join(map(lambda x: f"{x[0]/np.pi*180:8.2f}° {x[1]:<12} \t(count={x[2]})", sorted(summary_list))))


if __name__ == "__main__":
    main()
