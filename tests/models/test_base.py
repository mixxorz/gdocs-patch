import pytest

from gdocs_patch.models.base import UNSET, Color, Dimension, TreeNode, UnsetType


def test_unset_is_a_singleton_with_readable_representation() -> None:
    assert UnsetType() is UNSET
    assert repr(UNSET) == "UNSET"


def test_models_compare_by_exact_class_and_attributes() -> None:
    assert Dimension(magnitude=12, unit="PT") == Dimension(
        magnitude=12,
        unit="PT",
    )
    assert Dimension(magnitude=12, unit="PT") != Dimension(
        magnitude=13,
        unit="PT",
    )
    assert Dimension() != Color()


def test_model_representation_and_unhashability() -> None:
    dimension = Dimension(magnitude=12, unit="PT")

    assert repr(dimension) == "Dimension(magnitude=12, unit='PT')"
    with pytest.raises(TypeError):
        hash(dimension)


def test_tree_node_adds_child_and_sets_its_parent() -> None:
    root = TreeNode()
    child = TreeNode()

    root.add_child(child)

    assert root.children == [child]
    assert child.parent is root


def test_dimension_uses_proto_defaults() -> None:
    dimension = Dimension()

    assert dimension.magnitude == 0
    assert dimension.unit == "UNIT_UNSPECIFIED"


def test_color_uses_proto_defaults_and_accepts_boundaries() -> None:
    assert Color() == Color(red=0, green=0, blue=0)
    assert Color(red=0.0, green=0.5, blue=1.0) == Color(
        red=0.0,
        green=0.5,
        blue=1.0,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("red", -0.01),
        ("green", 1.01),
        ("blue", 2.0),
    ],
)
def test_color_rejects_components_outside_unit_interval(
    field: str,
    value: float,
) -> None:
    values = {"red": 0.0, "green": 0.0, "blue": 0.0}
    values[field] = value

    with pytest.raises(
        ValueError,
        match=rf"color {field} must be between 0.0 and 1.0",
    ):
        Color(**values)
