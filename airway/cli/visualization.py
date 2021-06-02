from argparse import ArgumentParser

from airway.cli.base import BaseCLI


class VisCLI(BaseCLI):
    def add_subparser_args(self, parser: ArgumentParser):
        pass

    def handle_args(self, args):
        print("vis")
        pass
