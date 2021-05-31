import sys

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

from airway.util.parsing import parse_map_coord_to_distance
from airway.util.util import get_data_paths_from_args

plt.rcParams.update({"font.size": 7})

# |>--><-><-><-><-><->-<|
# |>- Parse arguments -<|
# |>--><-><-><-><-><->-<|

(
    output_data_path,
    bronchus_shell_data_path,
    map_coord_to_dist_data_path,
    final_coords_data_path,
    pre_post_processing_data_path,
    post_post_processing_data_path,
) = get_data_paths_from_args(inputs=5)

try:
    show_plot = sys.argv[7].lower() == "true"
except IndexError:
    show_plot = True

try:
    show_bronchus = sys.argv[8].lower() == "true"
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
    7: "#0000ff",
    8: "#ff0000",
}

# |>--><-><-><-><-><--<|
# |>- Create figures -<|
# |>--><-><-><-><-><--<|

fig = plt.figure()
ax1 = fig.add_subplot(221, projection="3d")
ax2 = fig.add_subplot(222, projection="3d")
ax3 = fig.add_subplot(223, projection="3d")
ax4 = fig.add_subplot(224, projection="3d")
fig.tight_layout()
nodes_per_axis = []

# |>-><-><-><-><-><-><-><-><-><--<|
# |>- Potentially draw bronchus -<|
# |>-><-><-><-><-><-><-><-><-><--<|

arr = np.load(bronchus_shell_data_path / "bronchus_coords_outer_shell.npz")["arr_0"]

xs = arr[1]
ys = arr[2]
zs = -arr[0]
colors = []

distances = {}
max_dist = 0

if show_bronchus:
    distances = parse_map_coord_to_distance(map_coord_to_dist_data_path / "map_coord_to_distance.txt")
    max_dist = max(distances.values())

    # Normalize colors
    for key in distances.keys():
        distances[key] /= float(max_dist)

    for i in range(len(xs)):
        try:
            colors.append(1.0 - distances[arr[0][i], arr[1][i], arr[2][i]])
        except:
            colors.append(0)

    ax1.scatter(xs, ys, zs, s=0.1, alpha=0.2, c=colors)

# |>--><-><-><-><-><-><-><-><-><-><-><-><-><--<|
# |>- Draw split tree before post processing -<|
# |>--><-><-><-><-><-><-><-><-><-><-><-><-><--<|

# Draw coords
final_coords_file = final_coords_data_path / "final_coords.npz"
if final_coords_file.exists():
    c = np.load(final_coords_file)["arr_0"]
    ax1.scatter(c[1], c[2], -c[0], s=1, c="red")
    nodes_per_axis.append(len(c[0]))

# Draw edges
final_edges_file = final_coords_data_path / "final_edges.npz"
# print(final_edges_file)
if final_edges_file.exists():
    e = np.load(final_edges_file)["arr_0"]
    for i in range(len(e[0])):
        ax1.plot(e[1][i], e[2][i], -e[0][i], c="red", linewidth=0.5)

# |>-><-><-><-><-><-><-><-><-><-><-><-><-><--<|
# |>- Draw split tree after post processing -<|
# |>-><-><-><-><-><-><-><-><-><-><-><-><-><--<|

axis_stage_file = [
    (ax2, pre_post_processing_data_path / "tree.graphml"),
    (ax3, post_post_processing_data_path / "pre-recoloring.graphml"),
    (ax4, post_post_processing_data_path / "tree.graphml"),
]

for ax, file in axis_stage_file:
    if not file.exists():
        print(f"ERROR: File {file} does not exist!")
        sys.exit(1)
    print(str(file))
    graph = nx.read_graphml(file)
    nodes_per_axis.append(len(graph.nodes()))

    # Add nodes
    x = []
    y = []
    z = []
    c = []
    for data in graph.nodes.data():
        x.append(-data[1]["x"])
        y.append(data[1]["y"])
        z.append(data[1]["z"])
        c.append(colors_map[data[1]["lobe"]])
    ax.scatter(y, z, x, s=1, c=c)

    # Add edges
    x = []
    y = []
    z = []
    c = []
    for fr, to in graph.edges():
        f = graph.nodes[fr]
        t = graph.nodes[to]
        x.append([-f["x"], -t["x"]])
        y.append([f["y"], t["y"]])
        z.append([f["z"], t["z"]])
        # c.append([colors_map[f['lobe']], colors_map[t['lobe']]])
        c.append(colors_map[f["lobe"]])
    for xe, ye, ze, ce in zip(x, y, z, c):
        ax.plot(ye, ze, xe, c=ce, linewidth=0.5)

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

    # ax.set_xlabel("mm")
    # ax.set_ylabel("mm")
    # ax.set_zlabel("mm")
    ax.pbaspect = [1.0, 1.0, 1.0]
    ax.autoscale()
    ax.view_init(30, 0)

    xticks = np.arange(xs.min(), xs.max(), 50)
    ax.set_xticks(xticks)
    ax.set_xticklabels((xticks / 2).round())

    yticks = np.arange(ys.min(), ys.max(), 50)
    ax.set_yticks(yticks)
    ax.set_yticklabels((yticks / 2).round())

    zticks = np.arange(zs.min(), zs.max(), 50)
    ax.set_zticks(zticks)
    ax.set_zticklabels(-(zticks / 2).round())
    ax.zaxis.labelpad = 10

    # Comment these for a clean view
    # ax.axis("off")
    ax.set_title(f"{title} (n={nodes_per_axis[index]})\n[axis in mm]", y=0.85)

    ax.grid(False)

    ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))

plt.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)

for index, (ax, _) in enumerate(ax_titles):
    extent = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(output_data_path / f"{index}_progression.png", bbox_inches=extent, dpi=300, transparent=True)


# Save as image
# plt.tight_layout(pad=10)
plt.savefig(output_data_path / "splits.png", dpi=300, transparent=True)

if show_plot:
    plt.show()
