import shutil
import subprocess
import tempfile
from pathlib import Path


def test_stages():
    example_patient = Path("example_data") / "model.npz"
    if example_patient.exists():
        temp_dir = tempfile.mkdtemp(prefix="airway-tests-dummy-")
        patient_id = "patient_id"
        stage01_path = Path(temp_dir) / "stage-01" / patient_id
        stage01_path.mkdir(exist_ok=True, parents=True)
        print(Path.cwd())
        shutil.copy(example_patient, stage01_path)
        command = ["python3", "airway_cli.py", "stages", "-1", "-v", "-P", temp_dir, "2-10", "color_mask", "3d"]
        print(" ".join(command))
        ret = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(ret)
        assert b"STDERR" not in ret.stdout, ret.stdout
