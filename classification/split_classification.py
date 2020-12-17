""" Classify splits in graphml tree
"""
import copy
import itertools
from pathlib import Path
from queue import Queue
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


def classify_tree(
        original_tree: nx.Graph,
        successors: Dict[str, List[str]],
        classification_config: Dict[str, Dict[str, Any]],
):
    all_trees = {}

    # queue contains the tree currently being worked on, and the current steps to work on
    initial_cost = len(original_tree) * 1000
    tree_variations_queue = Queue()
    tree_variations_queue.put((original_tree, ["0"], initial_cost))
    final_trees = []

    while not tree_variations_queue.empty():
        print()
        print(list(map(lambda x: f"next={x[1]}, cost={x[2]}", list(tree_variations_queue.queue))))
        tree, (current_node_id, *rest_node_ids), cost = tree_variations_queue.get()
        node = tree.nodes[current_node_id]
        node_point = get_point(node)
        if node['split_classification'] in classification_config:
            children_in_rules = classification_config[node['split_classification']]['children'].copy()
            adjust_for_unaccounted_children = len(successors[current_node_id]) - len(children_in_rules)
            children_in_rules.extend([None] * adjust_for_unaccounted_children)
            cost_with_perm: List[Tuple[int, List[Tuple[str, str]]]] = []
            for perm in set(itertools.permutations(children_in_rules)):
                successors_with_permutations = list(zip(successors[current_node_id], perm))
                descendant_list = sum([classification_config.get(p, {}).get('descendants', [])
                                       for _, p in successors_with_permutations], [])
                print(f"perm={perm}, descendants={descendant_list} => {successors_with_permutations}")
                permutation_shares_descendants = len(descendant_list) != len(set(descendant_list))
                if permutation_shares_descendants:
                    continue
                curr_cost = cost
                all_classifications_with_vectors = all(
                    classification in classification_config
                    and 'vector' in classification_config.get(classification, {})
                    for _, classification in successors_with_permutations
                )
                print(all_classifications_with_vectors)
                if all_classifications_with_vectors:
                    for child_id, classification in successors_with_permutations:
                        child_node = tree.nodes[child_id]
                        child_point = get_point(child_node)
                        vec = child_point - node_point
                        if classification is not None:
                            curr_cost -= 1000
                            curr_cost += np.linalg.norm(np.array(classification_config[classification]['vector']) - vec)
                cost_with_perm.append((curr_cost, successors_with_permutations))
                if not all_classifications_with_vectors:
                    break
            cost_with_perm.sort(key=lambda k: k[0])
            print(cost_with_perm)
            if cost_with_perm:
                for curr_cost, successors_with_permutations in cost_with_perm:
                    print(successors_with_permutations)
                    new_tree = tree.copy()
                    for child_id, classification in successors_with_permutations:
                        if classification is not None:
                            new_tree.nodes[child_id]['split_classification'] = classification
                    next_nodes = rest_node_ids.copy() + [
                        child_id for child_id, classification in successors_with_permutations
                        if classification in classification_config
                    ]
                    if len(next_nodes) == 0:
                        final_trees.append((curr_cost, new_tree))
                    else:
                        tree_variations_queue.put((new_tree, next_nodes, curr_cost))
            else:
                final_trees.append((curr_cost, new_tree))
    return final_trees


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
    all_trees = classify_tree(tree, successors, classification_config)
    print(len(all_trees))
    # all_trees.sort(key=lambda x: x[0])
    # print(len(all_trees))
    validated_trees_with_cost: List[Tuple[nx.Graph, int]] = []
    for cost, tree in all_trees:
        # if is_valid_tree(tree, classification_config, successors):
        validated_trees_with_cost.append((tree, cost))
    validated_trees_with_cost.sort(key=lambda k: k[1])
    print(len(validated_trees_with_cost))
    print('\n'.join(map(lambda a: f"{a[0]}: {a[1]}", validated_trees_with_cost)))
    # print(validated_trees_with_cost)
    classified_tree = validated_trees_with_cost[0][0]
    # exit(0)
    # classified_tree = traverse_tree(tree, classification_config)
    nx.write_graphml(classified_tree, output_path)


if __name__ == "__main__":
    main()
