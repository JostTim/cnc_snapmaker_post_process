import math
import re
import numpy as np
from re import Pattern
from pathlib import Path

from argparse import ArgumentParser
from rich import pretty, traceback
from rich.console import Console

from typing import Type, List, Optional, get_type_hints

traceback.install(show_locals=True)
# pretty.install()

console = Console()


class MatchException(Exception):
    pass


def interpolate_circle(x, y, xe, ye, r, num_points=100):
    # Calculate the center of the circle
    dx, dy = xe - x, ye - y
    q = np.sqrt(dx**2 + dy**2)
    if q > 2 * r:
        raise ValueError("The points are too far apart for the given radius.")

    # Calculate the midpoint
    mx, my = (x + xe) / 2, (y + ye) / 2

    # Calculate the distance from the midpoint to the center
    d = np.sqrt(r**2 - (q / 2) ** 2)

    # Calculate the center of the circle (two possible centers)
    cx1 = mx - d * dy / q
    cy1 = my + d * dx / q
    cx2 = mx + d * dy / q
    cy2 = my - d * dx / q

    # Choose the correct center based on clockwise direction
    if (x - cx1) * (ye - cy1) - (y - cy1) * (xe - cx1) < 0:
        cx, cy = cx1, cy1
    else:
        cx, cy = cx2, cy2

    # Calculate start and end angles
    start_angle = np.arctan2(y - cy, x - cx)
    end_angle = np.arctan2(ye - cy, xe - cx)

    # Ensure the angles are in the correct order for clockwise direction
    if end_angle > start_angle:
        end_angle -= 2 * np.pi

    # Generate points along the arc
    angles = np.linspace(start_angle, end_angle, num_points)
    arc_x = cx + r * np.cos(angles)
    arc_y = cy + r * np.sin(angles)

    return arc_x, arc_y


def serialize_points(pointsx, pointsy):
    gcode_lines = []
    for x, y in zip(pointsx, pointsy):
        gcode_lines.append(f"G1 X{x:.4f} Y{y:.4f}")
    return gcode_lines


def interpolate_arc(x0, y0, x1, y1, r, clockwise=True, segments=100):
    dx = x1 - x0
    dy = y1 - y0
    d = math.sqrt(dx**2 + dy**2)

    # if d > 2 * abs(r):
    #    raise ValueError("The radius is too short for the specified angle")
    console.print("problem for ", x0, y0, x1, y1, r)

    h = math.sqrt(abs(r) ** 2 - (d / 2) ** 2)
    mx = (x0 + x1) / 2
    my = (y0 + y1) / 2
    sign = -1 if clockwise else 1
    cx = mx - sign * h * dy / d
    cy = my + sign * h * dx / d

    start_angle = math.atan2(y0 - cy, x0 - cx)
    end_angle = math.atan2(y1 - cy, x1 - cx)

    if clockwise:
        if end_angle > start_angle:
            end_angle -= 2 * math.pi
    else:
        if end_angle < start_angle:
            end_angle += 2 * math.pi

    angle_step = (end_angle - start_angle) / segments
    gcode_lines = []

    for step in range(1, segments + 1):
        angle = start_angle + step * angle_step
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        gcode_lines.append(f"G1 X{x:.4f} Y{y:.4f}")

    return gcode_lines


class Self:

    def __new__(cls, obj):
        return obj


class PreviousValue:
    last_value_container: list

    def __init__(self):
        self.last_value = 0.0

    def update(self, value: float | None):
        last_value = self.last_value
        if value is not None:
            self.last_value = value
        return last_value


start_x = PreviousValue()
start_y = PreviousValue()
start_z = PreviousValue()


class ZeroDefault(float):
    def __new__(cls, obj) -> float:
        if obj is None:
            return 0.0
        else:
            return float(obj)


class PreviousDefault(float):
    last_value_container = [0.0]

    def __new__(cls, obj) -> float:
        if obj is not None:
            cls.last_value_container[0] = float(obj)
        return cls.last_value_container[0]


class PreviousX(PreviousDefault):
    last_value_container = [0.0]


class PreviousY(PreviousDefault):
    last_value_container = [0.0]


class PreviousZ(PreviousDefault):
    last_value_container = [0.0]


class PreviousF(PreviousDefault):
    last_value_container = [0.0]


class Code:

    pattern: Pattern[str] | List[Pattern[str]]
    line: str

    def __init__(self, line: str):
        self.line = line

        reverse_class_list: List[Type[Code]] = list(reversed(type(self).mro()))
        reverse_class_list = [
            cls for cls in reverse_class_list if issubclass(cls, Code) and cls != Code]

        # console.print(reverse_class_list)

        attributes = {}
        type_hints = {}
        for cls in reverse_class_list:
            d = cls.match(line)
            if d is not None:
                console.print(f"This matches {cls.__name__}", style="cyan2")
                type_hints.update(get_type_hints(cls))
                attributes.update(d)
            else:
                console.print(
                    f"Not a {type(self).__name__}", style="bright_red")
                raise MatchException("No match")

        self.set_attributes(
            self.finish_attributes_dict(attributes, type_hints)
        )

    def set_attributes(self, dict: dict):
        for key, value in dict.items():
            setattr(self, key, value)

    @classmethod
    def match(cls: "Type[Code]", line) -> dict | None:
        patterns = [cls.pattern] if not isinstance(
            cls.pattern, list) else cls.pattern
        result = {}
        for pattern in patterns:
            if match := pattern.search(line):
                result.update(match.groupdict())
            else:
                return None
        return result

    @classmethod
    def parse_line(cls, object):
        try:
            return cls(object)
        except MatchException:
            return None

    def process(self):
        return [self.line]

    def finish_attributes_dict(self, attributes: dict, type_hints: dict):
        attributes = {k: type_hints.get(k, Self)(v)
                      for k, v in attributes.items()}
        console.print(f"Finished {type(self).__name__}", style="bright_green")
        return attributes


class SpindleCommand(Code):

    pattern = re.compile(r"M(?P<M>\d)")
    M: int


class StopCommand(SpindleCommand):

    pattern = re.compile("M5")


class StartCommand(SpindleCommand):

    pattern = re.compile(r"M3 +(?P<P>\d+)")
    P: int


class MoveCommand(Code):

    pattern = re.compile(
        r"G(?P<G>\d) +(?:X(?P<X>[\d.-]+))? *(?:Y(?P<Y>[\d.-]+))? *(?:Z(?P<Z>[\d.-]+))? *(?:F(?P<F>[\d.-]+))?")
    G: int
    X: PreviousX
    Y: PreviousY
    Z: PreviousZ
    F: PreviousF
    start_X: float
    start_Y: float
    start_Z: float

    def finish_attributes_dict(self, attributes: dict, type_hints: dict):

        attributes["start_X"] = start_x.update(attributes["X"])
        attributes["start_Y"] = start_y.update(attributes["Y"])
        attributes["start_Z"] = start_z.update(attributes["Z"])

        return super().finish_attributes_dict(attributes, type_hints)


class LinearMove(MoveCommand):

    pattern = re.compile(r"G[01]")


class ArcMove(MoveCommand):

    pattern = [re.compile(r"G[23]"), re.compile(r"(?:R(?P<R>[\d.-]+))")]
    R: float

    def process(self):

        # return [f"Previous : X{self.start_X}, Y{self.start_Y}, Z{self.start_Z}",
        #         f"Current : X{self.X}, Y{self.Y}, Z{self.Z}", self.line, '----']

        points = interpolate_circle(self.start_X, self.start_Y, self.X,
                                    self.Y, self.R, num_points=100)
        new_lines = serialize_points(*points)

        return ["# new arc"] + new_lines + ["# end of new arc"]


def get_code(line: str) -> Code | None:
    code_lookups: List[Type[Code]] = [
        StopCommand, StartCommand, LinearMove, ArcMove]
    console.print(f"Parsing line {line}", style="blue")
    codes: List[Code] = [v for v in [code.parse_line(
        line) for code in code_lookups] if v is not None]
    if len(codes) == 0:
        console.print("Not a code", style="bright_red")
        return None
    elif len(codes) > 1:
        raise ValueError(f"Conflict : {codes=}")
    return codes[0]


def read_file_content(path):
    path = Path(path).resolve()
    with open(path, "r") as f:
        content = f.read()
    return content


def write_file_content(path, content):
    path = Path(path).resolve()
    with open(path, "w") as f:
        for line in content:
            f.write(line)
            f.write("\n")


def parse_file_content(gcode: str):
    lines = gcode.splitlines()

    output = []
    for line in lines:
        line = line.lstrip()
        code = get_code(line)
        if code is None:
            console.print("Code is None")
            output.append(line)
            continue
        console.print("Code is NOT NONE", style="dark_orange3")
        output.extend(code.process())

    return output


def run():

    console.print(ZeroDefault("0.15"))
    console.print(ZeroDefault(None))

    parser = ArgumentParser()
    parser.add_argument(
        "-f", "--file", help="path of the file to process", required=True)

    args = parser.parse_args()

    path = args.file
    output = parse_file_content(read_file_content(path))
    console.print(output)

    write_file_content("test_output.cnc", output)


if __name__ == "__main__":
    home = Path.home()
    path = home / "Desktop" / "luce_1.cnc"
    with open(path, "r") as f:
        content = f.read()
    shit = process_gcode(content)
    console.print(shit)
