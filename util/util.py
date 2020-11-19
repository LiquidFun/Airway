import sys
from pathlib import Path
import random
import string


def get_data_paths_from_args(outputs=1, inputs=1):
    """ Returns output and input data paths from sys.argv

    It exits if these are not defined
    """

    if len(sys.argv[1:]) < outputs+inputs:
        print("ERROR: Insufficient count of input/output paths supplied!")
        print(f"\tExpected {outputs} output paths and {inputs} input paths!")
        print(f"\tGot sys.argv: {sys.argv[1:]}")
        sys.exit(1)

    return (Path(sys.argv[index+1]) for index in range(outputs+inputs))
    # return (
    #     Path(arg) if index <= outputs+inputs else arg
    #     for index, arg in enumerate(sys.argv[1:], start=1)
    # )


def get_patient_name(patient_id):
    random.seed(int(patient_id))
    vowels = "aeiou"
    name = ""
    letters = string.ascii_lowercase
    for i in range(4):
        while True:
            curr = letters[random.randint(0, len(letters) - 1)]
            if i & 1:
                if curr in vowels:
                    break
            else:
                if curr not in vowels:
                    break

        name += curr
    return name.capitalize()
