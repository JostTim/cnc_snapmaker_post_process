import numpy as np
from pathlib import Path


from . gcode import ArcMove, LinearMove, Command
from . files import File

from typing import List, Type, Optional


class Rule:

    def __init__(self, command: "Command"):
        self.command = command

    def match(self) -> bool:
        return False

    def transform(self) -> List[Command]:
        return [self.command]


class TransformationRuleSet:

    rules: List[Type[Rule]]
    commands: List["Command"]
    file: File

    def __init__(self, file: File):
        self.commands = file.commands
        self.file = file

    def transform_command(self, command: "Command") -> List[Command]:
        for rule in self.rules:
            rule = rule(command)
            if rule.match():
                return rule.transform()
        return [command]

    def transform(self):
        commands = []
        for command in self.commands:
            commands.extend(self.transform_command(command))
        self.commands = commands
        return self

    def generate_output(self) -> List[str]:
        output: List[str] = []
        for command in self.commands:
            output.append(command.generate_line())
        return output

    def to_file(self, path: str | Path, file_class: Optional[Type[File]] = None):
        if file_class is None:
            file_class = type(self.file)
        file = file_class(path)
        file.commands = self.commands
        file.content = self.generate_output()
        return file


class ArcRule(Rule):

    command: ArcMove

    def match(self):
        return True if isinstance(self.command, ArcMove) else False

    def transform(self):
        return self.interpolate_circle(self.command.start_X,
                                       self.command.start_Y,
                                       self.command.X,
                                       self.command.Y,
                                       self.command.R,
                                       self.command.F,
                                       self.command.Z,
                                       num_points=100)

    def interpolate_circle(self, x, y, xe, ye, r, f, z, num_points=100):
        # Calculate the center of the circle
        dx, dy = xe - x, ye - y
        q = np.sqrt(dx**2 + dy**2)
        if q > 2 * r:
            raise ValueError(
                "The points are too far apart for the given radius.")

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

        starts_x, starts_y = [x] + list(arc_x)[:-1], [y] + list(arc_y)[:-1]
        ends_x, ends_y = list(arc_x), list(arc_y)

        return self.serialize_points_to_commands(starts_x, starts_y, ends_x, ends_y, f, z)

    def serialize_points_to_commands(self, starts_x, starts_y, ends_x, ends_y, f, z) -> List[Command]:
        commands: List[Command] = []
        for start_x, start_y, end_x, end_y in zip(starts_x, starts_y, ends_x, ends_y):

            commands.append(
                LinearMove.manual_instanciation(G=1,
                                                X=end_x,
                                                Y=end_y,
                                                Z=z,
                                                start_X=start_x,
                                                start_Y=start_y,
                                                start_Z=z,
                                                F=f
                                                )
            )

        return commands


class SnapmakerTransformation(TransformationRuleSet):

    rules = [ArcRule]

# Test it ?


# def interpolate_arc(x0, y0, x1, y1, r, clockwise=True, segments=100):
#     dx = x1 - x0
#     dy = y1 - y0
#     d = math.sqrt(dx**2 + dy**2)

#     if d > 2 * abs(r):
#         raise ValueError("The radius is too short for the specified angle")

#     h = math.sqrt(abs(r) ** 2 - (d / 2) ** 2)
#     mx = (x0 + x1) / 2
#     my = (y0 + y1) / 2
#     sign = -1 if clockwise else 1
#     cx = mx - sign * h * dy / d
#     cy = my + sign * h * dx / d

#     start_angle = math.atan2(y0 - cy, x0 - cx)
#     end_angle = math.atan2(y1 - cy, x1 - cx)

#     if clockwise:
#         if end_angle > start_angle:
#             end_angle -= 2 * math.pi
#     else:
#         if end_angle < start_angle:
#             end_angle += 2 * math.pi

#     angle_step = (end_angle - start_angle) / segments
#     gcode_lines = []

#     for step in range(1, segments + 1):
#         angle = start_angle + step * angle_step
#         x = cx + r * math.cos(angle)
#         y = cy + r * math.sin(angle)
#         gcode_lines.append(f"G1 X{x:.4f} Y{y:.4f}")

#     return gcode_lines
