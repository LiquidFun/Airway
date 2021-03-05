import pydicom
import csv

from airway.util.util import get_data_paths_from_args
from airway.util.util import get_patient_name


def read_metadata(path):
    patients = []
    for patient in path.glob("*"):
        data = pydicom.dcmread(path / patient / "Bronchus" / "IMG1")
        values = {}
        keys = ["PatientID",
                "AdditionalPatientHistory",
                "PatientSex",
                "AcquisitionDate",
                "Manufacturer",
                "ManufacturerModelName",
                "SliceThickness"
                ]
        for key in keys:
            values[key] = str(data.data_element(key).value)
        values["Name"] = get_patient_name(values["PatientID"])
        patients.append(values)
    return patients


def write_table(path, data):
    with open(path / "metadata.csv", 'w') as file:
        writer = csv.writer(file)
        for patient in data:
            writer.writerow(patient)


def reformat_data(data):
    d = sorted(data, key=lambda dic: int(dic["PatientID"]))
    for i in range(len(d)):
        d[i]["#"] = str(i + 1)
    new_data = [["#",
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


def main():
    output_data_path, input_data_path = get_data_paths_from_args()
    data = read_metadata(input_data_path)
    formatted_data = reformat_data(data)
    first_row = True
    for patient in formatted_data:
        print('| ', ' | '.join(patient), ' |', sep='')
        if first_row:
            print("|:----" * len(patient), end='|\n')
            first_row = False
    write_table(output_data_path, formatted_data)


if __name__ == "__main__":
    main()
