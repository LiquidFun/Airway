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

import subprocess
from concurrent.futures import ProcessPoolExecutor


reqVersion = (3, 6)  # because of concurrent.futures and f-strings
currVersion = (sys.version_info.major, sys.version_info.minor)
assert currVersion < reqVersion, "ERROR: Your python is too old. Minimum: 3.6"


def stage(path: str, worker: int, forced: bool, prev_stage: str, stage_id, script_path, *args):
    """ stage()
    
    stage() is the meta function for calculating most stages in parallel.

    TODO: more documentation
    
    args: all remaining arguments are passed to the script
    """
    print(f"Processing {stage_id}... ")

    raw_path = Path(path) / prev_stage
    out_path = Path(path) / stage_id

    # check if predecessor stage exists
    assert raw_path.exists(), f"ERROR: {raw_path} does not exist. Calculate the predecessor stage first!"

    # check if output directory 'stage-xx' exists
    if out_path.exists() and not forced:
        print(f"WARNING: {out_path} already exists, use the -f flag to overwrite.")
        sys.exit(1)
    else:
        path_dirs = raw_path.glob('*')
        out_path.mkdir(exist_ok=True, mode=0o777)

        # build the list of subprocess-arguments for later use with subprocess.run
        subprocess_args = []
        for curr_path in path_dirs:
            out_pat_path = out_path / curr_path
            raw_pat_path = raw_path / curr_path.name
            out_pat_path.mkdir(exist_ok=True, mode=0o777)

            subprocess_args.append([
                "python3",
                script_path,
                raw_pat_path,
                out_pat_path,
                *args
            ])
        concurrent_executor(subprocess_args, worker)


def subprocess_executor(argument):
    return subprocess.run(argument, capture_output=True, encoding="utf-8")


def concurrent_executor(subprocess_args, worker):
    count = 0
    with ProcessPoolExecutor(max_workers=worker) as executor:
        for retVal in executor.map(subprocess_executor, subprocess_args):
            count += 1
            print("---- Output for process {}: ----\nSTDOUT:\n{}\n\nSTDERR:\n{}\n\n"
                  .format(count, retVal.stdout, retVal.stderr))

            if len(retVal.stderr) > 0:
                stage = str(Path(subprocess_args[0][3]).parents[0].name)
                if stage in errors:
                    errors[stage].append(count)
                else:
                    errors[stage] = [count]


def show_error_statistics():
    print("\n\n########## ERROR STATISTICS  #########\n")
    if errors:
        err_count = 0
        for key, val in errors.items():
            err_count += len(val)
            print("\n{}:{:>3} errors".format(key, len(val)))
        print("\n++++ Overall errors: {} ++++\n".format(err_count))
    else:
        print("\n++++ No errors occured ++++\n")


def main():
    base_path = Path(sys.argv[0]).parents[0]

    defaults = {"path": None, "workers": 4, "force": False}
    config_path = Path(base_path) / "config"
    if Path(config_path).exists():
        with open(config_path, 'r') as config:
            for line in config:
                if '=' in line:
                    l = line.strip().split('=')
                    rest = ''.join(l[1:])
                    defaults[l[0]] = rest
                    if l[0] == "force":
                        defaults[l[0]] = rest.lower() == "true"

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", default=defaults["path"], help="working path")
    parser.add_argument("-s", "--stages", type=int, action='append', help="list of stages to calculate")
    parser.add_argument("-w", "--worker", type=int, default=defaults["workers"], help="number of parallel workers")
    parser.add_argument("-f", "--force", help="force overwriting of previous stages",
                        default=defaults["force"], action="store_true")
    args = parser.parse_args()

    assert args.path is not None, "ERROR: Working path required"
    path = args.path

    if args.stages is None:
        print("ERROR: No stages given, doing nothing.")
        sys.exit(1)
    else:
        stages = set(args.stages)

    workers = args.worker
    forced = args.force

    if 1 in stages:
        # stage01(path, worker, forced, predStage, stageID, scriptPath)
        stage(path, workers, forced, "raw_airway", "stage-01",
              str(base_path) + "/image_processing/save_images_as_npy.py")
    if 2 in stages:
        stage(path, workers, forced, "stage-01", "stage-02",
              str(base_path) + "/image_processing/remove_all_0_layers.py")
    if 3 in stages:
        stage(path, workers, forced, "stage-02", "stage-03",
              str(base_path) + "/tree_extraction/bfs_distance_method.py")
    if 4 in stages:
        stage(path, workers, forced, "stage-03", "stage-04",
              str(base_path) + "/tree_extraction/create_tree.py")
    if 5 in stages:
        stage(path, workers, forced, "stage-04", "stage-05",
              str(base_path) + "/tree_extraction/compose_tree.py")
    if 6 in stages:
        stage(path, workers, forced, "stage-05", "stage-06",
              str(base_path) + "/tree_extraction/post_processing.py")
    if 7 in stages:
        stage(path, workers, forced, "stage-06", "stage-07",
              str(base_path) + "/tree_extraction/separate_lobes.py")
    if 10 in stages:  # analysis
        retVal = subprocess.run([
            'python3',
            str(base_path) + '/analysis/analyze_tree.py',
            path
        ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
        retVal = subprocess.run([
            'python3',
            str(base_path) + '/visualization/plot_dist_to_first_split.py',
            path,
            "False"
        ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
        retVal = subprocess.run([
            'python3',
            str(base_path) + '/analysis/plot_connected_lobes_status.py',
            path,
            "False"
        ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))

    if 11 in stages:  # analysis
        retVal = subprocess.run([
            'python3',
            str(base_path) + '/analysis/metadata.py',
            path
        ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
    if 20 in stages:  # preparing for visualization
        stage(path, workers, forced, "stage-02", "stage-20", f"{base_path}/image_processing/generate_bronchus_coords.py")
    if 21 in stages:  # object generation
        stage(path, workers, forced, "stage-02", "stage-21", f"{base_path}/obj_generation/gen_obj.py")
        stage(path, workers, True, "stage-07", "stage-21", f"{base_path}/obj_generation/gen_split_obj.py")
    if 22 in stages:  # plots and fancy stuff
        # Generate split plots
        stage(
            path,
            workers,
            forced,
            "stage-06",
            "stage-22",
            Path(base_path) / "visualization/plot_splits.py",
            "False",  # This tells the script not to display pyplot interactively
        )
    if 23 in stages:  # plots and fancy stuff
        # generate 2D-plots of the whole tree and the lobes
        stage(path, workers, forced, "stage-07", "stage-23", base_path.joinpath("visualization/generate_2d_tree.py"))
    if 29 in stages:  # website has many more  prerequisites
        stage(path, workers, forced, "stage-22", "stage-29", f"{base_path}/visualization/create_website.py")
    if len(stages) == 0:
        print("ERROR: Unknown Stage given. Following stages available:")
        sys.exit(1)

    show_error_statistics()


##########

if __name__ == "__main__":
    errors = {}  # used for collecting errors while executing parallel tasks
    oldmask = os.umask(0o002)
    main()
    os.umask(oldmask)
