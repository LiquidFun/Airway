import sys
from pathlib import Path


def get_data_paths_from_args(outputs=1, inputs=1):
    """ Returns output and input data paths from sys.argv

    It exits if these are not defined
    """
    try:
        return (
            Path(sys.argv[index+1]) for index in range(outputs + inputs)
        )
    except IndexError:
        print("ERROR: No data or target folder found, aborting")
        sys.exit(1)
