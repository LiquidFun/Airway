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
from typing import Dict, Any, List

import subprocess
from subprocess import PIPE
import yaml
from concurrent.futures import ProcessPoolExecutor


reqVersion = (3, 6)  # because of concurrent.futures and f-strings
currVersion = (sys.version_info.major, sys.version_info.minor)
assert currVersion >= reqVersion, "ERROR: Your python is too old. Minimum: 3.6"

errors = {}  # used for collecting errors while executing parallel tasks


def main():
    base_path = Path(sys.argv[0]).parents[0]

    defaults = {"path": None, "workers": 4, "force": False, "debug": False, "all": False}
    defaults_path = base_path / "defaults.yaml"
    if defaults_path.exists():
        with open(defaults_path) as config_file:
            defaults.update(yaml.load(config_file, yaml.FullLoader))

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", default=defaults["path"], help="airway data path")
    parser.add_argument("-s", "--stages", type=str, action='append', help="list of stages to calculate")
    parser.add_argument("-a", "--all", default=defaults['all'], action='store_true',
                        help="generates all stages (may take a long time)")
    parser.add_argument("-w", "--workers", type=int, default=defaults["workers"], help="number of parallel workers")
    parser.add_argument("-f", "--force", help="force overwriting of previous stages",
                        default=defaults["force"], action="store_true")
    parser.add_argument("-1", "--single", help="will do a single patient instead of all patients",
                        default=defaults['debug'], action="store_true")
    args = parser.parse_args()

    assert args.path is not None, "ERROR: Airway data path required!"
    assert args.stages is not None or args.all, "ERROR: No stages given, doing nothing!"

    stage_configs_path = base_path / "stage_configs.yaml"
    assert stage_configs_path.exists(), "ERROR: Stage configs path does not exist!"
    with open(stage_configs_path) as stage_configs_file:
        stage_configs: Dict = yaml.load(stage_configs_file, yaml.FullLoader)
        # Link keyword (eg. '1', '17', 'tree', 'vis', etc.) to stages (eg. 'raw_airway', 'stage-01', 'stage-31', etc.)
        keyword_to_stages: Dict[str, List[str]] = {}
        for stage_name, stage_config in stage_configs.items():
            if stage_name != "defaults":
                assert 'stage-' in stage_name, f"ERROR: Cannot handle stage name {stage_name}!"

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

        if args.all:
            stages_to_process = stage_configs.keys()
        else:
            stages_to_process = {keyword for s in args.stages for keyword in keyword_to_stages[s]}

        # TODO: Handle in correct dependency order

        for curr_stage_name in stages_to_process:
            assert curr_stage_name in stage_configs, f"ERROR: Unknown stage name {curr_stage_name}!"
            stage(curr_stage_name, **stage_configs[curr_stage_name], **vars(args))

    # if 10 in stages:  # analysis
    #     retVal = subprocess.run(
    #         ['python3', Path(base_path) / 'analysis/analyze_tree.py', path],
    #         capture_output=True,
    #         encoding='utf-8'
    #     )
    #     print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
    #     retVal = subprocess.run(
    #         ['python3', Path(base_path) / 'visualization/plot_dist_to_first_split.py', path, "False"],
    #         capture_output=True,
    #         encoding='utf-8'
    #     )
    #     print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
    #     retVal = subprocess.run(
    #         ['python3', Path(base_path) / 'analysis/plot_connected_lobes_status.py', path, "False"],
    #         capture_output=True,
    #         encoding='utf-8'
    #     )
    #     print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))

    # if 11 in stages:  # analysis
    #     retVal = subprocess.run(
    #         ['python3', Path(base_path) / 'analysis/metadata.py', path],
    #         capture_output=True,
    #         encoding='utf-8'
    #     )
    #     print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
    # if 20 in stages:  # preparing for visualization
    #     stage(path, workers, force, "stage-02", "stage-20", f"{base_path}/image_processing/generate_bronchus_coords.py")
    # if 21 in stages:  # object generation
    #     stage(path, workers, force, "stage-02", "stage-21", f"{base_path}/obj_generation/gen_obj.py")
    #     stage(path, workers, True, "stage-07", "stage-21", f"{base_path}/obj_generation/gen_split_obj.py")
    # if 22 in stages:  # plots and fancy stuff
    #     # Generate split plots
    #     stage(
    #         path,
    #         workers,
    #         force,
    #         "stage-06",
    #         "stage-22",
    #         Path(base_path) / "visualization/plot_splits.py",
    #         "False",  # This tells the script not to display pyplot interactively
    #     )

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

        TODO: Implement args, per_patient and single

    """
    print(f"====== Processing {stage_name} ======")

    script_path = Path(__file__).parents[0] / script
    assert script_path.exists(), f"ERROR: script {script_path} does not exist!"

    output_stage_path = Path(path) / stage_name

    input_stage_paths = [Path(path) / input_stage_path for input_stage_path in inputs]

    # check if output directory 'stage-xx' exists
    if output_stage_path.exists() and not force:
        print(f"ERROR: {output_stage_path} already exists, use the -f flag to overwrite.")
        sys.exit(1)
    else:
        for input_stage_path in input_stage_paths:
            assert input_stage_path.exists(), f"ERROR: {input_stage_path} does not exist. " \
                                              f"Calculate the predecessor stage first!"
            patient_dirs = input_stage_path.glob('*')
            output_stage_path.mkdir(exist_ok=True, mode=0o777)

            # build the list of subprocess-arguments for later use with subprocess.run
            subprocess_args = []
            for patient_dir in patient_dirs:
                patient_output_stage_path = output_stage_path / patient_dir.name
                patient_input_stage_paths = [isp / patient_dir.name for isp in input_stage_paths]
                patient_output_stage_path.mkdir(exist_ok=True, mode=0o777)

                subprocess_args.append(["python3", script_path, patient_output_stage_path, *patient_input_stage_paths, *args])
            concurrent_executor(subprocess_args, workers)


def subprocess_executor(argument):
    # return subprocess.run(argument, capture_output=True, encoding="utf-8")
    # Above is Python 3.7, so PIPE instead of capture_output=True
    return subprocess.run(argument, encoding="utf-8", stdout=PIPE, stderr=PIPE)


def concurrent_executor(subprocess_args, worker):
    global errors
    with ProcessPoolExecutor(max_workers=worker) as executor:
        for count, retVal in enumerate(executor.map(subprocess_executor, subprocess_args), start=1):
            print(f"---- Output for process #{count} ----")
            print(f"STDOUT:\n{retVal.stdout}\n")
            print(f"STDERR:\n{retVal.stderr}\n")

            if len(retVal.stderr) > 0:
                stage_name = str(Path(subprocess_args[0][3]).parents[0].name)
                if stage_name not in errors:
                    errors[stage_name] = []
                errors[stage_name].append(count)


def show_error_statistics():
    global errors
    print("\n\n########## ERROR STATISTICS  #########\n")
    if errors:
        err_count = 0
        for key, val in errors.items():
            err_count += len(val)
            print(f"\n{key}:{len(val):>3} errors")
        print(f"\n++++ Overall errors: {err_count} ++++\n")
    else:
        print("\n++++ No errors occurred ++++\n")


if __name__ == "__main__":
    previous_mask = os.umask(0o002)
    main()
    os.umask(previous_mask)
