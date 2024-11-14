from argparse import ArgumentParser
from pathlib import Path

from . import files, transformations
from . files import File
from . transformations import TransformationRuleSet

from typing import Type
# from rich import traceback
# traceback.install(show_locals=True)


def run():

    parser = ArgumentParser()
    parser.add_argument(
        "-f", "--file", help="path of the file to process", required=True)
    parser.add_argument("-m", "--machine",
                        help="Machine gcode set to use", default="snapmaker")

    args = parser.parse_args()

    path = Path(args.file).resolve()
    machine_name = str(args.machine).capitalize()

    machine_file_class: Type[File] = getattr(files, machine_name + "File")
    transformation_class: Type[TransformationRuleSet] = getattr(
        transformations, machine_name + "Transformation")

    root, filename, extension = path.parent, Path(path).stem, Path(path).suffix

    output_path = root / f"{filename}-transformed{extension}"

    file = machine_file_class(path)
    file = (file.
            read_content().
            parse_commands().
            to_tranformer(transformation_class).
            transform().
            to_file(output_path).
            write_content()
            )
