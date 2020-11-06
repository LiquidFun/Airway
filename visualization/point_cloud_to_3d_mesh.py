import os

import mayavi
import numpy as np

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_folder = os.path.join(project_dir, "data/3124983/")

arr = np.load(os.path.join(data_folder, "bronchus_coords_outer_shell.npy"))

# mlab.figure()
# mlab.pipeline.mesh(arr)

# mlab.show()
