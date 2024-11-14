from typing import List


class SelfReturn:

    def __new__(cls, obj):
        return obj


class ZeroDefault(float):
    def __new__(cls, obj) -> float:
        if obj is None:
            return 0.0
        else:
            return float(obj)


class PreviousDefault(float):
    last_value_container: List[float]

    def __new__(cls, obj) -> float:
        if obj is not None:
            cls.last_value_container[0] = float(obj)
        return cls.last_value_container[0]


class PreviousValueStorer:
    last_value_container: List[float]

    def __new__(cls, value: float | None) -> float:
        last_value = cls.last_value_container[0]
        if value is not None:
            cls.last_value_container[0] = value
        return last_value


class PreviousXDefault(PreviousDefault):
    last_value_container = [0.0]


class PreviousYDefault(PreviousDefault):
    last_value_container = [0.0]


class PreviousZDefault(PreviousDefault):
    last_value_container = [0.0]


class PreviousFDefault(PreviousDefault):
    last_value_container = [0.0]


class PreviousXStorer(PreviousValueStorer):
    last_value_container = [0.0]


class PreviousYStorer(PreviousValueStorer):
    last_value_container = [0.0]


class PreviousZStorer(PreviousValueStorer):
    last_value_container = [0.0]
