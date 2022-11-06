from pathlib import Path
from typing import Dict, Any

import yaml
import pytest

stage_configs_path = Path().cwd() / "airway" / "configs" / "stage_configs.yaml"


def test_existence():
    assert stage_configs_path.exists()


@pytest.fixture
def stage_configs():
    with stage_configs_path.open("r") as file:
        return yaml.load(file.read(), yaml.FullLoader)


@pytest.fixture
def stage_configs_no_defaults(stage_configs) -> Dict[str, Dict[str, Any]]:
    del stage_configs["defaults"]
    return stage_configs


def test_has_defaults(stage_configs):
    assert "defaults" in stage_configs


def test_all_stages_with_description(stage_configs_no_defaults):
    assert all(config.get("description", "") for config in stage_configs_no_defaults.values())


def test_all_script_files_exist(stage_configs_no_defaults):
    for config in stage_configs_no_defaults.values():
        assert Path(config["script"]).exists(), f"File '{config['script']}' does not exist!"


def test_all_inputs_exist(stage_configs_no_defaults):
    for config in stage_configs_no_defaults.values():
        for input_stage in config["inputs"]:
            assert input_stage in stage_configs_no_defaults or input_stage in ["raw_airway"]


def test_all_stages_have_groups(stage_configs_no_defaults):
    for config in stage_configs_no_defaults.values():
        assert len(config.get("groups", [])) != 0
