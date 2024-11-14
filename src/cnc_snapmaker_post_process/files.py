from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from pathlib import Path


from .gcode import Command, Gcode, SnapmakerGcode

from typing import List, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .transformations import TransformationRuleSet


class File:

    gcode_class = Gcode
    content: List[str]
    commands: List[Command]

    def __init__(self, path: str | Path):
        self.path = path
        self.console = Console()

    def read_content(self):
        path = Path(self.path).resolve()
        with open(path, "r") as f:
            content = f.read()
        self.content = [line.lstrip() for line in content.splitlines()]
        self.console.print(Text().append(
            "Read content of file ", style="blue").append(f"{path}", style="bright_magenta"))
        return self

    def write_content(self):
        path = Path(self.path).resolve()
        with open(path, "w") as f:
            for line in self.content:
                f.write(line)
                f.write("\n")
        self.console.print(Text().append(
            "Wrote content to file ", style="blue").append(f"{path}", style="bright_magenta"))
        return self

    def parse_commands(self):
        gcode = self.gcode_class()
        commands, renders = [], []
        for line_number, line in enumerate(self.content):
            command = gcode.get_code(line)
            renders.append(command.rich_render(line_number + 1))
            commands.append(command)
        self.console.print(
            Panel(Group(*[render for render in renders if render is not None]),
                  title="Parsing",
                  border_style='blue',
                  title_align='left'))
        self.commands = commands
        return self

    def to_tranformer(self, transformer_class: Type["TransformationRuleSet"]) -> "TransformationRuleSet":
        return transformer_class(self)


class SnapmakerFile(File):

    gcode_class = SnapmakerGcode
