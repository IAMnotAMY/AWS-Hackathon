"""Property-based tests for geometric constraint validation.

**Feature: nl-floorspace-agent, Property 5: Geometric Constraint Validation**
**Validates: Requirements 5.1, 5.2, 5.5**
"""

import pytest
from hypothesis import given, strategies as st, assume
import math

from src.nl_floorspace_agent.geometry.generator import GeometryGenerator
from src.nl_floorspace_agent.geometry.validator import GeometryValidator
from src.nl_floorspace_agent.models.core import (
    SpaceRequirement, Dimensions, Units, BuildingElement, ElementType, ElementSpec
)


class TestGeometricConstraints:
    """Property-based tests for geometric constraint validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GeometryGenerator()
        self.validator = GeometryValidator()
    
    @given(
        space_width=st.floats(min_value=2.0, max_value=20.0),
        space_length=st.floats(min_value=2.0, max_value=20.0),
        element_width=st.floats(min_value=0.1, max_value=25.0),  # Can be larger than space
        element_height=st.floats(min_value=0.1, max_value=5.0),
        wall=st.sampled_from(["north", "south", "east", "west"]),
        alpha=st.floats(min_value=0.0, max_value=1.0),
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_element_fits_within_wall_boundaries(self, space_width, space_length, 
                                               element_width, element_height, 
                                               wall, alpha, units):
        """Property 5: For any window or door placement, the element should fit within wall boundaries.
        
        **Feature: nl-floorspace-agent, Property 5: Geometric Constraint Validation**
        **Validates: Requirements 5.1, 5.2, 5.5**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [space_width, space_length, element_width, element_height, alpha]))
        
        # Create space geometry first
        dimensions = Dimensions(width=space_width, length=space_length, units=units)
        geometry, _ = self.generator.create_rectangular_space_geometry(dimensions)
        
        # Get the wall length for the specified wall
        edge_id = self.generator._get_edge_for_wall(geometry, wall)
        assume(edge_id is not None)
        
        edge = next(e for e in geometry.edges if e.id == edge_id)
        wall_length = self.validator.calculate_edge_length(edge, geometry.vertices)
        
        # Convert element width to meters for comparison
        element_width_meters = element_width if units == Units.SI else element_width * 0.3048
        
        # Test the constraint: element should fit within wall boundaries
        fits_within_wall = self.validator.validate_element_fits_on_wall(
            element_width_meters, edge, geometry.vertices
        )
        
        # The element should fit if and only if its width is less than or equal to wall length
        expected_fits = element_width_meters <= wall_length
        
        assert fits_within_wall == expected_fits, \
            f"Element width {element_width_meters:.2f}m vs wall length {wall_length:.2f}m: " \
            f"expected fits={expected_fits}, got fits={fits_within_wall}"
    
    @given(
        space_width=st.floats(min_value=3.0, max_value=20.0),
        space_length=st.floats(min_value=3.0, max_value=20.0),
        element1_width=st.floats(min_value=0.5, max_value=2.0),
        element1_alpha=st.floats(min_value=0.1, max_value=0.9),
        element2_width=st.floats(min_value=0.5, max_value=2.0),
        element2_alpha=st.floats(min_value=0.1, max_value=0.9),
        wall=st.sampled_from(["north", "south", "east", "west"]),
        units=st.sampled_from([Units.SI])  # Use SI to avoid conversion complexity
    )
    def test_elements_do_not_overlap_on_same_wall(self, space_width, space_length,
                                                 element1_width, element1_alpha,
                                                 element2_width, element2_alpha,
                                                 wall, units):
        """Property 5: Multiple elements on the same wall should not overlap.
        
        **Feature: nl-floorspace-agent, Property 5: Geometric Constraint Validation**
        **Validates: Requirements 5.1, 5.2, 5.5**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [
            space_width, space_length, element1_width, element1_alpha,
            element2_width, element2_alpha
        ]))
        
        # Create space geometry
        dimensions = Dimensions(width=space_width, length=space_length, units=units)
        geometry, _ = self.generator.create_rectangular_space_geometry(dimensions)
        
        # Get wall length
        edge_id = self.generator._get_edge_for_wall(geometry, wall)
        assume(edge_id is not None)
        
        edge = next(e for e in geometry.edges if e.id == edge_id)
        wall_length = self.validator.calculate_edge_length(edge, geometry.vertices)
        
        # Both elements should fit individually on the wall
        assume(element1_width <= wall_length)
        assume(element2_width <= wall_length)
        
        # Test overlap validation
        existing_elements = [(element2_width, element2_alpha)]
        no_overlap = self.validator.validate_no_element_overlap(
            element1_width, element1_alpha, existing_elements, wall_length
        )
        
        # Calculate expected overlap
        element1_start = element1_alpha * wall_length - element1_width / 2
        element1_end = element1_alpha * wall_length + element1_width / 2
        element2_start = element2_alpha * wall_length - element2_width / 2
        element2_end = element2_alpha * wall_length + element2_width / 2
        
        # Elements overlap if their ranges intersect
        expected_no_overlap = (element1_end <= element2_start) or (element1_start >= element2_end)
        
        assert no_overlap == expected_no_overlap, \
            f"Element 1: [{element1_start:.2f}, {element1_end:.2f}], " \
            f"Element 2: [{element2_start:.2f}, {element2_end:.2f}], " \
            f"Wall length: {wall_length:.2f}m, " \
            f"Expected no overlap: {expected_no_overlap}, Got: {no_overlap}"
    
    @given(
        element_type=st.sampled_from(["window", "door"]),
        width=st.floats(min_value=0.01, max_value=10.0),
        height=st.floats(min_value=0.01, max_value=10.0)
    )
    def test_element_dimensions_reasonableness(self, element_type, width, height):
        """Property 5: Element dimensions should be reasonable for their intended use.
        
        **Feature: nl-floorspace-agent, Property 5: Geometric Constraint Validation**
        **Validates: Requirements 5.1, 5.2, 5.5**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [width, height]))
        
        # Test dimension validation
        is_reasonable = self.validator.validate_element_dimensions_reasonable(
            element_type, width, height
        )
        
        # Define expected reasonable ranges
        if element_type == "window":
            expected_reasonable = (0.2 <= width <= 5.0) and (0.2 <= height <= 4.0)
        elif element_type == "door":
            expected_reasonable = (0.5 <= width <= 3.0) and (1.5 <= height <= 3.5)
        else:
            expected_reasonable = (0.1 <= width <= 10.0) and (0.1 <= height <= 10.0)
        
        assert is_reasonable == expected_reasonable, \
            f"{element_type.title()} dimensions {width:.2f}m x {height:.2f}m: " \
            f"expected reasonable={expected_reasonable}, got reasonable={is_reasonable}"
    
    @given(
        space_width=st.floats(min_value=1.0, max_value=10.0),
        space_length=st.floats(min_value=1.0, max_value=10.0),
        window_width=st.floats(min_value=0.3, max_value=2.0),
        window_height=st.floats(min_value=0.3, max_value=2.0),
        wall=st.sampled_from(["north", "south", "east", "west"]),
        alpha=st.floats(min_value=0.1, max_value=0.9),
        units=st.sampled_from([Units.SI])
    )
    def test_valid_window_placement_succeeds(self, space_width, space_length,
                                           window_width, window_height,
                                           wall, alpha, units):
        """Test that valid window placements succeed without constraint violations.
        
        **Feature: nl-floorspace-agent, Property 5: Geometric Constraint Validation**
        **Validates: Requirements 5.1, 5.2, 5.5**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [space_width, space_length, window_width, window_height, alpha]))
        
        # Ensure window fits on the wall
        wall_length = space_width if wall in ["north", "south"] else space_length
        assume(window_width <= wall_length)
        
        # Create space requirement with valid window
        dimensions = Dimensions(width=space_width, length=space_length, units=units)
        
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
        
        # This should succeed without raising constraint violations
        try:
            model = self.generator.generate_geometry(requirement)
            
            # Verify the window was created
            assert len(model.window_definitions) == 1, "Should have one window definition"
            assert len(model.stories[0].windows) == 1, "Should have one window instance"
            
            # The window should have been placed successfully
            window_def = model.window_definitions[0]
            assert window_def.width == window_width, "Window width should match specification"
            assert window_def.height == window_height, "Window height should match specification"
            
        except ValueError as e:
            if "constraint violations" in str(e):
                pytest.fail(f"Valid window placement should not cause constraint violations: {e}")
            else:
                # Re-raise other ValueError types (like unreasonable dimensions)
                raise
    
    def test_oversized_window_placement_fails(self):
        """Test that oversized window placements fail with constraint violations.
        
        **Feature: nl-floorspace-agent, Property 5: Geometric Constraint Validation**
        **Validates: Requirements 5.1, 5.2, 5.5**
        """
        # Create a small space
        dimensions = Dimensions(width=2.0, length=2.0, units=Units.SI)
        
        # Try to place a window that's wider than the wall
        window_spec = ElementSpec(
            width=3.0,  # Wider than 2m wall
            height=1.2,  # Reasonable height
            wall="north",
            alpha=0.5
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
        
        # This should fail with constraint violations
        with pytest.raises(ValueError, match="constraint violations"):
            self.generator.generate_geometry(requirement)
    
    def test_unreasonable_window_dimensions_rejected(self):
        """Test that unreasonable window dimensions are rejected."""
        generator = GeometryGenerator()
        
        # Test window too small
        with pytest.raises(ValueError, match="unreasonable"):
            generator.create_window_definition(width=0.1, height=0.1)
        
        # Test window too large
        with pytest.raises(ValueError, match="unreasonable"):
            generator.create_window_definition(width=10.0, height=8.0)
    
    def test_unreasonable_door_dimensions_rejected(self):
        """Test that unreasonable door dimensions are rejected."""
        generator = GeometryGenerator()
        
        # Test door too small
        with pytest.raises(ValueError, match="unreasonable"):
            generator.create_door_definition(width=0.3, height=1.0)
        
        # Test door too large
        with pytest.raises(ValueError, match="unreasonable"):
            generator.create_door_definition(width=5.0, height=4.0)