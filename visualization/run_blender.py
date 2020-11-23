import subprocess
import sys
from pathlib import Path

from util.util import get_data_paths_from_args

output_data_path, input_data_path = get_data_paths_from_args()
output_path = output_data_path / "left_upper_lobe#"
input_path = input_data_path / "bronchus.obj"
script_path = Path(__file__).parent.absolute() / "render_with_blender.py"
run_in_background = False
if 4 <= len(sys.argv):
    run_in_background = sys.argv[3].lower() == "true"

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
    '--', input_path,
])
subprocess.Popen(command)
