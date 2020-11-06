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

def stage(path, worker, forced, predStage, stageID, scriptPath, *args):
    """ stage()
    
    stage() is the meta function for calculating most stages in parallel.

    TODO: more documentation
    
    args: all remaining arguments are passed to the script
    """
    print("processing {} ... ".format(stageID))

    rawPath = path + "/" + predStage
    outPath = path + "/" + stageID
    
    # check if predecessor stage exists
    if not checkPath(rawPath):
        print("ERROR: {} does not exists. Calculate the predecessor stage first!"
                .format(rawPath))
        sys.exit(1)
    
    # check if output directory 'stage-xx' exists
    if  checkPath(outPath) and not  forced:
        print(  "WARNING: {} already exists, use the -f flag to overwrite."
                .format(outPath))
        sys.exit(1)
    else:

        patDirs = Path(rawPath).glob('*')
        createDir(outPath)

        #build the list of subprocesse-arguments for later use with subprocess.run
        subprocessArgs = []
        for pat in patDirs:
            #print("processing patient-id {}".format(str(pat.name)))

            outPatPath = outPath + "/" + str(pat.name)
            rawPatPath = rawPath + "/" + str(pat.name)
            createDir(outPatPath)

            subprocessArgs.append([
                "python3",
                scriptPath,
                rawPatPath,
                outPatPath,
                *args
            ])

        concurrentExecutor(subprocessArgs, worker)

def subprocessExecutor(argument):
    return subprocess.run(argument, capture_output=True, encoding="utf-8")

def concurrentExecutor(subprocessArgs, worker):
    count = 0
    with ProcessPoolExecutor(max_workers=worker) as executor:
        for retVal in executor.map(subprocessExecutor, subprocessArgs):
            count += 1
            print("---- Output for process {}: ----\nSTDOUT:\n{}\n\nSTDERR:\n{}\n\n"
                    .format(count, retVal.stdout, retVal.stderr))

            if len(retVal.stderr) > 0:
                stage = str(Path(subprocessArgs[0][3]).parents[0].name)
                if stage in errors: 
                    errors[stage].append(count)
                else:
                    errors[stage] = [count]
                
def checkPath(pathString):
    path = Path(pathString)
    if path.is_dir():
        return True
    else:
        return False

def createDir(pathString):
    path = Path(pathString)
    path.mkdir(exist_ok=True, mode=0o777)

def show_error_statistics():
    print("\n\n########## ERROR STATISTICS  #########\n")
    if len(errors) > 0:
        err_count = 0
        for key, val in errors.items():
            err_count += len(val)
            print("\n{}:{:>3} errors".format(key,len(val)))
        print("\n++++ Overall errors: {} ++++\n".format(err_count))
    else:
        print("\n++++ No errors occured ++++\n")

def main():

    basePath = Path(sys.argv[0]).parents[0]

    defaults = {"path": None, "workers": 4, "force": False}
    configPath = os.path.join(basePath, "config")
    if os.path.exists(configPath):
        with open(configPath, 'r') as config:
            for line in config:
                if '=' in line:
                    l = line.strip().split('=')
                    rest = ''.join(l[1:])
                    defaults[l[0]] = rest
                    if l[0] == "force":
                        defaults[l[0]] = rest.lower() == "true"

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", default=defaults["path"],
                        help="working path")
    parser.add_argument("-s", "--stages", type=int,
                        action='append', help="list of stages to calculate")
    parser.add_argument("-w", "--worker", type=int,
                        default=defaults["workers"],
                        help="number of parallel workers")
    parser.add_argument("-f", "--force", help="force overwriting of previous stages",
                        default=defaults["force"], action="store_true")
    args = parser.parse_args()

    if args.path is None:
        print("ERROR: path needed")
        sys.exit(1)
    elif not checkPath(args.path):
        print("ERROR: path does not exist")
        sys.exit(1)
    else:
        path = args.path

    if args.stages is None:
        print("ERROR: No stages given, doing nothing.")
        sys.exit(1)
    else:
        stages = set(args.stages)
    
    worker = args.worker
    forced = args.force

    if 1 in stages:
        #stage01(path, worker, forced, predStage, stageID, scriptPath)
        stage(path, worker, forced, "raw_airway", "stage-01",
              str(basePath) + "/image_processing/save_images_as_npy.py")
    if 2 in stages:
        stage(path, worker, forced, "stage-01", "stage-02",
              str(basePath) + "/image_processing/remove_all_0_layers.py")
    if 3 in stages:
        stage(path, worker, forced, "stage-02", "stage-03",
              str(basePath) + "/tree_extraction/bfs_distance_method.py")
    if 4 in stages:
        stage(path, worker, forced, "stage-03", "stage-04",
              str(basePath) + "/tree_extraction/create_tree.py")
    if 5 in stages:
        stage(path, worker, forced, "stage-04", "stage-05",
              str(basePath) + "/tree_extraction/compose_tree.py")
    if 6 in stages:
        stage(path, worker, forced, "stage-05", "stage-06",
              str(basePath) + "/tree_extraction/post_processing.py")
    if 7 in stages:
        stage(path, worker, forced, "stage-06", "stage-07",
              str(basePath) + "/tree_extraction/separate_lobes.py")
    if 10 in stages: # analysis
        retVal = subprocess.run([
                'python3',
                str(basePath) + '/analysis/analyze_tree.py',
                path
            ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
        retVal = subprocess.run([
                'python3',
                str(basePath) + '/visualization/plot_dist_to_first_split.py',
                path,
                "False"
            ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
        retVal = subprocess.run([
                'python3',
                str(basePath) + '/analysis/plot_connected_lobes_status.py',
                path,
                "False"
            ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))

    if 11 in stages: # analysis
        retVal = subprocess.run([
                'python3',
                str(basePath) + '/analysis/metadata.py',
                path
            ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(retVal.stdout, retVal.stderr))
    if 20 in stages: # preparing for visualization
        stage(path, worker, forced, "stage-02", "stage-20",
              str(basePath) + "/image_processing/generate_bronchus_coords.py")
    if 21 in stages: # object generation
        stage(path, worker, forced, "stage-02", "stage-21",
              str(basePath) + "/obj_generation/gen_obj.py")
        stage(path, worker, True, "stage-07", "stage-21",
              str(basePath) + "/obj_generation/gen_split_obj.py")
    if 22 in stages: # plots and fancy stuff
        # Generate split plots
        stage(
            path,
            worker,
            forced,
            "stage-06",
            "stage-22",
            os.path.join(basePath, "visualization/plot_splits.py"),
            "False", # This tells the script not to display pyplot interactively
        )
    if 23 in stages: # plots and fancy stuff
        # generate 2D-plots of the whole tree and the lobes
        stage(path, worker, forced, "stage-07", "stage-23",
            basePath.joinpath("visualization/generate_2d_tree.py"))
    if 29 in stages: # website has many more  prerequisites
        stage(path, worker, forced, "stage-22", "stage-29", 
              str(basePath) + "/visualization/create_website.py")
    if len(stages) == 0:
        print("ERROR: Unknown Stage given. Following stages available:")
        sys.exit(1)
    
    show_error_statistics()

##########
errors = {} # used for collecting errors while executing parallel tasks

reqVersion = (3,6) # because of concurrent.futures
currVersion = (sys.version_info.major, sys.version_info.minor)
if currVersion < reqVersion:
    print("ERROR: Your python is too old. Minimum: 3.6")
    sys.exit(1)
else:
    oldmask = os.umask(0o002)
    main()
    os.umask(oldmask)
