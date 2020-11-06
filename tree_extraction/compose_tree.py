import sys
from pathlib import Path
from os.path import abspath
import os
import numpy as np
import networkx as nx
import math
#import psutil
from time import sleep

# checks if a file is already opened by a other process # 
#def hasHandle(fpath):
#    for proc in psutil.process_iter():
#        try:
#            for item in proc.open_files():
#                if fpath == item.path:
#                    return True
#        except Exception:
#            pass
#    return False

def getValueFromModel(coord, reducedModel):
    return reducedModel[coord[0],coord[1],coord[2]]

# returns the lobe number and the path length to this coordinate
def checkAxis(axisID , coordList, direction, reducedModel):
    maximum = np.shape(reducedModel)[axisID]
    coord = coordList[axisID]
    pathLen = 0
    #print(  "check: " + direction + " of " + str(axisID) + " coord: " + str(coord)
    #        + " maximum " + str(maximum))
    currCoordList = coordList.copy()
    while coord in range(0,maximum - 1):
        pathLen = pathLen + 1

        if direction == "positive":
            coord = coord + 1
        else:
            coord = coord - 1

        currCoordList[axisID] = coord
        #print(  "COORDS: " + str(currCoordList) + " --> "
        #        + str(getValueFromModel(currCoordList)))
        
        lobe = getValueFromModel(currCoordList, reducedModel)
        if lobe > 1:
            break
    return lobe, pathLen

# returns the lobe number where coord is (possibly) within therefore
def getLobe(coords, reducedModel):
    origCoordList = [int(round(i)) for i in coords]
    lobePaths = {}

    for i in range(0,7):
        lobePaths.update({i:8192})

    for axisID in range(0,3):
        for direction in ["positive", "negative"]:
            lobePathLen = checkAxis(axisID, origCoordList, direction, reducedModel)
            if lobePaths.get(lobePathLen[0]) > lobePathLen[1]:
                lobePaths.update({lobePathLen[0]:lobePathLen[1]})

    # if more than MAXPATHLEN pixel between split and lobe set lobe number to 0
    MAXPATHLEN = 24
    if lobePaths.get(min(lobePaths, key=lobePaths.get)) > MAXPATHLEN:
        return 0
    else:
        return min(lobePaths, key=lobePaths.get)

# returns a dict with association coordinate -> node Number 
def createNodes(graph, npCoord, npCoordAttributes, reducedModel):
    #get node coordinates
    maxCoords = np.shape(npCoord)[1]
    dicCoordsToNodes = {}
    i=0
    while i < maxCoords: 
        currCoord = (npCoord[0][i],npCoord[1][i],npCoord[2][i])
        dicCoordsToNodes.update({currCoord:i})
        #level counts from root, where root = 0
        levelVal = 8192
        if i == 0:
            levelVal = 0
       
        # first split never belongs to a lobe
        if i == 1:
            lobeVal = 0
        else:
            lobeVal = getLobe(currCoord, reducedModel)
        group_size = npCoordAttributes[i][1]

        graph.add_node(
            i,
            x = currCoord[0],
            y = currCoord[1],
            z = currCoord[2],
            lobe=lobeVal,
            level=levelVal,
            group_size=group_size
        )
        i = i+1

    return dicCoordsToNodes


def getWeight (coord1, coord2):
    return math.sqrt((coord1[0]-coord2[0])**2 + (coord1[1]-coord2[1])**2
                        + (coord1[2]-coord2[2])**2)


#returns a dict with association edge -> weight 
def createEdges(graph, npEdges, dicCoords, edgeAttributes):
    dicEdgesToWeight = {}
    #print(str(np.shape(npEdges)))
    maxEdges = np.shape(npEdges)[1]
    i=0
    while i < maxEdges:
        coord1 = (npEdges[0][i][0], npEdges[1][i][0], npEdges[2][i][0])
        coord2 = (npEdges[0][i][1], npEdges[1][i][1], npEdges[2][i][1])
        currWeight = getWeight(coord1, coord2)
        edge = (dicCoords[coord1], dicCoords[coord2])
        dicEdgesToWeight.update({edge: currWeight})
        group_sizes = ' '.join([str(attr) for attr in edgeAttributes[i]])
        graph.add_edge(
            edge[0],
            edge[1],
            weight=currWeight,
            group_sizes=group_sizes
        )
        i = i+1

    return dicEdgesToWeight


def showStats(graph, patID):
    print("\nstatistics for the graph of patient: " + patID)
    print("patient: " + patID)
    print("nodes: " + str(graph.number_of_nodes()))
    print("edges: " + str(graph.number_of_edges()))
    print()


def eraseLevelfromGraph(graph, maxLevel):
    graph = graph.copy()
    nodeList = list(nx.nodes(graph))
    startNode = min([int(a) for a in nodeList])
    print(f"(startNode={startNode})", end=' -> ')
    startLevel = graph.nodes[str(startNode)]['level']
    print(f"(level={startLevel})", end=' -> ')
    maxLevel = maxLevel + startLevel

    for node in nodeList:
        if graph.nodes[node]['level'] >= maxLevel:
            #print("node " + str(node) + " level " + str(graph.nodes[node]['level']))
            graph.remove_node(node)

    return graph

# takes a graph and set the level attribute to every node
def setLevel(inputGraph):
    graph = inputGraph.copy()
    for node in nx.nodes(graph):
        neighbors = nx.neighbors(graph,node)
        # identify parent
        if node != 0:
            parent = node 
            for possParent in neighbors:
                if graph.nodes[parent]['level'] > graph.nodes[possParent]['level']:
                    parent = possParent
            #print("parent {} -- level -> {}"
            #        .format(parent,graph.nodes[parent]['level']))
            graph.nodes[node]['level'] = graph.nodes[parent]['level'] + 1
    return graph

def getChilds(graph, node):
    childs = []
    neighbors = nx.neighbors(graph,node)
    for possChild in neighbors:
        if graph.nodes[possChild]['level'] > graph.nodes[node]['level']:
            childs.append(possChild)
    return childs

def setAttributeToNode(graph, filt, target):
    """ 
    setAttributeToNode(graph, filter, target) set or update existing atributes to
    a node filtered by filter.

    graph -> a graph
    filt = (filterAttrib,filterVal) -> Nodes whom filterAttrib has filterVal
    target = (targetAttrib,targetValue) -> set new targetValue to a nodes targetAttrib

    """
    graph = graph.copy()

    def filterForAttrib(node):
        return graph.nodes[node][filt[0]] == filt[1]
        
    view = nx.subgraph_view(graph, filter_node=filterForAttrib)

    for node in nx.nodes(view):
        graph.nodes[node][target[0]] = target[1]

    return graph


###### main ######
def main():
    try:
        sourcePath = sys.argv[1]
        targetPath = sys.argv[2]
    except IndexError:
        print("ERROR: No data or target folder found, aborting")
        sys.exit(1)

    patID = Path(sourcePath).parts[-1]

    if Path(sourcePath).is_dir and Path(targetPath).is_dir:
        coordFilePath = os.path.join(sourcePath, "final_coords.npy")
        edgesFilePath = os.path.join(sourcePath, "final_edges.npy")
        coordAttributesFilePath = os.path.join(sourcePath, "coord_attributes.npy")
        edgeAttributesFilePath = os.path.join(sourcePath, "edge_attributes.npy")
    else:
        sys.exit(1)

    #create path to reduced_model (stage-02):
    modelPath = str(Path(sourcePath).parents[1]) + "/stage-02/" + patID + "/reduced_model.npy"

    if not Path(modelPath).exists():
        print("ERROR: stage-02 needed")
        print(modelPath)
        sys.exit(-1)

    reducedModel = np.load(modelPath)

    npCoord = np.load(coordFilePath)
    npEdges = np.load(edgesFilePath)
    npCoordAttributes = np.load(coordAttributesFilePath)
    npEdgesAttributes = np.load(edgeAttributesFilePath, allow_pickle=True)

    # create empty graphs
    graph = nx.Graph(patient=int(patID))
    # compose graphs
    dicCoords = createNodes(graph, npCoord, npCoordAttributes, reducedModel)
    dicEdges = createEdges(graph, npEdges, dicCoords, npEdgesAttributes)

    # set levels to the graph
    graph = setLevel(graph)
    # level 2 does not belong to a lobe
    graph = setAttributeToNode(graph, ('level', 2), ('lobe', 0))

    showStats(graph, patID)

    nx.write_graphml(graph, os.path.join(targetPath, "tree.graphml"))

            
if __name__ == "__main__":
    main()
