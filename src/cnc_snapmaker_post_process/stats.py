from rich.text import Text
from rich.console import Group
from rich.panel import Panel

from .gcode import Command
from .files import File

from typing import Dict, Type, List


class FileStatistics:

    classes: Dict[Type[Command], Dict[Type[Command] | None, int]]

    def __init__(self, file: File):
        self.file = file
        self.classes = {}

    def record(self, original_command: Command, transformed_command: Command | List[Command] | None):

        if isinstance(transformed_command, list):
            for transformed_c in transformed_command:
                self.record(original_command, transformed_c)

        else:
            original_command_class = type(original_command)
            transformed_command_class = type(transformed_command) if transformed_command is not None else None

            class_statistics = self.classes.get(original_command_class, {})

            counts = class_statistics.get(transformed_command_class, 0) + 1

            class_statistics[transformed_command_class] = counts

            self.classes[original_command_class] = class_statistics

    def print_report(self):

        lines = []
        for command_found, transformed_commands in self.classes.items():
            for transformed_command, count in transformed_commands.items():
                lines.append(self.print_association(command_found, transformed_command, count))
        self.file.console.print(
            Panel(
                Group(*lines),
                title="Statistics Report",
                title_align="left",
                border_style="chartreuse1",
            )
        )

    def print_association(self, command_found: Type[Command], transformed_command: Type[Command] | None, count: int):
        plural = "s" if count > 1 else ""
        if transformed_command is not None:
            return (
                Text(style="chartreuse1")
                .append("🔄 Transformed command")
                .append(f" {command_found.__name__}", style="dark_cyan")
                .append(" into")
                .append(f" {transformed_command.__name__}", style="dark_cyan")
                .append(f" {count}", style="magenta1")
                .append(f" time{plural}")
            )
        else:
            return (
                Text(style="yellow4")
                .append("⏩ No changement for command")
                .append(f" {command_found.__name__}", style="dark_cyan")
                .append(f" {count}", style="magenta1")
                .append(f" time{plural}")
            )
