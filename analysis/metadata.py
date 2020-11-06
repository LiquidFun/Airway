import os
import sys
import random
import string

import pydicom
import csv

def read_metadata(path):
    patients = []
    for patient in os.listdir(path):
        data = pydicom.dcmread(os.path.join(path, patient, "Bronchus/IMG1"))
        #print(data.dir("Man"))
        vals = {}
        keys = ["PatientID", 
                "AdditionalPatientHistory", 
                "PatientSex",
                "AcquisitionDate",
                "Manufacturer",
                "ManufacturerModelName",
                "SliceThickness"
                ]
        for key in keys:
            vals[key] = str(data.data_element(key).value)
        vals["Name"] = get_name(vals["PatientID"])
        patients.append(vals)
    return patients

def get_name(patient_id):
    random.seed(int(patient_id))
    vowels = "aeiou"
    name = ""
    l = string.ascii_lowercase
    for i in range(4):
        while True:
            curr = l[random.randint(0, len(l)-1)]
            if i&1:
                if curr in vowels:
                    break
            else:
                if curr not in vowels:
                    break

        name += curr
    return name.capitalize()

def write_table(path, data):
    with open(os.path.join(path, "metadata.csv"), 'w') as file:
        writer = csv.writer(file)
        for patient in data:
            writer.writerow(patient)

def reformat_data(data):
    d = sorted(data, key=lambda dic: int(dic["PatientID"]))
    for i in range(len(d)):
        d[i]["#"] = str(i+1)
    new_data = [[   "#", 
                    "Name",
                    "PatientID",
                    "PatientSex",
                    "AdditionalPatientHistory",
                    "AcquisitionDate",
                    "Manufacturer",
                    "ManufacturerModelName",
                    "SliceThickness"
                    ]]
    for patient in d:
        line = []
        for key in new_data[0]:
            line.append(patient[key])
        new_data.append(line)
    return new_data


if __name__ == "__main__":
    try:
        PATH = sys.argv[1]
    except IndexError:
        print("ERROR: No data path provided, aborting!")
        sys.exit(1)

    RAW = os.path.join(PATH, "raw_airway")
    STAGE11 = os.path.join(PATH, "stage-11")

    if not os.path.exists(STAGE11):
        os.makedirs(STAGE11)

    data = read_metadata(RAW)
    formatted_data = reformat_data(data)
    first_row = True
    for patient in formatted_data:
        print('| ', end='')
        print(' | '.join(patient), end='')
        print(' |')
        if first_row:
            print("|:----"*len(patient), end='|\n')
            first_row = False
    write_table(STAGE11, formatted_data)

