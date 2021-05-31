"""
This script expects two command line arguments.

The first, output, is the directory where you want the output graphs for a certain
patient to be stored at, e.g. ~/Airway/stage-22/123123.

The second, input, is the directory where the graphml files for a certain
patient are stored e.g. ~/Airway/stage-05/123123.

"""

import os
import math

import igraph as ig

from airway.util.util import get_data_paths_from_args


##############################################
#  Parse the command line arguments and      #
#  store them in variables input and output  #
##############################################
output_data_path, input_data_path = get_data_paths_from_args()
print(output_data_path)

# Maps lobe number in .graph.ml-file to color in visualization
lobe_color_dict = {0: "grey", 1: "grey", 2: "#e6ff50", 3: "#6478fa", 4: "#41d741", 5: "#fa4646", 6: "#fa87f5"}

# Maps transformed edge width from .graphml-files to edge width in px
edge_width_dict = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10}

############################
#  Visualization of graphs #
############################
lobe_list = list(input_data_path.glob("*.graphml"))
for filepath in lobe_list:
    lobe = str(filepath.name)
    # Read file and convert it to directed graph
    graph = ig.Graph.Read_GraphML(str(filepath))
    graph.to_directed(mutual=False)

    # Setting vertex label, color and size
    graph.vs["label"] = graph.vs["id"]
    graph.vs["color"] = [lobe_color_dict[lobe] for lobe in graph.vs["lobe"]]
    graph.vs["size"] = 30

    # Setting edge width and disable arrow at end of edges
    # We found 271 as maximum edge weight
    graph.es["width"] = [
        edge_width_dict[math.floor(int(element) / 27)] if element < 270 else edge_width_dict[9]
        for element in graph.es["weight"]
    ]
    graph.es["arrow_size"] = 0

    # Retrieving the tree's roots
    roots = [0]
    # Retrieving possible multiple roots in lobes
    if lobe.startswith("lobe"):
        roots = [index for index in range(0, len(graph.vs)) if graph.degree(index, mode="in") == 0 or index == 0]

    # Layout and draw the graph
    layout = graph.layout_reingold_tilford(root=roots)
    picture_size = (800, 480)
    if lobe.startswith("tree"):
        number_of_nodes = len(graph.vs)
        picture_size = (2000 + 3 * number_of_nodes, 1000 + number_of_nodes)  # (3500,1500)
    ig.plot(graph, os.path.join(output_data_path, lobe) + ".png", layout=layout, bbox=picture_size)
