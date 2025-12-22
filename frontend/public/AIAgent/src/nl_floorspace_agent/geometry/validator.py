"""Geometry validation placeholder."""

import math
from typing import List, Tuple, Dict, Optional
from ..models.floorspace import Geometry, Edge, Vertex, WindowInstance, DoorInstance, WindowDefinition, DoorDefinition


class GeometryValidator:
    """Validates geometric constraints for building elements."""
    
    def __init__(self):
        """Initialize the geometry validator."""
        pass
    
    def calculate_edge_length(self, edge: Edge, vertices: List[Vertex]) -> float:
        """Calculate the length of an edge.
        
        Args:
            edge: The edge to measure
            vertices: List of vertices in the geometry
            
        Returns:
            Length of the edge in meters
        """
        if len(edge.vertex_ids) != 2:
            raise ValueError("Edge must connect exactly 2 vertices")
        
        # Find the vertices
        vertex_dict = {v.id: v for v in vertices}
        v1 = vertex_dict.get(edge.vertex_ids[0])
        v2 = vertex_dict.get(edge.vertex_ids[1])
        
        if not v1 or not v2:
            raise ValueError("Edge vertices not found in geometry")
        
        # Calculate Euclidean distance
        dx = v2.x - v1.x
        dy = v2.y - v1.y
        return math.sqrt(dx * dx + dy * dy)
    
    def validate_element_fits_on_wall(self, element_width: float, edge: Edge, 
                                    vertices: List[Vertex]) -> bool:
        """Validate that an element fits within the wall boundaries.
        
        Args:
            element_width: Width of the element in meters
            edge: The edge (wall) to place element on
            vertices: List of vertices in the geometry
            
        Returns:
            True if element fits, False otherwise
        """
        if element_width <= 0:
            return False
        
        wall_length = self.calculate_edge_length(edge, vertices)
        return element_width <= wall_length
    
    def validate_no_element_overlap(self, new_element_width: float, new_alpha: float,
                                  existing_elements: List[Tuple[float, float]], 
                                  wall_length: float) -> bool:
        """Validate that a new element doesn't overlap with existing elements on the same wall.
        
        Args:
            new_element_width: Width of the new element in meters
            new_alpha: Alpha position (0-1) of the new element
            existing_elements: List of (width, alpha) tuples for existing elements
            wall_length: Length of the wall in meters
            
        Returns:
            True if no overlap, False if overlap detected
        """
        if new_element_width <= 0 or not (0 <= new_alpha <= 1):
            return False
        
        # Calculate new element's position range
        new_start = new_alpha * wall_length - new_element_width / 2
        new_end = new_alpha * wall_length + new_element_width / 2
        
        # Check against existing elements
        for existing_width, existing_alpha in existing_elements:
            if existing_width <= 0 or not (0 <= existing_alpha <= 1):
                continue
            
            existing_start = existing_alpha * wall_length - existing_width / 2
            existing_end = existing_alpha * wall_length + existing_width / 2
            
            # Check for overlap
            if not (new_end <= existing_start or new_start >= existing_end):
                return False  # Overlap detected
        
        return True
    
    def validate_element_dimensions_reasonable(self, element_type: str, width: float, 
                                             height: float) -> bool:
        """Validate that element dimensions are reasonable for their intended use.
        
        Args:
            element_type: Type of element ("window" or "door")
            width: Element width in meters
            height: Element height in meters
            
        Returns:
            True if dimensions are reasonable, False otherwise
        """
        if width <= 0 or height <= 0:
            return False
        
        if element_type.lower() == "window":
            # More lenient window dimensions: 0.2m to 5m wide, 0.2m to 4m high
            return (0.2 <= width <= 5.0) and (0.2 <= height <= 4.0)
        elif element_type.lower() == "door":
            # More lenient door dimensions: 0.5m to 3m wide, 1.5m to 3.5m high
            return (0.5 <= width <= 3.0) and (1.5 <= height <= 3.5)
        else:
            # Unknown element type, use general constraints
            return (0.1 <= width <= 10.0) and (0.1 <= height <= 10.0)
    
    def validate_wall_sufficient_for_elements(self, wall_length: float, 
                                            elements: List[Tuple[str, float, float, float]]) -> bool:
        """Validate that a wall is long enough to accommodate all specified elements.
        
        Args:
            wall_length: Length of the wall in meters
            elements: List of (element_type, width, height, alpha) tuples
            
        Returns:
            True if wall is sufficient, False otherwise
        """
        if wall_length <= 0:
            return False
        
        # Calculate total width needed (assuming elements don't overlap)
        total_width = sum(width for _, width, _, _ in elements if width > 0)
        
        # Add minimum spacing between elements (10cm between each)
        if len(elements) > 1:
            total_width += (len(elements) - 1) * 0.1
        
        return total_width <= wall_length
    
    def validate_geometry_constraints(self, geometry: Geometry, 
                                    windows: List[WindowInstance],
                                    doors: List[DoorInstance],
                                    window_definitions: List[WindowDefinition],
                                    door_definitions: List[DoorDefinition]) -> Dict[str, List[str]]:
        """Validate all geometric constraints for a complete geometry.
        
        Args:
            geometry: The geometry to validate
            windows: List of window instances
            doors: List of door instances
            window_definitions: List of window definitions
            door_definitions: List of door definitions
            
        Returns:
            Dictionary with constraint violations grouped by type
        """
        violations = {
            "element_fit": [],
            "element_overlap": [],
            "dimension_reasonable": [],
            "wall_sufficient": []
        }
        
        # Create lookup dictionaries
        window_def_dict = {wd.id: wd for wd in window_definitions}
        door_def_dict = {dd.id: dd for dd in door_definitions}
        edge_dict = {e.id: e for e in geometry.edges}
        
        # Group elements by edge
        elements_by_edge = {}
        
        # Process windows
        for window in windows:
            if window.edge_id not in elements_by_edge:
                elements_by_edge[window.edge_id] = []
            
            window_def = window_def_dict.get(window.window_definition_id)
            if window_def:
                elements_by_edge[window.edge_id].append({
                    "type": "window",
                    "width": window_def.width,
                    "height": window_def.height,
                    "alpha": window.alpha,
                    "instance": window,
                    "definition": window_def
                })
        
        # Process doors
        for door in doors:
            if door.edge_id not in elements_by_edge:
                elements_by_edge[door.edge_id] = []
            
            door_def = door_def_dict.get(door.door_definition_id)
            if door_def:
                elements_by_edge[door.edge_id].append({
                    "type": "door",
                    "width": door_def.width,
                    "height": door_def.height,
                    "alpha": door.alpha,
                    "instance": door,
                    "definition": door_def
                })
        
        # Validate constraints for each edge
        for edge_id, elements in elements_by_edge.items():
            edge = edge_dict.get(edge_id)
            if not edge:
                continue
            
            try:
                wall_length = self.calculate_edge_length(edge, geometry.vertices)
            except ValueError:
                continue
            
            # Check if each element fits on the wall
            for element in elements:
                if not self.validate_element_fits_on_wall(element["width"], edge, geometry.vertices):
                    violations["element_fit"].append(
                        f"{element['type'].title()} '{element['instance'].name}' "
                        f"(width {element['width']:.2f}m) doesn't fit on wall "
                        f"(length {wall_length:.2f}m)"
                    )
                
                # Check if dimensions are reasonable
                if not self.validate_element_dimensions_reasonable(
                    element["type"], element["width"], element["height"]
                ):
                    violations["dimension_reasonable"].append(
                        f"{element['type'].title()} '{element['instance'].name}' "
                        f"has unreasonable dimensions: {element['width']:.2f}m x {element['height']:.2f}m"
                    )
            
            # Check for overlaps between elements on the same wall
            for i, element1 in enumerate(elements):
                for j, element2 in enumerate(elements[i + 1:], i + 1):
                    existing_elements = [(element2["width"], element2["alpha"])]
                    if not self.validate_no_element_overlap(
                        element1["width"], element1["alpha"], existing_elements, wall_length
                    ):
                        violations["element_overlap"].append(
                            f"{element1['type'].title()} '{element1['instance'].name}' "
                            f"overlaps with {element2['type']} '{element2['instance'].name}' "
                            f"on the same wall"
                        )
            
            # Check if wall is sufficient for all elements
            element_specs = [
                (elem["type"], elem["width"], elem["height"], elem["alpha"]) 
                for elem in elements
            ]
            if not self.validate_wall_sufficient_for_elements(wall_length, element_specs):
                violations["wall_sufficient"].append(
                    f"Wall (length {wall_length:.2f}m) is not sufficient for "
                    f"{len(elements)} elements with total width "
                    f"{sum(elem['width'] for elem in elements):.2f}m"
                )
        
        return violations