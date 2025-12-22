"""Geometry generation for building spaces."""

import uuid
import math
from typing import List, Tuple, Optional, Dict
from ..models.core import SpaceRequirement, Dimensions, Units, BuildingElement, ElementType, ElementSpec
from ..models.floorspace import (
    FloorspaceModel, Story, Geometry, Vertex, Edge, Face, Space,
    WindowDefinition, DoorDefinition, WindowInstance, DoorInstance
)
from .validator import GeometryValidator
from .space_builder import SpaceBuilder


class GeometryGenerator:
    """Generates geometric representations of building spaces."""
    
    def __init__(self):
        """Initialize the geometry generator."""
        self._id_counter = 0
        self.validator = GeometryValidator()
        self.space_builder = SpaceBuilder()
    
    def _generate_id(self, prefix: str = "") -> str:
        """Generate a unique ID with optional prefix."""
        self._id_counter += 1
        if prefix:
            return f"{prefix}_{self._id_counter}"
        return str(self._id_counter)
    
    def _convert_to_meters(self, value: float, units: Units) -> float:
        """Convert a value to meters based on units."""
        if units == Units.IP:  # Imperial (feet)
            return value * 0.3048  # feet to meters
        return value  # Already in meters (SI)
    
    def create_rectangular_space_geometry(self, dimensions: Dimensions, 
                                        origin_x: float = 0.0, 
                                        origin_y: float = 0.0) -> Tuple[Geometry, str]:
        """Create geometry for a rectangular space.
        
        Args:
            dimensions: Space dimensions
            origin_x: X coordinate of bottom-left corner
            origin_y: Y coordinate of bottom-left corner
            
        Returns:
            Tuple of (Geometry object, face_id for the space)
        """
        # Convert dimensions to meters
        width = self._convert_to_meters(dimensions.width, dimensions.units)
        length = self._convert_to_meters(dimensions.length, dimensions.units)
        
        # Validate dimensions are positive
        if width <= 0 or length <= 0:
            raise ValueError(f"Dimensions must be positive: width={width}, length={length}")
        
        # Create vertices for rectangular space (counter-clockwise from bottom-left)
        vertices = [
            Vertex(
                id=self._generate_id("vertex"),
                x=origin_x,
                y=origin_y,
                edge_ids=[]
            ),
            Vertex(
                id=self._generate_id("vertex"),
                x=origin_x + width,
                y=origin_y,
                edge_ids=[]
            ),
            Vertex(
                id=self._generate_id("vertex"),
                x=origin_x + width,
                y=origin_y + length,
                edge_ids=[]
            ),
            Vertex(
                id=self._generate_id("vertex"),
                x=origin_x,
                y=origin_y + length,
                edge_ids=[]
            )
        ]
        
        # Create edges connecting vertices in order
        edges = []
        for i in range(4):
            next_i = (i + 1) % 4
            edge = Edge(
                id=self._generate_id("edge"),
                vertex_ids=[vertices[i].id, vertices[next_i].id],
                face_ids=[]
            )
            edges.append(edge)
            
            # Update vertex edge references
            vertices[i].edge_ids.append(edge.id)
            vertices[next_i].edge_ids.append(edge.id)
        
        # Create face for the space (counter-clockwise edge order)
        face = Face(
            id=self._generate_id("face"),
            edge_ids=[edge.id for edge in edges],
            edge_order=[1, 1, 1, 1]  # All edges in positive direction
        )
        
        # Update edge face references
        for edge in edges:
            edge.face_ids.append(face.id)
        
        # Create geometry object
        geometry = Geometry(
            id=self._generate_id("geometry"),
            vertices=vertices,
            edges=edges,
            faces=[face]
        )
        
        return geometry, face.id
    
    def validate_space_geometry(self, geometry: Geometry) -> bool:
        """Validate that space geometry forms a closed polygon with valid coordinates.
        
        Args:
            geometry: The geometry to validate
            
        Returns:
            True if geometry is valid, False otherwise
        """
        if not geometry.vertices or not geometry.edges or not geometry.faces:
            return False
        
        # Check that all coordinates are finite numbers
        for vertex in geometry.vertices:
            if not (math.isfinite(vertex.x) and math.isfinite(vertex.y)):
                return False
        
        # Check that each edge connects exactly 2 vertices
        for edge in geometry.edges:
            if len(edge.vertex_ids) != 2:
                return False
            
            # Verify vertices exist
            vertex_ids = {v.id for v in geometry.vertices}
            if not all(vid in vertex_ids for vid in edge.vertex_ids):
                return False
        
        # Check that faces have valid edge references and form closed polygons
        for face in geometry.faces:
            if len(face.edge_ids) < 3:  # Need at least 3 edges for a polygon
                return False
            
            if len(face.edge_ids) != len(face.edge_order):
                return False
            
            # Verify edges exist
            edge_ids = {e.id for e in geometry.edges}
            if not all(eid in edge_ids for eid in face.edge_ids):
                return False
            
            # Verify edge order values are valid
            if not all(order in [1, -1] for order in face.edge_order):
                return False
        
        return True
    
    def _get_edge_for_wall(self, geometry: Geometry, wall: str) -> Optional[str]:
        """Get the edge ID for a specific wall direction.
        
        Args:
            geometry: The geometry object
            wall: Wall direction (north, south, east, west)
            
        Returns:
            Edge ID for the specified wall, or None if not found
        """
        if not geometry.edges or len(geometry.edges) < 4:
            return None
        
        # For a rectangular room, edges are in order: bottom, right, top, left
        # This corresponds to: south, east, north, west
        wall_to_edge_index = {
            "south": 0,  # Bottom edge
            "east": 1,   # Right edge  
            "north": 2,  # Top edge
            "west": 3    # Left edge
        }
        
        edge_index = wall_to_edge_index.get(wall.lower())
        if edge_index is not None and edge_index < len(geometry.edges):
            return geometry.edges[edge_index].id
        
        return None
    
    def create_window_definition(self, width: float, height: float, name: str) -> WindowDefinition:
        """Create a window definition.
        
        Args:
            width: Window width in meters
            height: Window height in meters
            name: Window name
            
        Returns:
            WindowDefinition object
        """
        return WindowDefinition(
            id=self._generate_id("window_def"),
            name=name,
            height=height,
            width=width,
            window_type="Fixed",
            sill_height=1.0  # Default sill height
        )
    
    def create_door_definition(self, width: float, height: float, name: str) -> DoorDefinition:
        """Create a door definition.
        
        Args:
            width: Door width in meters
            height: Door height in meters
            name: Door name
            
        Returns:
            DoorDefinition object
        """
        return DoorDefinition(
            id=self._generate_id("door_def"),
            name=name,
            height=height,
            width=width,
            door_type="Swinging"
        )
    
    def create_window_instance(self, window_definition_id: str, edge_id: str, 
                             alpha: float, name: str) -> WindowInstance:
        """Create a window instance.
        
        Args:
            window_definition_id: ID of the window definition
            edge_id: ID of the edge to place the window on
            alpha: Position along the edge (0.0 to 1.0)
            name: Window instance name
            
        Returns:
            WindowInstance object
        """
        return WindowInstance(
            id=self._generate_id("window"),
            name=name,
            window_definition_id=window_definition_id,
            edge_id=edge_id,
            alpha=alpha
        )
    
    def create_door_instance(self, door_definition_id: str, edge_id: str,
                           alpha: float, name: str) -> DoorInstance:
        """Create a door instance.
        
        Args:
            door_definition_id: ID of the door definition
            edge_id: ID of the edge to place the door on
            alpha: Position along the edge (0.0 to 1.0)
            name: Door instance name
            
        Returns:
            DoorInstance object
        """
        return DoorInstance(
            id=self._generate_id("door"),
            name=name,
            door_definition_id=door_definition_id,
            edge_id=edge_id,
            alpha=alpha
        )
    
    def generate_geometry(self, requirement: SpaceRequirement, 
                         existing_model: Optional[FloorspaceModel] = None,
                         allow_overlap: bool = False) -> FloorspaceModel:
        """Generate geometry for a space requirement.
        
        Args:
            requirement: The space requirement
            existing_model: Existing FloorspaceModel to add space to (optional)
            allow_overlap: Whether to allow overlapping spaces
            
        Returns:
            FloorspaceModel with generated geometry
        """
        # Determine placement coordinates
        origin_x, origin_y = self.space_builder.get_placement_coordinates(
            existing_model, requirement.dimensions, requirement.placement, allow_overlap
        )
        
        # Create space geometry
        geometry, face_id = self.create_rectangular_space_geometry(
            requirement.dimensions, origin_x, origin_y
        )
        
        # Validate the generated geometry
        if not self.validate_space_geometry(geometry):
            raise ValueError("Generated geometry is invalid")
        
        # Create space object
        space_name = requirement.room_type or "Space"
        space = Space(
            id=self._generate_id("space"),
            name=space_name,
            face_id=face_id,
            color="#E6F3FF",  # Light blue default color
            type="space"
        )
        
        # Process windows and doors
        window_definitions = []
        door_definitions = []
        window_instances = []
        door_instances = []
        
        for element in requirement.elements:
            if element.type == ElementType.WINDOW and element.specifications:
                for i in range(element.count):
                    spec = element.specifications
                    if spec.width and spec.height and spec.wall:
                        # Convert dimensions to meters
                        window_width = self._convert_to_meters(spec.width, requirement.dimensions.units)
                        window_height = self._convert_to_meters(spec.height, requirement.dimensions.units)
                        
                        # Create window definition
                        window_def = self.create_window_definition(
                            width=window_width,
                            height=window_height,
                            name=f"Window {len(window_definitions) + 1}"
                        )
                        window_definitions.append(window_def)
                        
                        # Create window instance
                        edge_id = self._get_edge_for_wall(geometry, spec.wall)
                        if edge_id:
                            # Use provided alpha or default to center of wall
                            alpha = spec.alpha if spec.alpha is not None else 0.5
                            window_inst = self.create_window_instance(
                                window_definition_id=window_def.id,
                                edge_id=edge_id,
                                alpha=alpha,
                                name=f"Window {len(window_instances) + 1}"
                            )
                            window_instances.append(window_inst)
            
            elif element.type == ElementType.DOOR and element.specifications:
                for i in range(element.count):
                    spec = element.specifications
                    if spec.width and spec.height and spec.wall:
                        # Convert dimensions to meters
                        door_width = self._convert_to_meters(spec.width, requirement.dimensions.units)
                        door_height = self._convert_to_meters(spec.height, requirement.dimensions.units)
                        
                        # Create door definition
                        door_def = self.create_door_definition(
                            width=door_width,
                            height=door_height,
                            name=f"Door {len(door_definitions) + 1}"
                        )
                        door_definitions.append(door_def)
                        
                        # Create door instance
                        edge_id = self._get_edge_for_wall(geometry, spec.wall)
                        if edge_id:
                            # Use provided alpha or default to center of wall
                            alpha = spec.alpha if spec.alpha is not None else 0.5
                            door_inst = self.create_door_instance(
                                door_definition_id=door_def.id,
                                edge_id=edge_id,
                                alpha=alpha,
                                name=f"Door {len(door_instances) + 1}"
                            )
                            door_instances.append(door_inst)
        
        # Create or update model
        if existing_model:
            # Add to existing model
            model = existing_model
            
            # Add new definitions
            model.window_definitions.extend(window_definitions)
            model.door_definitions.extend(door_definitions)
            
            # Add to existing story or create new one
            if model.stories:
                story = model.stories[0]  # Add to first story for now
                
                # Merge geometries (simplified - just add new elements)
                story.geometry.vertices.extend(geometry.vertices)
                story.geometry.edges.extend(geometry.edges)
                story.geometry.faces.extend(geometry.faces)
                story.spaces.append(space)
                story.windows.extend(window_instances)
                story.doors.extend(door_instances)
            else:
                # Create new story
                story = Story(
                    id=self._generate_id("story"),
                    name="Story 1",
                    geometry=geometry,
                    spaces=[space],
                    windows=window_instances,
                    doors=door_instances,
                    floor_to_ceiling_height=3.0,
                    multiplier=1,
                    color="#FFFFFF"
                )
                model.stories.append(story)
        else:
            # Create new model
            story = Story(
                id=self._generate_id("story"),
                name="Story 1",
                geometry=geometry,
                spaces=[space],
                windows=window_instances,
                doors=door_instances,
                floor_to_ceiling_height=3.0,
                multiplier=1,
                color="#FFFFFF"
            )
            
            # Create default application and project configurations
            application_config = {
                "currentSelections": {
                    "story": story.id,
                    "space": None,
                    "shading": None,
                    "image": None,
                    "subSelection": None
                },
                "modes": {
                    "currentMode": "spaces"
                }
            }
            
            project_config = {
                "config": {
                    "units": requirement.dimensions.units.value,
                    "language": "EN-US",
                    "north_axis": 0
                },
                "grid": {
                    "visible": True,
                    "spacing": 1.0
                },
                "view": {
                    "min_x": geometry.vertices[0].x - 1,
                    "min_y": geometry.vertices[0].y - 1,
                    "max_x": geometry.vertices[2].x + 1,
                    "max_y": geometry.vertices[2].y + 1
                },
                "map": {
                    "visible": False,
                    "latitude": 39.7392,
                    "longitude": -104.9903,
                    "zoom": 4.5,
                    "rotation": 0,
                    "elevation": 0
                }
            }
            
            model = FloorspaceModel(
                application=application_config,
                project=project_config,
                stories=[story],
                window_definitions=window_definitions,
                door_definitions=door_definitions,
                building_units=[],
                thermal_zones=[],
                space_types=[],
                construction_sets=[],
                version="1.4.3"
            )
        
        # Validate geometric constraints
        violations = self.validator.validate_geometry_constraints(
            geometry, window_instances, door_instances, 
            window_definitions, door_definitions
        )
        
        # Check for critical violations
        critical_violations = []
        for violation_type, messages in violations.items():
            if violation_type in ["element_fit", "element_overlap"] and messages:
                critical_violations.extend(messages)
        
        if critical_violations:
            raise ValueError(f"Geometric constraint violations: {'; '.join(critical_violations)}")
        
        return model
    
    def _get_edge_for_wall(self, geometry: Geometry, wall: str) -> Optional[str]:
        """Get the edge ID for a wall reference.
        
        Args:
            geometry: The geometry containing edges
            wall: Wall reference (e.g., "north", "south", "east", "west", or edge index)
            
        Returns:
            Edge ID or None if not found
        """
        # For rectangular spaces, edges are ordered: bottom, right, top, left
        # Map wall names to edge indices
        wall_mapping = {
            "south": 0,  # bottom edge
            "bottom": 0,
            "east": 1,   # right edge
            "right": 1,
            "north": 2,  # top edge
            "top": 2,
            "west": 3,   # left edge
            "left": 3
        }
        
        wall_lower = wall.lower()
        if wall_lower in wall_mapping:
            edge_index = wall_mapping[wall_lower]
            if edge_index < len(geometry.edges):
                return geometry.edges[edge_index].id
        
        # Try parsing as integer index
        try:
            edge_index = int(wall)
            if 0 <= edge_index < len(geometry.edges):
                return geometry.edges[edge_index].id
        except ValueError:
            pass
        
        return None
    
    def create_window_definition(self, width: float, height: float, 
                                name: str = "Window",
                                window_type: str = "Fixed",
                                sill_height: float = 0.9) -> WindowDefinition:
        """Create a window definition.
        
        Args:
            width: Window width in meters
            height: Window height in meters
            name: Window name
            window_type: Type of window
            sill_height: Height of window sill from floor in meters
            
        Returns:
            WindowDefinition object
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Window dimensions must be positive: width={width}, height={height}")
        
        if sill_height < 0:
            raise ValueError(f"Sill height must be non-negative: {sill_height}")
        
        # Validate dimensions are reasonable
        if not self.validator.validate_element_dimensions_reasonable("window", width, height):
            raise ValueError(f"Window dimensions are unreasonable: {width:.2f}m x {height:.2f}m")
        
        return WindowDefinition(
            id=self._generate_id("window_def"),
            name=name,
            height=height,
            width=width,
            window_type=window_type,
            sill_height=sill_height
        )
    
    def create_door_definition(self, width: float, height: float,
                              name: str = "Door",
                              door_type: str = "Door") -> DoorDefinition:
        """Create a door definition.
        
        Args:
            width: Door width in meters
            height: Door height in meters
            name: Door name
            door_type: Type of door
            
        Returns:
            DoorDefinition object
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Door dimensions must be positive: width={width}, height={height}")
        
        # Validate dimensions are reasonable
        if not self.validator.validate_element_dimensions_reasonable("door", width, height):
            raise ValueError(f"Door dimensions are unreasonable: {width:.2f}m x {height:.2f}m")
        
        return DoorDefinition(
            id=self._generate_id("door_def"),
            name=name,
            height=height,
            width=width,
            door_type=door_type
        )
    
    def create_window_instance(self, window_definition_id: str, edge_id: str,
                              alpha: float, name: str = "Window") -> WindowInstance:
        """Create a window instance on an edge.
        
        Args:
            window_definition_id: ID of the window definition
            edge_id: ID of the edge to place window on
            alpha: Position along edge (0-1)
            name: Window instance name
            
        Returns:
            WindowInstance object
        """
        if not (0 <= alpha <= 1):
            raise ValueError(f"Alpha must be between 0 and 1: {alpha}")
        
        return WindowInstance(
            id=self._generate_id("window"),
            name=name,
            window_definition_id=window_definition_id,
            edge_id=edge_id,
            alpha=alpha
        )
    
    def create_door_instance(self, door_definition_id: str, edge_id: str,
                            alpha: float, name: str = "Door") -> DoorInstance:
        """Create a door instance on an edge.
        
        Args:
            door_definition_id: ID of the door definition
            edge_id: ID of the edge to place door on
            alpha: Position along edge (0-1)
            name: Door instance name
            
        Returns:
            DoorInstance object
        """
        if not (0 <= alpha <= 1):
            raise ValueError(f"Alpha must be between 0 and 1: {alpha}")
        
        return DoorInstance(
            id=self._generate_id("door"),
            name=name,
            door_definition_id=door_definition_id,
            edge_id=edge_id,
            alpha=alpha
        )