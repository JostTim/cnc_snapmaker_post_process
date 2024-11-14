from rich.console import Console
from pathlib import Path

from .gcode import Command, Gcode, SnapmakerGcode

from typing import List


class File:

    gcode_class = Gcode

    def __init__(self, path):
        self.path = path
        self.console = Console()

    def read_content(self):
        path = Path(self.path).resolve()
        with open(path, "r") as f:
            content = f.read()
        return content

    def write_content_to(self, path, content: List[str]):
        path = Path(path).resolve()
        with open(path, "w") as f:
            for line in content:
                f.write(line)
                f.write("\n")

    def parse_commands(self, content: str) -> List[Command]:
        lines = content.splitlines()

        gcode = self.gcode_class()
        commands = []
        for line in lines:
            line = line.lstrip()
            command = gcode.get_code(line)
            self.console.print(command.rich_render())
            commands.append(command)

        return commands


class SnapmakerFile(File):

    gcode_class = SnapmakerGcode
