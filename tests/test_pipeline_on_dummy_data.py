import shutil
import subprocess
import tempfile
from pathlib import Path


def test_stages():
    temp_dir = tempfile.mkdtemp(prefix="airway-tests-dummy-")
    patient_id = "patient_id"
    stage01_path = Path(temp_dir) / "stage-01" / patient_id
    stage01_path.mkdir(exist_ok=True, parents=True)
    print(Path.cwd())
    shutil.copy(Path("example_data") / "model.npz", stage01_path)
    subprocess.run(["python3", "airway-pipeline.py", "-1", "-v", "-P", temp_dir, "2-7", "color_mask", "3d"],
                   stdout=subprocess.PIPE, stdin=subprocess.PIPE)
