""" Used to separate lobes
"""
import networkx as nx

from airway.tree_extraction.compose_tree import erase_level_from_graph
from airway.tree_extraction.post_processing import load_graph
from airway.util.util import get_data_paths_from_args


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
        lobe_graph = erase_level_from_graph(lobe_graph, 4)
        print(lobe_graph.number_of_nodes())
        nx.write_graphml(lobe_graph, target_path / f"lobe-{curr_lobe}-{patient}.graphml")


# ============================================================================
# ----------------------------------- Main -----------------------------------
# ============================================================================


def main():
    """Executes all methods given above in the correct order"""
    # |>-<-><-><-><-><-><-><-<|
    # |>- Process arguments -<|
    # |>-<-><-><-><-><-><-><-<|

    output_data_path, input_data_path = get_data_paths_from_args()
    patient = input_data_path.name

    print(f"\nstage-07 current patient: {patient}\n")

    # |>-<-><-><-><->-<|
    # |>- Load graph -<|
    # |>-<-><-><-><->-<|

    graph = load_graph(input_data_path / "tree.graphml")

    # |>-<-><-><-><-><-<|
    # |>- Write lobes -<|
    # |>-<-><-><-><-><-<|

    if not output_data_path.exists():
        output_data_path.mkdir(parents=True)
    nx.write_graphml(graph, output_data_path / "tree.graphml")

    # Store subtrees and connection statistics
    create_subtrees(graph, patient, output_data_path)


if __name__ == "__main__":
    main()
