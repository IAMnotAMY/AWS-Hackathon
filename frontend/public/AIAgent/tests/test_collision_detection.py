"""Property-based tests for collision detection.

**Feature: nl-floorspace-agent, Property 9: Collision Detection**
**Validates: Requirements 3.4**
"""

import pytest
from hypothesis import given, strategies as st, assume
import math

from src.nl_floorspace_agent.geometry.generator import GeometryGenerator
from src.nl_floorspace_agent.geometry.space_builder import SpaceBuilder
from src.nl_floorspace_agent.models.core import (
    SpaceRequirement, Dimensions, Units
)
from src.nl_floorspace_agent.models.floorspace import Space


class TestCollisionDetection:
    """Property-based tests for collision detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GeometryGenerator()
        self.space_builder = SpaceBuilder()
    
    @given(
        space1_width=st.floats(min_value=1.0, max_value=10.0),
        space1_length=st.floats(min_value=1.0, max_value=10.0),
        space2_width=st.floats(min_value=1.0, max_value=10.0),
        space2_length=st.floats(min_value=1.0, max_value=10.0),
        offset_x=st.floats(min_value=-5.0, max_value=15.0),
        offset_y=st.floats(min_value=-5.0, max_value=15.0),
        units=st.sampled_from([Units.SI])
    )
    def test_collision_detection_accuracy(self, space1_width, space1_length,
                                        space2_width, space2_length,
                                        offset_x, offset_y, units):
        """Property 9: For any space placement attempt that would result in overlapping geometry, 
        the agent should reject the placement unless explicitly requested.
        
        **Feature: nl-floorspace-agent, Property 9: Collision Detection**
        **Validates: Requirements 3.4**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [
            space1_width, space1_length, space2_width, space2_length, offset_x, offset_y
        ]))
        
        # Create first space at origin
        dimensions1 = Dimensions(width=space1_width, length=space1_length, units=units)
        geometry1, _ = self.generator.create_rectangular_space_geometry(dimensions1, 0.0, 0.0)
        
        # Create second space at offset position
        dimensions2 = Dimensions(width=space2_width, length=space2_length, units=units)
        geometry2, _ = self.generator.create_rectangular_space_geometry(dimensions2, offset_x, offset_y)
        
        # Test collision detection
        overlap_detected = self.space_builder.check_space_overlap(geometry1, geometry2)
        
        # Calculate expected overlap using bounding box logic
        bounds1 = self.space_builder.calculate_space_bounds(geometry1)
        bounds2 = self.space_builder.calculate_space_bounds(geometry2)
        
        min_x1, min_y1, max_x1, max_y1 = bounds1
        min_x2, min_y2, max_x2, max_y2 = bounds2
        
        tolerance = 0.01  # Same tolerance used in space_builder
        expected_overlap = not (max_x1 + tolerance <= min_x2 or 
                               max_x2 + tolerance <= min_x1 or
                               max_y1 + tolerance <= min_y2 or 
                               max_y2 + tolerance <= min_y1)
        
        assert overlap_detected == expected_overlap, \
            f"Space 1 bounds: {bounds1}, Space 2 bounds: {bounds2}, " \
            f"Expected overlap: {expected_overlap}, Detected: {overlap_detected}"
    
    @given(
        space_width=st.floats(min_value=1.0, max_value=5.0),
        space_length=st.floats(min_value=1.0, max_value=5.0),
        units=st.sampled_from([Units.SI])
    )
    def test_placement_at_origin_for_empty_building(self, space_width, space_length, units):
        """Test that spaces are placed at origin when no existing spaces are present.
        
        **Feature: nl-floorspace-agent, Property 9: Collision Detection**
        **Validates: Requirements 3.4**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [space_width, space_length]))
        
        # Create space requirement
        dimensions = Dimensions(width=space_width, length=space_length, units=units)
        requirement = SpaceRequirement(
            dimensions=dimensions,
            elements=[],
            room_type="TestRoom"
        )
        
        # Generate geometry with no existing model
        model = self.generator.generate_geometry(requirement, existing_model=None)
        
        # Verify space was placed at origin
        assert len(model.stories) == 1, "Should have exactly one story"
        story = model.stories[0]
        
        # Check that the space starts at or near origin
        bounds = self.space_builder.calculate_space_bounds(story.geometry)
        min_x, min_y, max_x, max_y = bounds
        
        # Space should start at origin (0, 0)
        tolerance = 1e-10
        assert abs(min_x - 0.0) < tolerance, f"Space should start at x=0, got min_x={min_x}"
        assert abs(min_y - 0.0) < tolerance, f"Space should start at y=0, got min_y={min_y}"
        
        # Space should have correct dimensions
        actual_width = max_x - min_x
        actual_length = max_y - min_y
        
        assert abs(actual_width - space_width) < tolerance, \
            f"Width mismatch: expected {space_width}, got {actual_width}"
        assert abs(actual_length - space_length) < tolerance, \
            f"Length mismatch: expected {space_length}, got {actual_length}"
    
    def test_overlapping_placement_rejected_by_default(self):
        """Test that collision detection correctly identifies overlapping spaces.
        
        **Feature: nl-floorspace-agent, Property 9: Collision Detection**
        **Validates: Requirements 3.4**
        """
        # Test the collision detection directly
        space_builder = SpaceBuilder()
        
        # Create two overlapping geometries
        dimensions1 = Dimensions(width=3.0, length=3.0, units=Units.SI)
        geometry1, _ = self.generator.create_rectangular_space_geometry(dimensions1, 0.0, 0.0)
        
        dimensions2 = Dimensions(width=2.0, length=2.0, units=Units.SI)
        geometry2, _ = self.generator.create_rectangular_space_geometry(dimensions2, 1.0, 1.0)  # Overlaps
        
        # Test collision detection
        overlap_detected = space_builder.check_space_overlap(geometry1, geometry2)
        assert overlap_detected, "Should detect overlap between overlapping spaces"
        
        # Test validation rejection
        is_valid, violations = space_builder.validate_placement(geometry2, [geometry1], allow_overlap=False)
        assert not is_valid, "Should reject overlapping placement"
        assert len(violations) > 0, "Should report violations"
        assert any("overlap" in v.lower() for v in violations), "Should mention overlap in violations"
        
        # Test non-overlapping geometries
        geometry3, _ = self.generator.create_rectangular_space_geometry(dimensions2, 5.0, 5.0)  # No overlap
        
        no_overlap = space_builder.check_space_overlap(geometry1, geometry3)
        assert not no_overlap, "Should not detect overlap between non-overlapping spaces"
        
        is_valid_separate, violations_separate = space_builder.validate_placement(geometry3, [geometry1], allow_overlap=False)
        assert is_valid_separate, "Should accept non-overlapping placement"
        assert len(violations_separate) == 0, "Should report no violations for valid placement"
    
    def test_overlapping_placement_allowed_when_requested(self):
        """Test that overlapping space placement succeeds when explicitly allowed.
        
        **Feature: nl-floorspace-agent, Property 9: Collision Detection**
        **Validates: Requirements 3.4**
        """
        # Create first space
        dimensions1 = Dimensions(width=3.0, length=3.0, units=Units.SI)
        requirement1 = SpaceRequirement(
            dimensions=dimensions1,
            elements=[],
            room_type="Room1"
        )
        
        # Generate first space
        model = self.generator.generate_geometry(requirement1)
        
        # Add overlapping space with overlap allowed
        dimensions2 = Dimensions(width=2.0, length=2.0, units=Units.SI)
        requirement2 = SpaceRequirement(
            dimensions=dimensions2,
            elements=[],
            room_type="Room2"
        )
        
        # This should succeed because overlap is explicitly allowed
        updated_model = self.generator.generate_geometry(
            requirement2, existing_model=model, allow_overlap=True
        )
        
        # Verify both spaces exist
        assert len(updated_model.stories) == 1, "Should have one story"
        story = updated_model.stories[0]
        assert len(story.spaces) == 2, "Should have two spaces"
        
        # Verify space names
        space_names = {space.name for space in story.spaces}
        assert "Room1" in space_names, "First room should exist"
        assert "Room2" in space_names, "Second room should exist"
    
    @given(
        existing_width=st.floats(min_value=2.0, max_value=8.0),
        existing_length=st.floats(min_value=2.0, max_value=8.0),
        new_width=st.floats(min_value=1.0, max_value=5.0),
        new_length=st.floats(min_value=1.0, max_value=5.0),
        units=st.sampled_from([Units.SI])
    )
    def test_non_overlapping_placement_succeeds(self, existing_width, existing_length,
                                              new_width, new_length, units):
        """Test that non-overlapping space placement succeeds.
        
        **Feature: nl-floorspace-agent, Property 9: Collision Detection**
        **Validates: Requirements 3.4**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [existing_width, existing_length, new_width, new_length]))
        
        # Create first space at origin
        dimensions1 = Dimensions(width=existing_width, length=existing_length, units=units)
        requirement1 = SpaceRequirement(
            dimensions=dimensions1,
            elements=[],
            room_type="ExistingRoom"
        )
        
        model = self.generator.generate_geometry(requirement1)
        
        # Add second space (space_builder should find non-overlapping placement)
        dimensions2 = Dimensions(width=new_width, length=new_length, units=units)
        requirement2 = SpaceRequirement(
            dimensions=dimensions2,
            elements=[],
            room_type="NewRoom"
        )
        
        # This should succeed by finding a non-overlapping placement
        updated_model = self.generator.generate_geometry(
            requirement2, existing_model=model, allow_overlap=False
        )
        
        # Verify both spaces exist
        assert len(updated_model.stories) == 1, "Should have one story"
        story = updated_model.stories[0]
        assert len(story.spaces) == 2, "Should have two spaces"
        
        # Verify no overlap between the geometries
        # Extract individual space geometries (simplified check)
        bounds_list = []
        
        # Get bounds of each face (assuming each space has one face)
        for space in story.spaces:
            face = next(f for f in story.geometry.faces if f.id == space.face_id)
            
            # Get vertices for this face
            face_vertices = []
            for edge_id in face.edge_ids:
                edge = next(e for e in story.geometry.edges if e.id == edge_id)
                for vertex_id in edge.vertex_ids:
                    vertex = next(v for v in story.geometry.vertices if v.id == vertex_id)
                    face_vertices.append(vertex)
            
            # Calculate bounds for this face
            if face_vertices:
                x_coords = [v.x for v in face_vertices]
                y_coords = [v.y for v in face_vertices]
                bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                bounds_list.append(bounds)
        
        # Check that the two spaces don't overlap
        if len(bounds_list) == 2:
            bounds1, bounds2 = bounds_list
            min_x1, min_y1, max_x1, max_y1 = bounds1
            min_x2, min_y2, max_x2, max_y2 = bounds2
            
            tolerance = 0.01
            no_overlap = (max_x1 + tolerance <= min_x2 or 
                         max_x2 + tolerance <= min_x1 or
                         max_y1 + tolerance <= min_y2 or 
                         max_y2 + tolerance <= min_y1)
            
            assert no_overlap, f"Spaces should not overlap: bounds1={bounds1}, bounds2={bounds2}"
    
    def test_placement_validation_rejects_invalid_coordinates(self):
        """Test that placement validation rejects invalid coordinates."""
        space_builder = SpaceBuilder()
        
        # Create geometry with invalid coordinates
        dimensions = Dimensions(width=2.0, length=2.0, units=Units.SI)
        
        # Test with NaN coordinates
        geometry_nan, _ = self.generator.create_rectangular_space_geometry(dimensions, float('nan'), 0.0)
        is_valid, violations = space_builder.validate_placement(geometry_nan, [])
        assert not is_valid, "Should reject NaN coordinates"
        assert any("invalid values" in v for v in violations), "Should mention invalid values"
        
        # Test with extremely large coordinates
        geometry_large, _ = self.generator.create_rectangular_space_geometry(dimensions, 50000.0, 0.0)
        is_valid, violations = space_builder.validate_placement(geometry_large, [])
        assert not is_valid, "Should reject extremely large coordinates"
        assert any("extremely large" in v for v in violations), "Should mention extremely large coordinates"