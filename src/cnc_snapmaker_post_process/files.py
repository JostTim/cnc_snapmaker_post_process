from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from pathlib import Path


from .gcode import Command, Gcode, SnapmakerGcode


from typing import List, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .transformations import TransformationRuleSet
    from .patterning import Patterner


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
        self.console.print(
            Panel(
                Text().append("📄 Read content of file ", style="blue").append(f"{path}", style="light_salmon3"),
                title="Reading",
                border_style="blue bold",
                title_align="left",
                highlight=True,
            )
        )
        return self

    def write_content(self):
        path = Path(self.path).resolve()
        with open(path, "w") as f:
            for line in self.content:
                f.write(line)
                f.write("\n")
        self.console.print(
            Panel(
                Text().append("📝 Wrote content to file ", style="blue").append(f"{path}", style="light_salmon3"),
                title="Writing",
                border_style="blue bold",
                title_align="left",
                highlight=True,
            )
        )
        return self

    def parse_commands(self) -> "File":
        gcode = self.gcode_class()
        commands, renders = [], []
        for line_number, line in enumerate(self.content):
            command = gcode.get_code(line)
            renders.append(command.rich_render(line_number + 1))
            commands.append(command)

        self.console.print(
            Panel(
                Group(
                    *[
                        Text(style="blue")
                        .append("Parsing file :")
                        .append(f"{self.path}", style="light_salmon3")
                        .append(" with ")
                        .append(f"{self.gcode_class.__name__}", style="dark_cyan")
                        .append(" class.")
                    ]
                    + [render for render in renders if render is not None]
                ),
                title="Parsing",
                border_style="blue bold",
                title_align="left",
                highlight=True,
            )
        )
        self.commands = commands
        return self

    def to_tranformer(self, transformer_class: Type["TransformationRuleSet"]) -> "TransformationRuleSet":
        return transformer_class(self)

    def to_patterner(self, patterner_class: "Type[Patterner]") -> "Patterner":
        return patterner_class(self)

    def generate_content(self, inplace=False) -> List[str]:
        content = []
        for command in self.commands:
            content.append(command.generate_line())

        if inplace:
            self.content = content
        return content

    @classmethod
    def from_commands(cls, path: str | Path, commands: List[Command]):
        file = cls(path)
        file.commands = commands
        file.generate_content(inplace=True)
        return file


class SnapmakerFile(File):

    gcode_class = SnapmakerGcode
