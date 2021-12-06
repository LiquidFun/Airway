import sys
from pathlib import Path
import random
import string
from typing import Set

import markdown
from weasyprint import HTML

from airway.util.config_parsers import parse_defaults


def get_data_paths_from_args(outputs=1, inputs=1):
    """Returns output and input data paths from sys.argv

    It exits if these are not defined
    """

    if len(sys.argv[1:]) < outputs + inputs:
        print("ERROR: Insufficient count of input/output paths supplied!")
        print(f"\tExpected {outputs} output paths and {inputs} input paths!")
        print(f"\tGot sys.argv: {sys.argv[1:]}")
        sys.exit(1)

    return (Path(sys.argv[index + 1]) for index in range(outputs + inputs))
    # return (
    #     Path(arg) if index <= outputs+inputs else arg
    #     for index, arg in enumerate(sys.argv[1:], start=1)
    # )


def get_patient_name(patient_id):
    random.seed(patient_id)
    vowels = set("aeiou")
    consonants = set(string.ascii_lowercase) - vowels
    either = [sorted(consonants), sorted(vowels)]
    return "".join(random.choice(either[c % 2]) for c in range(4)).capitalize()


def get_keyword_to_patient_ids(stage_configs):
    for stage_config in stage_configs:
        print(stage_config)


def generate_pdf_report(folder_path: Path, file_name_without_ending: str, content: str):
    with open(Path(folder_path) / f"{file_name_without_ending}.md", "w") as file:
        file.write(content)

    with open(Path(folder_path) / f"{file_name_without_ending}.md", "r") as file:
        md = markdown.markdown(file.read())
        md = md.replace("<img", '<img width="600"')
        with open(
            Path(folder_path) / f"{file_name_without_ending}.html", "w", encoding="utf-8", errors="xmlcharrefreplace"
        ) as html_file:
            html_file.write(md)

    a = HTML(Path(folder_path) / f"{file_name_without_ending}.html")
    a.write_pdf(Path(folder_path) / f"{file_name_without_ending}.pdf", presentational_hints=True)


def get_ignored_patients() -> Set[str]:
    return set(map(str, parse_defaults().get("ignore_patients", [])))
