import os
import sys

import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import networkx as nx
plt.rcParams.update({'font.size': 6})

# |>--><-><-><-><-><->-<|
# |>- Parse arguments -<|
# |>--><-><-><-><-><->-<|

try:
    source_data_path = os.path.dirname(os.path.dirname(sys.argv[1]))
    target_data_path = sys.argv[2]
    patient = os.path.basename(sys.argv[1])
except IndexError:
    print("ERROR: No source or data path provided, aborting!")
    sys.exit(1)

try:
    show_plot = sys.argv[3].lower() == "true"
except IndexError:
    show_plot = True

try:
    show_bronchus = sys.argv[4].lower() == "true"
except IndexError:
    show_bronchus = False

# |>-<-><-><-><-><-><->-<|
# |>- Define color map -<|
# |>-<-><-><-><-><-><->-<|

colors_map = {
    0: "#000000",
    1: "#bee6be",
    2: "#d6cc50",
    3: "#6478fa",
    4: "#41d741",
    5: "#fa4646",
    6: "#fa87f5",
}


# |>--><-><-><-><-><--<|
# |>- Create figures -<|
# |>--><-><-><-><-><--<|

fig = plt.figure()
ax1 = fig.add_subplot(221, projection='3d')
ax2 = fig.add_subplot(222, projection='3d')
ax3 = fig.add_subplot(223, projection='3d')
ax4 = fig.add_subplot(224, projection='3d')
fig.tight_layout()
nodes_per_axis = []

# |>-><-><-><-><-><-><-><-><-><--<|
# |>- Potentially draw bronchus -<|
# |>-><-><-><-><-><-><-><-><-><--<|

arr = np.load(os.path.join(source_data_path, "stage-20/" + patient + "/bronchus_coords_outer_shell.npy"))

xs = arr[1]
ys = arr[2]
zs = -arr[0]
colors = []

distances = {}
max_dist = 0

if show_bronchus:

    with open(os.path.join(source_data_path, "stage-03/" + patient + "/map_coord_to_distance.txt"), 'r') as dist_file:
        for line in dist_file.read().split('\n'):
            if line != '':
                coord = tuple([int(a) for a in line.split(':')[0].split(',')])
                dist = int(line.split(':')[1])
                distances[coord] = dist
                max_dist = max(max_dist, dist)

    # Normalize colors
    for key in distances.keys():
        distances[key] /= float(max_dist)

    for i in range(len(xs)):
        try:
            colors.append(1.0-distances[arr[0][i], arr[1][i], arr[2][i]])
        except:
            colors.append(0)

    ax1.scatter(xs, ys, zs, s=.1,  alpha=.2, c=colors)

# |>--><-><-><-><-><-><-><-><-><-><-><-><-><--<|
# |>- Draw split tree before post processing -<|
# |>--><-><-><-><-><-><-><-><-><-><-><-><-><--<|

# Draw coords
final_coords_file = os.path.join(source_data_path, "stage-04/" + patient + "/final_coords.npy")
if os.path.isfile(final_coords_file):
    c = np.load(final_coords_file)
    ax1.scatter(c[1], c[2], -c[0], s=5, c="red")
    nodes_per_axis.append(len(c[0]))

# Draw edges
final_edges_file = os.path.join(source_data_path, "stage-04/" + patient + "/final_edges.npy")
# print(final_edges_file)
if os.path.isfile(final_edges_file):
    e = np.load(final_edges_file)
    for i in range(len(e[0])):
        ax1.plot(e[1][i], e[2][i], -e[0][i], c='red')

# |>-><-><-><-><-><-><-><-><-><-><-><-><-><--<|
# |>- Draw split tree after post processing -<|
# |>-><-><-><-><-><-><-><-><-><-><-><-><-><--<|

axis_stage_file = [
    (ax2, "stage-05", "tree.graphml"),
    (ax3, "stage-06", "pre-recoloring.graphml"),
    (ax4, "stage-06", "tree.graphml"),
]

for ax, stage, file in axis_stage_file:
    graph = nx.read_graphml(os.path.join(source_data_path, stage, patient, file))
    nodes_per_axis.append(len(graph.nodes()))

    # Add nodes
    x = []; y = []; z = []; c = []
    for data in graph.nodes.data():
        x.append(-data[1]['x'])
        y.append(data[1]['y'])
        z.append(data[1]['z'])
        c.append(colors_map[data[1]['lobe']])
    ax.scatter(y, z, x, s=5, c=c)

    # Add edges
    x = []; y = []; z = []; c = []
    for fr, to in graph.edges():
        f = graph.nodes[fr]
        t = graph.nodes[to]
        x.append([-f['x'], -t['x']])
        y.append([f['y'], t['y']])
        z.append([f['z'], t['z']])
        # c.append([colors_map[f['lobe']], colors_map[t['lobe']]])
        c.append(colors_map[f['lobe']])
    for xe, ye, ze, ce in zip(x, y, z, c):
        ax.plot(ye, ze, xe, c=ce)


# |>-<-><-><-><-><-<|
# |>- Format axes -<|
# |>-<-><-><-><-><-<|

ax_titles = [
    (ax1, f"After creation"),
    (ax2, f"After composing"),
    (ax3, f"After node-removal (post-processing)"),
    (ax4, f"After recoloring (post-processing)"),
] 

for index, (ax, title) in enumerate(ax_titles):
    ax.set_title(title + f" (n={nodes_per_axis[index]})\n[axis in mm]")

    #ax.set_xlabel("mm")
    #ax.set_ylabel("mm")
    #ax.set_zlabel("mm")
    ax.pbaspect = [1.0, 1.0, 1.0]
    ax.autoscale()
    ax.view_init(30, 0)

    xticks=np.arange(xs.min(), xs.max(), 50)
    ax.set_xticks(xticks)
    ax.set_xticklabels((xticks/2).round())

    yticks=np.arange(ys.min(), ys.max(), 50)
    ax.set_yticks(yticks)
    ax.set_yticklabels((yticks/2).round())

    zticks=np.arange(zs.min(), zs.max(), 50)
    ax.set_zticks(zticks)
    ax.set_zticklabels(-(zticks/2).round())
    ax.zaxis.labelpad = 10

    ax.grid(False)

    ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))

# Save as image
plt.tight_layout()
plt.savefig(os.path.join(target_data_path, "splits.png"), dpi=300)

if show_plot:
    plt.show()
