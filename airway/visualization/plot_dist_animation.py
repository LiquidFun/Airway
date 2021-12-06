import matplotlib.pyplot as plt
import numpy as np

groups = np.load("../data/3124983/map_distance_to_coords.npz")["arr_0"]
print(len(groups))

fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")

n = 100

xlim = [1000, 0]
ylim = [1000, 0]
zlim = [1000, 0]

i = 0
group_colors = []
group_coords = []
for index, group in enumerate(groups):
    xs = []
    ys = []
    zs = []
    curr_colors = []
    for t in group:
        xlim[0] = min(xlim[0], t[1])
        xlim[1] = max(xlim[1], t[1])
        ylim[0] = min(ylim[0], t[2])
        ylim[1] = max(ylim[1], t[2])
        zlim[0] = min(zlim[0], -t[0])
        zlim[1] = max(zlim[1], -t[0])
        xs.append(t[1])
        ys.append(t[2])
        zs.append(-t[0])
        curr_colors.append(1.0 - index / len(groups))
    group_coords.append((xs, ys, zs))
    group_colors.append(curr_colors)

# ax.scatter(xs, ys, zs, s=.1, c=colors, alpha=.1)

# print(path)
ax.set_xlim(xlim)
ax.set_ylim(ylim)
ax.set_zlim(zlim)
for index in range(len(group_coords)):
    # ax.cla()
    xs, ys, zs = group_coords[index]
    # ax.plot_wireframe(np.array(xs), np.array(ys), np.array(zs))
    ax.scatter(xs, ys, zs)
    ax.draw()
    plt.pause(0.00001)
# path = '../tree_extraction/tree_coords.npz'
# if os.path.isfile(path):
#     coords = np.load(path)['arr_0']
#     d = [b for a,b,c in coords]
#     e = [c for a,b,c in coords]
#     f = [-a for a,b,c in coords]
#     ax.scatter(d, e, f, s=5, c="red")
