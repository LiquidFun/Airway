from pathlib import Path
from typing import Dict, Any

import yaml

from airway.util.const import (
    CONFIGS_PATH,
    PACKAGE_PATH,
    CLASSIFICATION_CONFIG_PATH,
    STAGE_CONFIGS_PATH,
    ARRAY_ENCODING_PATH,
)


def get_dict_from_yaml(curr_config_path: Path, ignore_if_does_not_exist=False) -> Dict:
    if ignore_if_does_not_exist and not curr_config_path.exists():
        return {}
    assert curr_config_path.exists(), f"Config {curr_config_path} does not exist!"
    with curr_config_path.open("r") as config_file:
        return yaml.load(config_file.read(), yaml.FullLoader)


def parse_classification_config():
    classification_config = get_dict_from_yaml(CLASSIFICATION_CONFIG_PATH)
    return classification_config


def parse_stage_configs():
    stage_configs = get_dict_from_yaml(STAGE_CONFIGS_PATH)
    defaults = stage_configs["defaults"]
    del stage_configs["defaults"]
    for stage_name, config in stage_configs.items():
        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value
    return stage_configs


def parse_array_encoding() -> Dict[str, int]:
    return get_dict_from_yaml(ARRAY_ENCODING_PATH)


def parse_inverted_array_encoding() -> Dict[int, str]:
    return {v: k for k, v in parse_array_encoding()}


def parse_defaults() -> Dict[str, Any]:
    defaults = {}
    # Iterate over example defaults first, so that the defaults
    # written in defaults.yaml overwrite these.
    for filename in ["example_defaults.yaml", "defaults.yaml"]:
        for directory in [PACKAGE_PATH, CONFIGS_PATH]:
            defaults.update(get_dict_from_yaml(directory / filename, ignore_if_does_not_exist=True))
    return defaults


def update_defaults(new_defaults: Dict[str, Any]):
    filename = CONFIGS_PATH / "defaults.yaml"
    old_defaults = get_dict_from_yaml(filename, ignore_if_does_not_exist=True)

    # Don't use dict.update because it simply replaces all deep dicts and lists. One level should however be enough
    for key, value in new_defaults.items():
        if key not in old_defaults:
            old_defaults[key] = value
        elif isinstance(old_defaults[key], list):
            old_defaults[key].extend(value)
        elif isinstance(old_defaults[key], dict):
            old_defaults[key].update(value)
        else:
            raise ValueError(f"Invalid {key} in {new_defaults}, cannot update old defaults: {old_defaults}!")

    with open(filename, "w") as file:
        dump = yaml.dump(old_defaults)
        file.write(dump)
