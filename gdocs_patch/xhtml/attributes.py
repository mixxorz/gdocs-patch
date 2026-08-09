import math
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from typing import Any, cast

from gdocs_patch.models import UNSET, Color, Dimension, UnsetType

from .nodes import Decoder, Encoder, Field, ValidationError

_CANONICAL_INTEGER = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")
_CANONICAL_FLOAT = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?\Z")


def _format_number(value: int | float) -> str:
    if value == 0:
        return "0"
    text = repr(value)
    return text[:-2] if text.endswith(".0") else text


class Attribute[T](Field[T], ABC):
    """A field represented by exactly one XML attribute."""

    def __init__(
        self,
        xml_name: str | None = None,
        *,
        required: bool = False,
        default: T | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.xml_name = xml_name
        self.required = required
        self.default = default

    def __set_name__(self, owner: type, name: str) -> None:
        super().__set_name__(owner, name)
        if self.xml_name is None:
            self.xml_name = name

    @property
    def bound_xml_name(self) -> str:
        if self.xml_name is None:
            raise TypeError("attribute is not bound to a Tag")
        return self.xml_name

    def get_default(self) -> T | UnsetType:
        return self.default

    def xml_names(self) -> set[str]:
        return {self.bound_xml_name}

    def validate(self, value: T | UnsetType) -> None:
        if value is UNSET and self.required:
            raise ValidationError(f"{self.name} is required")

    def decode_from_attributes(
        self, attributes: Mapping[str, str], decoder: Decoder
    ) -> T | UnsetType:
        raw = attributes.get(self.bound_xml_name)
        if raw is None:
            if self.required:
                decoder.fail(
                    "missing required attribute",
                    attribute_name=self.bound_xml_name,
                )
            return self.get_default()
        try:
            return self.decode(raw)
        except (TypeError, ValueError) as error:
            decoder.fail(str(error), attribute_name=self.bound_xml_name)

    def encode_into_attributes(
        self,
        value: T | UnsetType,
        attributes: MutableMapping[str, str],
        encoder: Encoder,
    ) -> None:
        if value is UNSET:
            return
        attributes[self.bound_xml_name] = self.encode(cast(T, value))

    @abstractmethod
    def decode(self, raw: str) -> T:
        raise NotImplementedError

    @abstractmethod
    def encode(self, value: T) -> str:
        raise NotImplementedError


class StringAttribute(Attribute[str]):
    def decode(self, raw: str) -> str:
        return raw

    def encode(self, value: str) -> str:
        return value


class BooleanAttribute(Attribute[bool]):
    def decode(self, raw: str) -> bool:
        if raw == "true":
            return True
        if raw == "false":
            return False
        raise ValueError(f"expected 'true' or 'false', got {raw!r}")

    def encode(self, value: bool) -> str:
        return "true" if value else "false"


class IntegerAttribute(Attribute[int]):
    def decode(self, raw: str) -> int:
        if _CANONICAL_INTEGER.fullmatch(raw) is None:
            raise ValueError(f"expected a canonical integer, got {raw!r}")
        return int(raw)

    def encode(self, value: int) -> str:
        return str(value)


class NonNegativeIntegerAttribute(IntegerAttribute):
    def decode(self, raw: str) -> int:
        value = super().decode(raw)
        if value < 0:
            raise ValueError(f"expected a non-negative integer, got {raw!r}")
        return value


class PositiveIntegerAttribute(IntegerAttribute):
    def decode(self, raw: str) -> int:
        value = super().decode(raw)
        if value <= 0:
            raise ValueError(f"expected a positive integer, got {raw!r}")
        return value


class FloatAttribute(Attribute[float]):
    def decode(self, raw: str) -> float:
        if _CANONICAL_FLOAT.fullmatch(raw) is None:
            raise ValueError(f"expected a float in canonical finite form, got {raw!r}")
        result = float(raw)
        if not math.isfinite(result) or _format_number(result) != raw:
            raise ValueError(f"expected a float in canonical finite form, got {raw!r}")
        return result

    def encode(self, value: float) -> str:
        return _format_number(value)


class ChoiceAttribute(Attribute[str]):
    def __init__(
        self,
        xml_name: str | None = None,
        *,
        choices: set[str],
        required: bool = False,
        default: str | UnsetType = UNSET,
    ) -> None:
        super().__init__(xml_name, required=required, default=default)
        self.choices = choices

    def decode(self, raw: str) -> str:
        if raw not in self.choices:
            choices = ", ".join(sorted(self.choices))
            raise ValueError(f"expected one of {choices}, got {raw!r}")
        return raw

    def encode(self, value: str) -> str:
        return value


class PointAttribute(Attribute[Dimension]):
    def decode(self, raw: str) -> Dimension:
        return Dimension(magnitude=FloatAttribute().decode(raw), unit="PT")

    def encode(self, value: Dimension) -> str:
        return FloatAttribute().encode(value.magnitude)


class LiteralAttribute(Attribute[bool]):
    """Presence of one XML attribute with a fixed literal value."""

    def __init__(self, xml_name: str, *, value: str) -> None:
        super().__init__(xml_name)
        self.value = value

    def decode(self, raw: str) -> bool:
        if raw != self.value:
            raise ValueError(f"expected {self.value!r}, got {raw!r}")
        return True

    def encode(self, value: bool) -> str:
        return self.value


class MultiValueAttribute[T](Field[T], ABC):
    """One field represented by several XML attributes."""

    def __init__(
        self,
        attributes: Mapping[str, Attribute[Any]],
        *,
        required: bool = False,
    ) -> None:
        super().__init__()
        self.attributes = dict(attributes)
        self.required = required

    def xml_names(self) -> set[str]:
        names: set[str] = set()
        for attribute in self.attributes.values():
            names.update(attribute.xml_names())
        return names

    def decode_from_attributes(
        self, attributes: Mapping[str, str], decoder: Decoder
    ) -> T | UnsetType:
        values = {
            name: attribute.decode_from_attributes(attributes, decoder)
            for name, attribute in self.attributes.items()
        }
        try:
            value = self.compress(values)
        except (TypeError, ValueError) as error:
            decoder.fail(str(error))
        if value is UNSET and self.required:
            decoder.fail(f"{self.name} is required")
        return value

    def encode_into_attributes(
        self,
        value: T | UnsetType,
        attributes: MutableMapping[str, str],
        encoder: Encoder,
    ) -> None:
        values = self.decompress(value)
        for name, attribute in self.attributes.items():
            attribute.encode_into_attributes(
                cast(Any, values.get(name, UNSET)), attributes, encoder
            )

    def validate(self, value: T | UnsetType) -> None:
        if value is UNSET and self.required:
            raise ValidationError(f"{self.name} is required")

    @abstractmethod
    def compress(self, values: Mapping[str, object]) -> T | UnsetType:
        raise NotImplementedError

    @abstractmethod
    def decompress(self, value: T | UnsetType) -> Mapping[str, object]:
        raise NotImplementedError


class ColorAttribute(MultiValueAttribute[Color | None]):
    def __init__(
        self,
        *,
        transparent: LiteralAttribute,
        red: FloatAttribute,
        green: FloatAttribute,
        blue: FloatAttribute,
        required: bool = False,
    ) -> None:
        super().__init__(
            {
                "transparent": transparent,
                "red": red,
                "green": green,
                "blue": blue,
            },
            required=required,
        )

    def compress(self, values: Mapping[str, object]) -> Color | None | UnsetType:
        transparent = values["transparent"]
        red = values["red"]
        green = values["green"]
        blue = values["blue"]
        components = (red, green, blue)

        if transparent is UNSET and all(value is UNSET for value in components):
            return UNSET
        if transparent is True:
            if any(value is not UNSET for value in components):
                raise ValueError("transparent color cannot include RGB components")
            return None
        if any(value is UNSET for value in components):
            raise ValueError("opaque color requires red, green, and blue")

        return Color(
            red=cast(float, red),
            green=cast(float, green),
            blue=cast(float, blue),
        )

    def decompress(self, value: Color | None | UnsetType) -> Mapping[str, object]:
        if value is UNSET:
            return {}
        if value is None:
            return {"transparent": True}
        color = cast(Color, value)
        return {
            "red": color.red,
            "green": color.green,
            "blue": color.blue,
        }
