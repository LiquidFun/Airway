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
    tree.nodes['0']['split_classification'] = 'Trachea'
    for node_id, children_ids in nx.bfs_successors(tree, "0"):
        node = tree.nodes[node_id]
        node_point = get_point(node)
        curr_classification = node['split_classification']
        print(node_id, children_ids, curr_classification)
        taken_classifications = set()
        for child_id in children_ids:
            child_node = tree.nodes[child_id]
            child_point = get_point(child_node)
            vec = child_point - node_point
            best = (1e9, f"c{child_id}")
            if curr_classification in classification_config:
                for child in classification_config[curr_classification]['children']:
                    if child in taken_classifications:
                        continue
                    try:
                        curr_dist = np.linalg.norm(np.array(classification_config[child]['vector']) - vec)
                    except (KeyError, IndexError):
                        curr_dist = 1e8
                    # print(curr_dist, child)
                    if best[0] > curr_dist:
                        best = (curr_dist, child)
                    # print(child)
            child_node['split_classification'] = best[1]
            taken_classifications.add(best[1])
            print(f"\tVector {node_id}->{child_id}: {list(vec)} ({best[1]})")
        print()
    return tree


def main():
    output_path, tree, classification_config = get_inputs()
    classified_tree = traverse_tree(tree, classification_config)
    nx.write_graphml(classified_tree, output_path)


if __name__ == "__main__":
    main()