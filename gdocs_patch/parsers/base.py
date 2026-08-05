from abc import ABC, abstractmethod
from typing import Any, Literal

from gdocs_patch.models.base import Color, Dimension


class GDocParser[T](ABC):
    @abstractmethod
    def parse(self, data: Any) -> T:
        raise NotImplementedError


class DimensionParser(GDocParser[Dimension]):
    def parse(self, data: Any) -> Dimension:
        unit: Literal["UNIT_UNSPECIFIED", "PT"] = data.get("unit", "UNIT_UNSPECIFIED")
        return Dimension(magnitude=float(data.get("magnitude", 0.0)), unit=unit)


class ColorParser(GDocParser[Color]):
    def parse(self, data: Any) -> Color:
        rgb = data.get("rgbColor", {})
        return Color(
            red=float(rgb.get("red", 0)),
            green=float(rgb.get("green", 0)),
            blue=float(rgb.get("blue", 0)),
        )


Dimension.gdoc_parser = DimensionParser()
Color.gdoc_parser = ColorParser()
