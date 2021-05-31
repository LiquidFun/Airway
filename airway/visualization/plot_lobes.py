import os

import numpy as np
import matplotlib.pyplot as plt

from airway.util.util import get_data_paths_from_args

output_data_path, input_data_path, stage4 = get_data_paths_from_args(inputs=2)

arr = np.load(input_data_path / "bronchus_coords_outer_shell.npz")["arr_0"]

fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")

patient = input_data_path.parent

colors_map = {
    1: "#bee6be",
    2: "#e6ff50",
    3: "#6478fa",
    4: "#41d741",
    5: "#fa4646",
    6: "#fa87f5",
    7: "#0000ff",
    8: "#ff0000",
}

xs = arr[1]
ys = arr[2]
zs = -arr[0]
colors = []
# colors = arr[3]/6.0
for a in arr[3]:
    colors.append(colors_map[a])

distances = {}
max_dist = 0

# Draw coords
final_coords_file = stage4 / "final_coords.npz"
if os.path.isfile(final_coords_file):
    c = np.load(final_coords_file)["arr_0"]
    ax.scatter(c[1], c[2], -c[0], s=10, c="red")

# Draw edges
final_edges_file = stage4 / "final_edges.npz"
if os.path.isfile(final_edges_file):
    e = np.load(final_edges_file)["arr_0"]
    for i in range(len(e[0])):
        ax.plot(e[1][i], e[2][i], -e[0][i], c="red")

ax.set_xlabel("mm")
ax.set_ylabel("mm")
ax.set_zlabel("mm")

xticks = np.arange(xs.min(), xs.max(), 50)
ax.set_xticks(xticks)
ax.set_xticklabels((xticks / 2).round())

yticks = np.arange(ys.min(), ys.max(), 50)
ax.set_yticks(yticks)
ax.set_yticklabels((yticks / 2).round())

zticks = np.arange(zs.min(), zs.max(), 50)
ax.set_zticks(zticks)
ax.set_zticklabels(-(zticks / 2).round())

ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
# ax.set_yticks(np.arange(ys.min(), ys.max()/2, 50))
# ax.set_zticks(np.arange(zs.min(), zs.max()/2, 50))
# ax.set_yticks(ticks[1])
# ax.set_zticks(ticks[2])

ax.grid(False)
ax.scatter(xs, ys, zs, s=0.03, c=colors, alpha=0.08)

# plt.savefig(output_data_path / "bronchus_splits.png")
plt.show()
