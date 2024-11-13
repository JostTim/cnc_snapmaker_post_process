import math, re, numpy as np
from re import Pattern
from pathlib import Path
from typing import Type, List, get_type_hints
from argparse import ArgumentParser
from rich import pretty, traceback
from rich.console import Console

traceback.install(show_locals=True)
pretty.install()

console = Console()


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


def process_gcode(gcode: str):
    lines = gcode.splitlines()
    current_x, current_y = 0, 0

    g1_lines = []

    for line in lines:
        line = line.lstrip()
        parse_g_moves(line)
        if line.startswith("G2") or line.startswith("G3"):
            result = parse_gcode_line(line)
            console.print(current_x, current_y, result)
            if result:
                x, y, r = result
                # clockwise = line.startswith("G2")
                g1_lines.extend(serialize_points(*interpolate_circle(current_x, current_y, x, y, r)))
                # g1_lines.extend(interpolate_arc(current_x, current_y, x, y, r, clockwise))
                current_x, current_y = x, y
        elif line.startswith("G0") or line.startswith("G1"):
            # Update current position for G1 moves
            match = re.match(r"G[01] X([\w.-]+) Y([\w.-]+)", line)
            if match:
                current_x = float(match.group(1))
                current_y = float(match.group(2))
            g1_lines.append(line)
        else:
            # Copy other lines directly
            g1_lines.append(line)

    return g1_lines


class Self:

    def __new__(cls, obj):
        return obj


class ZeroDefault(float):
    def __new__(cls, obj) -> float:
        if obj is None:
            return 0.0
        else:
            return float(obj)


class Code:

    pattern: Pattern[str] | List[Pattern[str]]
    line: str

    def __init__(self, line: str):
        self.line = line

        reverse_class_list: List[Type[Code]] = list(reversed(type(self).mro()))
        reverse_class_list = [cls for cls in reverse_class_list if issubclass(cls, Code) and cls != Code]

        # console.print(reverse_class_list)

        dict = {}
        for cls in reverse_class_list:
            d = cls.match(line)
            if d is not None:
                console.print(f"This matches {cls.__name__}", style="cyan2")
                type_hints = get_type_hints(cls)
                # console.print(type_hints)
                d = {k: type_hints.get(k, Self)(v) for k, v in d.items()}
                console.print(d)
                dict.update(d)
            else:
                console.print(f"Not a {type(self).__name__}", style="bright_red")
                raise ValueError("No match")

        for key, value in dict.items():
            setattr(self, key, value)

        console.print(f"Finished {type(self).__name__}", style="bright_green")

    @classmethod
    def match(cls: "Type[Code]", line) -> dict | None:
        patterns = [cls.pattern] if not isinstance(cls.pattern, list) else cls.pattern
        result = {}
        for pattern in patterns:
            if match := pattern.match(line):
                result.update(match.groupdict())
            else:
                return None
        return result

    @classmethod
    def parse_line(cls, object):
        try:
            return cls(object)
        except ValueError:
            return None

    def process(self):
        return [self.line]


class SpindleCommand(Code):

    pattern = re.compile(r"M(?P<M>\d)")
    M: int


class StopCommand(SpindleCommand):

    pattern = re.compile("M5")


class StartCommand(SpindleCommand):

    pattern = re.compile(r"M3 +(?P<P>\d+)")
    P: int


class MoveCommand(Code):

    pattern = re.compile(r"G(?P<G>\d) +(?:X(?P<X>[\d.-]+))? *(?:Y(?P<Y>[\d.-]+))? *(?:Z(?P<Z>[\d.-]+))?")
    G: int
    X: ZeroDefault
    Y: ZeroDefault
    Z: ZeroDefault


class LinearMove(MoveCommand):

    pattern = re.compile(r"G[12]")


class ArcMove(MoveCommand):

    pattern = [re.compile(r"G[23]"), re.compile(r"(?:R(?P<R>[\d.-]+))")]
    R: int

    def process(self):
        return [f"Changed {self.line}"]


def get_code(line: str) -> Code | None:
    code_lookups: List[Type[Code]] = [StopCommand, StartCommand, LinearMove, ArcMove]
    console.print(f"Parsing line {line}", style="blue")
    codes: List[Code] = [v for v in [code.parse_line(line) for code in code_lookups] if v is not None]
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


def parse_file_content(gcode: str):
    lines = gcode.splitlines()
    current_x, current_y = 0, 0

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


def parse_g_moves(line):

    g_move_pattern = re.compile(r"G(?P<G>[0123]) *(?:X(?P<X>[\d.-]+))? *(?:Y(?P<Y>[\d.-]+))? *(?:R(?P<R>[\d.-]+))?")
    match = g_move_pattern.match(line)
    if match:
        gcode = int(match["G"])
        x = float(match["X"])
        y = float(match["Y"])
        r = float(match["R"])
        console.print(gcode, x, y, r)


def parse_gcode_line(line):
    shit_pattern = re.compile(r"G(?P<G>[0123]) *(?:X(?P<x>[\d.-]+))? *(?:Y(?P<y>[\d.-]+))? *(?:R(?P<r>[\d.-]+))?")
    match = shit_pattern.match(line)
    if match:

        Gcode = int(match["G"])
        x = float(match["X"])
        y = float(match["Y"])
        r = float(match["R"])
        return x, y, r
    return None


def run():

    console.print(ZeroDefault("0.15"))
    console.print(ZeroDefault(None))

    parser = ArgumentParser()
    parser.add_argument("-f", "--file", help="path of the file to process", required=True)

    args = parser.parse_args()

    path = args.file
    output = parse_file_content(read_file_content(path))
    console.print(output)


if __name__ == "__main__":
    home = Path.home()
    path = home / "Desktop" / "luce_1.cnc"
    with open(path, "r") as f:
        content = f.read()
    shit = process_gcode(content)
    console.print(shit)
