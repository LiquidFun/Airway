import os
import sys

import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

try:
    source_data_path = os.path.dirname(os.path.dirname(sys.argv[1]))
    target_data_path = sys.argv[2]
    patient = os.path.basename(sys.argv[1])
except IndexError:
    print("ERROR: No source or data path provided, aborting!")
    sys.exit(1)

arr = np.load(os.path.join(source_data_path, f"stage-20/{patient}/full_lung_outer_shell_coords.npy"))
# print(arr)
# This only shows lobes where the id is 2 or 3 
# index = np.where(np.logical_or(arr[3]==2, arr[3]==3))
# print(index)
# arr = np.array([arr[0][index], 
#         arr[1][index], 
#         arr[2][index], 
#         arr[3][index]])
# print(arr)

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

colors_map = {
    1: "#bee6be",
    2: "#e6ff50",
    3: "#6478fa",
    4: "#41d741",
    5: "#fa4646",
    6: "#fa87f5",
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
final_coords_file = os.path.join(source_data_path, f"stage-04/{patient}/final_coords.npy")
if os.path.isfile(final_coords_file):
    c = np.load(final_coords_file)
    ax.scatter(c[1], c[2], -c[0], s=10, c="red")

# Draw edges
final_edges_file = os.path.join(source_data_path, f"stage-04/{patient}/final_edges.npy")
# print(final_edges_file)
if os.path.isfile(final_edges_file):
    e = np.load(final_edges_file)
    # print(e)
    for i in range(len(e[0])):
        ax.plot(e[1][i], e[2][i], -e[0][i], c='red')

ax.set_xlabel("mm")
ax.set_ylabel("mm")
ax.set_zlabel("mm")

xticks=np.arange(xs.min(), xs.max(), 50)
ax.set_xticks(xticks)
ax.set_xticklabels((xticks/2).round())

yticks=np.arange(ys.min(), ys.max(), 50)
ax.set_yticks(yticks)
ax.set_yticklabels((yticks/2).round())

zticks=np.arange(zs.min(), zs.max(), 50)
ax.set_zticks(zticks)
ax.set_zticklabels(-(zticks/2).round())


ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
# ax.set_yticks(np.arange(ys.min(), ys.max()/2, 50))
# ax.set_zticks(np.arange(zs.min(), zs.max()/2, 50))
# ax.set_yticks(ticks[1])
# ax.set_zticks(ticks[2])

ax.grid(False)
ax.scatter(xs, ys, zs, s=.03, c=colors, alpha=.08)

plt.show()
