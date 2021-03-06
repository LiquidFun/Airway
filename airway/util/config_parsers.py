from pathlib import Path
from typing import Dict

import yaml

config_path = Path().cwd() / "configs"


def get_dict_from_yaml(curr_config_path: Path):
    assert curr_config_path.exists(), f"Config {curr_config_path} does not exist!"
    with curr_config_path.open('r') as config_file:
        return yaml.load(config_file.read(), yaml.FullLoader)


def parse_classification_config():
    classification_config = get_dict_from_yaml(config_path / "classification.yaml")
    return classification_config


def parse_stage_configs():
    stage_configs = get_dict_from_yaml(config_path / "stage_configs.yaml")
    defaults = stage_configs['defaults']
    del stage_configs['defaults']
    for stage_name, config in stage_configs.items():
        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value
    return stage_configs


def parse_array_encoding() -> Dict[str, int]:
    return get_dict_from_yaml(config_path / "array_encoding.yaml")


def parse_inverted_array_encoding() -> Dict[int, str]:
    return {v: k for k, v in parse_array_encoding()}


def parse_defaults():
    defaults = {"path": None, "workers": 4, "force": False, "single": False,
                "all": False, "verbose": False, "clean": False, "profile": False}
    defaults_path = Path.cwd() / "defaults.yaml"
    if defaults_path.exists():
        with open(defaults_path) as config_file:
            defaults.update(yaml.load(config_file, yaml.FullLoader))
    return defaults
