from abc import ABC
from collections.abc import Callable, Generator, Mapping, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Never, Self, cast, overload
from xml.etree import ElementTree

from gdocs_patch.models import UNSET, UnsetType


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
        attribute_name: str | None = None,
        element_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.attribute_name = attribute_name
        self.element_name = element_name


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
        min_error: str | None = None,
        max_error: str | None = None,
    ) -> None:
        if min_num < 0:
            raise ValueError("min_num cannot be negative")
        if max_num is not None and max_num < min_num:
            raise ValueError("max_num cannot be smaller than min_num")
        self._node_type = node_type
        self.min_num = min_num
        self.max_num = max_num
        self.min_error = min_error
        self.max_error = max_error

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
        text_error: str = "unexpected text",
        tail_error: str = "unexpected text",
        min_error: str | None = None,
        positional_path_attributes: dict[str, str] | None = None,
        unique_by: Field[Any] | None = None,
        duplicate_error: str = "duplicate child key {key!r}",
    ) -> None:
        super().__init__()
        if min_num < 0:
            raise ValueError("min_num cannot be negative")
        if max_num is not None and max_num < min_num:
            raise ValueError("max_num cannot be smaller than min_num")
        self.specs = specs
        self.min_num = min_num
        self.max_num = max_num
        self.text_error = text_error
        self.tail_error = tail_error
        self.min_error = min_error
        self.positional_path_attributes = positional_path_attributes or {}
        self.unique_by = unique_by
        self.duplicate_error = duplicate_error

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

    def type_for_element(self, element: ElementTree.Element) -> "type[Tag] | None":
        spec = self.spec_for_element(element)
        if spec is None:
            return None
        node_type = spec.node_type
        if not issubclass(node_type, Tag):
            raise TypeError("element child declaration must refer to a Tag")
        return node_type

    def validate(self, value: list[Node] | UnsetType) -> None:
        if value is UNSET or not isinstance(value, list):
            raise ValidationError("children must be a list")

        if len(value) < self.min_num:
            if self.min_error is not None:
                raise ValidationError(self.min_error)
            raise ValidationError(
                f"{self.name} requires at least {self.min_num} child(ren); "
                f"got {len(value)}"
            )
        if self.max_num is not None and len(value) > self.max_num:
            raise ValidationError(
                f"{self.name} permits at most {self.max_num} child(ren); "
                f"got {len(value)}"
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
            if count < spec.min_num:
                if spec.min_error is not None:
                    raise ValidationError(spec.min_error)
                raise ValidationError(
                    f"{self.name} requires at least {spec.min_num} "
                    f"{spec.node_type.__name__} child(ren); got {count}"
                )
            if spec.max_num is not None and count > spec.max_num:
                if spec.max_error is not None:
                    raise ValidationError(spec.max_error)
                tag_name = getattr(spec.node_type, "tag_name", None)
                if spec.max_num == 1 and isinstance(tag_name, str):
                    local_name = tag_name.rsplit("}", 1)[-1]
                    raise ValidationError(f"expected at most one {local_name} child")
                raise ValidationError(
                    f"{self.name} permits at most {spec.max_num} "
                    f"{spec.node_type.__name__} child(ren); got {count}"
                )

    def validate_resolved_types(self, node_types: tuple[type[Node], ...]) -> None:
        if len(node_types) < self.min_num:
            if self.min_error is not None:
                raise ValidationError(self.min_error)
            raise ValidationError(
                f"{self.name} requires at least {self.min_num} child(ren); "
                f"got {len(node_types)}"
            )
        if self.max_num is not None and len(node_types) > self.max_num:
            raise ValidationError(
                f"{self.name} permits at most {self.max_num} child(ren); "
                f"got {len(node_types)}"
            )
        for spec in self.specs:
            count = sum(
                issubclass(node_type, spec.node_type) for node_type in node_types
            )
            if count < spec.min_num:
                if spec.min_error is not None:
                    raise ValidationError(spec.min_error)
                raise ValidationError(
                    f"{self.name} requires at least {spec.min_num} "
                    f"{spec.node_type.__name__} child(ren); got {count}"
                )
            if spec.max_num is not None and count > spec.max_num:
                if spec.max_error is not None:
                    raise ValidationError(spec.max_error)
                tag_name = getattr(spec.node_type, "tag_name", None)
                if spec.max_num == 1 and isinstance(tag_name, str):
                    local_name = tag_name.rsplit("}", 1)[-1]
                    raise ValidationError(f"expected at most one {local_name} child")
                raise ValidationError(
                    f"{self.name} permits at most {spec.max_num} "
                    f"{spec.node_type.__name__} child(ren); got {count}"
                )

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
        """Validate relationships between fully decoded fields on this tag."""

    def validate_after_attributes(self) -> None:
        """Validate field relationships before any child content is decoded."""

    def validate_after_descendants(self) -> None:
        """Validate decode semantics after all descendant content is decoded."""

    def validate_after_child_shell(self) -> None:
        """Validate fields after direct-child lexical/type shell validation."""

    def validate_resolved_child_types(
        self, child_types: tuple[type[Node], ...]
    ) -> None:
        """Validate relationships across resolved direct child alternatives."""

    def _validate_field(self, name: str, field: Field[Any]) -> None:
        try:
            field.validate(getattr(self, name))
        except ValidationError as error:
            raise ValidationError(
                f"{type(self).__name__}.{name}: {error}",
                attribute_name=error.attribute_name,
            ) from error

    def validate(self) -> None:
        if self.tag_name is None:
            raise ValidationError(f"{type(self).__name__} has no tag_name")
        fields = self.fields()
        for name, field in fields.items():
            if not isinstance(field, Children):
                self._validate_field(name, field)
        self.validate_after_child_shell()
        for name, field in fields.items():
            if isinstance(field, Children):
                self._validate_field(name, field)
                children = cast(list[Node], getattr(self, name))
                self.validate_resolved_child_types(
                    tuple(type(child) for child in children)
                )
        self.clean()

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

        fields = cls.fields()
        values = {
            name: field.decode_from_attributes(element.attrib, decoder)
            for name, field in fields.items()
            if not isinstance(field, Children)
        }
        node = cls(**values)
        try:
            for name, field in fields.items():
                if not isinstance(field, Children):
                    node._validate_field(name, field)
            node.validate_after_attributes()
        except ValidationError as error:
            decoder.fail(str(error), attribute_name=error.attribute_name)

        children_field = next(
            (field for field in fields.values() if isinstance(field, Children)), None
        )
        if children_field is not None and decoder.child_uniqueness_is_active:
            decoder.validate_whitespace_shell(element, children_field)
        decoder.validate_child_uniqueness(node)
        if children_field is not None:
            with decoder.children_of(node):
                setattr(
                    node,
                    cast(str, children_field.name),
                    children_field.decode_from(element, decoder),
                )
        try:
            node.validate_after_descendants()
        except ValidationError as error:
            decoder.fail(str(error), attribute_name=error.attribute_name)
        return node

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
        self._child_owners: list[Tag] = []
        self._uniqueness: list[tuple[Children, set[object]]] = []

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

    @contextmanager
    def children_of(self, owner: Tag) -> Generator[None]:
        self._child_owners.append(owner)
        field = next(
            (item for item in owner.fields().values() if isinstance(item, Children)),
            None,
        )
        if field is None:
            raise TypeError(f"{type(owner).__name__} has no Children field")
        self._uniqueness.append((field, set()))
        try:
            yield
        finally:
            self._uniqueness.pop()
            self._child_owners.pop()

    @property
    def child_uniqueness_is_active(self) -> bool:
        return bool(self._uniqueness and self._uniqueness[-1][0].unique_by is not None)

    def validate_whitespace_shell(
        self, element: ElementTree.Element, field: Children
    ) -> None:
        if element.text and element.text.strip() and not field.permits_text:
            self.fail(field.text_error)
        if not field.permits_text:
            for child in element:
                if child.tail and child.tail.strip():
                    self.fail(field.tail_error)

    def validate_child_uniqueness(self, child: Tag) -> None:
        if not self._uniqueness:
            return
        field, seen = self._uniqueness[-1]
        if field.unique_by is None:
            return
        key = field.unique_by.__get__(child, type(child))
        if key in seen:
            self.fail(field.duplicate_error.format(key=key))
        seen.add(key)

    def loads[T: Tag](self, source: str, root_type: type[T]) -> T:
        try:
            element = ElementTree.fromstring(source)
        except ElementTree.ParseError as error:
            raise DecodeError(str(error)) from error
        return self.decode_element(element, root_type)

    def decode_element[T: Tag](
        self, element: ElementTree.Element, node_type: type[T]
    ) -> T:
        return self._decode_element(element, node_type)

    def _decode_element[T: Tag](
        self, element: ElementTree.Element, node_type: type[T]
    ) -> T:
        node = node_type.decode_from(element, self)
        try:
            node.validate()
        except ValidationError as error:
            raise DecodeError(str(error), path=tuple(self._path)) from error
        return node

    def decode_children(
        self, parent: ElementTree.Element, field: Children
    ) -> list[Node]:
        result: list[Node] = []
        owner = self._child_owners[-1] if self._child_owners else None
        if field.unique_by is not None:
            self.validate_whitespace_shell(parent, field)

        def append_text(value: str | None, error_message: str) -> None:
            if value is None or not value:
                return
            if field.permits_text:
                result.append(Text(value))
            elif value.strip():
                self.fail(error_message)

        append_text(parent.text, field.text_error)
        child_totals: dict[str, int] = {}
        resolved: list[tuple[int, ElementTree.Element, Child, type[Tag]]] = []
        for position, child_element in enumerate(parent, 1):
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
                self.fail(field.tail_error)
            resolved.append((position, child_element, spec, child_type))

        child_types = tuple(child_type for _, _, _, child_type in resolved)
        try:
            if owner is not None:
                owner.validate_after_child_shell()
            field.validate_resolved_types(child_types)
            if owner is not None:
                owner.validate_resolved_child_types(child_types)
        except ValidationError as error:
            self.fail(str(error))

        child_counts: dict[str, int] = {}
        for position, child_element, spec, child_type in resolved:
            child_counts[child_element.tag] = child_counts.get(child_element.tag, 0) + 1
            path_step = child_element.tag
            repeated = spec.max_num is None or spec.max_num > 1
            if repeated and (
                not field.permits_text or child_totals[child_element.tag] > 1
            ):
                path_step += f"[{child_counts[child_element.tag]}]"
            try:
                with self.at(path_step):
                    child = self._decode_element(child_element, child_type)
            except DecodeError as error:
                positional_attribute = field.positional_path_attributes.get(
                    child_element.tag
                )
                if (
                    positional_attribute is not None
                    and error.attribute_name == positional_attribute
                ):
                    error.path = (*error.path[:-1], f"*[{position}]")
                raise
            result.append(child)
            append_text(child_element.tail, field.tail_error)

        return field.normalize(result)


class Encoder:
    def dumps(self, node: Tag) -> str:
        element = self.encode_element(node)
        return ElementTree.tostring(element, encoding="unicode", method="xml")

    def encode_element(self, node: Tag) -> ElementTree.Element:
        return self._encode_element(node)

    def _encode_element(self, node: Tag) -> ElementTree.Element:
        element = ElementTree.Element(cast(str, node.tag_name))
        for name, field in node.fields().items():
            if isinstance(field, Children):
                field.encode_into(getattr(node, name), element, self)
            else:
                field.encode_into_attributes(getattr(node, name), element.attrib, self)
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

            element = self._encode_element(cast(Tag, child))
            parent.append(element)
            previous_element = element
