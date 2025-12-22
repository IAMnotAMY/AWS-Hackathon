"""Unit tests for JSON export functionality."""

import json
import math
import pytest
from decimal import Decimal
from src.nl_floorspace_agent.export.json_exporter import FloorspaceJSONExporter
from src.nl_floorspace_agent.export.schema_validator import ValidationResult
from src.nl_floorspace_agent.models.floorspace import (
    FloorspaceModel,
    Story,
    Geometry,
    Vertex,
    Edge,
    Face,
    Space,
    WindowDefinition,
    DoorDefinition,
    WindowInstance,
    DoorInstance,
)


class TestFloorspaceJSONExporter:
    """Test cases for FloorspaceJSONExporter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.exporter = FloorspaceJSONExporter(coordinate_precision=3)

    def create_simple_model(self):
        """Create a simple FloorspaceModel for testing."""
        # Create vertices for a 5x4 rectangle
        vertices = [
            Vertex(id="1", x=0.0, y=0.0, edge_ids=["1", "4"]),
            Vertex(id="2", x=5.0, y=0.0, edge_ids=["1", "2"]),
            Vertex(id="3", x=5.0, y=4.0, edge_ids=["2", "3"]),
            Vertex(id="4", x=0.0, y=4.0, edge_ids=["3", "4"])
        ]
        
        # Create edges
        edges = [
            Edge(id="1", vertex_ids=["1", "2"], face_ids=["1"]),
            Edge(id="2", vertex_ids=["2", "3"], face_ids=["1"]),
            Edge(id="3", vertex_ids=["3", "4"], face_ids=["1"]),
            Edge(id="4", vertex_ids=["4", "1"], face_ids=["1"])
        ]
        
        # Create face
        faces = [
            Face(id="1", edge_ids=["1", "2", "3", "4"], edge_order=[1, 1, 1, 1])
        ]
        
        # Create geometry
        geometry = Geometry(id="1", vertices=vertices, edges=edges, faces=faces)
        
        # Create space
        spaces = [
            Space(id="1", name="Living Room", face_id="1", color="#FF0000")
        ]
        
        # Create story
        story = Story(
            id="1", 
            name="Story 1", 
            geometry=geometry, 
            spaces=spaces,
            floor_to_ceiling_height=3.0
        )
        
        # Create model
        model = FloorspaceModel(
            stories=[story],
            version="1.4.3"
        )
        
        return model

    def create_model_with_elements(self):
        """Create a FloorspaceModel with windows and doors for testing."""
        model = self.create_simple_model()
        
        # Add window definition
        window_def = WindowDefinition(
            id="wd1",
            name="Standard Window",
            height=1.5,
            width=1.0,
            window_type="Fixed",
            sill_height=0.9
        )
        model.window_definitions.append(window_def)
        
        # Add door definition
        door_def = DoorDefinition(
            id="dd1",
            name="Standard Door",
            height=2.1,
            width=0.9,
            door_type="Door"
        )
        model.door_definitions.append(door_def)
        
        # Add window instance
        window_instance = WindowInstance(
            id="wi1",
            name="Window 1",
            window_definition_id="wd1",
            edge_id="2",
            alpha=0.5
        )
        model.stories[0].windows.append(window_instance)
        
        # Add door instance
        door_instance = DoorInstance(
            id="di1",
            name="Door 1",
            door_definition_id="dd1",
            edge_id="4",
            alpha=0.3
        )
        model.stories[0].doors.append(door_instance)
        
        return model

    def test_exporter_initialization(self):
        """Test exporter initialization with different precision settings."""
        # Default precision
        exporter1 = FloorspaceJSONExporter()
        assert exporter1.coordinate_precision == 6
        assert exporter1._id_counter == 1
        
        # Custom precision
        exporter2 = FloorspaceJSONExporter(coordinate_precision=2)
        assert exporter2.coordinate_precision == 2

    def test_id_generation(self):
        """Test unique ID generation."""
        assert self.exporter.generate_id() == "1"
        assert self.exporter.generate_id() == "2"
        assert self.exporter.generate_id() == "3"
        
        # Test reset
        self.exporter.reset_id_counter()
        assert self.exporter.generate_id() == "1"

    def test_coordinate_formatting(self):
        """Test coordinate formatting with different precision levels."""
        # Test with precision 3
        assert self.exporter.format_coordinate(1.23456789) == 1.235
        assert self.exporter.format_coordinate(0.0) == 0.0
        assert self.exporter.format_coordinate(-1.23456789) == -1.235
        assert self.exporter.format_coordinate(10.0) == 10.0
        
        # Test with different precision
        exporter_2 = FloorspaceJSONExporter(coordinate_precision=2)
        assert exporter_2.format_coordinate(1.23456789) == 1.23
        
        # Test edge cases
        with pytest.raises(ValueError, match="Coordinate value cannot be NaN"):
            self.exporter.format_coordinate(float('nan'))
        
        with pytest.raises(ValueError, match="Coordinate value cannot be infinite"):
            self.exporter.format_coordinate(float('inf'))
        
        with pytest.raises(ValueError, match="Coordinate value cannot be infinite"):
            self.exporter.format_coordinate(float('-inf'))

    def test_version_validation(self):
        """Test version compatibility validation."""
        # Valid versions
        assert self.exporter.validate_version_compatibility("1.4.3") == True
        assert self.exporter.validate_version_compatibility("1.5.0") == True
        assert self.exporter.validate_version_compatibility("2.0.0") == True
        assert self.exporter.validate_version_compatibility("1.4.0") == True
        
        # Invalid versions
        assert self.exporter.validate_version_compatibility("1.3.0") == False
        assert self.exporter.validate_version_compatibility("0.9.0") == False
        assert self.exporter.validate_version_compatibility("invalid") == False
        assert self.exporter.validate_version_compatibility("") == False
        assert self.exporter.validate_version_compatibility("1.4") == False
        assert self.exporter.validate_version_compatibility("1.4.3.1") == False

    def test_build_application_config(self):
        """Test building default application configuration."""
        config = self.exporter.build_application_config()
        
        # Check required fields
        assert "currentSelections" in config
        assert "modes" in config
        assert "tools" in config
        assert "scale" in config
        
        # Check specific values
        assert config["currentSelections"]["tool"] == "Rectangle"
        assert config["currentSelections"]["mode"] == "spaces"
        assert "spaces" in config["modes"]
        assert "Rectangle" in config["tools"]

    def test_build_project_config(self):
        """Test building default project configuration."""
        # Test with default units
        config = self.exporter.build_project_config()
        assert config["config"]["units"] == "ip"
        
        # Test with custom units
        config_si = self.exporter.build_project_config(units="si")
        assert config_si["config"]["units"] == "si"
        
        # Check required fields
        assert "config" in config
        assert "north_axis" in config
        assert "ground" in config
        assert "grid" in config
        assert "view" in config
        assert "map" in config

    def test_vertex_to_dict(self):
        """Test vertex conversion to dictionary."""
        vertex = Vertex(id="1", x=1.23456, y=2.34567, edge_ids=["e1", "e2"])
        result = self.exporter.vertex_to_dict(vertex)
        
        expected = {
            "id": "1",
            "x": 1.235,  # Formatted with precision 3
            "y": 2.346,  # Formatted with precision 3
            "edge_ids": ["e1", "e2"]
        }
        assert result == expected

    def test_edge_to_dict(self):
        """Test edge conversion to dictionary."""
        edge = Edge(id="1", vertex_ids=["v1", "v2"], face_ids=["f1"])
        result = self.exporter.edge_to_dict(edge)
        
        expected = {
            "id": "1",
            "vertex_ids": ["v1", "v2"],
            "face_ids": ["f1"]
        }
        assert result == expected

    def test_face_to_dict(self):
        """Test face conversion to dictionary."""
        face = Face(id="1", edge_ids=["e1", "e2", "e3"], edge_order=[1, -1, 1])
        result = self.exporter.face_to_dict(face)
        
        expected = {
            "id": "1",
            "edge_ids": ["e1", "e2", "e3"],
            "edge_order": [1, -1, 1]
        }
        assert result == expected

    def test_space_to_dict(self):
        """Test space conversion to dictionary."""
        space = Space(id="1", name="Living Room", face_id="f1", color="#FF0000")
        result = self.exporter.space_to_dict(space)
        
        # Check required fields
        assert result["id"] == "1"
        assert result["name"] == "Living Room"
        assert result["face_id"] == "f1"
        assert result["color"] == "#FF0000"
        assert result["type"] == "space"
        
        # Check optional fields are set to None or empty lists
        assert result["handle"] is None
        assert result["building_unit_id"] is None
        assert result["daylighting_controls"] == []

    def test_window_definition_to_dict(self):
        """Test window definition conversion to dictionary."""
        window_def = WindowDefinition(
            id="1",
            name="Test Window",
            height=1.5,
            width=1.0,
            window_type="Fixed",
            sill_height=0.9
        )
        result = self.exporter.window_definition_to_dict(window_def)
        
        expected = {
            "id": "1",
            "name": "Test Window",
            "window_definition_mode": "Single Window",
            "wwr": None,
            "sill_height": 0.9,
            "window_spacing": None,
            "height": 1.5,
            "width": 1.0,
            "window_type": "Fixed",
            "overhang_projection_factor": None,
            "fin_projection_factor": None,
            "texture": "circles-5"
        }
        assert result == expected

    def test_door_definition_to_dict(self):
        """Test door definition conversion to dictionary."""
        door_def = DoorDefinition(
            id="1",
            name="Test Door",
            height=2.1,
            width=0.9,
            door_type="Door"
        )
        result = self.exporter.door_definition_to_dict(door_def)
        
        expected = {
            "id": "1",
            "name": "Test Door",
            "height": 2.1,
            "width": 0.9,
            "door_type": "Door",
            "texture": "circles-5"
        }
        assert result == expected

    def test_window_instance_to_dict(self):
        """Test window instance conversion to dictionary."""
        window = WindowInstance(
            id="1",
            name="Window 1",
            window_definition_id="wd1",
            edge_id="e1",
            alpha=0.5
        )
        result = self.exporter.window_instance_to_dict(window)
        
        expected = {
            "window_definition_id": "wd1",
            "edge_id": "e1",
            "alpha": 0.5,
            "id": "1",
            "name": "Window 1"
        }
        assert result == expected

    def test_door_instance_to_dict(self):
        """Test door instance conversion to dictionary."""
        door = DoorInstance(
            id="1",
            name="Door 1",
            door_definition_id="dd1",
            edge_id="e1",
            alpha=0.3
        )
        result = self.exporter.door_instance_to_dict(door)
        
        expected = {
            "door_definition_id": "dd1",
            "edge_id": "e1",
            "alpha": 0.3,
            "id": "1",
            "name": "Door 1"
        }
        assert result == expected

    def test_export_to_dict_simple_model(self):
        """Test exporting a simple model to dictionary."""
        model = self.create_simple_model()
        result = self.exporter.export_to_dict(model)
        
        # Check top-level structure
        assert "application" in result
        assert "project" in result
        assert "stories" in result
        assert "version" in result
        assert result["version"] == "1.4.3"
        
        # Check stories
        assert len(result["stories"]) == 1
        story = result["stories"][0]
        assert story["id"] == "1"
        assert story["name"] == "Story 1"
        assert story["floor_to_ceiling_height"] == 3.0
        
        # Check geometry
        geometry = story["geometry"]
        assert len(geometry["vertices"]) == 4
        assert len(geometry["edges"]) == 4
        assert len(geometry["faces"]) == 1
        
        # Check spaces
        assert len(story["spaces"]) == 1
        space = story["spaces"][0]
        assert space["name"] == "Living Room"
        assert space["color"] == "#FF0000"

    def test_export_to_dict_with_elements(self):
        """Test exporting a model with windows and doors to dictionary."""
        model = self.create_model_with_elements()
        result = self.exporter.export_to_dict(model)
        
        # Check window definitions
        assert len(result["window_definitions"]) == 1
        window_def = result["window_definitions"][0]
        assert window_def["name"] == "Standard Window"
        assert window_def["height"] == 1.5
        
        # Check door definitions
        assert len(result["door_definitions"]) == 1
        door_def = result["door_definitions"][0]
        assert door_def["name"] == "Standard Door"
        assert door_def["height"] == 2.1
        
        # Check window instances
        story = result["stories"][0]
        assert len(story["windows"]) == 1
        window = story["windows"][0]
        assert window["name"] == "Window 1"
        assert window["alpha"] == 0.5
        
        # Check door instances
        assert len(story["doors"]) == 1
        door = story["doors"][0]
        assert door["name"] == "Door 1"
        assert door["alpha"] == 0.3

    def test_export_to_json_without_validation(self):
        """Test exporting to JSON string without validation."""
        model = self.create_simple_model()
        json_str = self.exporter.export_to_json(model, validate=False)
        
        # Should return a string
        assert isinstance(json_str, str)
        
        # Should be valid JSON
        data = json.loads(json_str)
        assert "application" in data
        assert "stories" in data
        assert data["version"] == "1.4.3"

    def test_export_to_json_with_validation(self):
        """Test exporting to JSON string with validation."""
        model = self.create_simple_model()
        result = self.exporter.export_to_json(model, validate=True)
        
        # Should return tuple
        assert isinstance(result, tuple)
        json_str, validation_result = result
        
        # Validation should pass
        assert validation_result.is_valid
        assert isinstance(json_str, str)
        
        # Should be valid JSON
        data = json.loads(json_str)
        assert "application" in data
        assert "stories" in data

    def test_export_to_json_with_indentation(self):
        """Test JSON formatting with indentation."""
        model = self.create_simple_model()
        
        # Compact format
        compact_json = self.exporter.export_to_json(model, validate=False)
        assert '\n' not in compact_json
        
        # Indented format
        indented_json = self.exporter.export_to_json(model, indent=2, validate=False)
        assert '\n' in indented_json
        assert '  ' in indented_json  # Should have 2-space indentation

    def test_format_json(self):
        """Test JSON formatting method."""
        data = {"test": "value", "number": 123}
        
        # Compact format
        compact = self.exporter.format_json(data)
        assert compact == '{"test":"value","number":123}'
        
        # Indented format
        indented = self.exporter.format_json(data, indent=2)
        expected = '{\n  "test": "value",\n  "number": 123\n}'
        assert indented == expected

    def test_validate_and_export_to_dict_success(self):
        """Test successful validation and export."""
        model = self.create_simple_model()
        data, validation_result = self.exporter.validate_and_export_to_dict(model)
        
        assert validation_result.is_valid
        assert "application" in data
        assert "stories" in data

    def test_validate_and_export_to_dict_version_error(self):
        """Test validation failure due to unsupported version."""
        model = self.create_simple_model()
        model.version = "1.3.0"  # Unsupported version
        
        data, validation_result = self.exporter.validate_and_export_to_dict(model)
        
        assert not validation_result.is_valid
        assert "Unsupported version: 1.3.0" in validation_result.errors
        assert data == {}

    def test_validate_json_string(self):
        """Test JSON string validation."""
        # Valid JSON
        model = self.create_simple_model()
        json_str = self.exporter.export_to_json(model, validate=False)
        result = self.exporter.validate_json_string(json_str)
        assert result.is_valid
        
        # Invalid JSON
        invalid_json = '{"invalid": json}'
        result = self.exporter.validate_json_string(invalid_json)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_edge_cases_single_space(self):
        """Test edge case with single space and no elements."""
        model = self.create_simple_model()
        result = self.exporter.export_to_dict(model)
        
        # Should have exactly one story with one space
        assert len(result["stories"]) == 1
        assert len(result["stories"][0]["spaces"]) == 1
        assert len(result["stories"][0]["windows"]) == 0
        assert len(result["stories"][0]["doors"]) == 0
        assert len(result["window_definitions"]) == 0
        assert len(result["door_definitions"]) == 0

    def test_edge_cases_empty_building(self):
        """Test edge case with empty building (no spaces)."""
        model = FloorspaceModel(stories=[], version="1.4.3")
        result = self.exporter.export_to_dict(model)
        
        # Should have no stories
        assert len(result["stories"]) == 0
        assert len(result["window_definitions"]) == 0
        assert len(result["door_definitions"]) == 0

    def test_coordinate_precision_consistency(self):
        """Test that coordinate precision is applied consistently."""
        model = self.create_model_with_elements()
        
        # Set some coordinates with high precision
        model.stories[0].geometry.vertices[0].x = 1.123456789
        model.stories[0].geometry.vertices[0].y = 2.987654321
        
        result = self.exporter.export_to_dict(model)
        
        # Check vertex coordinates are formatted
        vertex = result["stories"][0]["geometry"]["vertices"][0]
        assert vertex["x"] == 1.123  # Precision 3
        assert vertex["y"] == 2.988  # Precision 3
        
        # Check window definition dimensions are formatted
        window_def = result["window_definitions"][0]
        assert isinstance(window_def["height"], float)
        assert isinstance(window_def["width"], float)

    def test_custom_application_and_project_config(self):
        """Test using custom application and project configurations."""
        model = self.create_simple_model()
        
        # Set custom configs
        model.application = {"custom": "app_config"}
        model.project = {"custom": "project_config"}
        
        result = self.exporter.export_to_dict(model)
        
        # Should use provided configs
        assert result["application"] == {"custom": "app_config"}
        assert result["project"] == {"custom": "project_config"}

    def test_validation_result_class(self):
        """Test ValidationResult class behavior."""
        # Valid result
        valid_result = ValidationResult(True)
        assert valid_result.is_valid
        assert bool(valid_result) == True
        assert str(valid_result) == "Validation passed"
        
        # Invalid result
        invalid_result = ValidationResult(False, ["Error 1", "Error 2"])
        assert not invalid_result.is_valid
        assert bool(invalid_result) == False
        assert "Error 1" in str(invalid_result)
        assert "Error 2" in str(invalid_result)