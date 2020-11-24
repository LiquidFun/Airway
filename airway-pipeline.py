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
from queue import Queue
from typing import Dict, List
import subprocess
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import yaml
from tqdm import tqdm

from util.color import Color
from util.util import get_patient_name

col = Color()

reqVersion = (3, 6)  # because of concurrent.futures and f-strings
currVersion = (sys.version_info.major, sys.version_info.minor)
assert currVersion >= reqVersion, "ERROR: Your python is too old. Minimum: 3.6"

errors = {}  # used for collecting errors while executing parallel tasks

base_path = Path(sys.argv[0]).parents[0]

log_path = base_path / "logs" / f"log_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}"


def parse_args(defaults):
    parser = argparse.ArgumentParser()
    parser.add_argument("stages", nargs="+", type=str, help="list of stages to calculate (e.g. 1, 2, 3, tree, vis)")
    parser.add_argument("-P", "--path", default=defaults["path"], help="airway data path")
    parser.add_argument("-w", "--workers", type=int, default=defaults["workers"],
                        help="number of parallel workers (threads)")
    parser.add_argument("-f", "--force", help="force overwriting of previous stages",
                        default=defaults["force"], action="store_true")
    parser.add_argument("-1", "--single", help="will do a single patient instead of all patients (useful for testing)",
                        default=defaults['single'], action="store_true")
    parser.add_argument("-p", "--patients", type=str, action="append",
                        help="instead of processing all patients, only these patient ids will be used")
    parser.add_argument("-l", "--list_patients", action="store_true",
                        help="only list patients including their index and generated name in the given stages")
    parser.add_argument("-v", "--verbose", action="store_true", default=defaults['verbose'],
                        help="print stdout and stderr directly")
    parser.add_argument("-c", "--clean", action="store_true", default=defaults['clean'],
                        help="cleans given stage directories before running them")
    # TODO: Possibly implement these:
    # parser.add_argument("-i", "--interactive", help="run script for single patient without creating subprocess")
    # parser.add_argument("-s", "--stages", help="print a detailed description for each stage and exit")
    # parser.add_argument("-d", "--dependencies", help="create all given stages including their dependencies")
    args = parser.parse_args()
    if args.path in defaults['paths']:
        args.path = defaults['paths'][args.path]
    return args


def validate_args(args):
    assert args.path is not None, "ERROR: Airway data path required!"
    if args.clean:
        log(f"{col.yellow('WARNING')}: Argument {col.green('--clean')} was given. ",
            stdout=True, add_time=True)
        log("This will delete and rerun all the supplied stages!", stdout=True, tabs=1)
        log(f"This might delete data, do you really want to continue ({col.yellow('y')}/{col.yellow('n')}): ",
            stdout=True, tabs=1, end='')
        question = input()
        if question.lower() not in ['yes', 'y']:
            log("User questions their (life-)decisions! Aborting!", stdout=True, add_time=True)
            sys.exit(0)


def parse_defaults():
    defaults = {"path": None, "workers": 4, "force": False, "single": False,
                "all": False, "verbose": False, "clean": False}
    defaults_path = base_path / "defaults.yaml"
    if defaults_path.exists():
        with open(defaults_path) as config_file:
            defaults.update(yaml.load(config_file, yaml.FullLoader))
    return defaults


def main():
    log(f"Running {col.bold()}{col.green()}Airway{col.reset()}", stdout=True, add_time=True)
    start_time = datetime.now()

    defaults = parse_defaults()
    args = parse_args(defaults)
    validate_args(args)

    log(f"Using up to {col.green(args.workers)} workers", stdout=True, tabs=1)
    log(f"Using {col.green(args.path)} as data path", stdout=True, tabs=1)

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

        # Go through each stage in args and handle ranges ('5-7' as well as single calls '3',
        # keywords such as 'vis', 'analysis' and '3+' ranges)
        stages_to_process = set()
        for s_arg in args.stages:  # e.g. s_arg in ['1-3', '4', '5-7', 'analysis']
            try:
                to = 1000
                if '-' in s_arg:
                    fr, to = map(int, s_arg.split('-'))
                elif '+' in s_arg:
                    fr = int(s_arg.split('+')[0])
                else:
                    fr = to = int(s_arg)
                keywords = list(map(str, range(fr, to+1)))
            except ValueError:
                keywords = [s_arg]
            for s in keywords:
                if s in keyword_to_stages:
                    stages_to_process |= {keyword for keyword in keyword_to_stages[s]}

        assert all([isinstance(a, str) for a in stages_to_process]), "ERROR: Not all keywords are strings"

        # Root stage has no entry in configs, so ignore it
        root_stage = "raw_airway"

        def get_dependencies(name):
            """ This is a simple class which creates all the dependencies of a stage """
            _dependencies = {name}
            # Add all dependencies for each name in _dependencies until there are no changes anymore
            while True:
                copy = _dependencies.copy()
                for dependency in copy:
                    if dependency != root_stage:
                        _dependencies |= set(stage_configs[dependency]["inputs"])
                if len(_dependencies) == len(copy):
                    return _dependencies

        stages_to_process_in_dependency_order = []
        queue = Queue()
        for curr in sorted(stages_to_process):
            queue.put(curr)
        # Iterate over queue of stages and only insert a stage once all its dependencies have been inserted
        while not queue.empty():
            curr = queue.get()

            # Only keep dependencies which are in the list of stages to process without the
            # root_stage (raw_airway) and the current stage since these cannot be actual
            # dependencies of it.
            dependencies = get_dependencies(curr) & stages_to_process - {root_stage, curr}
            if all(dep in stages_to_process_in_dependency_order for dep in dependencies):
                stages_to_process_in_dependency_order.append(curr)
            else:
                queue.put(curr)

        formatted = ', '.join([
            col.yellow() + s.replace('stage-', '') + col.reset()
            for s in stages_to_process_in_dependency_order
        ])
        log(f"Stage processing order: {formatted}\n", stdout=True, tabs=1)

        for curr_stage_name in stages_to_process_in_dependency_order:
            assert curr_stage_name in stage_configs, f"ERROR: Unknown stage name {curr_stage_name}!"
            stage(curr_stage_name, **stage_configs[curr_stage_name], **vars(args))

    show_error_statistics()
    log(f"Finished in {col.green(str(datetime.now() - start_time))}", stdout=True, add_time=True)


def stage(
        stage_name: str,
        *,  # Arguments below must be keyword args
        path: str,
        workers: int,
        force: bool,
        script: str,
        inputs: List[str],
        args: List[str],
        single: bool,
        patients: List[str],  # TODO add desc
        per_patient: bool,
        list_patients: bool,  # TODO add desc
        verbose: bool, # TODO add desc
        **_,  # Ignore kwargs
    ):
    """Meta function for calculating most stages in parallel.

    args:
        stage_name: the name of the stage to calculate (eg. "stage-01")
        path: path to your root data folder (eg. "/home/me/data/airway/")
        workers: number of threads to use when computing (eg. 4)
        force: whether the state should be overwritten if it already exists (eg. True)
        script: path to script to run (eg. "image_processing/save_images_as_npz.py")
        inputs: list of input stage names for script (eg. ["raw_airway", "stage-02"])
        args: list of arguments supplied as strings to script (eg. ["False"]
        per_patient: whether script should only be called once for all patients (eg. True)
        single: whether only a single patient should be computed (eg. True)

    """

    if list_patients:
        log(f"Listing patients in {col.green(stage_name)}:", stdout=True, add_time=True)
        stage_path = Path(path) / stage_name
        for index, patient_dir in enumerate(sorted(stage_path.glob("*")), start=1):
            log(f"| {index} | {patient_dir.name} | {get_patient_name(patient_dir.name)} |", stdout=True, tabs=1)
        log("", stdout=True)
        return

    tqdm_prefix = log(f"{col.green()}Processing {stage_name}{col.reset()}", add_time=True)

    args = list(map(str, args))

    script_module = script.replace(".py", "").replace('/', '.')
    log(f"Running script {col.bold()}{script_module}{col.reset()} as module.\n")
    # assert script_path.exists(), f"ERROR: script {script_path} does not exist!"

    output_stage_path = Path(path) / stage_name

    input_stage_paths = [Path(path) / input_stage_path for input_stage_path in inputs]

    # check if output directory 'stage-xx' exists
    if output_stage_path.exists() and not force:
        log(f"ERROR: {output_stage_path} already exists, use the -f flag to overwrite.", stdout=True)
        sys.exit(1)
    else:
        input_stage_path = input_stage_paths[0]
        assert input_stage_path.exists(), f"ERROR: {input_stage_path} does not exist. " \
                                          f"Calculate the predecessor stage first!"
        output_stage_path.mkdir(exist_ok=True, parents=True)

        # build the list of subprocess-arguments for later use with subprocess.run
        subprocess_args = []

        patient_dirs = input_stage_path.glob('*')
        if patients:
            log("Handling only these patients:", stdout=True, add_time=True)
            log('\n'.join(map(col.yellow, patients)) + "\n", stdout=True, tabs=1)
            patient_dirs = list(filter(lambda p: p.name in patients, patient_dirs))

        # If script should be called for every patient
        if per_patient:
            # Iterate over each patient directory
            for patient_dir in patient_dirs:
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
        concurrent_executor(subprocess_args, workers, tqdm_prefix=tqdm_prefix, verbose=verbose)
        # log("", stdout=True)


def log(message: str, stdout=False, add_time=False, tabs=0, end='\n'):
    """ Logs to a file and optionally to stdout

    args:
        message: a string (possibly multiline) which will be logged
        stdout: if the message should be added to stdout
        add_time: will add formatted timestamp for the first non-empty message
                  possibly replacing indentation through tabs
        tabs: padding in front of each line in the message.
              1 tab will align it with lines which have add_time
        end: same as the end arg in print(), is just passed through

    """
    if not log_path.parent.exists():
        log_path.parent.mkdir(exist_ok=True)
    lines = message.split('\n')
    time_added = False
    for i in range(len(lines)):
        add_time_for_this_line = lines[i].strip() != '' and add_time and not time_added
        tabs_adjusted_to_time = tabs-1 if add_time_for_this_line else tabs
        if tabs_adjusted_to_time >= 1:
            prefix = ' ' * 11 * tabs_adjusted_to_time
            lines[i] = prefix + lines[i]
        if add_time_for_this_line:
            time_fmt = f"[{col.green()}{datetime.now().strftime('%H:%M:%S')}{col.reset()}] "
            lines[i] = time_fmt + lines[i]
            time_added = True
    message = '\n'.join(lines)
    with open(log_path, 'a+') as log_file:
        if stdout:
            print(message, end=end)
        filtered_message = col.filter_color_codes(message)
        log_file.write(filtered_message + end)
    return message


def subprocess_executor(args):
    """ Run a single script with args """
    # return subprocess.run(argument, capture_output=True, encoding="utf-8")
    # Above is Python 3.7, so PIPE instead of capture_output=True
    return subprocess.run(args, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def concurrent_executor(subprocess_args, worker, tqdm_prefix="", verbose=False):
    """ Executes multiple scripts as their own modules, logging their STDOUT and STDERR """
    global errors
    with ProcessPoolExecutor(max_workers=worker) as executor:
        bar_fmt = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_inv_fmt}{postfix}]"
        with tqdm(total=len(subprocess_args), unit="run", desc=tqdm_prefix, ncols=80, bar_format=bar_fmt) as progress_bar:
            for count, retVal in enumerate(executor.map(subprocess_executor, subprocess_args), start=1):

                out = f"\nOutput for Process {col.yellow(count)}/{col.yellow(len(subprocess_args))}"
                out += f" (Patient {col.green(Path(retVal.args[3]).name)})\n"
                out += f"STDOUT:\n{retVal.stdout}\n"
                progress_bar.update()

                if len(retVal.stderr) > 0:
                    out += f"\nSTDERR:\n{retVal.stderr}\n"
                    stage_name = str(Path(subprocess_args[0][3]).parents[0].name)
                    if stage_name not in errors:
                        errors[stage_name] = []
                    errors[stage_name].append(count)
                log(out, tabs=1, add_time=True, stdout=verbose)


def show_error_statistics():
    """ Display error statistics for all computed stages using a global dict """
    global errors
    if errors:
        log(f"Error Statistics:", stdout=True, add_time=True)
        print(col.red())
        err_count = 0
        for key, val in errors.items():
            err_count += len(val)
            plural = "errors" if len(val) > 1 else "error"
            log(f"{key}: {len(val):>3} {plural}", stdout=True, tabs=1)
        log(f"Overall errors: {err_count}\n{col.reset()}", stdout=True, tabs=1)
    else:
        log("No errors occurred", stdout=True, add_time=True)


if __name__ == "__main__":
    previous_mask = os.umask(0o002)
    previous_cwd = Path.cwd()
    os.chdir(base_path)
    # Remove logs if there are too many
    log_files = sorted(log_path.parent.glob('*'), key=lambda p: p.stat().st_mtime)
    for existing_log_file in log_files[:-9]:
        existing_log_file.unlink()
    main()
    log_link_path = base_path / "log"
    if log_link_path.exists():
        os.unlink(log_link_path)
    os.link(log_path, log_link_path)
    log(f'Saved log file to {col.green()}{log_path}{col.reset()} (linked to ./log)', stdout=True, add_time=True)
    os.chdir(previous_cwd)
    os.umask(previous_mask)
