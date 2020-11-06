#!/usr/bin/env python3
import sys
import csv 
from pathlib import Path

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size': 4})

def getGraphEditDistance():
    # calculate the graph edit distance beetween all trees
    # okay this takes extreme long -> only for small trees nodes(tree)=12 max
    gedDict = {}
    for pa in patIDList:
        for pb in patIDList:
            if pa == pb:
                break
            print("\ncalc ged from " + str(pa) + " - " + str(pb))
            print(
                "nodes: " 
                + str(treeDict[pa].number_of_nodes())
                + " <---> " 
                + str(treeDict[pb].number_of_nodes())
            )
            key = pa + "~" + pb
            gedDict.update({key: nx.graph_edit_distance(treeDict[pa], treeDict[pb])})
            print(key + " --> " + str(treeDict.get(key)))

def longestPathLength(tree):
    d = nx.shortest_path_length(tree, source="0")
    return max([length for target,length in d.items()])

def maximumINdependentSetLength(tree):
    d = nx.maximal_independent_set(tree)
    return len(d)

def createGeneralTreeStatisticsFile(csvPath):
    if Path.exists(Path(csvPath)):
        print("WARNING: File was overwritten: " + csvPath)
    else:
        Path(csvPath).touch(exist_ok=False)

    with open(csvPath, 'w', newline='') as f:
        csvWriter = csv.writer(f)

        csvWriter.writerow([
            'patient',
            'nodes',
            'edges',
            'longest_path_length',
            'maximum_independent_set_length'
        ])
        statList = []
        for key, tree in treeDict.items():
            currRow = []
            currRow.append(str(key))
            currRow.append(tree.number_of_nodes())
            currRow.append(tree.number_of_edges())
            currRow.append(longestPathLength(tree))
            currRow.append(maximumINdependentSetLength(tree))
            statList.append(currRow)

        csvWriter.writerows(statList)

def perLobeStatistics():
    #closures
    def nodeQuotient():
        g = treeDict.get(str(graph.graph['patient'])) 
        try:
            return g.number_of_nodes() / graph.number_of_nodes()  
        except:
            return 0

    def edgesQuotient():
        g = treeDict.get(str(graph.graph['patient'])) 
        try:
            return g.number_of_edges() / graph.number_of_edges() 
        except:
            return 0

    for lobe in range (2,7):
        paths = list(Path(stage7).glob('**/lobe-' + str(lobe) + '*.graphml'))

        with open(str(targetPath) + '/lobe-' + str(lobe) + '.csv', 'w', newline='') as f:
            csvWriter = csv.writer(f)
            csvWriter.writerow([
                'patient',
                'nodes',
                'edges',
                'nodeQuotient',
                'edgeQuotient'
            ])
            for path in paths:
                graph = nx.read_graphml(path)
                csvWriter.writerow([
                    graph.graph['patient'],
                    graph.number_of_nodes(),
                    graph.number_of_edges(),
                    nodeQuotient(),
                    edgesQuotient()
                ])

def upperLeftLobeDistanceAnalysis(plot_path, csv_path):

    #setup path to lobe.graphml files
    upperLeftLobeList = Path(stage7).glob('*')
    upperLeftLobeList = [
        Path(str(patDir) + "/lobe-3-" + str(patDir.parts[-1]) + ".graphml")
        for patDir in upperLeftLobeList
        if patDir.is_dir() and (Path(str(patDir) + "/lobe-3-" + str(patDir.parts[-1]) + ".graphml")).is_file()
    ]
    #print(len(upperLeftLobeList))

    #fill a dicitionary with lobe graphs
    leftLobeDict = {}
    for lobePath in upperLeftLobeList:
        leftLobeDict.update({lobePath.parts[-2]:nx.read_graphml(lobePath)})
    print("Found " +str(len(leftLobeDict)) +" upper left lobes for analysis.")
    count = len(leftLobeDict)
    notTreeList = []
    lobeTreeDict = {}
    #iterate over the lobes 
    for key, lobe in leftLobeDict.items():
        #print (key, nx.get_node_attributes(lobe, 'level'))

        #check if there are lobes not beeing a tree
        if not nx.is_tree(lobe):
            count = count - 1
            notTreeList.append(key)
        else:
            lobeTreeDict.update({key: lobe})

    print("Detected trees: " + str(count) + "/" + str(len(leftLobeDict)))
    print("Patients whose lobes are not a tree: ")
    for tree in notTreeList:
        print(tree)

    print("Classifying left upper lobes:")
    distanceDict = {}
    classifiedCounter = 0
    for key, lobe in leftLobeDict.items():
        nodelist = []
        for node, data in lobe.nodes.items():
            nodelist.append(int(node))
        distanceValue = getDistanceValue(lobe, nodelist, key)
        if distanceValue != (-1, -1):
            distanceDict[key] = distanceValue
        if distanceValue == (0, 0):
            classifiedCounter = classifiedCounter + 1
        print("----------------------------------------------------------------")

    print("Successfully classified " + str(classifiedCounter) + " lobes as Type A.")

    print("Found " + str(len(distanceDict) - classifiedCounter) + " potential candidates for Type B.")
    #print (distanceDict)
    #print (len(distanceDict))
    plotDistanceValues(distanceDict, plot_path)
    export_classifcation_csv(distanceDict, csv_path)

def getDistanceValue(lobe, nodelist, key):
    root = min(nodelist)
    neighbourlist = list(nx.neighbors(lobe, str(root)))
    for neighbour in neighbourlist:
        if nx.get_node_attributes(lobe, 'level')[neighbour] < nx.get_node_attributes(lobe, 'level')[str(root)]:
            neighbourlist.remove(neighbour)
    neighbourcount = len(neighbourlist)
    if neighbourcount == 3:
        print(key, "classified as Type A")
        distValue = (0,0)
        print (neighbourlist)
    elif neighbourcount < 2:
        print(key, "Warning: less than 2 neighbours detected. Iterating....")
        nodelist.remove(root)
        if len(nodelist) != 0:
            distValue = getDistanceValue(lobe, nodelist, key)
        else :
            distValue = (-1,-1)
    elif neighbourcount > 3:
        print(key, "Error: more than 3 neigbours detected.")
        for neighbour in neighbourlist:
            length = lobe[str(root)][neighbour]['weight']
            print("Length: " +str(length))
        distValue = (-1,-1)
    elif neighbourcount == 2:
        print(key, "2 neighbours detected")
        weightList = []
        for neighbour in neighbourlist:
            length = lobe[str(root)][neighbour]['weight']
            print("Length: " + str(length))
            weightList.append(length)
        distValue = (weightList[0], weightList[1])

    return distValue

def plotDistanceValues(distanceDict, path):
    patients = []
    length1List = []
    length2List = []
    for key, (length1, length2) in distanceDict.items():
        patients.append(key)
        length1List.append(int(length1))
        length2List.append(int(length2))
    
    x = np.arange(len(patients))
    width = 0.35
    fig, ax = plt.subplots()
    bars1 = ax.bar(x - width/2, length1List, width, label="Length1")
    bars2 = ax.bar(x + width/2, length2List, width, label="Length2")

    ax.set_ylabel('Length')
    ax.set_title('Length of edges of type B candidates')
    ax.set_xticks(x)
    ax.set_xticklabels(patients)
    ax.legend()
    autolabel (bars1, ax)
    autolabel (bars2, ax)
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')
    fig.tight_layout()

    #plt.show()
    plt.savefig(path, dpi=200)

def autolabel(bars, ax):
    for bar in bars:
        height = bar.get_height()
        ax.annotate('{}'.format(height), xy = (bar.get_x() + bar.get_width() / 2, height), xytext = (0,3), textcoords = "offset points", ha = 'center', va = 'bottom')

def export_classifcation_csv(distanceDict, csv_path):
    if Path.exists(Path(csv_path)):
        print("WARNING: File was overwritten: " + csv_path)
    else:
        Path(csv_path).touch(exist_ok=False)

    with open(csv_path, 'w', newline='') as f:
        csv_writer = csv.writer(f)

        csv_writer.writerow([
            'patient',
            'classification',
            'length_1',
            'length_2',
        ])

        classification = []
        for key, (l1, l2) in distanceDict.items():
            curr_row = []
            curr_row.append(str(key))
            curr_row.append(get_classifcation(l1,l2))
            curr_row.append(l1)
            curr_row.append(l2)
            classification.append(curr_row)
            
        csv_writer.writerows(classification)  
        
def get_classifcation (l1,l2):
    if (l1,l2) == (0,0):
        return 'A'
    else:
        return 'B'
    
# path to stage-07
stage7 = sys.argv[1] + "/stage-07"
if not Path(stage7).is_dir():
    print('stage-07 missing: Please calculate stage 7 first.')
    sys.exit(-1)

# target directory
targetPath = Path(sys.argv[1] + "/stage-10")
targetPath.mkdir(exist_ok=True)


# paths to all trees
pathList = Path(stage7).glob('*')
pathList = [ Path(str(patDir) + "/tree.graphml") 
             for patDir in pathList if patDir.is_dir()]

lobeIDToString = {
    2: "LeftLowerLobe",
    3: "LeftUpperLobe",
    4: "RightLowerLobe",
    5: "RightMiddleLobe",
    6: "RightUpperLobe",
}


# list of all patientIDs
patIDList = [patDir.parts[-2] for patDir in pathList if patDir.parents[0].is_dir()]

#load all trees in dictionary (patID -> nx.graph)
treeDict = {}
for treePath in pathList:
    treeDict.update({treePath.parts[-2]:nx.read_graphml(treePath)})
print("loaded trees: " + str(len(treeDict.keys())))

# analysers
createGeneralTreeStatisticsFile(str(targetPath) + '/csvTREE.csv')
perLobeStatistics()
upperLeftLobeDistanceAnalysis(str(targetPath) + '/type-B-edge-lengths.png', str(targetPath) + '/classification.csv')

