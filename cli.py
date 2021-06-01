#!/usr/bin/python3
from argparse import ArgumentParser
from airway.cli.stages import Stages


def handle_args():
    argparser = ArgumentParser()
    cli_modules = [
        Stages("stages", ["stage", "s"]),
    ]
    for cli_module in cli_modules:
        cli_module.add_as_subparser(argparser)
    argparser.parse_args()
    argparser.handle_args()


if __name__ == "__main__":
    handle_args()
