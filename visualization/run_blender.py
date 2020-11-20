import subprocess
from pathlib import Path

from util.util import get_data_paths_from_args

output_data_path, input_data_path = get_data_paths_from_args()
output_path = output_data_path / "left_upper_lobe#"
input_path = input_data_path / "bronchus.obj"
script_path = Path(__file__).parent.absolute() / "render_with_blender.py"

command = [
    'blender',
    '-P', script_path,
    '-E', 'CYCLES',
    '-o', output_path,
    '-f', '0',
    '-b',
    '--', input_path,
]
subprocess.Popen(command)
