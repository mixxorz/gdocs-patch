from abc import ABC
from collections.abc import Callable, Generator, Iterable, Mapping, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Never, Self, cast, overload
from xml.etree import ElementTree

from gdocs_patch.models import UNSET, UnsetType

from .base import display_name


def _quantity(value: int) -> str:
    return "one" if value == 1 else str(value)


def _children(value: int) -> str:
    return "child" if value == 1 else "children"


def _node_name(node_type: type["Node"]) -> str:
    tag_name = getattr(node_type, "tag_name", None)
    return display_name(tag_name) if isinstance(tag_name, str) else node_type.__name__


@dataclass(frozen=True)
class SourcePosition:
    """One-based position of an element in the source XML."""

    line: int
    column: int


@dataclass(frozen=True)
class SourceLocation:
    """Structural path and optional textual position of a decoded node."""

    path: tuple[str, ...]
    position: SourcePosition | None = None

    def format(self, suffix: str = "") -> str:
        path = "/" + "/".join(display_name(step) for step in self.path) + suffix
        if self.position is None:
            return path
        return f"{path} (line {self.position.line}, column {self.position.column})"

    def __str__(self) -> str:
        return self.format()


class XHTMLModelError(ValueError):
    """Base error for the declarative XHTML model."""


class ValidationError(XHTMLModelError):
    """The XHTML tree does not conform to its declared model."""

    def __init__(self, message: str, *, attribute_name: str | None = None) -> None:
        super().__init__(message)
        self.attribute_name = attribute_name


class DecodeError(XHTMLModelError):
    """An XML element cannot be decoded into the requested XHTML tree."""

    def __init__(
        self,
        message: str,
        *,
        path: tuple[str, ...] = (),
        position: SourcePosition | None = None,
        attribute_name: str | None = None,
        element_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.position = position
        self.attribute_name = attribute_name
        self.element_name = element_name


class Node:
    """Base class for nodes in the declarative XHTML tree."""


class SourceMap:
    """Associate decoded nodes with locations without modifying the nodes."""

    def __init__(self) -> None:
        self._entries: dict[int, tuple[Node, SourceLocation]] = {}

    def record(self, node: Node, location: SourceLocation) -> None:
        self._entries[id(node)] = (node, location)

    def location_for(self, node: Node) -> SourceLocation:
        stored_node, location = self._entries[id(node)]
        if stored_node is not node:
            raise KeyError(node)
        return location


@dataclass(eq=True)
class Text(Node):
    value: str


class Field[T](ABC):
    """A value declared on a Tag."""

    required = False

    def __init__(self) -> None:
        self.name: str | None = None

    def __set_name__(self, _owner: type["Tag"], name: str) -> None:
        self.name = name

    @property
    def storage_name(self) -> str:
        if self.name is None:
            raise TypeError("field is not bound to a Tag")
        return f"_{self.name}"

    @overload
    def __get__(self, instance: None, owner: type["Tag"]) -> Self: ...

    @overload
    def __get__(self, instance: "Tag", owner: type["Tag"]) -> T | UnsetType: ...

    def __get__(
        self, instance: "Tag | None", owner: type["Tag"]
    ) -> Self | T | UnsetType:
        if instance is None:
            return self
        return getattr(instance, self.storage_name)

    def __set__(self, instance: "Tag", value: T | UnsetType) -> None:
        setattr(instance, self.storage_name, value)

    def get_default(self) -> T | UnsetType:
        return UNSET

    def xml_names(self) -> set[str]:
        return set()

    def validate(self, _value: T | UnsetType) -> None:
        pass

    def decode_from_attributes(
        self, _attributes: Mapping[str, str], _decoder: "Decoder"
    ) -> T | UnsetType:
        raise TypeError("field is not represented by XML attributes")

    def encode_into_attributes(
        self,
        _value: T | UnsetType,
        _attributes: MutableMapping[str, str],
        _encoder: "Encoder",
    ) -> None:
        raise TypeError("field is not represented by XML attributes")


class Child:
    """One permitted direct child type and its cardinality."""

    def __init__(
        self,
        node_type: type[Node] | Callable[[], type[Node]],
        *,
        min_num: int = 0,
        max_num: int | None = None,
    ) -> None:
        if min_num < 0:
            raise ValueError("min_num cannot be negative")
        if max_num is not None and max_num < min_num:
            raise ValueError("max_num cannot be smaller than min_num")
        self._node_type = node_type
        self.min_num = min_num
        self.max_num = max_num

    @property
    def node_type(self) -> type[Node]:
        value = self._node_type
        if isinstance(value, type) and issubclass(value, Node):
            return value
        resolved = value()
        if not isinstance(resolved, type) or not issubclass(resolved, Node):
            raise TypeError("lazy Child reference must return a Node type")
        return resolved

    def matches_node(self, node: Node) -> bool:
        return isinstance(node, self.node_type)

    def matches_element(self, element: ElementTree.Element) -> bool:
        node_type = self.node_type
        return issubclass(node_type, Tag) and node_type.tag_name == element.tag


class Children(Field[list[Node]]):
    """Ordered mixed content accepted by a Tag."""

    def __init__(
        self,
        *specs: Child,
        min_num: int = 0,
        max_num: int | None = None,
        unique_by: Field[Any] | None = None,
    ) -> None:
        super().__init__()
        if min_num < 0:
            raise ValueError("min_num cannot be negative")
        if max_num is not None and max_num < min_num:
            raise ValueError("max_num cannot be smaller than min_num")
        self.specs = specs
        self.min_num = min_num
        self.max_num = max_num
        self.unique_by = unique_by

    def __set_name__(self, owner: type["Tag"], name: str) -> None:
        super().__set_name__(owner, name)
        if self.unique_by is None:
            return
        if self.unique_by.name is None:
            raise TypeError("unique child field must be bound to a Tag")
        for spec in self.specs:
            node_type = spec.node_type
            if not issubclass(node_type, Tag):
                raise TypeError("unique child declarations must refer to Tag types")
            if node_type.fields().get(self.unique_by.name) is not self.unique_by:
                raise TypeError(
                    f"{node_type.__name__} does not declare unique field "
                    f"{self.unique_by.name!r}"
                )

    def get_default(self) -> list[Node]:
        return []

    def __set__(self, instance: "Tag", value: list[Node] | UnsetType) -> None:
        if value is UNSET:
            raise TypeError("children cannot be UNSET")
        super().__set__(instance, self.normalize(value))

    def normalize(self, value: object) -> list[Node]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("children must be a list")

        result: list[Node] = []
        for child in cast(list[object], value):
            if isinstance(child, str):
                child = Text(child)
            if not isinstance(child, Node):
                raise TypeError("children must contain Node instances or strings")
            if isinstance(child, Text):
                if not child.value:
                    continue
                if result and isinstance(result[-1], Text):
                    result[-1].value += child.value
                    continue
            result.append(child)
        return result

    @property
    def permits_text(self) -> bool:
        return any(spec.node_type is Text for spec in self.specs)

    def spec_for_element(self, element: ElementTree.Element) -> Child | None:
        matches = [spec for spec in self.specs if spec.matches_element(element)]
        if len(matches) > 1:
            raise ValidationError(
                f"<{element.tag}> matches multiple child declarations"
            )
        return matches[0] if matches else None

    def validate(self, value: list[Node] | UnsetType) -> None:
        if value is UNSET or not isinstance(value, list):
            raise ValidationError("children must be a list")

        if len(value) < self.min_num:
            raise ValidationError(
                f"expected at least {_quantity(self.min_num)} child element"
                f"{'' if self.min_num == 1 else 's'}"
            )
        if self.max_num is not None and len(value) > self.max_num:
            raise ValidationError(
                f"expected at most {_quantity(self.max_num)} child element"
                f"{'' if self.max_num == 1 else 's'}"
            )

        for node in value:
            matches = [spec for spec in self.specs if spec.matches_node(node)]
            if not matches:
                raise ValidationError(
                    f"{type(node).__name__} is not permitted in {self.name}"
                )
            if len(matches) > 1:
                raise ValidationError(
                    f"{type(node).__name__} matches multiple child declarations"
                )

        for spec in self.specs:
            count = sum(spec.matches_node(node) for node in value)
            child_name = _node_name(spec.node_type)
            if count < spec.min_num:
                raise ValidationError(
                    f"expected at least {_quantity(spec.min_num)} {child_name} "
                    f"{_children(spec.min_num)}"
                )
            if spec.max_num is not None and count > spec.max_num:
                raise ValidationError(
                    f"expected at most {_quantity(spec.max_num)} {child_name} "
                    f"{_children(spec.max_num)}"
                )

        if self.unique_by is not None:
            seen: set[object] = set()
            for node in value:
                tag = cast(Tag, node)
                key: object = self.unique_by.__get__(tag, type(tag))
                if key in seen:
                    raise ValidationError(f"duplicate child key {key!r}")
                seen.add(key)

    def decode_from(
        self, element: ElementTree.Element, decoder: "Decoder"
    ) -> list[Node]:
        return decoder.decode_children(element, self)

    def encode_into(
        self,
        value: list[Node] | UnsetType,
        element: ElementTree.Element,
        encoder: "Encoder",
    ) -> None:
        encoder.encode_children(cast(list[Node], value), element)


class Tag(Node):
    """An XHTML element whose fields declaratively define its grammar."""

    tag_name: str | None = None
    field_order: tuple[str, ...] = ()
    children = Children()

    @classmethod
    def fields(cls) -> dict[str, Field[Any]]:
        result: dict[str, Field[Any]] = {}
        for base in reversed(cls.__mro__):
            for name, value in vars(base).items():
                if isinstance(value, Field):
                    result[name] = value

        if cls.field_order:
            missing = set(cls.field_order) - set(result)
            if missing:
                names = ", ".join(sorted(missing))
                raise TypeError(f"{cls.__name__} orders unknown field(s): {names}")
            ordered = {name: result[name] for name in cls.field_order}
            ordered.update(
                (name, field) for name, field in result.items() if name not in ordered
            )
            result = ordered

        children_fields = [
            field for field in result.values() if isinstance(field, Children)
        ]
        if len(children_fields) > 1:
            raise TypeError(f"{cls.__name__} declares more than one Children field")
        return result

    @classmethod
    def attribute_fields(cls) -> dict[str, Field[Any]]:
        """Return fields represented by XML attributes rather than child content."""
        return {
            name: field
            for name, field in cls.fields().items()
            if not isinstance(field, Children)
        }

    @property
    def attribute_values(self) -> dict[str, object]:
        """Return this tag's decoded XML attribute values."""
        return {name: getattr(self, name) for name in self.attribute_fields()}

    def __init__(self, **values: object) -> None:
        fields = self.fields()
        unknown = set(values) - set(fields)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise TypeError(f"unknown field(s) for {type(self).__name__}: {names}")

        for name, field in fields.items():
            if name in values:
                value = values[name]
            elif field.required:
                raise TypeError(
                    f"missing required field {name!r} for {type(self).__name__}"
                )
            else:
                value = field.get_default()
            setattr(self, name, value)

    def clean(self) -> None:
        """Validate relationships between fields on a complete tag."""

    def validate(self) -> None:
        if self.tag_name is None:
            raise ValidationError(f"{type(self).__name__} has no tag_name")
        for name, field in self.fields().items():
            field.validate(getattr(self, name))
        self.clean()

    @classmethod
    def decode_from(cls, element: ElementTree.Element, decoder: "Decoder") -> Self:
        if cls.tag_name is None:
            decoder.fail(f"{cls.__name__} has no tag_name")
        if element.tag != cls.tag_name:
            decoder.fail(f"expected <{cls.tag_name}>, got <{element.tag}>")

        allowed_attributes: set[str] = set()
        for field in cls.attribute_fields().values():
            allowed_attributes.update(field.xml_names())
        unknown_attributes = set(element.attrib) - allowed_attributes
        if unknown_attributes:
            attribute_name = min(unknown_attributes)
            decoder.fail("unknown attribute", attribute_name=attribute_name)

        values = {
            name: field.decode_from_attributes(element.attrib, decoder)
            for name, field in cls.attribute_fields().items()
        }
        node = cls(**values)
        node.children = cls.children.decode_from(element, decoder)
        return node

    def __repr__(self) -> str:
        values = ", ".join(f"{name}={getattr(self, name)!r}" for name in self.fields())
        return f"{type(self).__name__}({values})"

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and all(
            getattr(self, name) == getattr(other, name) for name in self.fields()
        )


class Decoder:
    def __init__(self, source_positions: Iterable[SourcePosition] = ()) -> None:
        self._path: list[str] = []
        self._source_positions = iter(source_positions)
        self._current_location: SourceLocation | None = None
        self.source_map = SourceMap()

    def fail(
        self,
        message: str,
        *,
        attribute_name: str | None = None,
        element_name: str | None = None,
    ) -> Never:
        location = self._current_location or SourceLocation(tuple(self._path))
        raise DecodeError(
            message,
            path=location.path,
            position=location.position,
            attribute_name=attribute_name,
            element_name=element_name,
        )

    @contextmanager
    def at(self, tag_name: str) -> Generator[None]:
        """Track the element currently being decoded.

        Errors raised inside the context include this element in their XML path. The
        previous path is restored afterward so decoding can continue with a sibling.
        """
        self._path.append(tag_name)
        try:
            yield
        finally:
            self._path.pop()

    def decode_element[T: Tag](
        self, element: ElementTree.Element, node_type: type[T]
    ) -> T:
        position = next(self._source_positions, None)
        location = SourceLocation(tuple(self._path), position)
        previous_location = self._current_location
        self._current_location = location
        try:
            node = node_type.decode_from(element, self)
            self.source_map.record(node, location)
            try:
                node.validate()
            except ValidationError as error:
                raise DecodeError(
                    str(error),
                    path=location.path,
                    position=location.position,
                    attribute_name=error.attribute_name,
                ) from error
            return node
        finally:
            self._current_location = previous_location

    def decode_children(
        self, parent: ElementTree.Element, field: Children
    ) -> list[Node]:
        result: list[Node] = []

        def append_text(value: str | None) -> None:
            if value is None or not value:
                return
            if field.permits_text:
                result.append(Text(value))
            elif value.strip():
                self.fail("text is not permitted under this parent")

        append_text(parent.text)
        child_totals: dict[str, int] = {}
        resolved: list[tuple[ElementTree.Element, Child, type[Tag]]] = []
        for child_element in parent:
            child_totals[child_element.tag] = child_totals.get(child_element.tag, 0) + 1
            spec = field.spec_for_element(child_element)
            if spec is None:
                self.fail(
                    "element is not permitted under this parent:",
                    element_name=child_element.tag,
                )
            child_type = spec.node_type
            if not issubclass(child_type, Tag):
                raise TypeError("element child declaration must refer to a Tag")
            if (
                child_element.tail
                and child_element.tail.strip()
                and not field.permits_text
            ):
                self.fail("text is not permitted under this parent")
            resolved.append((child_element, spec, child_type))

        child_counts: dict[str, int] = {}
        for child_element, spec, child_type in resolved:
            child_counts[child_element.tag] = child_counts.get(child_element.tag, 0) + 1
            path_step = child_element.tag
            repeated = spec.max_num is None or spec.max_num > 1
            if repeated and (
                not field.permits_text or child_totals[child_element.tag] > 1
            ):
                path_step += f"[{child_counts[child_element.tag]}]"
            with self.at(path_step):
                child = self.decode_element(child_element, child_type)
            result.append(child)
            append_text(child_element.tail)

        return field.normalize(result)


class Encoder:
    def encode_element(self, node: Tag) -> ElementTree.Element:
        element = ElementTree.Element(cast(str, node.tag_name))
        for name, field in node.attribute_fields().items():
            field.encode_into_attributes(getattr(node, name), element.attrib, self)
        type(node).children.encode_into(node.children, element, self)
        return element

    def encode_children(
        self, children: list[Node], parent: ElementTree.Element
    ) -> None:
        previous_element: ElementTree.Element | None = None
        for child in children:
            if isinstance(child, Text):
                if previous_element is None:
                    parent.text = (parent.text or "") + child.value
                else:
                    previous_element.tail = (previous_element.tail or "") + child.value
                continue

            element = self.encode_element(cast(Tag, child))
            parent.append(element)
            previous_element = element
