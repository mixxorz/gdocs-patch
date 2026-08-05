from typing import ClassVar, Literal


class Model:
    """Base behavior shared by mutable Google Docs model objects."""

    __hash__ = None  # pyright: ignore[reportAssignmentType]

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and vars(self) == vars(other)

    def __repr__(self) -> str:
        fields = ", ".join(f"{name}={value!r}" for name, value in vars(self).items())
        return f"{type(self).__name__}({fields})"


class UnsetType:
    """Sentinel type for provider fields that were not supplied."""

    _instance: ClassVar["UnsetType | None"] = None

    def __new__(cls) -> "UnsetType":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"


UNSET = UnsetType()


class TreeNode(Model):
    """A node with an optional parent and ordered children."""

    __slots__ = ("parent",)

    def __init__(self) -> None:
        self.parent: TreeNode | None = None
        self.children: list[TreeNode] = []

    def add_child(self, child: "TreeNode") -> None:
        child.parent = self
        self.children.append(child)


class Dimension(Model):
    """A Google Docs measurement and its unit."""

    def __init__(
        self,
        *,
        magnitude: float = 0,
        unit: Literal["UNIT_UNSPECIFIED", "PT"] = "UNIT_UNSPECIFIED",
    ) -> None:
        self.magnitude = magnitude
        self.unit = unit


class Color(Model):
    """An opaque RGB color with components in the unit interval."""

    def __init__(
        self,
        *,
        red: float = 0,
        green: float = 0,
        blue: float = 0,
    ) -> None:
        components = {"red": red, "green": green, "blue": blue}
        for name, value in components.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"color {name} must be between 0.0 and 1.0")
        self.red = red
        self.green = green
        self.blue = blue
