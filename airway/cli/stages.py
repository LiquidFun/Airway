import sys
import textwrap
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Dict, List, Set

from airway.cli.base import BaseCLI
from airway.util import const
from airway.util.util import get_patient_name


class StagesCLI(BaseCLI):
    def add_subparser_args(self):
        defaults = self.defaults
        parser = self.add_subparser(["stages", "s"], help_="Create stages in parallel")
        parser.add_argument(
            "stages",
            nargs="*",
            type=str,
            help="list of stages to calculate (e.g. 1, 2, 3, tree, vis). "
            "If left empty, all stages will be listed with a short description.",
        )
        parser.add_argument("-P", "--path", default=defaults["path"], help="airway data path")
        parser.add_argument(
            "-w", "--workers", type=int, default=defaults["workers"], help="number of parallel workers (threads)"
        )
        parser.add_argument(
            "-f", "--force", help="force overwriting of previous stages", default=defaults["force"], action="store_true"
        )
        parser.add_argument(
            "-1",
            "--single",
            help="will do a single patient instead of all patients (useful for testing)",
            default=defaults["single"],
            action="store_true",
        )
        parser.add_argument(
            "-p",
            "--patients",
            type=str,
            action="append",
            help="instead of processing all patients, only these patient ids will be used",
        )
        parser.add_argument(
            "-l",
            "--list_patients",
            action="store_true",
            help="only list patients including their index and generated name in the given stages",
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", default=defaults["verbose"], help="print stdout and stderr directly"
        )
        parser.add_argument(
            "-c",
            "--clean",
            action="store_true",
            default=defaults["clean"],
            help="cleans given stage directories before running them",
        )
        # TODO: Possibly implement these:
        # parser.add_argument("--profile", action="store_true", default=defaults["profile"],
        #                    help="profile modules with cProfile to see which parts are taking long")
        # parser.add_argument("-i", "--interactive", help="run script for single patient without creating subprocess")
        # parser.add_argument("-d", "--dependencies", help="create all given stages including their dependencies")
        # parser.add_argument("-D", "--dependents", help="create all given stages including their dependents")
        # dependency=all predecessor stages to this one, dependant=stages requiring this one (find better names)

    def _validate_args(self, args):
        col = self.col
        if args.clean:
            self.log(
                f"{col.yellow('WARNING')}: Argument {col.green('--clean')} was given. ", stdout=True, add_time=True
            )
            self.log("This will delete and rerun all the supplied stages!", stdout=True, tabs=1)
            self.log(
                f"This might delete data, do you really want to continue ({col.yellow('y')}/{col.yellow('n')}): ",
                stdout=True,
                tabs=1,
                end="",
            )
            question = input()
            if question.lower() not in ["yes", "y"]:
                self.log("User questions their (life-)choices! Aborting!", stdout=True, add_time=True)
                sys.exit(0)
        self.insert_path_keyword_as_path(args)

    def _list_all_stages(self):
        log, col = self.log, self.col
        log(f"Listing all stages", stdout=True, add_time=True)
        for stage_config_name, params in self.stage_configs.items():
            optional_keyword = f" ({col.cyan(params['groups'][0])})" if len(params.get("groups", [])) > 0 else ""
            log(f"{col.green(stage_config_name)}{optional_keyword}: ", stdout=True, tabs=1)
            log(f"- Input stages: [{', '.join(map(col.blue, params.get('inputs', '')))}]", stdout=True, tabs=1)
            log("- " + "\n  ".join(textwrap.wrap(params.get("description", ""), width=50)), stdout=True, tabs=1)
            log("", stdout=True, tabs=1)

    def _get_keyword_to_stages(self) -> Dict[str, List[str]]:
        # Link keyword (eg. '1', '17', 'tree', 'vis', etc.) to stages:
        #              (eg. 'raw_airway', 'stage-01', 'stage-31', etc.)
        keyword_to_stages: Dict[str, List[str]] = {"all": []}
        for stage_name, stage_config in self.stage_configs.items():
            if "stage-" not in stage_name:
                self.exit(f"Cannot handle stage name {self.col.yellow(stage_name)}")
            keyword_to_stages["all"].append(stage_name)

            # Add keyword to generate one or more stages
            keyword_to_stages[str(int(stage_name.split("-")[1]))] = [stage_name]
            for group in stage_config["groups"]:
                if group not in keyword_to_stages:
                    keyword_to_stages[group] = []
                keyword_to_stages[group].append(stage_name)
            stage_config.pop("groups", None)
        return keyword_to_stages

    def _get_stages_to_process(self, args_stages: List[str]) -> Set[str]:
        # Go through each stage in args and handle ranges ('5-7' as well as single calls '3',
        # keywords such as 'vis', 'analysis' and '3+' ranges)
        keyword_to_stage = self._get_keyword_to_stages()
        stages_to_process = set()
        for s_arg in args_stages:  # e.g. s_arg in ['1-3', '4', '5-7', 'analysis']
            try:
                to = 1000
                if "-" in s_arg:
                    fr, to = map(int, s_arg.split("-"))
                elif "+" in s_arg:
                    fr = int(s_arg.split("+")[0])
                else:
                    fr = to = int(s_arg)
                keywords = list(map(str, range(fr, to + 1)))
            except ValueError:
                keywords = [s_arg]
            for s in keywords:
                if s in keyword_to_stage:
                    stages_to_process |= set(keyword_to_stage[s])
        assert all(isinstance(a, str) for a in stages_to_process), "ERROR: Not all keywords are strings"
        return stages_to_process

    def _get_stage_dependencies(self, name: str) -> Set[str]:
        """This returns all the recursive dependencies of a stage"""
        _dependencies = {name}
        # Add all dependencies for each name in _dependencies until there are no changes anymore
        while True:
            copy = _dependencies.copy()
            for dependency in copy:
                # Root stage has no entry in configs, so ignore it
                if dependency != const.ROOT_STAGE:
                    _dependencies |= set(self.stage_configs[dependency]["inputs"])
            if len(_dependencies) == len(copy):
                return _dependencies

    def _get_stages_in_dependency_order(self, args_stages: List[str]) -> List[str]:
        stages_to_process = self._get_stages_to_process(args_stages)
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
            dependencies = self._get_stage_dependencies(curr) & stages_to_process - {const.ROOT_STAGE, curr}
            if all(dep in stages_to_process_in_dependency_order for dep in dependencies):
                stages_to_process_in_dependency_order.append(curr)
            else:
                queue.put(curr)
        return stages_to_process_in_dependency_order

    def handle_args(self, args):
        col = self.col
        start_time = datetime.now()

        self._validate_args(args)

        self.log(f"Using up to {col.green(args.workers)} workers", stdout=True, tabs=1)
        self.log(f"Using {col.green(args.path)} as data path", stdout=True, tabs=1)

        if not args.stages:
            self._list_all_stages()
            sys.exit(0)

        stages_to_process_in_dependency_order = self._get_stages_in_dependency_order(args.stages)

        formatted = ", ".join([col.yellow(s.replace("stage-", "")) for s in stages_to_process_in_dependency_order])
        self.log(f"Stage processing order: {formatted}\n", stdout=True, tabs=1)

        for curr_stage_name in stages_to_process_in_dependency_order:
            assert curr_stage_name in self.stage_configs, f"ERROR: Unknown stage name {curr_stage_name}!"
            self.stage(curr_stage_name, **self.stage_configs[curr_stage_name], **vars(args))

        self.show_error_statistics()
        self.log(f"Finished in {col.green(str(datetime.now() - start_time))}", stdout=True, add_time=True)

    def stage(
        self,
        stage_name: str,
        *,  # Arguments below must be keyword args
        path: Path,
        workers: int,
        force: bool,
        script: str,
        inputs: List[str],
        args: List[str],
        single: bool,
        patients: List[str],  # TODO add desc
        per_patient: bool,
        list_patients: bool,  # TODO add desc
        verbose: bool,  # TODO add desc
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
        log, col = self.log, self.col

        if list_patients:
            self._list_patients(stage_path=path / stage_name)
            return

        script_module = script.replace(".py", "").replace("/", ".")
        log(f"Running script {col.bold()}{script_module}{col.reset()} as module.\n")

        output_stage_path = path / stage_name
        input_stage_paths = [path / input_stage_path for input_stage_path in inputs]

        stage_args = list(map(str, args))

        # check if output directory 'stage-xx' exists
        if output_stage_path.exists() and not force:
            self.exit(f"{col.yellow(output_stage_path)} already exists, use the -f flag to overwrite.")
        else:
            input_stage_path = input_stage_paths[0]
            if input_stage_path.name != "raw_airway" and not input_stage_path.exists():
                self.exit(f"{col.yellow(input_stage_path)} does not exist. " f"Calculate the predecessor stage first!")
            output_stage_path.mkdir(exist_ok=True, parents=True)

            # build the list of subprocess-arguments for later use with subprocess.run
            subprocess_args = []

            # If script should be called for every patient
            if per_patient:
                patient_dirs = input_stage_path.glob("*")
                if patients:
                    keyword_to_patient_id = self.get_keyword_to_patient_id_dict(path)
                    patient_ids = set()
                    for keyword in patients:
                        if keyword not in keyword_to_patient_id:
                            self.exit(f"Patient {col.blue(keyword)} is unknown!")
                        patient_ids.add(keyword_to_patient_id[keyword])
                    log("Handling only these patients:", stdout=True, add_time=True)
                    log("\n".join(map(col.yellow, patient_ids)) + "\n", stdout=True, tabs=1)
                    patient_dirs = list(filter(lambda p: p.name in patient_ids, patient_dirs))

                # Iterate over each patient directory
                for patient_dir in sorted(patient_dirs):
                    patient_output_stage_path = output_stage_path / patient_dir.name
                    patient_input_stage_paths = [isp / patient_dir.name for isp in input_stage_paths]
                    patient_output_stage_path.mkdir(exist_ok=True, mode=0o744)

                    subprocess_args.append([patient_output_stage_path, *patient_input_stage_paths, *stage_args])
                    # Only add a single patient if 'single' given
                    if single:
                        break
            # Call script with default directory otherwise
            else:
                subprocess_args.append([output_stage_path, *input_stage_paths, *stage_args])
            tqdm_prefix = log(f"{col.green(f'Processing {stage_name}')}", add_time=True)
            self.concurrent_executor(subprocess_args, script_module, workers, tqdm_prefix=tqdm_prefix, verbose=verbose)

    def _list_patients(self, stage_path: Path):
        self.log(f"Listing patients in {self.col.green(stage_path.name)}:", stdout=True, add_time=True)
        for index, patient_dir in enumerate(sorted(stage_path.glob("*")), start=1):
            patient_name = get_patient_name(patient_dir.name)
            self.log(f"| {index} | {patient_dir.name} | {patient_name} |", stdout=True, tabs=1)
        self.log("", stdout=True)
