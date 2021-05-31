""" Classify splits in graphml tree
"""
import copy
import itertools
import math
import sys
from queue import PriorityQueue
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import networkx as nx

from airway.util.config_parsers import parse_classification_config
from airway.util.util import get_data_paths_from_args

trees_thrown_out = 0
global_angles = []


def get_inputs():
    output_data_path, tree_input_path = get_data_paths_from_args(inputs=1)
    classification_config = parse_classification_config()
    tree = nx.read_graphml(tree_input_path / "tree.graphml")
    output_path = output_data_path / "tree.graphml"
    return output_path, tree, classification_config


def get_point(node):
    return np.array([node["x"], node["y"], node["z"]])


def cost_exponential_diff_function(curr_vec: np.array, target_vec: np.array, exp=2, div=math.pi / 3):
    angle_pre_arccos = (curr_vec @ target_vec) / (np.linalg.norm(curr_vec) * np.linalg.norm(target_vec))
    angle_radians = np.arccos(np.clip(angle_pre_arccos, -1, 1))
    global_angles.append(angle_radians)
    return (angle_radians / div) ** exp


def classify_tree(
    starting_tree: nx.Graph,
    successors: Dict[str, List[str]],
    classification_config: Dict[str, Dict[str, Any]],
    starting_node="0",
    starting_cost=0,
):
    """
    Creates every valid classification for a tree based on the rules in classification.yaml

    Terminology:
        starting_* - function was called with these parameters
        curr_* - node which is temporarily considered root node in while loop
        child_* - nodes and their attributes which are children of curr
    """
    global trees_thrown_out

    # queue contains the tree currently being worked on, and the current steps to work on
    tree_variations_queue = PriorityQueue()
    tree_variations_queue.put((starting_cost, starting_tree, [starting_node]))

    print(starting_cost, starting_tree, starting_node, starting_tree.nodes[starting_node]["split_classification"])
    cost_hack = 0

    # While there are any tree variations in queue iterate over them
    while not tree_variations_queue.empty():
        curr_cost, curr_tree, next_node_id_list = tree_variations_queue.get()

        # Save which classifications have already been used so no invalid trees are created unnecessarily
        curr_classifications_used = {curr_tree.nodes[index]["split_classification"] for index in curr_tree.nodes}

        # If there is a tree variation which has no next nodes in list, then return it if it is a valid tree.
        # Sine tree variations is a priority queue this must be the best possible (lowest cost) tree
        if len(next_node_id_list) == 0:
            if is_valid_tree(curr_tree, classification_config, successors, starting_node):
                return [(curr_cost, curr_tree)]
            else:
                trees_thrown_out += 1
                continue

        # Divide next node list into curr node id, and rest which still need to be checked
        (curr_node_id, *rest_node_ids) = next_node_id_list
        curr_node = curr_tree.nodes[curr_node_id]
        curr_classification = curr_node["split_classification"]
        curr_node_point = get_point(curr_node)

        # Only handle if current classification (i.e. Bronchus/RB3, etc) is actually in classification config
        if curr_classification in classification_config:

            # If there are more children than in the config then extend list to account for all of them
            children_in_rules: List[Optional[str]] = [
                child
                for child in classification_config[curr_classification]["children"]
                if child not in curr_classifications_used
            ]
            # The ids as strings of nodes which succeed current node
            successor_ids: List[str] = successors.get(curr_node_id, [])
            adjust_for_unaccounted_children: int = len(successor_ids) - len(children_in_rules)
            children_in_rules.extend([None] * adjust_for_unaccounted_children)

            # Defines list of all permutations of children including their cost
            # e.g. [(34.3, [('3', 'Bronchus')]) cost and the permutation where the node id specifies which
            # classification should be used
            cost_with_perm: List[Tuple[int, List[Tuple[str, str]]]] = []
            for perm in set(itertools.permutations(children_in_rules, r=len(successor_ids))):
                successors_with_permutations: List[Tuple[str, str]] = list(zip(successor_ids, perm))

                # Create a list of all descendants for each children, this then can be used to check whether any
                # of them share descendants when this list has non unique members
                descendant_list = sum(
                    [
                        list(classification_config.get(p, {}).get("deep_descendants", set()))
                        + ([] if p is None else [p])
                        for _, p in successors_with_permutations
                    ],
                    [],
                )
                permutation_shares_descendants = len(descendant_list) != len(set(descendant_list))
                if permutation_shares_descendants:
                    continue

                # Then check whether all children config rules have vectors defined, if not just take the best
                perm_cost = curr_cost
                do_all_classifications_have_vectors = any(
                    classification in classification_config
                    and "vector" in classification_config.get(classification, {})
                    for _, classification in successors_with_permutations
                )

                # Calculate cost of current permutation
                if do_all_classifications_have_vectors:
                    for child_id, classification in successors_with_permutations:
                        child_node = curr_tree.nodes[child_id]
                        child_point = get_point(child_node)
                        vec = child_point - curr_node_point
                        if classification in classification_config:
                            target_vec = classification_config[classification]["vector"]
                            child_node["cost"] = float(cost_exponential_diff_function(vec, target_vec, 1, 1))
                            perm_cost += child_node["cost"]
                cost_with_perm.append((perm_cost, successors_with_permutations))

                # Only add first permutation if not all children have vectors
                if not do_all_classifications_have_vectors:
                    # print("Break since not all classifications have vectors")
                    break

            # Sort by cost, so we evaluate low cost first
            cost_with_perm.sort(key=lambda k: k[0])

            # If cost_with_perm is not empty
            if cost_with_perm:
                for perm_cost, successors_with_permutations in cost_with_perm:
                    # print("successors with permutations:", successors_with_permutations)
                    perm_tree = curr_tree.copy()
                    for child_id, classification in successors_with_permutations:
                        if classification is not None:
                            perm_tree.nodes[child_id]["split_classification"] = classification
                    next_nodes = rest_node_ids.copy() + [
                        child_id
                        for child_id, classification in successors_with_permutations
                        if classification in classification_config
                    ]
                    take_best = classification_config[curr_node["split_classification"]]["take_best"]
                    if take_best:
                        for child_node_id in successors[curr_node_id]:
                            perm_cost, perm_tree = classify_tree(
                                perm_tree, successors, classification_config, child_node_id, perm_cost + cost_hack
                            )[0]
                            next_nodes.remove(child_node_id)
                    cost_hack += 0.000001
                    tree_variations_queue.put((perm_cost + cost_hack, perm_tree, next_nodes))
                    if take_best:
                        break
                    # print("Breaking for node", node['split_classification'], "since it is specified as take_best")
            else:
                # print("WEIRD ELSE?")
                tree_variations_queue.put((curr_cost, curr_tree, []))
    return [(curr_cost, curr_tree)]
    raise Exception("Sacrebleu! Only invalid trees are possible!")


def merge_tree_into(tree_into, tree_other):
    for node_id in tree_into.nodes:
        node = tree_into.nodes[node_id]
        other_node = tree_other.nodes[node_id]
        if node["split_classification"][0] == "c":
            node["split_classification"] = other_node["split_classification"]


def is_valid_tree(
    tree: nx.Graph,
    classification_config: Dict[str, Dict[str, Any]],
    successors: Dict[str, List[str]],
    start_node_id: str = "0",
):
    required_descendants = set()
    have_appeared = set()

    def recursive_is_valid_tree(current_id):
        nonlocal required_descendants, have_appeared, tree
        classification = tree.nodes[current_id]["split_classification"]

        # Make sure each classification appears only once
        if classification in have_appeared:
            print(f"Classification {classification} appears twice!")
            return False
        have_appeared.add(classification)

        # Remember required descendants for subtree
        required_descendants.discard(classification)
        curr_descendants = set()
        if classification in classification_config:
            curr_descendants = set(classification_config[classification].get("descendants", []))
        required_descendants |= curr_descendants

        # Recursively iterate over each node and require each node to be valid
        for child_id in successors.get(current_id, []):
            if not recursive_is_valid_tree(child_id):
                return False

        # Tree is valid only if all descendants have been removed in the recursive steps above
        if not required_descendants.isdisjoint(curr_descendants):
            print(
                f"Invalid because {required_descendants} is required as descendant, but is not available."
                f" Descendants: {curr_descendants} for node {classification}"
            )
            return False
        return True

    return recursive_is_valid_tree(start_node_id)


def show_classification_vectors(tree, successors):
    for node_id, children_ids in successors.items():
        node = tree.nodes[node_id]
        node_point = get_point(node)
        curr_classification = node["split_classification"]
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
        dd = cc["deep_descendants"]
        dd += cc.get("descendants", [])
        for child in cc["children"]:
            dd += recursive_get(child)
        cc["deep_descendants"] = list(set(dd))
        return dd

    recursive_get("Trachea")


def add_defaults_to_classification_config(classification_config):
    defaults = {"children": [], "deep_descendants": [], "descendants": [], "take_best": False}
    for cid in classification_config:
        for key, val in defaults.items():
            classification_config[cid][key] = classification_config[cid].get(key, copy.deepcopy(val))
    for cid in classification_config:
        if "vector" in classification_config[cid]:
            classification_config[cid]["vector"] = np.array(classification_config[cid]["vector"])


def add_default_split_classification_id_to_tree(tree: nx.Graph):
    for node in tree.nodes:
        tree.nodes[node]["split_classification_gt"] = ""
        tree.nodes[node]["split_classification"] = f"c{node}"
    tree.nodes["0"]["split_classification"] = "Trachea"


def add_cost_by_level_in_tree(tree, successors):
    def recursive_add_cost(curr_id="0", cost=1000000.0):
        tree.nodes[curr_id]["cost"] = float(0.0)
        for child_id in successors.get(curr_id, []):
            recursive_add_cost(child_id, cost / 2)

    recursive_add_cost()
    tree.nodes["0"]["cost"] = float(0.0)


def get_total_cost_in_tree(tree, successors):
    def rec_total(curr_id="0"):
        return tree.nodes[curr_id]["cost"] + sum(rec_total(child_id) for child_id in successors.get(curr_id, []))

    return rec_total()


def get_all_classifications_in_tree(tree, successors):
    def rec(curr_id):
        return [tree.nodes[curr_id]["split_classification"]] + sum([rec(i) for i in successors.get(curr_id, [])], [])

    return rec("0")


def add_colors_in_tree(tree, classification_config):
    for node_id in tree.nodes:
        node = tree.nodes[node_id]
        try:
            node["color"] = classification_config[node["split_classification"]]["color"]
        except KeyError:
            pass


def main():
    output_path, tree, classification_config = get_inputs()
    successors = dict(nx.bfs_successors(tree, "0"))
    add_defaults_to_classification_config(classification_config)
    add_default_split_classification_id_to_tree(tree)
    add_deep_descendants_to_classification_config(classification_config)
    add_cost_by_level_in_tree(tree, successors)
    print("\n".join(map(str, classification_config.items())))
    all_trees = classify_tree(tree, successors, classification_config)
    # print(f"All trees: {len(all_trees)}")
    all_trees.sort(key=lambda x: x[0])
    validated_trees = []
    print(f"Invalid trees thrown out: {trees_thrown_out}")
    print(f"All trees: {len(all_trees)}")
    for cost, curr_tree in all_trees:
        if is_valid_tree(curr_tree, classification_config, successors):
            validated_trees.append((cost, curr_tree))
    print(f"Valid trees: {len(validated_trees)}")
    # for curr_cost, curr_tree in validated_trees:
    #     all_classifications = get_all_classifications_in_tree(curr_tree, successors)
    #     print(f"Cost={curr_cost:.2f}, {'B1+2 is in tree' if 'LB1+2' in all_classifications else ''}")
    # print('\n'.join(map(lambda a: f"{a[0]}: {a[1]}", validated_trees_with_cost)))

    try:
        classified_tree = validated_trees[0][1]
    except IndexError:
        print("ERROR: Could not create valid tree! Using invalid tree instead.", file=sys.stderr)
        classified_tree = all_trees[0][1]
    add_colors_in_tree(classified_tree, classification_config)
    show_classification_vectors(classified_tree, successors)
    nx.write_graphml(classified_tree, output_path)

    # print("Angles found: ", ' '.join(map(lambda x: f"{x/math.pi*180:.2f}°", sorted(global_angles))))


if __name__ == "__main__":
    main()
