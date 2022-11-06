import shutil
import tempfile
from functools import partial
from pathlib import Path

from airway.cli.base import BaseCLI
from airway.util.config_parsers import update_defaults
from airway.util.const import PACKAGE_PATH, CONFIGS_PATH


class TutorialCLI(BaseCLI):
    def __init__(self):
        super().__init__()
        self.logv = partial(self.log, stdout=True, tabs=1, max_width=120)  # Verbose
        self.logvt = partial(self.logv, add_time=True)  # Verbose & time

    def add_subparser_args(self) -> None:
        parser = self.add_subparser(["tutorial", "t"], "CLI for running the example and tutorial")

    def handle_args(self, args) -> None:
        c = self.col

        example_model_path = PACKAGE_PATH / "airway" / "example_data" / "model.npz"
        example_stages_path = Path(tempfile.mkdtemp(prefix="airway-tutorial-"))
        patient_name = "pat01"
        keyword = "example"
        flags = {"path": keyword}

        def question(msg: str, default_is_yes=False):
            self.logvt(f"{msg} [{c.yellow('yY'[default_is_yes])}/{c.yellow('Nn'[default_is_yes])}]? ", end=c.yellow())
            answer = input().strip().lower() in (["yes", "y"] + ([""] if default_is_yes else []))
            self.logv(c.reset())
            return answer

        def delay(msg: str):
            self.logvt(f"{msg}", end=c.yellow())
            input()
            self.logv(c.reset())

        def command(arg, **kwargs):
            flags_ = [f"{c.green('--' + key)} {c.cyan(value)}" for key, value in kwargs.items()]
            return f"\n{c.purple('$')} " + " ".join([arg] + flags_) + "\n"

        self.logv("Running tutorial")
        self.logv(
            f"This tutorial will guide you through running the "
            f"example supplied in \n\t{self.col.cyan(example_model_path)}"
        )
        self.logv(f"It is recommended to have another terminal ready to type commands if necessary")
        if not question(
            f"Do you wish to use the default directory for the examples?\n\t{c.green(example_stages_path)}",
            default_is_yes=True,
        ):
            self.logv("What directory do you wish to use instead?")
            example_stages_path = Path(input())
        update_defaults({"paths": {keyword: str(example_stages_path.absolute())}})
        self.logv(
            f"Updated defaults! Now you can use the keyword {c.yellow(keyword)} instead of using the full path "
            f"when using the {c.green('--path')} argument in the stages/vis commands."
        )
        self.logv(f"You can update the defaults anytime manually in {c.green(CONFIGS_PATH / 'defaults.yaml')}")
        with open(CONFIGS_PATH / "defaults.yaml", "r") as file:
            self.logv(f"Here is what the {c.green('defaults.yaml')} currently looks like this: {c.cyan()}")
            self.logv("=" * 60)
            self.logv(file.read())
            self.logv(c.reset())
        self.logv(f"To view each parameter including an explanation see {c.green('example_defaults.yaml')}.")
        if question(
            f"Do you wish to overwrite the default path to always use the keyword {c.yellow(keyword)}?"
            f"\nIf you don't then you will have to remember to add {c.green('--path')} {c.yellow(keyword)}."
        ):
            update_defaults({"path": keyword})
            self.logv(f"Defaults updated! Now you may use stages/vis without adding {c.green('--path')}")
            # del flags['path']
        self.logv(f"Let's get to running the stages now!")
        patient_dir = example_stages_path / "stage-01" / patient_name
        patient_dir.mkdir(exist_ok=True, parents=True)
        shutil.copy(example_model_path, patient_dir)
        self.logv(f"The example model in {c.green(example_model_path)} has been copied to stage-01 for you.")
        self.logv(
            f"This means the input stage was defined for patient {c.cyan(patient_name)}"
            f" and most other stages can be calculated using this stage."
        )
        self.logv(f"To run the next stage type: {command('airway stages 2', **flags)}")
        delay("Continue?")
        self.logv(f"To see what each stage does you can type: {command('airway stages')}")
        delay("Continue?")
        self.logv(
            f"Now to visualise the segments we need to calculate a couple more stages. To do this type: "
            f"{command('airway stages 2-10 color_masks 3d', **flags)}"
            f"\nNote that {c.green('2-10')} is a range, "
            f"and both {c.green('color_masks')} "
            f"and {c.green('3d')} are stage names (these are shown in parenthesis in the stage overview)."
        )
        delay("Continue?")
        self.logv(f"You need to install blender now (e.g. sudo apt install blender)")
        self.logv(
            f"Now you can visualise it in 3D in Blender by typing: "
            f"{command('airway vis -o pat01', **flags)}"
            f"Blender should open with the 3D model of the example patient."
        )
        self.logv(f"As you may notice, the example data is not a real patient.")
        self.logv(f"It does however have the same structure which might be found in a real patient.")
        self.logv(
            f"To run it on your own data you now have to create the {c.yellow('model.npz')} "
            f"file and put it into the stage-01 directory of your own data path."
        )
        self.logv(f"Your data path can be called whatever you want, just add a keyword in the defaults.yaml file.")
        self.logv(f"Then run the commands you have seen here again with a different path flag.")
