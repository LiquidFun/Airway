import numpy as np
from matplotlib import pyplot as plt

arrs = np.load("../data/P0/dist_to_coords.npz")["arr_0"]

a = [len(arr) for arr in arrs]

plt.plot(range(len(a)), a)
plt.xlabel("Manhattan distance from start pixel at the top of the lungs")
plt.ylabel("Number of pixels matching the criteria")
plt.title("Number of pixels for each distance from the start pixel")
plt.savefig("./images/pixel-count-per-distance.png")
plt.show()
