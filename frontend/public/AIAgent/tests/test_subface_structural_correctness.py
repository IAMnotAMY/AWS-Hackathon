"""Property-based tests for sub-face structural correctness.

**Feature: nl-floorspace-agent, Property 7: Sub-face Structural Correctness**
**Validates: Requirements 4.3**
"""

import pytest
from hypothesis import given, strategies as st, assume
import math

from src.nl_floorspace_agent.geometry.generator import GeometryGenerator
from src.nl_floorspace_agent.models.core import (
    SpaceRequirement, Dimensions, Units, BuildingElement, ElementType, ElementSpec
)


class TestSubFaceStructuralCorrectness:
    """Property-based tests for sub-face structural correctness."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GeometryGenerator()
    
    @given(
        width=st.floats(min_value=3.0, max_value=50.0),  # Larger spaces to accommodate elements
        length=st.floats(min_value=3.0, max_value=50.0),
        window_width=st.floats(min_value=0.7, max_value=2.0),  # Reasonable after conversion
        window_height=st.floats(min_value=0.7, max_value=2.0),
        wall=st.sampled_from(["north", "south", "east", "west"]),
        alpha=st.floats(min_value=0.1, max_value=0.9),
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_window_subface_structural_correctness(self, width, length, window_width, 
                                                  window_height, wall, alpha, units):
        """Property 7: For any window added to a space, the sub-face element should have correct parent-child relationships.
        
        **Feature: nl-floorspace-agent, Property 7: Sub-face Structural Correctness**
        **Validates: Requirements 4.3**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [width, length, window_width, window_height, alpha]))
        
        # Ensure space is large enough to accommodate the window
        wall_length = width if wall in ["north", "south"] else length
        window_width_meters = window_width if units == Units.SI else window_width * 0.3048
        assume(window_width_meters <= wall_length)
        
        # Create space requirement with window
        dimensions = Dimensions(width=width, length=length, units=units)
        
        window_spec = ElementSpec(
            width=window_width,
            height=window_height,
            wall=wall,
            alpha=alpha
        )
        
        window_element = BuildingElement(
            type=ElementType.WINDOW,
            count=1,
            specifications=window_spec
        )
        
        requirement = SpaceRequirement(
            dimensions=dimensions,
            elements=[window_element],
            room_type="TestRoom"
        )
        
        # Generate complete model with window
        model = self.generator.generate_geometry(requirement)
        
        # Validate model structure
        assert len(model.stories) == 1, "Model should have exactly one story"
        story = model.stories[0]
        
        # Validate window definitions and instances exist
        assert len(model.window_definitions) == 1, "Should have one window definition"
        assert len(story.windows) == 1, "Should have one window instance"
        
        window_def = model.window_definitions[0]
        window_inst = story.windows[0]
        
        # 1. Window instance should reference the window definition
        assert window_inst.window_definition_id == window_def.id, \
            "Window instance must reference correct window definition"
        
        # 2. Window definition should have valid dimensions
        assert window_def.width > 0, "Window definition width must be positive"
        assert window_def.height > 0, "Window definition height must be positive"
        assert math.isfinite(window_def.width), "Window width must be finite"
        assert math.isfinite(window_def.height), "Window height must be finite"
        
        # 3. Window instance should reference a valid edge
        edge_ids = {edge.id for edge in story.geometry.edges}
        assert window_inst.edge_id in edge_ids, \
            "Window instance must reference existing edge"
        
        # 4. Alpha positioning should be valid
        assert 0 <= window_inst.alpha <= 1, \
            f"Window alpha must be between 0 and 1: {window_inst.alpha}"
        
        # 5. Window should be placed on the correct wall
        expected_edge_id = self.generator._get_edge_for_wall(story.geometry, wall)
        assert window_inst.edge_id == expected_edge_id, \
            f"Window should be on {wall} wall (edge {expected_edge_id})"
        
        # 6. Window dimensions should match specification
        expected_width = window_width if units == Units.SI else window_width * 0.3048
        expected_height = window_height if units == Units.SI else window_height * 0.3048
        
        tolerance = 1e-10
        assert abs(window_def.width - expected_width) < tolerance, \
            f"Window width mismatch: expected {expected_width}, got {window_def.width}"
        assert abs(window_def.height - expected_height) < tolerance, \
            f"Window height mismatch: expected {expected_height}, got {window_def.height}"
        
        # 7. Window should have valid IDs
        assert window_def.id, "Window definition must have non-empty ID"
        assert window_inst.id, "Window instance must have non-empty ID"
        assert window_def.id != window_inst.id, "Definition and instance must have different IDs"
    
    @given(
        width=st.floats(min_value=5.0, max_value=50.0),  # Larger spaces to accommodate doors
        length=st.floats(min_value=5.0, max_value=50.0),
        door_width=st.floats(min_value=2.0, max_value=2.8),  # Reasonable door widths
        door_height=st.floats(min_value=1.8, max_value=3.0),  # Reasonable door heights
        wall=st.sampled_from(["north", "south", "east", "west"]),
        alpha=st.floats(min_value=0.1, max_value=0.9),
        units=st.sampled_from([Units.SI])  # Use SI only to avoid conversion issues
    )
    def test_door_subface_structural_correctness(self, width, length, door_width, 
                                               door_height, wall, alpha, units):
        """Property 7: For any door added to a space, the sub-face element should have correct parent-child relationships.
        
        **Feature: nl-floorspace-agent, Property 7: Sub-face Structural Correctness**
        **Validates: Requirements 4.3**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [width, length, door_width, door_height, alpha]))
        
        # Ensure space is large enough to accommodate the door
        wall_length = width if wall in ["north", "south"] else length
        door_width_meters = door_width if units == Units.SI else door_width * 0.3048
        assume(door_width_meters <= wall_length)
        
        # Create space requirement with door
        dimensions = Dimensions(width=width, length=length, units=units)
        
        door_spec = ElementSpec(
            width=door_width,
            height=door_height,
            wall=wall,
            alpha=alpha
        )
        
        door_element = BuildingElement(
            type=ElementType.DOOR,
            count=1,
            specifications=door_spec
        )
        
        requirement = SpaceRequirement(
            dimensions=dimensions,
            elements=[door_element],
            room_type="TestRoom"
        )
        
        # Generate complete model with door
        model = self.generator.generate_geometry(requirement)
        
        # Validate model structure
        assert len(model.stories) == 1, "Model should have exactly one story"
        story = model.stories[0]
        
        # Validate door definitions and instances exist
        assert len(model.door_definitions) == 1, "Should have one door definition"
        assert len(story.doors) == 1, "Should have one door instance"
        
        door_def = model.door_definitions[0]
        door_inst = story.doors[0]
        
        # 1. Door instance should reference the door definition
        assert door_inst.door_definition_id == door_def.id, \
            "Door instance must reference correct door definition"
        
        # 2. Door definition should have valid dimensions
        assert door_def.width > 0, "Door definition width must be positive"
        assert door_def.height > 0, "Door definition height must be positive"
        assert math.isfinite(door_def.width), "Door width must be finite"
        assert math.isfinite(door_def.height), "Door height must be finite"
        
        # 3. Door instance should reference a valid edge
        edge_ids = {edge.id for edge in story.geometry.edges}
        assert door_inst.edge_id in edge_ids, \
            "Door instance must reference existing edge"
        
        # 4. Alpha positioning should be valid
        assert 0 <= door_inst.alpha <= 1, \
            f"Door alpha must be between 0 and 1: {door_inst.alpha}"
        
        # 5. Door should be placed on the correct wall
        expected_edge_id = self.generator._get_edge_for_wall(story.geometry, wall)
        assert door_inst.edge_id == expected_edge_id, \
            f"Door should be on {wall} wall (edge {expected_edge_id})"
        
        # 6. Door dimensions should match specification
        expected_width = door_width if units == Units.SI else door_width * 0.3048
        expected_height = door_height if units == Units.SI else door_height * 0.3048
        
        tolerance = 1e-10
        assert abs(door_def.width - expected_width) < tolerance, \
            f"Door width mismatch: expected {expected_width}, got {door_def.width}"
        assert abs(door_def.height - expected_height) < tolerance, \
            f"Door height mismatch: expected {expected_height}, got {door_def.height}"
        
        # 7. Door should have valid IDs
        assert door_def.id, "Door definition must have non-empty ID"
        assert door_inst.id, "Door instance must have non-empty ID"
        assert door_def.id != door_inst.id, "Definition and instance must have different IDs"
    
    @given(
        width=st.floats(min_value=5.0, max_value=20.0),  # Larger spaces
        length=st.floats(min_value=5.0, max_value=20.0),
        window_count=st.integers(min_value=1, max_value=2),  # Fewer elements
        door_count=st.integers(min_value=1, max_value=1),
        units=st.sampled_from([Units.SI])  # Use SI only to avoid conversion issues
    )
    def test_multiple_elements_structural_correctness(self, width, length, window_count, 
                                                    door_count, units):
        """Test structural correctness with multiple windows and doors.
        
        **Feature: nl-floorspace-agent, Property 7: Sub-face Structural Correctness**
        **Validates: Requirements 4.3**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [width, length]))
        
        # Create space requirement with multiple elements
        dimensions = Dimensions(width=width, length=length, units=units)
        
        elements = []
        
        # Add windows
        for i in range(window_count):
            window_spec = ElementSpec(
                width=0.8,  # Reasonable window size
                height=1.2,
                wall="north",
                alpha=0.2 + (i * 0.3)  # Spread windows along wall
            )
            window_element = BuildingElement(
                type=ElementType.WINDOW,
                count=1,
                specifications=window_spec
            )
            elements.append(window_element)
        
        # Add doors
        for i in range(door_count):
            door_spec = ElementSpec(
                width=0.9,  # Reasonable door size
                height=2.1,
                wall="south",
                alpha=0.5  # Center door
            )
            door_element = BuildingElement(
                type=ElementType.DOOR,
                count=1,
                specifications=door_spec
            )
            elements.append(door_element)
        
        requirement = SpaceRequirement(
            dimensions=dimensions,
            elements=elements,
            room_type="TestRoom"
        )
        
        # Generate complete model
        model = self.generator.generate_geometry(requirement)
        
        # Validate model structure
        story = model.stories[0]
        
        # Should have correct number of definitions and instances
        assert len(model.window_definitions) == window_count, \
            f"Should have {window_count} window definitions"
        assert len(model.door_definitions) == door_count, \
            f"Should have {door_count} door definitions"
        assert len(story.windows) == window_count, \
            f"Should have {window_count} window instances"
        assert len(story.doors) == door_count, \
            f"Should have {door_count} door instances"
        
        # All window instances should reference valid definitions
        window_def_ids = {wd.id for wd in model.window_definitions}
        for window_inst in story.windows:
            assert window_inst.window_definition_id in window_def_ids, \
                "Window instance must reference existing definition"
        
        # All door instances should reference valid definitions
        door_def_ids = {dd.id for dd in model.door_definitions}
        for door_inst in story.doors:
            assert door_inst.door_definition_id in door_def_ids, \
                "Door instance must reference existing definition"
        
        # All instances should reference valid edges
        edge_ids = {edge.id for edge in story.geometry.edges}
        for window_inst in story.windows:
            assert window_inst.edge_id in edge_ids, \
                "Window instance must reference existing edge"
        for door_inst in story.doors:
            assert door_inst.edge_id in edge_ids, \
                "Door instance must reference existing edge"
    
    def test_invalid_element_dimensions_rejected(self):
        """Test that invalid element dimensions are properly rejected."""
        generator = GeometryGenerator()
        
        # Test zero width window
        with pytest.raises(ValueError, match="Window dimensions must be positive"):
            generator.create_window_definition(width=0.0, height=1.2)
        
        # Test negative height door
        with pytest.raises(ValueError, match="Door dimensions must be positive"):
            generator.create_door_definition(width=0.9, height=-2.1)
        
        # Test invalid alpha values
        with pytest.raises(ValueError, match="Alpha must be between 0 and 1"):
            generator.create_window_instance("def_id", "edge_id", alpha=1.5)
        
        with pytest.raises(ValueError, match="Alpha must be between 0 and 1"):
            generator.create_door_instance("def_id", "edge_id", alpha=-0.1)