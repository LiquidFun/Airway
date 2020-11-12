import sys
from pathlib import Path

import numpy as np

try:
    output_data_path = Path(sys.argv[1])
    input_data_path = Path(sys.argv[2])
except IndexError:
    print("ERROR: No patient data path supplied")
    sys.exit(1)


def print_model_description(model):
    total_sum = np.sum(model)
    print(f"Total sum: {total_sum:,}")
    print(f"Total pixels in model: {np.product(np.array(model.shape)):,}")
    return total_sum


model = np.load(input_data_path / "model.npy")

print("{} images loaded".format(len(model)))

print("Printing sum as validation as only 0-layers are being removed the sum should not change.")
print("Before reduction:")
old_total_sum = print_model_description(model)

# Axis description:
#      0: top to bottom
#      1: front to back
#      2: left to right

print("\nReducing model: ", end='')
print(model.shape, end=' ')

for axis in [0, 1, 2]:
    sums = np.sum(np.sum(model, axis=axis), axis=(axis+1) % 2)
    # print(sums)

    # Track all =0 layers from front from that axis
    remove_front_index = 0
    while sums[remove_front_index] == 0:
        remove_front_index += 1

    # Track all =0 layers from back from that axis
    remove_back_index = len(sums)-1
    while sums[remove_back_index] == 0:
        remove_back_index -= 1

    # Remove those layers
    model = np.delete(model, list(range(remove_front_index-1)) + list(range(remove_back_index+2, len(sums))), axis=(axis+1)%3)
    sums = np.sum(np.sum(model, axis=axis), axis=(axis+1) % 2)
    # print(sums)
    print(' -> ', model.shape, end=' ')

print("\n\nAfter reduction:")
curr_total_sum = print_model_description(model)

if curr_total_sum == old_total_sum:
    np.save(output_data_path / "reduced_model", model)
else:
    raise Exception("It seems like the script removed actual data from the model; this should not happen!")
