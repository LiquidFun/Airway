#!/usr/bin/python3
import sys
from argparse import ArgumentParser
from airway.cli.stages import StagesCLI
from airway.cli.tutorial import TutorialCLI
from airway.cli.visualization import VisCLI
from airway import __version__


def handle_args():
    cli_modules = [
        StagesCLI(),
        VisCLI(),
        TutorialCLI(),
    ]
    argparser = ArgumentParser()
    argparser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparser = argparser.add_subparsers(
        required=True,
        dest="command",
        title="Airway command",
        # description="commands for ",
        help="help",
    )
    for cli_module in cli_modules:
        cli_module.add_as_subparser(subparser)
    args = argparser.parse_args()
    if hasattr(args, "handle_args"):
        args.handle_args(args)
    else:
        sys.exit("Unknown argument!")


def main():
    handle_args()


if __name__ == "__main__":
    main()
