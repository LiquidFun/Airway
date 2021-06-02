#!/usr/bin/python3
import sys
from argparse import ArgumentParser
from airway.cli.stages import StagesCLI
from airway.cli.visualization import VisCLI


def handle_args():
    cli_modules = [
        StagesCLI(["stage", "stages", "s"]),
        VisCLI(["vis", "visualization", "v"]),
    ]
    argparser = ArgumentParser()
    subparser = argparser.add_subparsers(
        required=True, dest="command", title="command",
        description="commands for ",
        help="help",
    )
    for cli_module in cli_modules:
        cli_module.add_as_subparser(subparser)
    args = argparser.parse_args()
    if hasattr(args, "handle_args"):
        args.handle_args(args)
    else:
        sys.exit("Unknown argument!")


if __name__ == "__main__":
    handle_args()
