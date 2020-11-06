"""Module to generate .obj file from splits (places cubes where splits are)
"""
import os
import sys

import networkx as nx
import numpy as np

from gen_obj import normalize

def gen_split_obj(target_data_path, graph):

    vertices = []
    edge_vertices = []

    for node in graph.nodes.data():
        n = node[1]
        x, y, z = n['x'], n['y'], n['z']
        di = [-1, 1]
        for x_ in di:
            for y_ in di:
                for z_ in di:
                    vertices.append([-(z+z_), -(x+x_), y+y_])

    for node, successors in nx.bfs_successors(graph, '0'):
        for succ in successors:
            for curr in [node, succ]:
                n = graph.nodes[curr]
                x, y, z = n['x'], n['y'], n['z']
                for i in [-0.5, 0.5]:
                    edge_vertices.append((-(z+i), -(x+i), y+i))

    vertices = normalize(vertices)
    edge_vertices = normalize(edge_vertices)

    with open(target_data_path, 'w') as file:
        file.write("# Vertices\n")
        for x, y, z in vertices:
            file.write(f"v {x:.3f} {y:.3f} {z:.3f}\n")
        file.write("# Edge Vertices\n")
        for x, y, z in edge_vertices:
            file.write(f"v {x:.3f} {y:.3f} {z:.3f}\n")
        file.write("\n# Faces\n")
        for i in range(0, len(vertices), 8):
            file.write(f"f {i+1} {i+3} {i+7} {i+5}\n")
            file.write(f"f {i+2} {i+4} {i+8} {i+6}\n")
            file.write(f"f {i+1} {i+2} {i+6} {i+5}\n")
            file.write(f"f {i+3} {i+4} {i+8} {i+7}\n")
            file.write(f"f {i+1} {i+2} {i+4} {i+3}\n")
            file.write(f"f {i+5} {i+6} {i+8} {i+7}\n")

        file.write("# Edge faces\n")
        for i in range(0, len(edge_vertices), 4):
            j = i + len(vertices) + 1
            file.write(f"f {j} {j+1} {j+3} {j+2}\n")

def main():
    try:
        source_data_path = sys.argv[1]
        target_data_path = sys.argv[2]
    except IndexError:
        print("ERROR: No source or data path provided, aborting!")
        sys.exit(1)

    if not os.path.exists(target_data_path):
        os.makedirs(target_data_path)

    graph = nx.read_graphml(os.path.join(source_data_path, "tree.graphml"))
    gen_split_obj(os.path.join(target_data_path, "splits.obj"), graph)



if __name__ == "__main__":
    main()
