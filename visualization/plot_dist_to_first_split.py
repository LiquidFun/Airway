import os
import sys

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
# plt.rcParams.update({'font.size': 6})

# |>--><-><-><-><-><->-<|
# |>- Parse arguments -<|
# |>--><-><-><-><-><->-<|

try:
    source_data_path = os.path.join(sys.argv[1], 'stage-07')
    target_data_path = os.path.join(sys.argv[1], 'stage-10/distances_to_first_split.png')
    patient = os.path.basename(sys.argv[1])
except IndexError:
    print("ERROR: No source or data path provided, aborting!")
    sys.exit(1)

try:
    show_plot = sys.argv[2].lower() == "true"
except IndexError:
    show_plot = True



# |>--><-><-><-><-><--<|
# |>- Create figures -<|
# |>--><-><-><-><-><--<|

fig = plt.figure()
ax1 = fig.add_subplot(111)


# |>-><-><-><-><-><-><-><-><-><-><-><-><-><--<|
# |>- Draw split tree after post processing -<|
# |>-><-><-><-><-><-><-><-><-><-><-><-><-><--<|

root_children_count = {}
weights = []
names = []
for index, patient in enumerate(sorted(os.listdir(source_data_path))):
    graphml_path = os.path.join(source_data_path, patient, "tree.graphml")
    if os.path.exists(graphml_path):
        graph = nx.read_graphml(graphml_path)
        # assert len(graph["0"]) <= 1, "ERROR: More than 1 edge from root node"
        l = len(graph['0'])
        if l not in root_children_count:
            root_children_count[l] = 0
        root_children_count[l] += 1


        # print(patient, end=', ')
        # print(list(graph["0"]), end=', ')
        weights.append(max([graph["0"][adj]["weight"] for adj in graph["0"]])/2)
        names.append(f"{index+1}. {patient}")

ind = np.arange(len(weights))


for length, count in root_children_count.items():
    print(f"There are {count} root nodes which have {length} children.")

print(f"Note that every root node should only have 1 child.")

# |>-<-><-><-><->-<|
# |>- Plot split -<|
# |>-<-><-><-><->-<|

plt.title("Length from Top to First Split per Patient in mm")
plt.ylabel("mm")
plt.xlabel("Patient IDs")
plt.xticks(ind, names, rotation="vertical", fontsize=6)
bar = plt.bar(ind, weights)

for rect in bar:
    height = rect.get_height()
    ax1.annotate(
        '{}'.format(int(round(height))),
        xy=(rect.get_x() + rect.get_width() / 2, height),
        xytext=(0, 3),  # 3 points vertical offset
        textcoords="offset points",
        ha='center',
        va='bottom',
        fontsize=6,
    )
plt.savefig(target_data_path)
if show_plot:
    plt.show()
