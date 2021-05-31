import pydicom
import csv

from airway.util.util import get_data_paths_from_args
from airway.util.util import get_patient_name

keys_of_interest = [
    "PatientID",
    "AdditionalPatientHistory",
    "PatientSex",
    "AcquisitionDate",
    "Manufacturer",
    "ManufacturerModelName",
    "SliceThickness",
]


def read_metadata(path):
    patients = []
    for patient_id in path.glob("*"):
        data = pydicom.dcmread(path / patient_id / "Bronchus" / "IMG1")
        values = {}
        for key in keys_of_interest:
            values[key] = str(data.data_element(key).value) if key in data else ""
        values["Name"] = get_patient_name(values["PatientID"])
        patients.append(values)
    return patients


def write_table(path, data):
    with open(path / "metadata.csv", "w") as file:
        writer = csv.writer(file)
        for patient in data:
            writer.writerow(patient)


def reformat_data(data):
    sorted_data = sorted(data, key=lambda dic: int(dic["PatientID"]))
    table = [["#", "Name", *keys_of_interest]]
    # Add new entry list for every patient where the table is used as reference
    for index, patient in enumerate(sorted_data, 1):
        patient["#"] = str(index)
        table.append([patient[key] for key in table[0]])
    return table


def main():
    output_data_path, input_data_path = get_data_paths_from_args()
    data = read_metadata(input_data_path)
    formatted_table = reformat_data(data)
    for formatted_line in formatted_table:
        print("| ", " | ".join(formatted_line), " |", sep="")
        # If is first line print formatting for markdown
        if formatted_line[0] == "#":
            print("|:----" * len(formatted_line), end="|\n")
    write_table(output_data_path, formatted_table)


if __name__ == "__main__":
    main()
