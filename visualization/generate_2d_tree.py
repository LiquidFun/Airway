'''
This script espects two command line arguments.

The first, input, is the directory where the graphml files for a certain
patient are stored e.g. ~/Airway/stage-05/123123.

The second, output, is the directory where you want the output graphs for a certain
patient to be stored at, e.g. ~/Airway/stage-22/123123.
'''

import os
import sys
import argparse as arg
from pathlib import Path
import glob
import igraph as ig
import math


################################################
##  Parse the command line arguments and      ##
##  store them in variables input and output  ##
################################################
parser = arg.ArgumentParser()
parser.add_argument('input', help='Path to patient directory: e.g. /Airway/stage-07/123123', type=Path)
parser.add_argument('output', help='Path to output directory: e.g. /Airway/stage-23/123123', type=Path)

if len(sys.argv) > 3:
    print("ERROR: Too many arguments")
    sys.exit(1)

parsed_arguments = parser.parse_args()
input = parsed_arguments.input
output = parsed_arguments.output

# Maps lobe number in .graph.ml-file to color in visualization
lobe_color_dict = {
    0: "grey",
    1: "grey",
    2: "#e6ff50",
    3: "#6478fa",
    4: "#41d741",
    5: "#fa4646",
    6: "#fa87f5"
}

# Maps transformed edge width from .graphml-files to edge width in px
edge_width_dict = {
    0: 1,
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
    6: 7,
    7: 8,
    8: 9,
    9: 10
}

##############################
##  Visualization of graphs ##
##############################
lobe_list = list(input.glob('*.graphml'))
for filepath in lobe_list:
    lobe = str(filepath.name)
    # Read file and convert it to diected graph
    #graph = ig.Graph.Read_GraphML(os.path.join(input, filepath[0]))
    graph = ig.Graph.Read_GraphML(str(filepath))
    graph.to_directed(mutual=False)

    # Setting vertex label, color and size
    graph.vs["label"] = graph.vs["id"]
    graph.vs["color"] = [lobe_color_dict[lobe] for lobe in graph.vs["lobe"]]
    graph.vs["size"] = 30

    # Setting edge width and disable arrow at end of edges
    # We found 271 as maximum edge weigth
    graph.es["width"] = [edge_width_dict[math.floor(int(element) / 27)] if element < 270 else edge_width_dict[9] for
                         element in graph.es["weight"]]
    graph.es["arrow_size"] = 0

    # Retrieving the tree's roots
    roots = [0]
    # Retrieving possible multiple roots in lobes
    if lobe.startswith('lobe'):
        roots = [index for index in range(0, len(graph.vs)) if graph.degree(index, mode="in") == 0 or index == 0]

    # Layout and draw the graph
    layout = graph.layout_reingold_tilford(root=roots)
    picture_size = (800, 480)
    if lobe.startswith('tree'):
        number_of_nodes = len(graph.vs)
        picture_size = (2000 + 3 * number_of_nodes, 1000 + number_of_nodes)  # (3500,1500)
    ig.plot(graph, os.path.join(output, lobe) + '.png', layout=layout, bbox=picture_size)


#Alle Patienten
'''
parser = arg.ArgumentParser()
parser.add_argument('input', help='Path to patient directory: e.g. /Airway/stage-05/123123', type=Path)
parser.add_argument('output', help='Path to output directory: e.g. /Airway/stage-22/123123', type=Path)

if len(sys.argv) > 3:
    print("ERROR: Too many arguments")
    sys.exit(1)

parsed_arguments = parser.parse_args()
input = parsed_arguments.input
output = parsed_arguments.output


patient_input_folder = [d for d in os.listdir(input) if os.path.isdir(os.path.join(input, d))]


lobe_color_dict = {
    0: "grey",
    1: "grey",
    2: "yellow",
    3: "blue",
    4: "green",
    5: "red",
    6: "purple"
}

edge_width_dict = {
    0: 1,
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
    6: 7,
    7: 8,
    8: 9,
    9: 10
}



lobe_list = ['tree','simplified-tree', 'lobe-2', 'lobe-3', 'lobe-4', 'lobe-5', 'lobe-6']
for patient in patient_input_folder:
    patient_output_folder = os.path.join(output,patient)
    if not os.path.isdir(patient_output_folder):
        os.mkdir(patient_output_folder)
    input_path = os.path.join(input,patient)

    os.chdir(input_path)
    for lobe in lobe_list:
        filename = glob.glob(lobe+'*')
        if filename:
            graph = ig.Graph.Read_GraphML(os.path.join(input_path, filename[0]))
            graph.to_directed(mutual=False)
            graph.vs["label"] = graph.vs["id"]
            graph.vs["color"] = [lobe_color_dict[lobe] for lobe in graph.vs["lobe"]]
            graph.vs["size"] = 30
            graph.es["arrow_size"] = 0
            graph.es["width"] = [edge_width_dict[math.floor(int(element)/27)] if element < 270 else edge_width_dict[9] for element in graph.es["weight"]]
            roots = [0]
            if lobe in ['lobe-2', 'lobe-3', 'lobe-4', 'lobe-5', 'lobe-6']:
                roots = [index for index in range(0, len(graph.vs)) if graph.degree(index, mode="in")==0 or index==0]
            layout = graph.layout_reingold_tilford(root = roots)
            picture_size = (800,480)
            if lobe in ['tree', 'simplified-tree']:
                number_of_nodes = len(graph.vs)
                picture_size = (2000+3*number_of_nodes,1000+number_of_nodes) #(3500,1500)
            ig.plot(graph, os.path.join(patient_output_folder, lobe)+'.png', layout=layout, bbox=picture_size)'''
