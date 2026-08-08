from abc import ABC, abstractmethod
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Never, Self, cast, overload
from xml.etree import ElementTree

from gdocs_patch.models import UNSET, UnsetType


class XHTMLModelError(ValueError):
    """Base error for the declarative XHTML model."""


class ValidationError(XHTMLModelError):
    """The XHTML tree does not conform to its declared model."""


class DecodeError(XHTMLModelError):
    """An XML element cannot be decoded into the requested XHTML tree."""

    def __init__(
        self,
        message: str,
        *,
        path: tuple[str, ...] = (),
        attribute_name: str | None = None,
        element_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.attribute_name = attribute_name
        self.element_name = element_name


class EncodeError(XHTMLModelError):
    """The XHTML tree cannot be encoded as XML."""


class Node:
    """Base class for nodes in the declarative XHTML tree."""

    def validate(self) -> None:
        pass


@dataclass(eq=True)
class Text(Node):
    value: str

    def validate(self) -> None:
        if not isinstance(self.value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValidationError("text value must be a string")


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

    @abstractmethod
    def decode_from(
        self, element: ElementTree.Element, decoder: "Decoder"
    ) -> T | UnsetType:
        raise NotImplementedError

    @abstractmethod
    def encode_into(
        self,
        value: T | UnsetType,
        element: ElementTree.Element,
        encoder: "Encoder",
    ) -> None:
        raise NotImplementedError


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
        text_error: str = "unexpected text",
        tail_error: str = "unexpected text",
    ) -> None:
        super().__init__()
        self.specs = specs
        self.text_error = text_error
        self.tail_error = tail_error

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

    def type_for_element(self, element: ElementTree.Element) -> "type[Tag] | None":
        matches = [
            spec.node_type for spec in self.specs if spec.matches_element(element)
        ]
        if len(matches) > 1:
            raise ValidationError(
                f"<{element.tag}> matches multiple child declarations"
            )
        if not matches:
            return None
        node_type = matches[0]
        if not issubclass(node_type, Tag):
            raise TypeError("element child declaration must refer to a Tag")
        return node_type

    def validate(self, value: list[Node] | UnsetType) -> None:
        if value is UNSET or not isinstance(value, list):
            raise ValidationError("children must be a list")

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
            if count < spec.min_num:
                raise ValidationError(
                    f"{self.name} requires at least {spec.min_num} "
                    f"{spec.node_type.__name__} child(ren); got {count}"
                )
            if spec.max_num is not None and count > spec.max_num:
                raise ValidationError(
                    f"{self.name} permits at most {spec.max_num} "
                    f"{spec.node_type.__name__} child(ren); got {count}"
                )

        for node in value:
            node.validate()

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
        if value is UNSET:
            raise EncodeError("children cannot be UNSET")
        encoder.encode_children(cast(list[Node], value), element)


class Tag(Node):
    """An XHTML element whose fields declaratively define its grammar."""

    tag_name: str | None = None

    @classmethod
    def fields(cls) -> dict[str, Field[Any]]:
        result: dict[str, Field[Any]] = {}
        for base in reversed(cls.__mro__):
            for name, value in vars(base).items():
                if isinstance(value, Field):
                    result[name] = value

        children_fields = [
            field for field in result.values() if isinstance(field, Children)
        ]
        if len(children_fields) > 1:
            raise TypeError(f"{cls.__name__} declares more than one Children field")
        return result

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

    def validate(self) -> None:
        if self.tag_name is None:
            raise ValidationError(f"{type(self).__name__} has no tag_name")
        for name, field in self.fields().items():
            try:
                field.validate(getattr(self, name))
            except ValidationError as error:
                raise ValidationError(
                    f"{type(self).__name__}.{name}: {error}"
                ) from error

    @classmethod
    def decode_from(cls, element: ElementTree.Element, decoder: "Decoder") -> Self:
        if cls.tag_name is None:
            decoder.fail(f"{cls.__name__} has no tag_name")
        if element.tag != cls.tag_name:
            decoder.fail(f"expected <{cls.tag_name}>, got <{element.tag}>")

        allowed_attributes: set[str] = set()
        for field in cls.fields().values():
            allowed_attributes.update(field.xml_names())
        unknown_attributes = set(element.attrib) - allowed_attributes
        if unknown_attributes:
            attribute_name = min(unknown_attributes)
            decoder.fail("unknown attribute", attribute_name=attribute_name)

        values = {
            name: field.decode_from(element, decoder)
            for name, field in cls.fields().items()
        }
        return cls(**values)

    @classmethod
    def loads(cls, source: str) -> Self:
        return Decoder().loads(source, cls)

    def dumps(self) -> str:
        return Encoder().dumps(self)

    def __repr__(self) -> str:
        values = ", ".join(f"{name}={getattr(self, name)!r}" for name in self.fields())
        return f"{type(self).__name__}({values})"

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and all(
            getattr(self, name) == getattr(other, name) for name in self.fields()
        )


class Decoder:
    def __init__(self) -> None:
        self._path: list[str] = []

    def fail(
        self,
        message: str,
        *,
        attribute_name: str | None = None,
        element_name: str | None = None,
    ) -> Never:
        raise DecodeError(
            message,
            path=tuple(self._path),
            attribute_name=attribute_name,
            element_name=element_name,
        )

    @contextmanager
    def at(self, tag_name: str) -> Generator[None]:
        self._path.append(tag_name)
        try:
            yield
        finally:
            self._path.pop()

    def loads[T: Tag](self, source: str, root_type: type[T]) -> T:
        try:
            element = ElementTree.fromstring(source)
        except ElementTree.ParseError as error:
            raise DecodeError(str(error)) from error
        return self.decode_element(element, root_type)

    def decode_element[T: Tag](
        self, element: ElementTree.Element, node_type: type[T]
    ) -> T:
        node = self._decode_element(element, node_type)
        try:
            node.validate()
        except ValidationError as error:
            raise DecodeError(str(error), path=tuple(self._path)) from error
        return node

    def _decode_element[T: Tag](
        self, element: ElementTree.Element, node_type: type[T]
    ) -> T:
        return node_type.decode_from(element, self)

    def decode_children(
        self, parent: ElementTree.Element, field: Children
    ) -> list[Node]:
        result: list[Node] = []

        def append_text(value: str | None, error_message: str) -> None:
            if value is None or not value:
                return
            if field.permits_text:
                result.append(Text(value))
            elif value.strip():
                self.fail(error_message)

        append_text(parent.text, field.text_error)
        for child_element in parent:
            child_type = field.type_for_element(child_element)
            if child_type is None:
                self.fail("unknown child element", element_name=child_element.tag)
            with self.at(child_element.tag):
                child = self._decode_element(child_element, child_type)
            result.append(child)
            append_text(child_element.tail, field.tail_error)

        return field.normalize(result)


class Encoder:
    def dumps(self, node: Tag) -> str:
        element = self.encode_element(node)
        return ElementTree.tostring(element, encoding="unicode", method="xml")

    def encode_element(self, node: Tag) -> ElementTree.Element:
        node.validate()
        return self._encode_element(node)

    def _encode_element(self, node: Tag) -> ElementTree.Element:
        if node.tag_name is None:
            raise EncodeError(f"{type(node).__name__} has no tag_name")
        element = ElementTree.Element(node.tag_name)
        for name, field in node.fields().items():
            field.encode_into(getattr(node, name), element, self)
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

            if not isinstance(child, Tag):
                raise EncodeError(f"cannot encode child of type {type(child).__name__}")
            element = self._encode_element(child)
            parent.append(element)
            previous_element = element
