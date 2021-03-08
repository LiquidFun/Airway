#!/usr/bin/env python3

import sys
import os
import argparse
import subprocess
from pathlib import Path
from plistlib import Dict

import yaml

from airway.util.util import get_patient_name


def run():
    base_path = Path(sys.argv[0]).parent
    os.chdir(base_path)
    stage_configs_path = base_path / "configs" / "stage_configs.yaml"
    vis_name_to_config: Dict[str, Dict] = {}
    with open(stage_configs_path) as stage_configs_file:
        stage_configs: Dict = yaml.load(stage_configs_file, yaml.FullLoader)
        for stage_name, configs in stage_configs.items():
            for name, args in configs.get('interactive_args', {}).items():
                if name in vis_name_to_config:
                    sys.exit(f"ERROR: Interactive name {name} already exists!")
                vis_name_to_config[name] = {
                    'script': configs['script'], 'args': args, 'per_patient': configs.get("per_patient", False),
                    'inputs': configs['inputs'], 'output': stage_name,
                }

    defaults_path = base_path / "defaults.yaml"
    if defaults_path.exists():
        with open(defaults_path) as config_file:
            defaults = yaml.load(config_file, yaml.FullLoader)

    parser = argparse.ArgumentParser()
    parser.add_argument("id", nargs='?', default="1", help="patient id (can be index, name, or id)")
    parser.add_argument("-P", "--path", default=defaults['path'], help="working data path")
    for name, config in vis_name_to_config.items():
        parser.add_argument(f"-{name[0]}", f"--{name}", default=False, action="store_true",
                            help=f"show plot of {name}")

    args = parser.parse_args()
    path = defaults['paths'].get(args.path, args.path)

    arg_dict = vars(args)

    for name, config in vis_name_to_config.items():
        if arg_dict[name]:
            script_module = config['script'].replace(".py", "").replace('/', '.')
            input_paths = [Path(path) / input_path for input_path in config['inputs']]
            keyword_to_patient_id = {}
            for input_path in input_paths:
                for patient_path in input_path.glob('*'):
                    patient = patient_path.name
                    keyword_to_patient_id[patient] = patient
            for index, patient in enumerate(sorted(keyword_to_patient_id), start=1):
                keyword_to_patient_id[str(index)] = patient
                keyword_to_patient_id[get_patient_name(patient)] = patient

            curr_patient_id = keyword_to_patient_id[str(args.id).capitalize()]

            output_patient_path = Path(path) / config['output']
            if config['per_patient']:
                output_patient_path /= curr_patient_id
            input_patient_paths = [p / curr_patient_id for p in input_paths]

            subprocess_args = list(map(str, [
                'python3', '-m',
                script_module,
                output_patient_path,
                *input_patient_paths,
                *config['args'],
            ]))
            return_val = subprocess.run(subprocess_args)
            print(f"STDOUT:\n{return_val.stdout}\n")
            print(f"STDERR:\n{return_val.stderr}\n\n")


if __name__ == "__main__":
    run()

