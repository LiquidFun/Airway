#!/usr/bin/env python3

""" Airway-pipeline.py is the glue for all airway scripts. It tries to do all the work
    in parallel. Therefore airway-pipeline comes with a bunch of parameters for
    selecting a stage to calculate, path management and how much parallel processes
    will be used for calculation.

"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, List
import subprocess
from subprocess import PIPE
from concurrent.futures import ProcessPoolExecutor

import yaml


reqVersion = (3, 6)  # because of concurrent.futures and f-strings
currVersion = (sys.version_info.major, sys.version_info.minor)
assert currVersion >= reqVersion, "ERROR: Your python is too old. Minimum: 3.6"

errors = {}  # used for collecting errors while executing parallel tasks

base_path = Path(sys.argv[0]).parents[0]


def main():

    defaults = {"path": None, "workers": 4, "force": False, "single": False, "all": False}
    defaults_path = base_path / "defaults.yaml"
    if defaults_path.exists():
        with open(defaults_path) as config_file:
            defaults.update(yaml.load(config_file, yaml.FullLoader))

    parser = argparse.ArgumentParser()
    parser.add_argument("stages", type=str, action='append', help="list of stages to calculate")
    parser.add_argument("-p", "--path", default=defaults["path"], help="airway data path")
    parser.add_argument("-w", "--workers", type=int, default=defaults["workers"], help="number of parallel workers")
    parser.add_argument("-f", "--force", help="force overwriting of previous stages",
                        default=defaults["force"], action="store_true")
    parser.add_argument("-1", "--single", help="will do a single patient instead of all patients (useful for testing)",
                        default=defaults['single'], action="store_true")
    # TODO: Possibly implement these:
    # parser.add_argument("-c", "--clean", help="Cleans given stage directories")
    # parser.add_argument("-s", "--stages", help="List possible stages with short description")
    args = parser.parse_args()

    assert args.path is not None, "ERROR: Airway data path required!"

    stage_configs_path = base_path / "stage_configs.yaml"
    assert stage_configs_path.exists(), "ERROR: Stage configs path does not exist!"
    with open(stage_configs_path) as stage_configs_file:
        stage_configs: Dict = yaml.load(stage_configs_file, yaml.FullLoader)
        # Link keyword (eg. '1', '17', 'tree', 'vis', etc.) to stages (eg. 'raw_airway', 'stage-01', 'stage-31', etc.)
        keyword_to_stages: Dict[str, List[str]] = {"all": []}
        for stage_name, stage_config in stage_configs.items():
            if stage_name != "defaults":
                assert 'stage-' in stage_name, f"ERROR: Cannot handle stage name {stage_name}!"
                keyword_to_stages['all'].append(stage_name)

                # Update with defaults without overwriting
                for key, val in stage_configs['defaults'].items():
                    if key not in stage_config:
                        stage_config[key] = val

                # Add keyword to generate one or more stages
                keyword_to_stages[str(int(stage_name.split('-')[1]))] = [stage_name]
                for group in stage_config['groups']:
                    if group not in keyword_to_stages:
                        keyword_to_stages[group] = []
                    keyword_to_stages[group].append(stage_name)
                stage_config.pop('groups', None)

        # Go through each stage in args and handle ranges ('-s 5-7' as well as single calls '-s 3')
        stages_to_process = set()
        for s_arg in args.stages:  # e.g. s_arg in ['1-3', '4', '5-7', 'analysis']
            if '-' in s_arg:
                fr = int(s_arg.split('-')[0])
                to = int(s_arg.split('-')[1]) + 1
                keywords = list(map(str, range(fr, to)))
            else:
                keywords = [s_arg]
            for s in keywords:
                stages_to_process |= {keyword for keyword in keyword_to_stages[str(s)]}

        assert all([isinstance(a, str) for a in stages_to_process]), "ERROR: Not all keywords are strings"

        # Root stage has no entry in configs, so ignore it
        root_stage = "raw_airway"

        class Dependency:
            """This is a simple class which is used to compare the dependency tree of various stages

            It calculates all of its own dependencies on init, then it looks whether another
            stage is in its dependencies in < (__lt__). If these do not share a dependency then
            either True or False is fine.
            """
            def __init__(self, name):
                self.name = name
                self.dependencies = {name}
                while True:
                    copy = self.dependencies.copy()
                    for dependency in copy:
                        if dependency != root_stage:
                            for i in stage_configs[dependency]["inputs"]:
                                if i not in self.dependencies:
                                    self.dependencies.add(i)
                    if len(self.dependencies) == len(copy):
                        break

            def __lt__(self, other):
                return other.name not in self.dependencies

        stages_to_process_in_dependency_order = sorted(stages_to_process, key=Dependency)
        formatted = ', '.join([s.replace('stage-', '') for s in stages_to_process_in_dependency_order])
        print(f"Processing stages in this order:\n{formatted}\n")

        for curr_stage_name in stages_to_process_in_dependency_order:
            assert curr_stage_name in stage_configs, f"ERROR: Unknown stage name {curr_stage_name}!"
            stage(curr_stage_name, **stage_configs[curr_stage_name], **vars(args))

    show_error_statistics()


def stage(
        stage_name: str,
        *,  # Arguments below must be keyword args
        path: str,
        workers: int,
        force: bool,
        script: str,
        inputs: List[str],
        args: List[str],
        per_patient: bool,
        single: bool,
        **_,  # Ignore kwargs
    ):
    """Meta function for calculating most stages in parallel.

    args:
        stage_name: the name of the stage to calculate (eg. "stage-01")
        path: path to your root data folder (eg. "/home/me/data/airway/")
        workers: number of threads to use when computing (eg. 4)
        force: whether the state should be overwritten if it already exists (eg. True)
        script: path to script to run (eg. "image_processing/save_images_as_npy.py")
        inputs: list of input stage names for script (eg. ["raw_airway", "stage-02"])
        args: list of arguments supplied as strings to script (eg. ["False"]
        per_patient: whether script should only be called once for all patients (eg. True)
        single: whether only a single patient should be computed (eg. True)

    """
    title = f"========== Processing {stage_name} =========="
    print("{0}\n{1}\n{0}\n".format("="*len(title), title))

    args = list(map(str, args))

    # script_path = Path(__file__).parents[0] / script
    script_module = script.replace(".py", "").replace('/', '.')
    print(f"Running script {script_module} as module.")
    # assert script_path.exists(), f"ERROR: script {script_path} does not exist!"

    output_stage_path = Path(path) / stage_name

    input_stage_paths = [Path(path) / input_stage_path for input_stage_path in inputs]

    # check if output directory 'stage-xx' exists
    if output_stage_path.exists() and not force:
        print(f"ERROR: {output_stage_path} already exists, use the -f flag to overwrite.")
        sys.exit(1)
    else:
        input_stage_path = input_stage_paths[0]
        assert input_stage_path.exists(), f"ERROR: {input_stage_path} does not exist. " \
                                          f"Calculate the predecessor stage first!"
        output_stage_path.mkdir(exist_ok=True, parents=True)

        # build the list of subprocess-arguments for later use with subprocess.run
        subprocess_args = []
        # If script should be called for every patient
        if per_patient:
            # Iterate over each patient directory
            for patient_dir in input_stage_path.glob('*'):
                patient_output_stage_path = output_stage_path / patient_dir.name
                patient_input_stage_paths = [isp / patient_dir.name for isp in input_stage_paths]
                patient_output_stage_path.mkdir(exist_ok=True, mode=0o777)

                subprocess_args.append(["python3", "-m", script_module, patient_output_stage_path,
                                        *patient_input_stage_paths, *args])
                # Only add a single patient if 'single' given
                if single:
                    break
        # Call script with default directory otherwise
        else:
            subprocess_args.append(["python3", "-m", script_module, output_stage_path, *input_stage_paths, *args])
        concurrent_executor(subprocess_args, workers)


def subprocess_executor(argument):
    # return subprocess.run(argument, capture_output=True, encoding="utf-8")
    # Above is Python 3.7, so PIPE instead of capture_output=True
    return subprocess.run(argument, encoding="utf-8", stdout=PIPE, stderr=PIPE)


def concurrent_executor(subprocess_args, worker):
    global errors
    with ProcessPoolExecutor(max_workers=worker) as executor:
        for count, retVal in enumerate(executor.map(subprocess_executor, subprocess_args), start=1):
            print(f"---- Output for Process {count}/{len(subprocess_args)} ----")
            print(f"STDOUT:\n{retVal.stdout}\n")
            print(f"STDERR:\n{retVal.stderr}\n")

            if len(retVal.stderr) > 0:
                stage_name = str(Path(subprocess_args[0][3]).parents[0].name)
                if stage_name not in errors:
                    errors[stage_name] = []
                errors[stage_name].append(count)


def show_error_statistics():
    global errors
    print("\n====== Error Statistics  ======\n")
    if errors:
        err_count = 0
        for key, val in errors.items():
            err_count += len(val)
            print(f"\n{key}:{len(val):>3} errors")
        print(f"---- Overall errors: {err_count} ----\n")
    else:
        print("---- No errors occurred ----\n")


if __name__ == "__main__":
    previous_mask = os.umask(0o002)
    previous_cwd = Path.cwd()
    os.chdir(base_path)
    main()
    os.chdir(previous_cwd)
    os.umask(previous_mask)
