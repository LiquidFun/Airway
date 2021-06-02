import subprocess
import sys
from abc import abstractmethod
from argparse import ArgumentParser, _SubParsersAction
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from tqdm import tqdm

from airway.util import const
from airway.util.color import Color
from airway.util.config_parsers import parse_defaults, parse_stage_configs
from airway.util.util import get_patient_name


class BaseCLI:
    def __init__(self, names: List[str]):
        self.defaults = parse_defaults()
        self.stage_configs = parse_stage_configs()
        self.log_path = const.LOGS_PATH / f"log_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}"
        self.col = Color()
        self.errors = {}
        self.name = names[0]
        self.aliases = names[1:]

    @abstractmethod
    def add_subparser_args(self, parser: ArgumentParser):
        pass

    @abstractmethod
    def handle_args(self, args):
        pass

    def _handle_args_wrapper(self, args):
        self.log(f"Running {self.col.bold()}{self.col.green('Airway')}", stdout=True, add_time=True)
        # Functions to run before handle_args()
        self.handle_args(args)
        # Functions to run after handle_args()
        self._remove_oldest_log_files()
        self._link_last_log_file()

    def _remove_oldest_log_files(self):
        log_files = sorted(self.log_path.parent.glob("*"), key=lambda p: p.stat().st_mtime)
        for existing_log_file in log_files[:-self.defaults["max_log_files"]]:
            existing_log_file.unlink()

    def _link_last_log_file(self):
        const.LOG_LN_PATH.unlink(missing_ok=True)
        self.log_path.link_to(const.LOG_LN_PATH)
        self.log(f"Saved log file to {self.col.green(self.log_path)} (linked to ./log)", stdout=True, add_time=True)

    def add_as_subparser(self, subparser_action: _SubParsersAction):
        subparser = subparser_action.add_parser(self.name, aliases=self.aliases, help="help sub")
        self.add_subparser_args(subparser)
        subparser.set_defaults(handle_args=self._handle_args_wrapper)

    @staticmethod
    def subprocess_executor(args):
        """Run a single script with args"""
        # return subprocess.run(argument, capture_output=True, encoding="utf-8")
        # Above is Python 3.7, so PIPE instead of capture_output=True

        # Important as the pycharm debugger expects strings in the flags of subprocess, this causes it to crash
        # as this program puts PosixPaths into the arg list.
        args_as_strings = list(map(str, args))
        return subprocess.run(args_as_strings, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def concurrent_executor(self, subprocess_args, script_module, workers, tqdm_prefix="", verbose=False):
        """Executes multiple scripts as their own modules, logging their STDOUT and STDERR"""
        subprocesses = [["python3", "-m", script_module] + args for args in subprocess_args]

        def get_progress_bar(process_count: int) -> tqdm:
            bar_fmt = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_inv_fmt}{postfix}]"
            return tqdm(total=process_count, unit="run", desc=tqdm_prefix, ncols=80, bar_format=bar_fmt)

        col = self.col
        with ProcessPoolExecutor(max_workers=workers) as executor:
            stage_name = Path(subprocesses[0][3]).parent.name
            with get_progress_bar(len(subprocesses)) as progress_bar:
                for count, retVal in enumerate(executor.map(self.subprocess_executor, subprocesses), start=1):
                    out = f"\nOutput for Process {col.yellow(count)}/{col.yellow(len(subprocesses))}"
                    out += f" (Patient {col.green(Path(retVal.args[3]).name)})\n"
                    out += f"STDOUT:\n{retVal.stdout}\n"
                    progress_bar.update()

                    if len(retVal.stderr) > 0:
                        out += f"\nSTDERR:\n{retVal.stderr}\n"
                        self.errors[stage_name] = self.errors.get(stage_name, []) + [count]
                    self.log(out, tabs=1, add_time=True, stdout=verbose)
            if stage_name in self.errors:
                plural = "processes" if len(self.errors[stage_name]) > 1 else "process"
                self.log(col.red(f"{len(self.errors[stage_name])} {plural} had errors!") + "\n", stdout=True, tabs=1)

    def get_keyword_to_patient_id_dict(self, data_path: Path) -> Dict[str, str]:
        keyword_to_patient_id = {}
        for stage_name, config in self.stage_configs.items():
            if config["per_patient"]:
                stage_path = data_path / stage_name
                keyword_to_patient_id |= {pat_dir.name: pat_dir.name for pat_dir in stage_path.glob("*")}
        for index, patient in enumerate(sorted(keyword_to_patient_id), start=1):
            keyword_to_patient_id[str(index)] = patient
            keyword_to_patient_id[get_patient_name(patient)] = patient
        return keyword_to_patient_id

    def log(self, message: str, stdout=False, add_time=False, tabs=0, end="\n", exit_code=None):
        """Logs to a file and optionally to stdout

        args:
            message: a string (possibly multiline) which will be logged
            stdout: if the message should be printed to stdout
            add_time: will add formatted timestamp for the first non-empty message
                      possibly replacing indentation through tabs
            tabs: padding in front of each line in the message.
                  1 tab will align it with lines which have add_time
            end: same as the end arg in print(), is just passed through
            exit_code: code to exit on, if None then will continue normally
        """
        col = self.col
        self.log_path.parent.mkdir(exist_ok=True)
        lines = message.split("\n")
        time_added = False
        for i in range(len(lines)):
            add_time_for_this_line = lines[i].strip() != "" and add_time and not time_added
            tabs_adjusted_to_time = tabs - 1 if add_time_for_this_line else tabs
            if tabs_adjusted_to_time >= 1:
                prefix = " " * 11 * tabs_adjusted_to_time
                lines[i] = prefix + lines[i]
            if add_time_for_this_line:
                time_fmt = f"{col.reset()}[{col.green()}{datetime.now().strftime('%H:%M:%S')}{col.reset()}] "
                lines[i] = time_fmt + lines[i]
                time_added = True
        message = "\n".join(lines)
        with open(self.log_path, "a+") as log_file:
            if stdout:
                print(message, end=end)
            filtered_message = col.filter_color_codes(message)
            log_file.write(filtered_message + end)
        if exit_code is not None:
            sys.exit(exit_code)
        return message

    def show_error_statistics(self):
        """Display error statistics for all computed stages using a dict"""
        if self.errors:
            self.log(f"Error Statistics:", stdout=True, add_time=True)
            print(self.col.red())
            for key, val in self.errors.items():
                plural = "errors" if len(val) > 1 else "error"
                self.log(f"{key}: {len(val):>3} {plural}", stdout=True, tabs=1)
            self.log(f"Overall errors: {sum(self.errors.values())}\n{self.col.reset()}", stdout=True, tabs=1)
        else:
            self.log("No errors occurred", stdout=True, add_time=True)
