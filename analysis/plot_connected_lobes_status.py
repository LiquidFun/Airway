#!/usr/bin/env python3

import os
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

def build_connection_matrix(stage7_path):
    """
    Reads all lobe-trees an ckecking if a lobe is connected (all nodes are (indirectly)
    connected).

    Returns a dictionary patID -> [status_lobe-2, ..., status_lobe-6], where
    status == 0 -> not connected
    status == 1 -> connected
    status == 2 -> not all lobes available (set for all lobes)
    """
    patient_dirs = stage7_path.glob('*')
    patient_dirs = [pat_dir.name for pat_dir in patient_dirs if pat_dir.is_dir()]

    graph_dict = {}
    print(graph_dict)
    for pat in patient_dirs:
        graph_files = sorted(list(stage7_path.joinpath(pat).glob('*lobe*.graphml')))
        conn_status = []
        for graph_file in graph_files:
            lobe_graph = nx.read_graphml(graph_file)
            conn_status.append(int(nx.is_connected(lobe_graph)))
        if len(conn_status) < 5:
            conn_status = [2 for i in range(2,7)]
        graph_dict.update({str(pat):conn_status})
    
    return graph_dict

def plotConnectionStatus(heatmap_path, graph_dict):
    """
    The prebuild connection-matrix is used to plot a heat map of the connection status
    """

    lobes = [   'LeftLowerLobe', 'LeftUpperLobe', 'RightLowerLobe', 'RightMiddleLobe',
                'RightUpperLobe']
    patients = [pat for pat in graph_dict.keys()]
    patients = sorted(patients)
    connMatrix = [graph_dict.get(pat) for pat in patients]

    print('plotConnectionStatus for ' + str(len(patients)) + ' patients')

    amntUncon = 0
    amntConPat = 0
    pID = 0
    print("\npatients where all lobes are connected:")
    for line in connMatrix:
        amntUncon += line.count(0)
        if line.count(1) == 5:
            #print("{}".format(patients[pID]))
            amntConPat += 1
        pID += 1

    print('unconnected lobes: {}/{} (#perfect patients: {})'
            .format(amntUncon,len(connMatrix)*5,amntConPat))

    fig, ax = plt.subplots(figsize=(3.5,12))
    im = ax.imshow(connMatrix,aspect=0.5)

    ax.set_xticks(np.arange(len(lobes)))
    ax.set_yticks(np.arange(len(patients)))
    ax.set_xticklabels(lobes)
    ax.set_yticklabels([f"{i+1}. {p}" for i, p in enumerate(patients)])
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')

    ax.set_title('unconnected lobe graphs: {}/{}\n({}%)'
            .format(amntUncon,len(connMatrix)*5,
                    round(amntUncon/(len(connMatrix)*5)*100,2)))
    fig.tight_layout()
    plt.savefig(heatmap_path, dpi=200)

def main():
    """
    Executes procedures in right order
    """

    # path to stage-07
    stage7 = Path(sys.argv[1] + "/stage-07")
    if not Path(stage7).is_dir():
        sys.err.write('stage-07 missing: Please calculate stage 7 first.')
        sys.exit(-1)

    # target directory
    target_path = Path(sys.argv[1] + "/stage-10")
    if not target_path.is_dir():
        target_path.mkdir()

    lobe_graph_dict = build_connection_matrix(stage7)
    plotConnectionStatus(target_path.joinpath('connection-status.png'),lobe_graph_dict)

if __name__ == "__main__":
    main()

