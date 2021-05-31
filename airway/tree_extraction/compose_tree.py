import sys
import math

import numpy as np
import networkx as nx

from airway.util.util import get_data_paths_from_args


def get_value_from_model(coord, reduced_model):
    return reduced_model[coord[0], coord[1], coord[2]]


# returns the lobe number and the path length to this coordinate
def check_axis(axis_id, coord_list, direction, reduced_model):
    maximum = np.shape(reduced_model)[axis_id]
    coord = coord_list[axis_id]
    path_len = 0
    # print(  "check: " + direction + " of " + str(axisID) + " coord: " + str(coord)
    #        + " maximum " + str(maximum))
    curr_coord_list = coord_list.copy()
    while coord in range(0, maximum - 1):
        path_len = path_len + 1

        coord += 1 if direction == "positive" else -1

        curr_coord_list[axis_id] = coord

        lobe = get_value_from_model(curr_coord_list, reduced_model)
        if lobe > 1:
            break
    return lobe, path_len


# returns the lobe number where coord is (possibly) within therefore
def get_lobe(coords, reduced_model):
    orig_coord_list = [int(round(i)) for i in coords]
    lobe_paths = {}

    for i in range(0, 7):
        lobe_paths.update({i: 8192})

    for axis_id in range(0, 3):
        for direction in ["positive", "negative"]:
            lobe_path_len = check_axis(axis_id, orig_coord_list, direction, reduced_model)
            if lobe_paths.get(lobe_path_len[0]) > lobe_path_len[1]:
                lobe_paths.update({lobe_path_len[0]: lobe_path_len[1]})

    # if more than maximum_path_length pixel between split and lobe set lobe number to 0
    maximum_path_length = 24
    if lobe_paths.get(min(lobe_paths, key=lobe_paths.get)) > maximum_path_length:
        return 0
    else:
        return min(lobe_paths, key=lobe_paths.get)


# returns a dict with association coordinate -> node Number
def create_nodes(graph, np_coord, np_coord_attributes, reduced_model):
    # get node coordinates
    max_coords = np.shape(np_coord)[1]
    dic_coords_to_nodes = {}
    i = 0
    while i < max_coords:
        curr_coord = (np_coord[0][i], np_coord[1][i], np_coord[2][i])
        dic_coords_to_nodes.update({curr_coord: i})
        # level counts from root, where root = 0
        level_val = 8192
        if i == 0:
            level_val = 0

        # first split never belongs to a lobe
        if i == 1:
            lobe_val = 0
        else:
            lobe_val = get_lobe(curr_coord, reduced_model)
        group_size = np_coord_attributes[i][1]
        group = np_coord_attributes[i][2]

        graph.add_node(
            i,
            x=curr_coord[0],
            y=curr_coord[1],
            z=curr_coord[2],
            lobe=lobe_val,
            level=level_val,
            group_size=group_size,
            group=group,
        )
        i += 1

    return dic_coords_to_nodes


def get_weight(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2 + (coord1[2] - coord2[2]) ** 2)


# returns a dict with association edge -> weight
def create_edges(graph, np_edges, dic_coords, edge_attributes):
    dic_edges_to_weight = {}
    # print(str(np.shape(npEdges)))
    max_edges = np.shape(np_edges)[1]
    i = 0
    while i < max_edges:
        coord1 = (np_edges[0][i][0], np_edges[1][i][0], np_edges[2][i][0])
        coord2 = (np_edges[0][i][1], np_edges[1][i][1], np_edges[2][i][1])
        curr_weight = get_weight(coord1, coord2)
        edge = (dic_coords[coord1], dic_coords[coord2])
        dic_edges_to_weight.update({edge: curr_weight})
        group_sizes = " ".join([str(attr) for attr in edge_attributes[i]])
        graph.add_edge(edge[0], edge[1], weight=curr_weight, group_sizes=group_sizes)
        i += 1

    return dic_edges_to_weight


def show_stats(graph, pat_id):
    print(f"\nstatistics for the graph of patient: {pat_id}")
    print(f"nodes: {graph.number_of_nodes()}")
    print(f"edges: {graph.number_of_edges()}\n")


def erase_level_from_graph(graph, max_level):
    graph = graph.copy()
    node_list = list(nx.nodes(graph))
    start_node = min([int(a) for a in node_list])
    print(f"(startNode={start_node})", end=" -> ")
    start_level = graph.nodes[str(start_node)]["level"]
    print(f"(level={start_level})", end=" -> ")
    max_level = max_level + start_level

    for node in node_list:
        if graph.nodes[node]["level"] >= max_level:
            # print("node " + str(node) + " level " + str(graph.nodes[node]['level']))
            graph.remove_node(node)

    return graph


# takes a graph and set the level attribute to every node
def set_level(input_graph):
    graph = input_graph.copy()
    for node in nx.nodes(graph):
        neighbors = nx.neighbors(graph, node)
        # identify parent
        if node != 0:
            parent = node
            for poss_parent in neighbors:
                if graph.nodes[parent]["level"] > graph.nodes[poss_parent]["level"]:
                    parent = poss_parent
            # print("parent {} -- level -> {}"
            #        .format(parent,graph.nodes[parent]['level']))
            graph.nodes[node]["level"] = graph.nodes[parent]["level"] + 1
    return graph


def get_children(graph, node):
    children = []
    neighbors = nx.neighbors(graph, node)
    for poss_child in neighbors:
        if graph.nodes[poss_child]["level"] > graph.nodes[node]["level"]:
            children.append(poss_child)
    return children


def set_attribute_to_node(graph, filter_by_value_attribute, target):
    """
    set_attribute_to_node(graph, filter, target) set or update existing attributes to
    a node filtered by filter.

    graph -> a graph
    filt = (filterAttrib,filterVal) -> Nodes whom filterAttrib has filterVal
    target = (targetAttrib,targetValue) -> set new targetValue to a nodes targetAttrib

    """
    graph = graph.copy()

    def filter_for_attrib(node_id):
        return graph.nodes[node_id][filter_by_value_attribute[0]] == filter_by_value_attribute[1]

    view = nx.subgraph_view(graph, filter_node=filter_for_attrib)

    for node in nx.nodes(view):
        graph.nodes[node][target[0]] = target[1]

    return graph


def main():
    output_data_path, tree_input_data_path, reduced_model_data_path = get_data_paths_from_args(inputs=2)

    patient_id = tree_input_data_path.parts[-1]

    if tree_input_data_path.is_dir and output_data_path.is_dir:
        coord_file_path = tree_input_data_path / "final_coords.npz"
        edges_file_path = tree_input_data_path / "final_edges.npz"
        coord_attributes_file_path = tree_input_data_path / "coord_attributes.npz"
        edge_attributes_file_path = tree_input_data_path / "edge_attributes.npz"
    else:
        sys.exit(f"ERROR: either {tree_input_data_path} or {output_data_path} do not exist!")

    if not reduced_model_data_path.exists():
        print(reduced_model_data_path)
        sys.exit("ERROR: stage-02 needed")

    reduced_model = np.load(reduced_model_data_path / "reduced_model.npz")["arr_0"]
    print(np.unique(reduced_model))
    reduced_model[reduced_model >= 7] = 0
    # Remove all voxels 7, 8 and 9 since these are veins/arteries and not useful in classification
    print(np.unique(reduced_model))

    np_coord = np.load(coord_file_path)["arr_0"]
    np_edges = np.load(edges_file_path)["arr_0"]
    np_coord_attributes = np.load(coord_attributes_file_path, allow_pickle=True)["arr_0"]
    np_edges_attributes = np.load(edge_attributes_file_path, allow_pickle=True)["arr_0"]

    # create empty graphs
    graph = nx.Graph(patient=patient_id)
    # compose graphs
    dic_coords = create_nodes(graph, np_coord, np_coord_attributes, reduced_model)
    dic_edges = create_edges(graph, np_edges, dic_coords, np_edges_attributes)

    # set levels to the graph
    graph = set_level(graph)
    # level 2 does not belong to a lobe
    graph = set_attribute_to_node(graph, ("level", 2), ("lobe", 0))

    show_stats(graph, patient_id)

    nx.write_graphml(graph, output_data_path / "tree.graphml")


if __name__ == "__main__":
    main()
