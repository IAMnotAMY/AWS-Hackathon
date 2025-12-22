"""Space builder placeholder."""

import math
from typing import List, Tuple, Optional, Dict
from ..models.core import SpaceRequirement, Dimensions, Units
from ..models.floorspace import FloorspaceModel, Story, Space, Geometry


class SpaceBuilder:
    """Handles space placement and building composition logic."""
    
    def __init__(self):
        """Initialize the space builder."""
        pass
    
    def calculate_space_bounds(self, geometry: Geometry) -> Tuple[float, float, float, float]:
        """Calculate the bounding box of a space geometry.
        
        Args:
            geometry: The geometry to calculate bounds for
            
        Returns:
            Tuple of (min_x, min_y, max_x, max_y)
        """
        if not geometry.vertices:
            return (0.0, 0.0, 0.0, 0.0)
        
        x_coords = [v.x for v in geometry.vertices]
        y_coords = [v.y for v in geometry.vertices]
        
        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
    
    def check_space_overlap(self, geometry1: Geometry, geometry2: Geometry, 
                           tolerance: float = 0.01) -> bool:
        """Check if two space geometries overlap.
        
        Args:
            geometry1: First space geometry
            geometry2: Second space geometry
            tolerance: Minimum separation distance to avoid overlap
            
        Returns:
            True if spaces overlap, False otherwise
        """
        bounds1 = self.calculate_space_bounds(geometry1)
        bounds2 = self.calculate_space_bounds(geometry2)
        
        min_x1, min_y1, max_x1, max_y1 = bounds1
        min_x2, min_y2, max_x2, max_y2 = bounds2
        
        # Check if bounding boxes overlap (with tolerance)
        return not (max_x1 + tolerance <= min_x2 or 
                   max_x2 + tolerance <= min_x1 or
                   max_y1 + tolerance <= min_y2 or 
                   max_y2 + tolerance <= min_y1)
    
    def find_placement_at_origin(self) -> Tuple[float, float]:
        """Find placement coordinates at origin for empty buildings.
        
        Returns:
            Tuple of (x, y) coordinates at origin
        """
        return (0.0, 0.0)
    
    def suggest_placement_relative_to_existing(self, existing_geometries: List[Geometry],
                                             new_space_dimensions: Dimensions,
                                             placement_hint: Optional[str] = None) -> List[Tuple[float, float, str]]:
        """Suggest placement coordinates relative to existing spaces.
        
        Args:
            existing_geometries: List of existing space geometries
            new_space_dimensions: Dimensions of the new space to place
            placement_hint: Optional hint like "north of", "east of", etc.
            
        Returns:
            List of (x, y, description) tuples for suggested placements
        """
        if not existing_geometries:
            return [(0.0, 0.0, "At origin (no existing spaces)")]
        
        suggestions = []
        
        # Convert dimensions to meters
        width = new_space_dimensions.width
        length = new_space_dimensions.length
        if new_space_dimensions.units == Units.IP:
            width *= 0.3048
            length *= 0.3048
        
        # Calculate overall bounds of existing building
        all_bounds = [self.calculate_space_bounds(geom) for geom in existing_geometries]
        overall_min_x = min(bounds[0] for bounds in all_bounds)
        overall_min_y = min(bounds[1] for bounds in all_bounds)
        overall_max_x = max(bounds[2] for bounds in all_bounds)
        overall_max_y = max(bounds[3] for bounds in all_bounds)
        
        gap = 0.1  # 10cm gap between spaces
        
        # Suggest placements around the existing building
        suggestions.extend([
            (overall_max_x + gap, overall_min_y, "East of existing building"),
            (overall_min_x - width - gap, overall_min_y, "West of existing building"),
            (overall_min_x, overall_max_y + gap, "North of existing building"),
            (overall_min_x, overall_min_y - length - gap, "South of existing building")
        ])
        
        # If there's a placement hint, prioritize matching suggestions
        if placement_hint:
            hint_lower = placement_hint.lower()
            prioritized = []
            others = []
            
            for x, y, desc in suggestions:
                if any(keyword in hint_lower for keyword in ["east", "right"]) and "East" in desc:
                    prioritized.append((x, y, desc))
                elif any(keyword in hint_lower for keyword in ["west", "left"]) and "West" in desc:
                    prioritized.append((x, y, desc))
                elif any(keyword in hint_lower for keyword in ["north", "above", "top"]) and "North" in desc:
                    prioritized.append((x, y, desc))
                elif any(keyword in hint_lower for keyword in ["south", "below", "bottom"]) and "South" in desc:
                    prioritized.append((x, y, desc))
                else:
                    others.append((x, y, desc))
            
            suggestions = prioritized + others
        
        return suggestions
    
    def validate_placement(self, new_geometry: Geometry, existing_geometries: List[Geometry],
                          allow_overlap: bool = False) -> Tuple[bool, List[str]]:
        """Validate that a space placement doesn't violate constraints.
        
        Args:
            new_geometry: Geometry of the space to place
            existing_geometries: List of existing space geometries
            allow_overlap: Whether to allow overlapping spaces
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        
        # Check for overlaps with existing spaces
        if not allow_overlap:
            for i, existing_geom in enumerate(existing_geometries):
                if self.check_space_overlap(new_geometry, existing_geom):
                    violations.append(f"New space overlaps with existing space {i + 1}")
        
        # Check that space has valid bounds
        bounds = self.calculate_space_bounds(new_geometry)
        min_x, min_y, max_x, max_y = bounds
        
        if max_x <= min_x or max_y <= min_y:
            violations.append("Space has invalid dimensions (zero or negative area)")
        
        # Check for reasonable coordinate values
        coords = [min_x, min_y, max_x, max_y]
        if not all(math.isfinite(coord) for coord in coords):
            violations.append("Space coordinates contain invalid values (NaN or infinite)")
        
        # Check for extremely large coordinates (might indicate placement errors)
        max_coord = 10000.0  # 10km limit
        if any(abs(coord) > max_coord for coord in coords):
            violations.append(f"Space coordinates are extremely large (>{max_coord}m)")
        
        return len(violations) == 0, violations
    
    def get_placement_coordinates(self, existing_model: Optional[FloorspaceModel],
                                 new_space_dimensions: Dimensions,
                                 placement_hint: Optional[str] = None,
                                 allow_overlap: bool = False) -> Tuple[float, float]:
        """Get placement coordinates for a new space.
        
        Args:
            existing_model: Existing FloorspaceModel or None for empty building
            new_space_dimensions: Dimensions of the new space
            placement_hint: Optional placement hint
            allow_overlap: Whether to allow overlapping spaces
            
        Returns:
            Tuple of (x, y) coordinates for placement
        """
        # If no existing model, place at origin
        if not existing_model or not existing_model.stories:
            return self.find_placement_at_origin()
        
        # Get existing geometries from all stories
        existing_geometries = []
        for story in existing_model.stories:
            if story.geometry:
                existing_geometries.append(story.geometry)
        
        if not existing_geometries:
            return self.find_placement_at_origin()
        
        # Get placement suggestions
        suggestions = self.suggest_placement_relative_to_existing(
            existing_geometries, new_space_dimensions, placement_hint
        )
        
        # Try each suggestion until we find a valid one
        from .generator import GeometryGenerator
        generator = GeometryGenerator()
        
        for x, y, description in suggestions:
            # Create temporary geometry at this position
            temp_geometry, _ = generator.create_rectangular_space_geometry(
                new_space_dimensions, x, y
            )
            
            # Validate the placement
            is_valid, violations = self.validate_placement(
                temp_geometry, existing_geometries, allow_overlap
            )
            
            if is_valid:
                return (x, y)
        
        # If no valid placement found and overlap is not allowed, raise error
        if not allow_overlap:
            raise ValueError(
                "Cannot find valid placement for new space without overlapping existing spaces. "
                "Consider allowing overlap or modifying space dimensions."
            )
        
        # Fall back to first suggestion if overlap is allowed
        if suggestions:
            return (suggestions[0][0], suggestions[0][1])
        
        # Ultimate fallback to origin
        return self.find_placement_at_origin()