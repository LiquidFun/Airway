#!/usr/bin/env python3
import csv
from pathlib import Path

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from airway.util.util import get_data_paths_from_args

plt.rcParams.update({"font.size": 4})


def get_graph_edit_distance():
    # calculate the graph edit distance between all trees
    # okay this takes extreme long -> only for small trees nodes(tree)=12 max
    ged_dict = {}
    for pa in pat_id_list:
        for pb in pat_id_list:
            if pa == pb:
                break
            print(f"\ncalc ged from {pa} - {pb}")
            print(f"nodes: {tree_dict[pa].number_of_nodes()} <---> {tree_dict[pb].number_of_nodes()}")
            key = f"{pa}~{pb}"
            ged_dict.update({key: nx.graph_edit_distance(tree_dict[pa], tree_dict[pb])})
            print(f"{key} --> {tree_dict.get(key)}")


def longest_path_length(tree):
    d = nx.shortest_path_length(tree, source="0")
    return max([length for target, length in d.items()])


def maximum_independent_set_length(tree):
    d = nx.maximal_independent_set(tree)
    return len(d)


def create_general_tree_statistics_file(csv_path):
    if Path.exists(Path(csv_path)):
        print(f"WARNING: File was overwritten: {csv_path}")
    else:
        Path(csv_path).touch(exist_ok=False)

    with open(csv_path, "w", newline="") as f:
        csv_writer = csv.writer(f)

        csv_writer.writerow(["patient", "nodes", "edges", "longest_path_length", "maximum_independent_set_length"])
        stat_list = []
        for key, tree in tree_dict.items():
            curr_row = [
                str(key),
                tree.number_of_nodes(),
                tree.number_of_edges(),
                longest_path_length(tree),
                maximum_independent_set_length(tree),
            ]
            stat_list.append(curr_row)

        csv_writer.writerows(stat_list)


def per_lobe_statistics():
    # closures
    def node_quotient():
        g = tree_dict.get(str(graph.graph["patient"]))
        try:
            return g.number_of_nodes() / graph.number_of_nodes()
        except ZeroDivisionError:
            return 0

    def edges_quotient():
        g = tree_dict.get(str(graph.graph["patient"]))
        try:
            return g.number_of_edges() / graph.number_of_edges()
        except ZeroDivisionError:
            return 0

    for lobe in range(2, 7):
        paths = list(input_data_path.glob("**/lobe-" + str(lobe) + "*.graphml"))

        with open(output_data_path / f"lobe-{lobe}.csv", "w", newline="") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(["patient", "nodes", "edges", "nodeQuotient", "edgeQuotient"])
            for path in paths:
                graph = nx.read_graphml(path)
                csv_writer.writerow(
                    [
                        graph.graph["patient"],
                        graph.number_of_nodes(),
                        graph.number_of_edges(),
                        node_quotient(),
                        edges_quotient(),
                    ]
                )


def upper_left_lobe_distance_analysis(plot_path, csv_path):
    # setup path to lobe.graphml files
    upper_left_lobe_list = []
    for pat_dir in sorted(input_data_path.glob("*")):
        lobe_path = pat_dir / f"lobe-3-{pat_dir.parts[-1]}.graphml"
        if lobe_path.is_file():
            upper_left_lobe_list.append(lobe_path)
    # fill a dictionary with lobe graphs
    left_lobe_dict = {}
    for lobePath in upper_left_lobe_list:
        left_lobe_dict[lobePath.parts[-2]] = nx.read_graphml(lobePath)
    lu_count = len(left_lobe_dict)
    print(f"Found {lu_count} upper left lobes for analysis.")
    not_tree_list = []
    lobe_tree_dict = {}

    # iterate over the lobes
    for key, lobe in left_lobe_dict.items():
        # print (key, nx.get_node_attributes(lobe, 'level'))
        # check if there are lobes not being a tree
        if not nx.is_tree(lobe):
            lu_count = lu_count - 1
            not_tree_list.append(key)
        else:
            lobe_tree_dict.update({key: lobe})

    print(f"Detected trees: {lu_count}/{len(left_lobe_dict)}")
    print("Patients whose lobes are not a tree: ")
    for tree in not_tree_list:
        print(tree)

    print(left_lobe_dict)
    for patient_id, nx_lobe in left_lobe_dict.items():
        first_node_index = list(nx_lobe.nodes)[0]

        def get_coords(node):
            return node["x"], node["y"], node["z"]

        print(get_coords(nx_lobe.nodes[first_node_index]))
        first_node = nx_lobe.nodes[first_node_index]
        _, succ = next(nx.bfs_successors(nx_lobe, first_node_index))
        print(succ)
        for s in succ:
            node = nx_lobe.nodes[s]
            print(get_coords(node))
            if node["x"] - first_node["x"] > 5:
                print(node, "is likely lingular")
        print()

    print("Classifying left upper lobes:")
    distance_dict = {}
    classified_counter = 0
    for key, lobe in left_lobe_dict.items():
        nodelist = []
        for node, data in lobe.nodes.items():
            nodelist.append(int(node))
        distance_value = get_distance_value(lobe, nodelist, key)
        if distance_value != (-1, -1):
            distance_dict[key] = distance_value
        if distance_value == (0, 0):
            classified_counter = classified_counter + 1
        print("-" * 70)

    print("Successfully classified " + str(classified_counter) + " lobes as Type A.")

    print("Found " + str(len(distance_dict) - classified_counter) + " potential candidates for Type B.")
    # print (distance_dict)
    # print (len(distance_dict))
    plot_distance_values(distance_dict, plot_path)
    export_classification_csv(distance_dict, csv_path)


def get_distance_value(lobe, nodelist, key):
    root = min(nodelist)
    neighbour_list = list(nx.neighbors(lobe, str(root)))
    for neighbour in neighbour_list.copy():
        if nx.get_node_attributes(lobe, "level")[neighbour] < nx.get_node_attributes(lobe, "level")[str(root)]:
            neighbour_list.remove(neighbour)
        elif lobe.nodes[neighbour]["x"] - lobe.nodes[str(root)]["x"] > 5:
            neighbour_list.remove(neighbour)
            print("lingular removed")
        print("neighbour: ", neighbour)
        neighbour_count = len(neighbour_list)
    if neighbour_count == 3:
        print(key, "classified as Type A")
        dist_value = (0, 0)
        print(neighbour_list)
    elif neighbour_count < 2:
        print(key, "Warning: less than 2 neighbours detected. Iterating....")
        nodelist.remove(root)
        if len(nodelist) != 0:
            dist_value = get_distance_value(lobe, nodelist, key)
        else:
            dist_value = (-1, -1)
    elif neighbour_count > 3:
        print(key, "Error: more than 3 neighbours detected.")
        for neighbour in neighbour_list:
            length = lobe[str(root)][neighbour]["weight"]
            print("Length: " + str(length))
        dist_value = (-1, -1)
    elif neighbour_count == 2:
        print(key, "2 neighbours detected")
        weight_list = []
        for neighbour in neighbour_list:
            length = lobe[str(root)][neighbour]["weight"]
            print("Length: " + str(length))
            weight_list.append(length)
        dist_value = (weight_list[0], weight_list[1])

    return dist_value


def plot_distance_values(distance_dict, path):
    patients = []
    length1_list = []
    length2_list = []
    for key, (length1, length2) in sorted(distance_dict.items()):
        patients.append(key)
        length1_list.append(int(length1))
        length2_list.append(int(length2))

    x = np.arange(len(patients))
    width = 0.35
    fig, ax = plt.subplots()
    bars1 = ax.bar(x - width / 2, length1_list, width, label="Length1")
    bars2 = ax.bar(x + width / 2, length2_list, width, label="Length2")

    ax.set_ylabel("Length")
    ax.set_title("Length of edges of type B candidates")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{index+1}. {pat}" for index, pat in zip(x, patients)])
    # ax.set_xticklabels(x + 1)
    ax.legend()
    autolabel(bars1, ax)
    autolabel(bars2, ax)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    fig.tight_layout()

    # plt.show()
    plt.savefig(path, dpi=200)
    plt.close()


def autolabel(bars, ax):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            "{}".format(height),
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )


def export_classification_csv(distance_dict, csv_path):
    if Path.exists(Path(csv_path)):
        print(f"WARNING: File was overwritten: {csv_path}")
    else:
        Path(csv_path).touch(exist_ok=False)

    with open(csv_path, "w", newline="") as f:
        csv_writer = csv.writer(f)

        csv_writer.writerow(
            [
                "patient",
                "classification",
                "length_1",
                "length_2",
            ]
        )

        classification = []
        for key, (l1, l2) in distance_dict.items():
            curr_row = [str(key), get_classification(l1, l2), l1, l2]
            classification.append(curr_row)

        csv_writer.writerows(classification)


def get_classification(l1, l2):
    if (l1, l2) == (0, 0):
        return "A"
    else:
        return "B"


if __name__ == "__main__":
    output_data_path, input_data_path = get_data_paths_from_args()

    # paths to all trees
    path_list = [pat_dir / "tree.graphml" for pat_dir in input_data_path.glob("*") if pat_dir.is_dir()]

    lobe_id_to_string = {
        2: "LeftLowerLobe",
        3: "LeftUpperLobe",
        4: "RightLowerLobe",
        5: "RightMiddleLobe",
        6: "RightUpperLobe",
    }

    # list of all patientIDs
    pat_id_list = [pat_dir.parts[-2] for pat_dir in path_list if pat_dir.parents[0].is_dir()]

    # load all trees in dictionary (patID -> nx.graph)
    tree_dict = {}
    for tree_path in path_list:
        if tree_path.is_file():
            tree_dict[tree_path.parts[-2]] = nx.read_graphml(tree_path)
    print("loaded trees: " + str(len(tree_dict.keys())))

    # analysers
    create_general_tree_statistics_file(output_data_path / "csvTREE.csv")
    per_lobe_statistics()
    upper_left_lobe_distance_analysis(
        output_data_path / "type-B-edge-lengths.png", output_data_path / "classification.csv"
    )
