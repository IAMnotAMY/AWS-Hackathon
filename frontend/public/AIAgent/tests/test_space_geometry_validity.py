"""Property-based tests for space geometry validity.

**Feature: nl-floorspace-agent, Property 8: Space Geometry Validity**
**Validates: Requirements 5.4**
"""

import pytest
from hypothesis import given, strategies as st, assume
import math

from src.nl_floorspace_agent.geometry.generator import GeometryGenerator
from src.nl_floorspace_agent.models.core import SpaceRequirement, Dimensions, Units


class TestSpaceGeometryValidity:
    """Property-based tests for space geometry validity."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GeometryGenerator()
    
    @given(
        width=st.floats(min_value=0.1, max_value=1000.0),
        length=st.floats(min_value=0.1, max_value=1000.0),
        height=st.one_of(st.none(), st.floats(min_value=0.1, max_value=100.0)),
        units=st.sampled_from([Units.SI, Units.IP]),
        origin_x=st.floats(min_value=-1000.0, max_value=1000.0),
        origin_y=st.floats(min_value=-1000.0, max_value=1000.0)
    )
    def test_space_geometry_validity_property(self, width, length, height, units, origin_x, origin_y):
        """Property 8: For any created space, the resulting geometry should form a closed polygon with valid coordinates.
        
        **Feature: nl-floorspace-agent, Property 8: Space Geometry Validity**
        **Validates: Requirements 5.4**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [width, length, origin_x, origin_y]))
        if height is not None:
            assume(math.isfinite(height))
        
        # Create space requirement
        dimensions = Dimensions(
            width=width,
            length=length,
            height=height,
            units=units
        )
        
        requirement = SpaceRequirement(
            dimensions=dimensions,
            elements=[],
            placement=None,
            room_type="TestRoom"
        )
        
        # Generate geometry
        geometry, face_id = self.generator.create_rectangular_space_geometry(
            dimensions, origin_x, origin_y
        )
        
        # Validate the geometry meets all requirements for a valid closed polygon
        
        # 1. Geometry should have vertices, edges, and faces
        assert len(geometry.vertices) > 0, "Geometry must have vertices"
        assert len(geometry.edges) > 0, "Geometry must have edges"
        assert len(geometry.faces) > 0, "Geometry must have faces"
        
        # 2. All coordinates should be valid (finite) numbers
        for vertex in geometry.vertices:
            assert math.isfinite(vertex.x), f"Vertex x coordinate must be finite: {vertex.x}"
            assert math.isfinite(vertex.y), f"Vertex y coordinate must be finite: {vertex.y}"
        
        # 3. For rectangular space, should have exactly 4 vertices and 4 edges
        assert len(geometry.vertices) == 4, "Rectangular space should have 4 vertices"
        assert len(geometry.edges) == 4, "Rectangular space should have 4 edges"
        assert len(geometry.faces) == 1, "Rectangular space should have 1 face"
        
        # 4. Each edge should connect exactly 2 vertices
        for edge in geometry.edges:
            assert len(edge.vertex_ids) == 2, "Each edge must connect exactly 2 vertices"
            
            # Verify vertices exist
            vertex_ids = {v.id for v in geometry.vertices}
            assert all(vid in vertex_ids for vid in edge.vertex_ids), "Edge vertices must exist"
        
        # 5. Face should reference all edges and form a closed polygon
        face = geometry.faces[0]
        assert len(face.edge_ids) == 4, "Rectangular face should have 4 edges"
        assert len(face.edge_order) == 4, "Face edge_order should match edge count"
        
        # Verify edges exist
        edge_ids = {e.id for e in geometry.edges}
        assert all(eid in edge_ids for eid in face.edge_ids), "Face edges must exist"
        
        # 6. Edge order values should be valid (1 or -1)
        assert all(order in [1, -1] for order in face.edge_order), "Edge order must be 1 or -1"
        
        # 7. Vertices should be connected in a closed loop
        # Build adjacency from edges
        vertex_connections = {}
        for edge in geometry.edges:
            v1, v2 = edge.vertex_ids
            if v1 not in vertex_connections:
                vertex_connections[v1] = []
            if v2 not in vertex_connections:
                vertex_connections[v2] = []
            vertex_connections[v1].append(v2)
            vertex_connections[v2].append(v1)
        
        # Each vertex should connect to exactly 2 other vertices (for rectangular space)
        for vertex_id, connections in vertex_connections.items():
            assert len(connections) == 2, f"Vertex {vertex_id} should connect to exactly 2 others"
        
        # 8. Geometry should pass the generator's own validation
        assert self.generator.validate_space_geometry(geometry), "Geometry should pass validation"
        
        # 9. Face ID should be returned and match the created face
        assert face_id == face.id, "Returned face_id should match created face"
        
        # 10. Verify the space has the expected dimensions (converted to meters)
        expected_width = width if units == Units.SI else width * 0.3048
        expected_length = length if units == Units.SI else length * 0.3048
        
        # Calculate actual dimensions from vertices
        vertices_by_id = {v.id: v for v in geometry.vertices}
        
        # Find min/max coordinates
        x_coords = [v.x for v in geometry.vertices]
        y_coords = [v.y for v in geometry.vertices]
        
        actual_width = max(x_coords) - min(x_coords)
        actual_length = max(y_coords) - min(y_coords)
        
        # Allow small floating point tolerance
        tolerance = 1e-10
        assert abs(actual_width - expected_width) < tolerance, f"Width mismatch: expected {expected_width}, got {actual_width}"
        assert abs(actual_length - expected_length) < tolerance, f"Length mismatch: expected {expected_length}, got {actual_length}"
    
    @given(
        width=st.floats(min_value=0.1, max_value=100.0),
        length=st.floats(min_value=0.1, max_value=100.0),
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_complete_floorspace_model_validity(self, width, length, units):
        """Test that complete FloorspaceModel generation produces valid geometry.
        
        **Feature: nl-floorspace-agent, Property 8: Space Geometry Validity**
        **Validates: Requirements 5.4**
        """
        # Filter out invalid floating point values
        assume(all(math.isfinite(x) for x in [width, length]))
        
        # Create space requirement
        dimensions = Dimensions(width=width, length=length, units=units)
        requirement = SpaceRequirement(
            dimensions=dimensions,
            elements=[],
            room_type="TestRoom"
        )
        
        # Generate complete model
        model = self.generator.generate_geometry(requirement)
        
        # Validate model structure
        assert len(model.stories) == 1, "Model should have exactly one story"
        
        story = model.stories[0]
        assert len(story.spaces) == 1, "Story should have exactly one space"
        assert story.geometry is not None, "Story should have geometry"
        
        # Validate geometry using the generator's validation
        assert self.generator.validate_space_geometry(story.geometry), "Story geometry should be valid"
        
        # Validate space references valid face
        space = story.spaces[0]
        face_ids = {f.id for f in story.geometry.faces}
        assert space.face_id in face_ids, "Space should reference existing face"
    
    def test_invalid_dimensions_rejected(self):
        """Test that invalid dimensions are properly rejected."""
        generator = GeometryGenerator()
        
        # Test zero width
        with pytest.raises(ValueError, match="Dimensions must be positive"):
            dimensions = Dimensions(width=0.0, length=5.0, units=Units.SI)
            generator.create_rectangular_space_geometry(dimensions)
        
        # Test negative length
        with pytest.raises(ValueError, match="Dimensions must be positive"):
            dimensions = Dimensions(width=5.0, length=-1.0, units=Units.SI)
            generator.create_rectangular_space_geometry(dimensions)
        
        # Test zero dimensions
        with pytest.raises(ValueError, match="Dimensions must be positive"):
            dimensions = Dimensions(width=0.0, length=0.0, units=Units.SI)
            generator.create_rectangular_space_geometry(dimensions)