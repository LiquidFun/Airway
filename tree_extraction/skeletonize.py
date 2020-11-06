from skimage.morphology import skeletonize
from skimage import data
import matplotlib.pyplot as plt
from skimage.util import invert
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 unused import

model = np.load("path here")

# perform skeletonization
skeleton = skeletonize(model)

# display results

# print(set(skeleton.flatten()))
np.save("skeleton.npy", skeleton)

# plt.imshow(skeleton, cmap=plt.cm.gray)
fig = plt.figure()
ax = fig.gca(projection='3d')
ax.voxels(skeleton, edgecolor='k')

plt.show()
