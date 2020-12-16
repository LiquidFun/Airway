""" Classify splits in graphml tree
"""
import copy
import itertools
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


all_trees = {}


def recursive_classify_tree(
        tree: nx.Graph,
        successors: Dict[str, List[str]],
        classification_config: Dict[str, Dict[str, Any]],
        current_node_id: str = "0",
        cost: int = None,
        classifications_used=set(),
):
    if cost is None:
        cost = len(tree) * 1000
    all_trees[tree] = min(all_trees.get(tree, 1e9), cost)
    node = tree.nodes[current_node_id]
    node_point = get_point(node)
    cost_and_trees: List[Tuple[int, nx.Graph]] = []
    if node['split_classification'] not in classification_config:
        cost_and_trees.append((cost, tree))
    else:
        children_in_rules = classification_config[node['split_classification']]['children'].copy()
        adjust_for_unaccounted_children = len(successors[current_node_id]) - len(children_in_rules)
        children_in_rules.extend([None] * adjust_for_unaccounted_children)
        cost_with_perm: List[Tuple[int, List[Tuple[str, str]]]] = []
        for perm in set(itertools.permutations(children_in_rules)):
            curr_cost = cost
            successors_with_permutations = list(zip(successors[current_node_id], perm))
            for child_id, classification in successors_with_permutations:
                child_node = tree.nodes[child_id]
                child_point = get_point(child_node)
                vec = child_point - node_point
                if classification is not None:
                    try:
                        curr_cost -= 1000
                        curr_cost += np.linalg.norm(np.array(classification_config[classification]['vector']) - vec)
                    except (KeyError, IndexError):
                        pass
            cost_with_perm.append((curr_cost, successors_with_permutations))
        # Sort by cost for each generated permutation
        cost_with_perm.sort(key=lambda k: k[0])
        for curr_cost, successors_with_permutations in cost_with_perm:
            for child_id, classification in successors_with_permutations:
                if classification is not None:
                    tree.nodes[child_id]['split_classification'] = classification
            for child_id, _ in successors_with_permutations:
                recursive_classify_tree(tree, successors, classification_config, child_id, curr_cost)
            if classification_config[node['split_classification']]['take_best']:
                break
            tree = tree.copy()
            # break
    # for child_id in successors[current_node_id]:
    # return cost_and_trees


def is_valid_tree(
        tree: nx.Graph,
        classification_config: Dict[str, Dict[str, Any]],
        successors: Dict[str, List[str]],
):
    required_descendants = set()
    have_appeared = set()

    def recursive_is_valid_tree(current_id):
        nonlocal required_descendants, have_appeared, tree
        classification = tree.nodes[current_id]['split_classification']
        required_descendants.discard(classification)
        if classification in classification_config:
            required_descendants |= set(classification_config[classification]['descendants'])
        print(classification, required_descendants)
        for child_id in successors.get(current_id, []):
            if child_id in have_appeared:
                return False
            if not recursive_is_valid_tree(child_id):
                return False
            if len(required_descendants) != 0:
                return False
        return True

    return recursive_is_valid_tree('0')


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


def add_defaults_to_classification_config(classification_config):
    defaults = {'children': [], 'optional_children': [], 'descendants': [], 'take_best': False}
    for cid in classification_config:
        for key, val in defaults.items():
            classification_config[cid][key] = classification_config[cid].get(key, copy.deepcopy(val))


def add_default_split_classification_id_to_tree(tree: nx.Graph):
    for node in tree.nodes:
        tree.nodes[node]['split_classification'] = f"c{node}"
    tree.nodes['0']['split_classification'] = 'Trachea'


def main():
    output_path, tree, classification_config = get_inputs()
    add_defaults_to_classification_config(classification_config)
    add_default_split_classification_id_to_tree(tree)
    successors = dict(nx.bfs_successors(tree, '0'))
    recursive_classify_tree(tree, successors, classification_config)
    print(len(all_trees))
    # all_trees.sort(key=lambda x: x[0])
    validated_trees_with_cost: List[Tuple[nx.Graph, int]] = []
    for tree, cost in all_trees.items():
        # if is_valid_tree(tree, classification_config, successors):
        validated_trees_with_cost.append((tree, cost))
    validated_trees_with_cost.sort(key=lambda k: k[1])
    print(len(validated_trees_with_cost))
    print('\n'.join(map(lambda a: f"{a[0]}: {a[1]}", validated_trees_with_cost)))
    # print(validated_trees_with_cost)
    classified_tree = validated_trees_with_cost[1][0]
    # exit(0)
    # classified_tree = traverse_tree(tree, classification_config)
    nx.write_graphml(classified_tree, output_path)


if __name__ == "__main__":
    main()
