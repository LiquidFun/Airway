""" Used to separate lobes
"""
import os
import sys
import csv
from pathlib import Path

import networkx as nx

from compose_tree import eraseLevelfromGraph
from compose_tree import setLevel
from post_processing import load_graph


# single splits without any edges are erased from graph
def erase_orphaned_nodes(view):
    degree_dict = dict(nx.degree(view))
    lobe_graph = view.copy()
    for node in degree_dict.keys():
        if degree_dict.get(node) == 0:
            lobe_graph.remove_node(node)

    return lobe_graph


# creating subtrees for each lobe based on the lobe attribute
def create_subtrees(graph, patient, target_path):
    # line will be written to csv file(patID, lobe2..6 if graph is connected)

    # closure
    def filter_for_lobe(node):
        return graph.nodes[node]["lobe"] == curr_lobe

    for curr_lobe in range(2, 7):
        view = nx.subgraph_view(graph, filter_node=filter_for_lobe)
        lobe_graph = view
        # lobe_graph = erase_orphaned_nodes(view)
        print(lobe_graph.number_of_nodes(), end=" -> ")
        if lobe_graph.number_of_nodes() == 0:
            print("x")
            continue
        lobe_graph = eraseLevelfromGraph(lobe_graph, 4)
        print(lobe_graph.number_of_nodes())
        nx.write_graphml(
            lobe_graph, os.path.join(target_path, f"lobe-{curr_lobe}-{patient}.graphml")
        )


# ============================================================================
# ----------------------------------- Main -----------------------------------
# ============================================================================


def main():
    """ Executes all methods given above in the correct order
    """
    # |>-<-><-><-><-><-><-><-<|
    # |>- Process arguments -<|
    # |>-<-><-><-><-><-><-><-<|

    try:
        data_folder = sys.argv[1]
        target_folder = sys.argv[2]
        patient = os.path.basename(sys.argv[1])
    except IndexError:
        print("ERROR: No data or target folder found, aborting")
        sys.exit(1)

    print(f"\nstage-07 current patient: {patient}\n")

    # |>-<-><-><-><->-<|
    # |>- Load graph -<|
    # |>-<-><-><-><->-<|

    graph = load_graph(os.path.join(data_folder, "tree.graphml"))

    # |>-<-><-><-><-><-<|
    # |>- Write lobes -<|
    # |>-<-><-><-><-><-<|

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    nx.write_graphml(graph, os.path.join(target_folder, "tree.graphml"))

    # Store subtrees and connection statistics
    create_subtrees(graph, patient, target_folder)


if __name__ == "__main__":
    main()
