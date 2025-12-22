"""Property-based tests for Floorspace JSON data models."""

import pytest
from hypothesis import given, strategies as st, assume
from pydantic import ValidationError
import json

from src.nl_floorspace_agent.models.floorspace import (
    VertexModel, EdgeModel, FaceModel, GeometryModel, SpaceModel,
    WindowDefinitionModel, DoorDefinitionModel, WindowInstanceModel,
    DoorInstanceModel, StoryModel, FloorspaceModelPydantic
)


# Hypothesis strategies for generating test data
@st.composite
def vertex_strategy(draw):
    """Generate valid vertex data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "x": draw(st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)),
        "y": draw(st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)),
        "edge_ids": draw(st.lists(st.text(min_size=1, max_size=20).filter(lambda x: x.strip()), max_size=10))
    }


@st.composite
def edge_strategy(draw):
    """Generate valid edge data."""
    vertex_id1 = draw(st.text(min_size=1, max_size=20).filter(lambda x: x.strip()))
    vertex_id2 = draw(st.text(min_size=1, max_size=20).filter(lambda x: x.strip() and x != vertex_id1))
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "vertex_ids": [vertex_id1, vertex_id2],
        "face_ids": draw(st.lists(st.text(min_size=1, max_size=20).filter(lambda x: x.strip()), max_size=5))
    }


@st.composite
def face_strategy(draw):
    """Generate valid face data."""
    edge_count = draw(st.integers(min_value=3, max_value=8))
    edge_ids = draw(st.lists(
        st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        min_size=edge_count, max_size=edge_count
    ))
    edge_order = draw(st.lists(
        st.sampled_from([1, -1]),
        min_size=edge_count, max_size=edge_count
    ))
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "edge_ids": edge_ids,
        "edge_order": edge_order
    }


@st.composite
def geometry_strategy(draw):
    """Generate valid geometry data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "vertices": draw(st.lists(vertex_strategy(), max_size=5)),
        "edges": draw(st.lists(edge_strategy(), max_size=5)),
        "faces": draw(st.lists(face_strategy(), max_size=3))
    }


@st.composite
def hex_color_strategy(draw):
    """Generate valid hex color strings."""
    r = draw(st.integers(min_value=0, max_value=255))
    g = draw(st.integers(min_value=0, max_value=255))
    b = draw(st.integers(min_value=0, max_value=255))
    return f"#{r:02X}{g:02X}{b:02X}"


@st.composite
def space_strategy(draw):
    """Generate valid space data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "face_id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "color": draw(hex_color_strategy()),
        "type": draw(st.text(min_size=1, max_size=20).filter(lambda x: x.strip()))
    }


@st.composite
def window_definition_strategy(draw):
    """Generate valid window definition data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "height": draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)),
        "width": draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)),
        "window_type": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "sill_height": draw(st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))
    }


@st.composite
def door_definition_strategy(draw):
    """Generate valid door definition data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "height": draw(st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False)),
        "width": draw(st.floats(min_value=0.1, max_value=3.0, allow_nan=False, allow_infinity=False)),
        "door_type": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    }


@st.composite
def window_instance_strategy(draw):
    """Generate valid window instance data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "window_definition_id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "edge_id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "alpha": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    }


@st.composite
def door_instance_strategy(draw):
    """Generate valid door instance data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "door_definition_id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "edge_id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "alpha": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    }


@st.composite
def story_strategy(draw):
    """Generate valid story data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        "name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "geometry": draw(geometry_strategy()),
        "spaces": draw(st.lists(space_strategy(), max_size=3)),
        "windows": draw(st.lists(window_instance_strategy(), max_size=3)),
        "doors": draw(st.lists(door_instance_strategy(), max_size=3)),
        "floor_to_ceiling_height": draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)),
        "multiplier": draw(st.integers(min_value=1, max_value=10)),
        "color": draw(hex_color_strategy())
    }


@st.composite
def floorspace_model_strategy(draw):
    """Generate valid FloorspaceModel data."""
    return {
        "application": draw(st.dictionaries(st.text(), st.text(), max_size=3)),
        "project": draw(st.dictionaries(st.text(), st.text(), max_size=3)),
        "stories": draw(st.lists(story_strategy(), max_size=2)),
        "window_definitions": draw(st.lists(window_definition_strategy(), max_size=3)),
        "door_definitions": draw(st.lists(door_definition_strategy(), max_size=3)),
        "building_units": draw(st.lists(st.dictionaries(st.text(), st.text(), max_size=2), max_size=2)),
        "thermal_zones": draw(st.lists(st.dictionaries(st.text(), st.text(), max_size=2), max_size=2)),
        "space_types": draw(st.lists(st.dictionaries(st.text(), st.text(), max_size=2), max_size=2)),
        "construction_sets": draw(st.lists(st.dictionaries(st.text(), st.text(), max_size=2), max_size=2)),
        "version": draw(st.text(min_size=1, max_size=20).filter(lambda x: x.strip()))
    }


class TestFloorspaceJSONStructure:
    """
    **Feature: nl-floorspace-agent, Property 6: Floorspace JSON Schema Compliance**
    **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
    
    Property-based tests for Floorspace JSON structure validation.
    """

    @given(vertex_data=vertex_strategy())
    def test_vertex_model_validation(self, vertex_data):
        """Test that valid vertex data creates valid VertexModel instances."""
        vertex = VertexModel(**vertex_data)
        assert vertex.id == vertex_data["id"]
        assert vertex.x == vertex_data["x"]
        assert vertex.y == vertex_data["y"]
        assert vertex.edge_ids == vertex_data["edge_ids"]

    @given(edge_data=edge_strategy())
    def test_edge_model_validation(self, edge_data):
        """Test that valid edge data creates valid EdgeModel instances."""
        edge = EdgeModel(**edge_data)
        assert edge.id == edge_data["id"]
        assert len(edge.vertex_ids) == 2
        assert edge.vertex_ids[0] != edge.vertex_ids[1]
        assert edge.face_ids == edge_data["face_ids"]

    @given(face_data=face_strategy())
    def test_face_model_validation(self, face_data):
        """Test that valid face data creates valid FaceModel instances."""
        face = FaceModel(**face_data)
        assert face.id == face_data["id"]
        assert len(face.edge_ids) >= 3
        assert len(face.edge_order) == len(face.edge_ids)
        assert all(order in [1, -1] for order in face.edge_order)

    @given(geometry_data=geometry_strategy())
    def test_geometry_model_validation(self, geometry_data):
        """Test that valid geometry data creates valid GeometryModel instances."""
        geometry = GeometryModel(**geometry_data)
        assert geometry.id == geometry_data["id"]
        assert len(geometry.vertices) == len(geometry_data["vertices"])
        assert len(geometry.edges) == len(geometry_data["edges"])
        assert len(geometry.faces) == len(geometry_data["faces"])

    @given(space_data=space_strategy())
    def test_space_model_validation(self, space_data):
        """Test that valid space data creates valid SpaceModel instances."""
        space = SpaceModel(**space_data)
        assert space.id == space_data["id"]
        assert space.name == space_data["name"]
        assert space.face_id == space_data["face_id"]
        assert space.color == space_data["color"]
        assert space.type == space_data["type"]

    @given(window_def_data=window_definition_strategy())
    def test_window_definition_model_validation(self, window_def_data):
        """Test that valid window definition data creates valid WindowDefinitionModel instances."""
        window_def = WindowDefinitionModel(**window_def_data)
        assert window_def.id == window_def_data["id"]
        assert window_def.name == window_def_data["name"]
        assert window_def.height > 0
        assert window_def.width > 0
        assert window_def.sill_height >= 0

    @given(door_def_data=door_definition_strategy())
    def test_door_definition_model_validation(self, door_def_data):
        """Test that valid door definition data creates valid DoorDefinitionModel instances."""
        door_def = DoorDefinitionModel(**door_def_data)
        assert door_def.id == door_def_data["id"]
        assert door_def.name == door_def_data["name"]
        assert door_def.height > 0
        assert door_def.width > 0

    @given(window_inst_data=window_instance_strategy())
    def test_window_instance_model_validation(self, window_inst_data):
        """Test that valid window instance data creates valid WindowInstanceModel instances."""
        window_inst = WindowInstanceModel(**window_inst_data)
        assert window_inst.id == window_inst_data["id"]
        assert window_inst.name == window_inst_data["name"]
        assert 0 <= window_inst.alpha <= 1

    @given(door_inst_data=door_instance_strategy())
    def test_door_instance_model_validation(self, door_inst_data):
        """Test that valid door instance data creates valid DoorInstanceModel instances."""
        door_inst = DoorInstanceModel(**door_inst_data)
        assert door_inst.id == door_inst_data["id"]
        assert door_inst.name == door_inst_data["name"]
        assert 0 <= door_inst.alpha <= 1

    @given(story_data=story_strategy())
    def test_story_model_validation(self, story_data):
        """Test that valid story data creates valid StoryModel instances."""
        story = StoryModel(**story_data)
        assert story.id == story_data["id"]
        assert story.name == story_data["name"]
        assert story.floor_to_ceiling_height > 0
        assert story.multiplier >= 1

    @given(floorspace_data=floorspace_model_strategy())
    def test_floorspace_model_validation(self, floorspace_data):
        """Test that valid floorspace data creates valid FloorspaceModelPydantic instances."""
        model = FloorspaceModelPydantic(**floorspace_data)
        assert model.version == floorspace_data["version"]
        assert len(model.stories) == len(floorspace_data["stories"])
        assert len(model.window_definitions) == len(floorspace_data["window_definitions"])
        assert len(model.door_definitions) == len(floorspace_data["door_definitions"])

    @given(floorspace_data=floorspace_model_strategy())
    def test_floorspace_json_serialization(self, floorspace_data):
        """Test that FloorspaceModel can be serialized to and from JSON."""
        model = FloorspaceModelPydantic(**floorspace_data)
        
        # Test JSON serialization
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        
        # Test JSON deserialization
        parsed_json = json.loads(json_str)
        reconstructed_model = FloorspaceModelPydantic(**parsed_json)
        
        # Verify the reconstructed model matches the original
        assert reconstructed_model.version == model.version
        assert len(reconstructed_model.stories) == len(model.stories)

    def test_invalid_vertex_validation(self):
        """Test that invalid vertex data raises ValidationError."""
        with pytest.raises(ValidationError):
            VertexModel(id="", x=1.0, y=1.0)  # Empty ID
        
        with pytest.raises(ValidationError):
            VertexModel(id="valid", x=float('nan'), y=1.0)  # NaN coordinate

    def test_invalid_edge_validation(self):
        """Test that invalid edge data raises ValidationError."""
        with pytest.raises(ValidationError):
            EdgeModel(id="edge1", vertex_ids=["v1"])  # Only one vertex
        
        with pytest.raises(ValidationError):
            EdgeModel(id="edge1", vertex_ids=["v1", "v1"])  # Same vertex twice

    def test_invalid_face_validation(self):
        """Test that invalid face data raises ValidationError."""
        with pytest.raises(ValidationError):
            FaceModel(id="face1", edge_ids=["e1", "e2"], edge_order=[1, -1, 1])  # Mismatched lengths
        
        with pytest.raises(ValidationError):
            FaceModel(id="face1", edge_ids=["e1"], edge_order=[1])  # Too few edges

    def test_invalid_space_validation(self):
        """Test that invalid space data raises ValidationError."""
        with pytest.raises(ValidationError):
            SpaceModel(id="space1", name="Room", face_id="face1", color="invalid")  # Invalid color
        
        with pytest.raises(ValidationError):
            SpaceModel(id="", name="Room", face_id="face1", color="#FF0000")  # Empty ID

    def test_invalid_window_definition_validation(self):
        """Test that invalid window definition data raises ValidationError."""
        with pytest.raises(ValidationError):
            WindowDefinitionModel(id="w1", name="Window", height=-1.0, width=1.0, window_type="fixed", sill_height=0.5)  # Negative height
        
        with pytest.raises(ValidationError):
            WindowDefinitionModel(id="w1", name="Window", height=1.0, width=0.0, window_type="fixed", sill_height=0.5)  # Zero width

    def test_invalid_door_definition_validation(self):
        """Test that invalid door definition data raises ValidationError."""
        with pytest.raises(ValidationError):
            DoorDefinitionModel(id="d1", name="Door", height=0.0, width=1.0, door_type="swing")  # Zero height
        
        with pytest.raises(ValidationError):
            DoorDefinitionModel(id="d1", name="Door", height=2.0, width=-1.0, door_type="swing")  # Negative width

    def test_invalid_alpha_validation(self):
        """Test that invalid alpha values raise ValidationError."""
        with pytest.raises(ValidationError):
            WindowInstanceModel(id="wi1", name="Window", window_definition_id="wd1", edge_id="e1", alpha=1.5)  # Alpha > 1
        
        with pytest.raises(ValidationError):
            DoorInstanceModel(id="di1", name="Door", door_definition_id="dd1", edge_id="e1", alpha=-0.1)  # Alpha < 0