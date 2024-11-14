from argparse import ArgumentParser
from typing import Type

from . import files, transformations
from . files import File
from . transformations import TransformationRuleSet

# from rich import traceback
# traceback.install(show_locals=True)


def run():

    parser = ArgumentParser()
    parser.add_argument(
        "-f", "--file", help="path of the file to process", required=True)
    parser.add_argument("-m", "--machine",
                        help="Machine gcode set to use", default="snapmaker")

    args = parser.parse_args()

    path: str = args.file
    machine_name = str(args.machine).capitalize()

    machine_file_class: Type[File] = getattr(files, machine_name + "File")
    transformation_class: Type[TransformationRuleSet] = getattr(
        transformations, machine_name + "Transformation")

    file = machine_file_class(path)
    commands = file.parse_commands(file.read_content())
    output_lines = transformation_class(commands).render()

    file.write_content_to("test_output.cnc", output_lines)
