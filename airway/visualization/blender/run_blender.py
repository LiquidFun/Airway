import subprocess
import sys
from pathlib import Path

from airway.util.config_parsers import parse_defaults
from airway.util.util import get_data_paths_from_args

print("\n".join(sys.argv))
(
    output_data_path,
    bronchus_input_data_path,
    splits_input_data_path,
    tree_input_data_path,
    model_input_data_path,
) = get_data_paths_from_args(inputs=4)

script_path = Path(__file__).parent.absolute() / "render_with_blender.py"

try:
    run_in_background = sys.argv[6].lower() == "true"
    assert sys.argv[6].lower() in ["true", "false"], "given arg is not True or False"
except IndexError:
    run_in_background = True

defaults = parse_defaults()

# Specify blender script to run
command = [
    defaults.get("blender", "blender"),
    "-P",
    script_path,
    "-E",
    "CYCLES",
]

# When running blender in background add -b flag and output path for frame 0
if run_in_background:
    command.extend(
        [
            "-o",
            output_data_path / "bronchus#",
            "-f",
            "0",
            "-b",
        ]
    )

# Add commandline args which will be passed through to the script
command.extend(
    [
        "--",
        bronchus_input_data_path / "bronchus.obj",
        bronchus_input_data_path / "skeleton.obj",
        splits_input_data_path / "splits.obj",
        tree_input_data_path / "tree.graphml",
        model_input_data_path / "reduced_model.npz",
    ]
)
print(command)
subprocess.Popen(command)
