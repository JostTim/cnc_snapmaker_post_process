from .gcode import Command


class FileStatistics:

    classes = {}

    def record(self, original_class: Command, output_class: Command, line_nb=None):

        self.classes.get(type(original_class), {})
