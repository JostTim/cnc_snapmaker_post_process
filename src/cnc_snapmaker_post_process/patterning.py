from re import Pattern, compile as re_compile

from pathlib import Path

from typing import Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .files import File


class _BaliseType:
    pass


Balise = _BaliseType()


NAMED_GROUP_PATTERN = re_compile(r"\((\?P<.*?>)(.*?)\)")
BALISE_REPLACEMENT = r"(\1(?:\2)|(?:{.*?}))"


def compile(pattern: str) -> Pattern:

    injected_pattern = NAMED_GROUP_PATTERN.sub(BALISE_REPLACEMENT, pattern)
    return re_compile(injected_pattern)


class Patterner:

    def __init__(self, file: "File"):
        self.file = file
        self.commands = []

    def transform(self) -> "Patterner":
        for index, command in enumerate(self.file.commands):
            if command.contains_a_balise:
                print(index, command)
        return self

    def to_file(self, path: str | Path, file_class: "Optional[Type[File]]" = None):
        if file_class is None:
            file_class = type(self.file)
        return file_class.from_commands(path, self.commands)
