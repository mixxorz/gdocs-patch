import json
from abc import ABC, abstractmethod
from typing import Literal, cast

from gdocs_patch.models.base import UNSET, Color, Dimension, UnsetType

type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)
type JsonObject = dict[str, JsonValue]


class GDocParseError(ValueError):
    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


class GDocParser[T](ABC):
    @abstractmethod
    def parse(self, data: JsonValue, *, path: str = "$") -> T:
        raise NotImplementedError


def object_value(value: JsonValue, path: str) -> JsonObject:
    if not isinstance(value, dict):
        raise GDocParseError(path, "expected object")
    return value


def array_value(value: JsonValue, path: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise GDocParseError(path, "expected array")
    return value


def string_value(value: JsonValue, path: str) -> str:
    if not isinstance(value, str):
        raise GDocParseError(path, "expected str")
    return value


def boolean_value(value: JsonValue, path: str) -> bool:
    if not isinstance(value, bool):
        raise GDocParseError(path, "expected bool")
    return value


def integer_value(value: JsonValue, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GDocParseError(path, "expected integer")
    return value


def number_value(value: JsonValue, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GDocParseError(path, "expected number")
    return float(value)


def literal_value[T: str](value: JsonValue, allowed: tuple[T, ...], path: str) -> T:
    parsed = string_value(value, path)
    if parsed not in allowed:
        raise GDocParseError(path, f"expected one of {allowed!r}")
    return cast(T, parsed)


def required_field(value: JsonObject, key: str, path: str) -> JsonValue:
    if key not in value:
        raise GDocParseError(field_path(path, key), "required field is missing")
    return value[key]


def optional_string_field(value: JsonObject, key: str, path: str) -> str | UnsetType:
    if key not in value:
        return UNSET
    return string_value(value[key], field_path(path, key))


def optional_object_field(
    value: JsonObject, key: str, path: str
) -> JsonObject | UnsetType:
    if key not in value:
        return UNSET
    return object_value(value[key], field_path(path, key))


def optional_array_field(
    value: JsonObject, key: str, path: str
) -> list[JsonValue] | UnsetType:
    if key not in value:
        return UNSET
    return array_value(value[key], field_path(path, key))


def optional_boolean_field(value: JsonObject, key: str, path: str) -> bool | UnsetType:
    if key not in value:
        return UNSET
    return boolean_value(value[key], field_path(path, key))


def optional_integer_field(value: JsonObject, key: str, path: str) -> int | UnsetType:
    if key not in value:
        return UNSET
    return integer_value(value[key], field_path(path, key))


def optional_literal_field[T: str](
    value: JsonObject, key: str, allowed: tuple[T, ...], path: str
) -> T | UnsetType:
    if key not in value:
        return UNSET
    return literal_value(value[key], allowed, field_path(path, key))


def field_path(parent: str, key: str) -> str:
    return f"{parent}.{key}"


def index_path(parent: str, index: int) -> str:
    return f"{parent}[{index}]"


def map_key_path(parent: str, key: str) -> str:
    return f"{parent}[{json.dumps(key)}]"


def parse_optional_color(value: JsonValue, path: str) -> Color | None:
    optional_color = object_value(value, path)
    if not optional_color:
        return None
    color_path = field_path(path, "color")
    color = required_field(optional_color, "color", path)
    return Color.gdoc_parser.parse(color, path=color_path)


class DimensionParser(GDocParser[Dimension]):
    def parse(self, data: JsonValue, *, path: str = "$") -> Dimension:
        value = object_value(data, path)
        magnitude = (
            number_value(value["magnitude"], field_path(path, "magnitude"))
            if "magnitude" in value
            else 0.0
        )
        unit: Literal["UNIT_UNSPECIFIED", "PT"] = (
            literal_value(
                value["unit"], ("UNIT_UNSPECIFIED", "PT"), field_path(path, "unit")
            )
            if "unit" in value
            else "UNIT_UNSPECIFIED"
        )
        return Dimension(magnitude=magnitude, unit=unit)


class ColorParser(GDocParser[Color]):
    def parse(self, data: JsonValue, *, path: str = "$") -> Color:
        value = object_value(data, path)
        rgb_path = field_path(path, "rgbColor")
        rgb = object_value(value.get("rgbColor", {}), rgb_path)
        red = number_value(rgb.get("red", 0), field_path(rgb_path, "red"))
        green = number_value(rgb.get("green", 0), field_path(rgb_path, "green"))
        blue = number_value(rgb.get("blue", 0), field_path(rgb_path, "blue"))
        try:
            return Color(red=red, green=green, blue=blue)
        except ValueError as error:
            raise GDocParseError(path, str(error)) from error


Dimension.gdoc_parser = DimensionParser()
Color.gdoc_parser = ColorParser()
