from pathlib import Path
import yaml


config_path = Path().cwd() / "config"


def get_dict_from_yaml(curr_config_path: Path):
    curr_config_path = config_path / "classification.yaml"
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
