import numpy as np

from airway.util.util import get_data_paths_from_args

output_data_path, input_data_path = get_data_paths_from_args()

reduced_data_file = input_data_path / "reduced_model.npz"
data = np.load(reduced_data_file)["arr_0"]

model = np.append(np.where(data == 1), ([data[data == 1]]), axis=0)
print(f"Model size: {len(model[0]):,}")
np.savez_compressed(output_data_path / "bronchus_coords", model)

model_adjacency_sum = np.sum([np.roll(data, i, axis=ax) for i in [-1, 1] for ax in [0, 1, 2]], axis=0)
model_outer_shell_only = np.where(np.logical_and(data == 1, model_adjacency_sum != 6))
model_outer_shell_only = np.append(
    model_outer_shell_only, [data[np.logical_and(data == 1, model_adjacency_sum != 6)]], axis=0
)
print(f"Outer shell model size: {len(model_outer_shell_only[0]):,}")
np.savez_compressed(output_data_path / "bronchus_coords_outer_shell", np.array(model_outer_shell_only))

# full_model = np.where(data >= 1)
# full_model = np.append(full_model, [data[data >= 1]], axis=0)
# print(len(full_model[0]))
# np.savez_compressed(os.path.join(target_data_path, "full_lung_coords"), np.array(full_model))


model_adjacency_sum = np.sum([np.roll(np.clip(data, 0, 1), i, axis=ax) for i in [-1, 1] for ax in [0, 1, 2]], axis=0)
full_model_outer_shell = np.where(np.logical_and(data >= 1, model_adjacency_sum != 6))
full_model_outer_shell = np.append(
    full_model_outer_shell, [data[np.logical_and(data >= 1, model_adjacency_sum != 6)]], axis=0
)
print(f"Full outer shell model size: {len(full_model_outer_shell[0]):,}")
np.savez_compressed(output_data_path / "full_lung_outer_shell_coords", np.array(full_model_outer_shell))

print(f"Writing coordinates to {output_data_path}\n")
