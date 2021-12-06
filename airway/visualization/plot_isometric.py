import os
import numpy as np
import sys
from matplotlib import pyplot as plt

patient_data_dir = "../data/pat0/"
visualizations_dir = "images/"

try:
    patient_id = sys.argv[1]
except IndexError:
    patient_id = "3127679"


def get_image_num(filename):
    return int(filename.replace(".npz", "").replace("IMG", ""))


model = []

ones_count = 0
for x, image_name in enumerate(sorted(os.listdir(patient_data_dir), key=get_image_num)):
    print("Loading image {}".format(image_name))

    model.append(np.load(os.path.join(patient_data_dir, image_name)))

model = np.array(model)

print(model.shape)

# Names base on a standing person in front of you
for axis, name in enumerate(["top-to-bottom", "front-to-back", "right-to-left"]):
    plt.imshow(np.sum(model, axis=axis))
    plt.savefig(os.path.join(visualizations_dir, name + "-heatmap.png"))
    plt.show()
