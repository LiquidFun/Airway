import os
import sys 

import numpy as np

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#patient_data_path = os.path.join(project_dir, "data/3124983")

if len(sys.argv) >= 3:
    patient_data_path = sys.argv[1]
    processed_data_path = sys.argv[2]
else:
    processed_data_path = os.path.join(os.path.join(project_dir, "data/{}"
        .format(patient_id)))

def print_model_description(model):
    total_sum = np.sum(model)
    print("Total sum: {}".format(total_sum))
    print("Total pixels in model: {:,}".format(np.product(np.array(model.shape))))
    return total_sum

model = np.load(os.path.join(patient_data_path, "model.npy"))

#print(model)

print("{} images loaded".format(len(model)))

print("Before reduction:")
old_total_sum = print_model_description(model)

# Axis description:
#      0: top to bottom
#      1: front to back
#      2: left to right

print("\nReducing model: ", end='')
print(model.shape, end=' ')

for axis in [0,1,2]:
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
    #np.save(os.path.join(patient_data_path, "reduced_model"), model)
    np.save(os.path.join(processed_data_path, "reduced_model"), model)
else:
    raise Exception("It seems like the script removed actual data from the model; this should not happen!")
