import subprocess
import sys
from pathlib import Path

from util.util import get_data_paths_from_args

output_data_path, bronchus_input_data_path, splits_input_data_path = get_data_paths_from_args(inputs=2)
output_path = output_data_path / "left_upper_lobe#"
bronchus_input_path = bronchus_input_data_path / "bronchus.obj"
skeleton_input_path = bronchus_input_data_path / "skeleton.obj"
splits_input_path = splits_input_data_path / "splits.obj"
script_path = Path(__file__).parent.absolute() / "render_with_blender.py"
print(sys.argv)
try:
    run_in_background = sys.argv[4].lower() == "true"
    assert sys.argv[4].lower() in ["true", "false"], "given arg is not True or False"
except IndexError:
    run_in_background = True

command = [
    'blender',
    '-P', script_path,
    '-E', 'CYCLES',
]
if run_in_background:
    command.extend([
        '-o', output_path,
        '-f', '0',
        '-b',
    ])

command.extend([
    '--',
    bronchus_input_path,
    skeleton_input_path,
    splits_input_path,
])
print(command)
subprocess.Popen(command)
