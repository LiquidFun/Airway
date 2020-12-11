""" Classify splits in graphml tree
"""
from pathlib import Path

import yaml
import numpy as np
import networkx as nx

from util.util import get_data_paths_from_args


def get_inputs():
    output_data_path, tree_input_path = get_data_paths_from_args(inputs=1)
    config_path = Path("configs") / "classification.yaml"
    with open(config_path) as config_file:
        classification_config = yaml.load(config_file, yaml.FullLoader)
    tree = nx.read_graphml(tree_input_path / "tree.graphml")
    print(classification_config)
    output_path = output_data_path / "tree.graphml"
    return output_path, tree, classification_config


def get_point(node):
    return np.array([node['x'], node['y'], node['z']])


def traverse_tree(tree, classification_config):
    for node_id, children_ids in nx.bfs_successors(tree, "0"):
        print(node_id, children_ids)
        node = tree.nodes[node_id]
        node['split_classification'] = f"c{node_id}"
        node_point = get_point(node)
        for child_id in children_ids:
            child_node = tree.nodes[child_id]
            child_point = get_point(child_node)
            vec = child_point - node_point
            print(f"\tVector {node_id}->{child_id}: {vec}")
        print()
    return tree


def main():
    output_path, tree, classification_config = get_inputs()
    classified_tree = traverse_tree(tree, classification_config)
    nx.write_graphml(classified_tree, output_path)


if __name__ == "__main__":
    main()