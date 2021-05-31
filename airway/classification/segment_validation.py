import re
from pathlib import Path
from typing import List, Tuple, Set, Dict

import networkx as nx
import yaml

from airway.util.config_parsers import parse_array_encoding, parse_classification_config
from airway.util.util import get_data_paths_from_args, get_ignored_patients


def get_input():
    output_data_path, tree_input_path = get_data_paths_from_args()
    trees: List[List[nx.Graph]] = []
    for tree_path in Path(tree_input_path).glob("*"):
        pair = []
        for name in ["tree.graphml", "tree_gt.graphml"]:
            if (tree_path / name).exists():
                pair.append(nx.read_graphml(tree_path / name))
        trees.append(pair)
    classification_config = parse_classification_config()
    return output_data_path, trees, classification_config


def main():
    output_path, trees, classification_config = get_input()
    ignored_patients = get_ignored_patients()
    clustering_endnodes = {
        name for name, config in classification_config.items() if config.get("clustering_endnode", False)
    }
    children: Dict[str, Set[str]] = {
        name: set(config.get("children", [])) & clustering_endnodes for name, config in classification_config.items()
    }
    print(len(clustering_endnodes), "segment-like nodes", clustering_endnodes)

    no_ignored = []
    with_ignored = []
    for index, tree_pair in enumerate(trees, 1):
        tree, tree_gt = tree_pair * 2 if len(tree_pair) == 1 else tree_pair
        # Ignore some nodes as otherwise segments may be counted twice (e.g.: LB7+8, LB7, and LB8)
        ignored_nodes: Set[str] = set()
        # print(f"\nPatient {tree.graph['patient']}")
        for node_id in tree_gt.nodes:
            node_gt = tree_gt.nodes[node_id]
            node = tree.nodes[node_id]

            sc = node["split_classification"]
            sc_gt = node_gt.get("split_classification_gt", "")
            if sc_gt == "":
                sc_gt = sc

            if sc_gt in clustering_endnodes and sc_gt not in ignored_nodes:
                ignored_nodes |= children.get(sc_gt, set())
                correctly_classified = sc_gt == sc
                if str(tree.graph["patient"]) not in ignored_patients:
                    no_ignored.append(correctly_classified)
                with_ignored.append(correctly_classified)

    def show_stats(lis: List[bool]):
        s = sum(lis)
        t = len(lis)
        print(f"{s}/{t} = {s/t:%}")
        no_ignored_count = len(trees) - len(ignored_patients)
        print(f"{t/no_ignored_count} segments per patient")

    print("Without ignored patients:")
    show_stats(no_ignored)
    # print("With ignored patients:")
    # show_stats(with_ignored)


if __name__ == "__main__":
    main()
