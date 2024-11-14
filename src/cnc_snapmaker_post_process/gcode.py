from rich.console import Group
from rich.text import Text
from re import Pattern, compile

from . exceptions import MatchException
from . memories import (SelfReturn, PreviousXDefault, PreviousYDefault,
                        PreviousZDefault, PreviousFDefault, PreviousXStorer, PreviousYStorer, PreviousZStorer)

from typing import List, Type, get_type_hints


class Command:

    pattern: Pattern[str] | List[Pattern[str]]
    line: str

    def __init__(self, line: str):
        self.line = line

        if line == "":
            return

        reverse_class_list: List[Type[Command]] = list(
            reversed(type(self).mro()))
        reverse_class_list = [
            cls for cls in reverse_class_list if issubclass(cls, Command) and cls != Command]

        # console.print(reverse_class_list)

        attributes = {}
        type_hints = {}
        for cls in reverse_class_list:
            d = cls.match(line)
            if d is not None:
                # console.print(f"This matches {cls.__name__}", style="cyan2")
                type_hints.update(get_type_hints(cls))
                attributes.update(d)
            else:
                # console.print(
                #     f"Not a {type(self).__name__}", style="bright_red")
                raise MatchException("No match")

        self.set_attributes(
            self.finish_attributes_dict(attributes, type_hints)
        )

    def set_attributes(self, dict: dict):
        for key, value in dict.items():
            setattr(self, key, value)

    @ classmethod
    def match(cls: "Type[Command]", line) -> dict | None:
        if not hasattr(cls, "pattern"):
            return {}  # if it's a placeholder class, always match
        patterns = [cls.pattern] if not isinstance(
            cls.pattern, list) else cls.pattern
        result = {}
        for pattern in patterns:
            if match := pattern.search(line):
                result.update(match.groupdict())
            else:
                return None
        return result

    @ classmethod
    def parse_line(cls, object):
        try:
            return cls(object)
        except MatchException:
            return None

    def process(self):
        return [self.line]

    def finish_attributes_dict(self, attributes: dict, type_hints: dict):
        attributes = {k: type_hints.get(k, SelfReturn)(v)
                      for k, v in attributes.items()}
        # console.print(f"Finished {type(self).__name__}", style="bright_green")
        return attributes

    @ classmethod
    def manual_instanciation(cls, dict_attributes):

        obj = cls("")
        obj.set_attributes(dict_attributes)
        return obj

    def __str__(self):
        values = [f"{key}:{value}" for key,
                  value in self.__dict__.items() if key != "line"]
        return f"<{type(self).__name__}> " + ", ".join(values)

    def __repr__(self):
        return str(self)

    def rich_render(self):

        if self.line == "":
            identification = ((" - ", ""), ("Empty line", "gray3"))
        elif isinstance(self, UnidentifiedCommand):
            identification = (
                (" - ", ""),
                ("Unidentified command type", "dark_orange3"))
        else:
            identification = (("\n\t", ""),
                              ("Identified as ", "blue"),
                              (f"{self}", "bright_magenta"))

        return Text.assemble(
            ("- Parsed line ", "blue"),
            (f'"{self.line}"', "cyan"),
            *identification
        )


class UnidentifiedCommand(Command):

    def __init__(self, line):
        self.line = line


class EmptyCommand(Command):
    def __init__(self):
        self.line = ""


class UnitsCommand(Command):

    pattern = compile("G(?:20)|(?:21)")


class MetricCommand(UnitsCommand):
    pattern = compile("G21")


class ImperialCommand(UnitsCommand):
    pattern = compile("G20")


class SpindleCommand(Command):
    pass


class StopSpindleCommand(SpindleCommand):

    pattern = compile("M5")


class StartSpindleCommand(SpindleCommand):

    pattern = compile(r"M3 +P(?P<P>\d+)")
    P: int


class MoveModeCommand(Command):
    pass


class AbsoluteCommand(MoveModeCommand):
    pattern = compile("G90")


class RelativeCommand(MoveModeCommand):
    pattern = compile("G91")


class MoveCommand(Command):

    pattern = compile(
        r"G(?P<G>\d) +(?:X(?P<X>[\d.-]+))? *(?:Y(?P<Y>[\d.-]+))? *(?:Z(?P<Z>[\d.-]+))? *(?:F(?P<F>[\d.-]+))?")
    G: int
    X: PreviousXDefault
    Y: PreviousYDefault
    Z: PreviousZDefault
    F: PreviousFDefault
    start_X: float
    start_Y: float
    start_Z: float

    def finish_attributes_dict(self, attributes: dict, type_hints: dict):

        attributes["start_X"] = PreviousXStorer(attributes["X"])
        attributes["start_Y"] = PreviousYStorer(attributes["Y"])
        attributes["start_Z"] = PreviousZStorer(attributes["Z"])

        return super().finish_attributes_dict(attributes, type_hints)


class LinearMove(MoveCommand):

    pattern = compile(r"G[01]")


class ArcMove(MoveCommand):

    pattern = [compile(r"G[23]"), compile(r"(?:R(?P<R>[\d.-]+))")]
    R: float

    # def process(self):

    #     points = interpolate_circle(self.start_X, self.start_Y, self.X,
    #                                 self.Y, self.R, num_points=100)
    #     new_lines = serialize_points(*points)

    #     return ["# new arc"] + new_lines + ["# end of new arc"]


class Gcode:

    command_set: List[Type[Command]]

    def get_code(self, line: str) -> Command:
        if line == "":
            return EmptyCommand()

        code_lookups = self.command_set
        codes = [v for v in [command.parse_line(
            line) for command in code_lookups] if v is not None]

        if len(codes) == 0:
            return UnidentifiedCommand(line)
        elif len(codes) > 1:
            raise ValueError(f"Conflict : {codes=}")
        else:
            return codes[0]


class SnapmakerGcode(Gcode):

    command_set = [
        StartSpindleCommand,  # M3
        StopSpindleCommand,  # M5
        MetricCommand,  # G21
        ImperialCommand,  # G20
        AbsoluteCommand,  # G90
        RelativeCommand,  # G91
        LinearMove,  # G0 / G1
        ArcMove  # G2 / G3
    ]