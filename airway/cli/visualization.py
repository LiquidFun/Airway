import sys
from argparse import ArgumentParser
from typing import Dict

from airway.cli.base import BaseCLI
from airway.util.util import get_patient_name


class VisCLI(BaseCLI):
    def __init__(self):
        super().__init__()
        self.vis_name_to_config: Dict[str, Dict] = {}
        for stage_name, configs in self.stage_configs.items():
            for name, args in configs.get("interactive_args", {}).items():
                if name in self.vis_name_to_config:
                    self.exit(f"Interactive name {self.col.green(name)} already exists!")
                self.vis_name_to_config[name] = {
                    "script": configs["script"],
                    "args": args,
                    "per_patient": configs.get("per_patient", True),
                    "inputs": configs["inputs"],
                    "output": stage_name,
                }

    def add_subparser_args(self):
        parser = self.add_subparser(["vis", "v"], "CLI for all interactive visualizations")
        parser.add_argument("id", nargs="?", default="1", type=str, help="patient id: (1-based) index, name, or id")
        parser.add_argument("-P", "--path", default=self.defaults["path"], help="working data path")
        for name, config in self.vis_name_to_config.items():
            parser.add_argument(
                f"-{name[0]}", f"--{name}", default=False, action="store_true", help=f"show plot of {name}"
            )

    def handle_args(self, args):
        self.insert_path_keyword_as_path(args)

        for name, config in self.vis_name_to_config.items():
            if getattr(args, name):
                input_paths = [args.path / input_path for input_path in config["inputs"]]
                keyword_to_patient_id = self.get_keyword_to_patient_id_dict(args.path)

                curr_patient_id = keyword_to_patient_id[args.id]

                output_patient_path = args.path / config["output"]
                if config["per_patient"]:
                    output_patient_path /= curr_patient_id
                input_patient_paths = [p / curr_patient_id for p in input_paths]

                subprocess_args = [list(map(str, [output_patient_path, *input_patient_paths, *config["args"]]))]
                script_module = config["script"].replace(".py", "").replace("/", ".")
                self.concurrent_executor(subprocess_args, script_module)
