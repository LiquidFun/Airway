import os
import sys
import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


if len(sys.argv) >= 3:
    source_data_path = sys.argv[1]
    print(source_data_path)
    target_data_path = sys.argv[2]
else:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_data_path = os.path.join(project_dir, "data/3124983/")

reduced_data_file = os.path.join(source_data_path, "reduced_model.npy")
data = np.load(reduced_data_file)

print("start: writing coordinates to " + target_data_path)

model = np.append(np.where(data == 1), ([data[data == 1]]), axis=0)
print(len(model[0]))
np.save(os.path.join(target_data_path, "bronchus_coords"), model)


model_adjacency_sum = np.sum([np.roll(data, i, axis=ax) for i in [-1,1] for ax in [0,1,2]], axis=0)
model_outer_shell_only = np.where(np.logical_and(data == 1, model_adjacency_sum != 6))
model_outer_shell_only = np.append(model_outer_shell_only, [data[np.logical_and(data == 1, model_adjacency_sum != 6)]], axis=0)
print(len(model_outer_shell_only[0]))
np.save(os.path.join(target_data_path, "bronchus_coords_outer_shell"), np.array(model_outer_shell_only))


# full_model = np.where(data >= 1)
# full_model = np.append(full_model, [data[data >= 1]], axis=0)
# print(len(full_model[0]))
# np.save(os.path.join(target_data_path, "full_lung_coords"), np.array(full_model))


model_adjacency_sum = np.sum([np.roll(np.clip(data, 0, 1), i, axis=ax) for i in [-1,1] for ax in [0,1,2]], axis=0)
full_model_outer_shell = np.where(np.logical_and(data >= 1, model_adjacency_sum != 6))
full_model_outer_shell = np.append(full_model_outer_shell, [data[np.logical_and(data >= 1, model_adjacency_sum != 6)]], axis=0)
print(len(full_model_outer_shell[0]))
np.save(os.path.join(target_data_path, "full_lung_outer_shell_coords"), np.array(full_model_outer_shell))

print("end: writing coordinates to " + target_data_path + "\n")
