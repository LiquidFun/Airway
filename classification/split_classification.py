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
    output_path = output_data_path / "tree.graphml"
    return output_path, tree, classification_config


def get_point(node):
    return np.array([node['x'], node['y'], node['z']])


def classify_tree(
        original_tree: nx.Graph,
        successors: Dict[str, List[str]],
        classification_config: Dict[str, Dict[str, Any]],
):
    initial_cost = get_total_cost_in_tree(original_tree, successors)
    # queue contains the tree currently being worked on, and the current steps to work on
    tree_variations_queue = Queue()
    tree_variations_queue.put((original_tree, ["0"], initial_cost))
    final_trees = []

    while not tree_variations_queue.empty():
        print()
        # print(list(map(lambda x: f"next={x[1]}, cost={x[2]}", list(tree_variations_queue.queue))))
        tree, (current_node_id, *rest_node_ids), cost = tree_variations_queue.get()
        node = tree.nodes[current_node_id]
        print(f"Current={current_node_id} ({node['split_classification']}), rest={rest_node_ids}")
        node_point = get_point(node)
        if node['split_classification'] in classification_config:
            children_in_rules = classification_config[node['split_classification']]['children'].copy()
            successor_ids = successors.get(current_node_id, [])
            adjust_for_unaccounted_children = len(successor_ids) - len(children_in_rules)
            children_in_rules.extend([None] * adjust_for_unaccounted_children)
            cost_with_perm: List[Tuple[int, List[Tuple[str, str]]]] = []
            for perm in set(itertools.permutations(children_in_rules, r=len(successor_ids))):
                successors_with_permutations = list(zip(successor_ids, perm))
                descendant_list = sum([
                    list(classification_config.get(p, {}).get('deep_descendants', set())) + ([] if p is None else [p])
                    for _, p in successors_with_permutations], [])
                print(f"perm={perm}, descendants={descendant_list} => {successors_with_permutations}")
                permutation_shares_descendants = len(descendant_list) != len(set(descendant_list))
                if permutation_shares_descendants:
                    continue
                curr_cost = cost
                # TODO: Change back to all
                all_classifications_with_vectors = any(
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
                            curr_cost -= child_node['cost']
                            curr_cost += np.linalg.norm(np.array(classification_config[classification]['vector']) - vec)
                cost_with_perm.append((curr_cost, successors_with_permutations))
                if not all_classifications_with_vectors:
                    break
            cost_with_perm.sort(key=lambda k: k[0])
            print("cost_with_perm:", *map(lambda s: f"\n\t{s}", cost_with_perm))
            if cost_with_perm:
                for curr_cost, successors_with_permutations in cost_with_perm:
                    print("successors with permutations:", successors_with_permutations)
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
                    if classification_config[node['split_classification']]['take_best']:
                        print("Breaking for node", node['split_classification'], "since it is specified as take_best")
                        break
            else:
                final_trees.append((cost, tree))
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
        # print(current_id, classification, required_descendants)
        for child_id in successors.get(current_id, []):
            if child_id in have_appeared:
                return False
            if not recursive_is_valid_tree(child_id):
                return False
        return True

    recursive_is_valid_tree('0')
    return len(required_descendants) == 0


def show_classification_vectors(tree, successors):
    for node_id, children_ids in successors.items():
        node = tree.nodes[node_id]
        node_point = get_point(node)
        curr_classification = node['split_classification']
        print(node_id, children_ids, curr_classification)
        for child_id in children_ids:
            child_node = tree.nodes[child_id]
            child_point = get_point(child_node)
            vec = child_point - node_point
            print(f"\tVector {node_id}->{child_id}: {list(vec)} ({tree.nodes[child_id]['split_classification']})")
        print()
    return tree


def add_deep_descendants_to_classification_config(classification_config):

    def recursive_get(classification):
        if classification not in classification_config:
            return []
        cc = classification_config[classification]
        dd = cc['deep_descendants']
        dd += cc.get('descendants', [])
        for child in cc['children']:
            dd += recursive_get(child)
        cc['deep_descendants'] = list(set(dd))
        return dd
    recursive_get('Trachea')


def add_defaults_to_classification_config(classification_config):
    defaults = {'children': [], 'deep_descendants': [], 'descendants': [], 'take_best': False}
    for cid in classification_config:
        for key, val in defaults.items():
            classification_config[cid][key] = classification_config[cid].get(key, copy.deepcopy(val))


def add_default_split_classification_id_to_tree(tree: nx.Graph):
    for node in tree.nodes:
        tree.nodes[node]['split_classification'] = f"c{node}"
    tree.nodes['0']['split_classification'] = 'Trachea'


def add_cost_by_level_in_tree(tree, successors):
    def recursive_add_cost(curr_id='0', cost=100000000.0):
        tree.nodes[curr_id]['cost'] = cost
        for child_id in successors.get(curr_id, []):
            recursive_add_cost(child_id, cost/10)
    recursive_add_cost()
    tree.nodes['0']['cost'] = 0


def get_total_cost_in_tree(tree, successors):
    def rec_total(curr_id='0'):
        return tree.nodes[curr_id]['cost'] + sum(rec_total(child_id) for child_id in successors.get(curr_id, []))
    return rec_total()


def get_all_classifications_in_tree(tree, successors):
    def rec(curr_id):
        return [tree.nodes[curr_id]['split_classification']] + sum([rec(i) for i in successors.get(curr_id, [])], [])
    return rec('0')


def add_colors_in_tree(tree, classification_config):
    for node_id in tree.nodes:
        node = tree.nodes[node_id]
        try:
            node['color'] = classification_config[node['split_classification']]['color']
        except KeyError:
            pass


def main():
    output_path, tree, classification_config = get_inputs()
    successors = dict(nx.bfs_successors(tree, '0'))
    add_defaults_to_classification_config(classification_config)
    add_default_split_classification_id_to_tree(tree)
    add_deep_descendants_to_classification_config(classification_config)
    add_cost_by_level_in_tree(tree, successors)
    print('\n'.join(map(str, classification_config.items())))
    all_trees = classify_tree(tree, successors, classification_config)
    print(f"All trees: {len(all_trees)}")
    all_trees.sort(key=lambda x: x[0])
    validated_trees = []
    for cost, curr_tree in all_trees:
        if is_valid_tree(curr_tree, classification_config, successors):
            validated_trees.append((cost, curr_tree))
    print(f"Valid trees: {len(validated_trees)}")
    for curr_cost, curr_tree in validated_trees:
        all_classifications = get_all_classifications_in_tree(curr_tree, successors)
        print(f"Cost={curr_cost:.2f}, {'B1+2 is in tree' if 'LB1+2' in all_classifications else ''}")
    # print('\n'.join(map(lambda a: f"{a[0]}: {a[1]}", validated_trees_with_cost)))

    classified_tree = validated_trees[0][1]
    add_colors_in_tree(classified_tree, classification_config)
    # try:
    # except IndexError:
    #     classified_tree = all_trees[0][1]
    show_classification_vectors(classified_tree, successors)
    nx.write_graphml(classified_tree, output_path)


if __name__ == "__main__":
    main()
