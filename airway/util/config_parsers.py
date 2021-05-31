from pathlib import Path
from typing import Dict, Any

import yaml

module_path = Path(__file__).parents[2]
configs_path = module_path / "configs"


def get_dict_from_yaml(curr_config_path: Path, ignore_if_does_not_exist=False) -> Dict:
    if ignore_if_does_not_exist and not curr_config_path.exists():
        return {}
    assert curr_config_path.exists(), f"Config {curr_config_path} does not exist!"
    with curr_config_path.open("r") as config_file:
        return yaml.load(config_file.read(), yaml.FullLoader)


def parse_classification_config():
    classification_config = get_dict_from_yaml(configs_path / "classification.yaml")
    return classification_config


def parse_stage_configs():
    stage_configs = get_dict_from_yaml(configs_path / "stage_configs.yaml")
    defaults = stage_configs["defaults"]
    del stage_configs["defaults"]
    for stage_name, config in stage_configs.items():
        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value
    return stage_configs


def parse_array_encoding() -> Dict[str, int]:
    return get_dict_from_yaml(configs_path / "array_encoding.yaml")


def parse_inverted_array_encoding() -> Dict[int, str]:
    return {v: k for k, v in parse_array_encoding()}


def parse_defaults() -> Dict[str, Any]:
    defaults = {}
    # Iterate over example defaults first, so that the defaults
    # written in defaults.yaml overwrite these.
    for filename in ["example_defaults.yaml", "defaults.yaml"]:
        for directory in [module_path, configs_path]:
            defaults.update(get_dict_from_yaml(directory / filename, ignore_if_does_not_exist=True))
    return defaults
