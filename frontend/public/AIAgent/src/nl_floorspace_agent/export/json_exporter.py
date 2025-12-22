"""JSON exporter for Floorspace JSON format."""

import json
import math
from typing import Dict, Any, Optional, Union
from decimal import Decimal, ROUND_HALF_UP
from ..models.floorspace import (
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
from .schema_validator import SchemaValidator, ValidationResult


class FloorspaceJSONExporter:
    """Exports FloorspaceModel to JSON format with validation and formatting."""

    def __init__(self, coordinate_precision: int = 6):
        """Initialize the exporter with ID counter and formatting options.
        
        Args:
            coordinate_precision: Number of decimal places for coordinate values
        """
        self._id_counter = 1
        self.coordinate_precision = coordinate_precision
        self.validator = SchemaValidator()

    def generate_id(self) -> str:
        """Generate a unique ID for geometric elements.
        
        Returns:
            str: Unique ID as string
        """
        id_str = str(self._id_counter)
        self._id_counter += 1
        return id_str

    def reset_id_counter(self) -> None:
        """Reset the ID counter to 1."""
        self._id_counter = 1

    def format_coordinate(self, value: float) -> float:
        """Format coordinate value with proper precision.
        
        Args:
            value: Coordinate value to format
            
        Returns:
            Formatted coordinate value
            
        Raises:
            ValueError: If coordinate is NaN or infinite
        """
        if math.isnan(value):
            raise ValueError("Coordinate value cannot be NaN")
        if math.isinf(value):
            raise ValueError("Coordinate value cannot be infinite")
        
        # Round to specified precision using Decimal for accurate rounding
        decimal_value = Decimal(str(value))
        rounded = decimal_value.quantize(
            Decimal('0.' + '0' * self.coordinate_precision),
            rounding=ROUND_HALF_UP
        )
        return float(rounded)

    def validate_version_compatibility(self, version: str) -> bool:
        """Validate version string format and compatibility.
        
        Args:
            version: Version string (e.g., "1.4.3")
            
        Returns:
            True if version is compatible, False otherwise
        """
        if not version:
            return False
        
        parts = version.split('.')
        if len(parts) != 3:
            return False
        
        try:
            major, minor, patch = [int(part) for part in parts]
            # Support versions 1.4.x and later
            return major >= 1 and (major > 1 or minor >= 4)
        except ValueError:
            return False

    def build_application_config(self) -> Dict[str, Any]:
        """Build default application configuration.
        
        Returns:
            Dict containing application state and UI configuration
        """
        return {
            "currentSelections": {
                "story": None,
                "story_id": "1",
                "subselection_ids": {},
                "component_id": None,
                "component_definition_id": None,
                "component_instance_id": None,
                "space_property_id": None,
                "tool": "Rectangle",
                "mode": "spaces",
                "snapMode": "grid-strict",
                "modeTab": "spaces",
                "subselectionType": None
            },
            "modes": [
                "spaces",
                "shading",
                "building_units",
                "thermal_zones",
                "pitched_roofs",
                "space_types",
                "images"
            ],
            "tools": [
                "Pan",
                "Drag",
                "Rectangle",
                "Polygon",
                "Eraser",
                "Select",
                "Map",
                "Fill",
                "Place Component",
                "Image",
                "Apply Property"
            ],
            "scale": {
                "x": {"pixels": 1192, "rwuRange": [-254.7008547008547, 254.7008547008547]},
                "y": {"pixels": 702, "rwuRange": [-150, 150]}
            }
        }

    def build_project_config(self, units: str = "ip") -> Dict[str, Any]:
        """Build default project configuration.
        
        Args:
            units: Unit system ("ip" for imperial, "si" for metric)
            
        Returns:
            Dict containing project settings
        """
        return {
            "config": {
                "units": units,
                "unitsEditable": True,
                "language": "EN-US"
            },
            "north_axis": 0,
            "ground": {
                "floor_offset": 0,
                "azimuth_angle": 0,
                "tilt_slope": 0
            },
            "grid": {
                "visible": True,
                "spacing": 5
            },
            "view": {
                "min_x": -50,
                "min_y": -50,
                "max_x": 50,
                "max_y": 50
            },
            "map": {
                "initialized": False,
                "enabled": False,
                "visible": True,
                "latitude": 39.7653,
                "longitude": -104.9863,
                "zoom": 4.5,
                "rotation": 0,
                "elevation": 0
            },
            "previous_story": {
                "visible": True
            },
            "show_import_export": True,
            "preview3D": {
                "enabled": True
            }
        }

    def vertex_to_dict(self, vertex: Vertex) -> Dict[str, Any]:
        """Convert Vertex to dictionary with formatted coordinates.
        
        Args:
            vertex: Vertex object
            
        Returns:
            Dict representation of vertex
        """
        return {
            "id": vertex.id,
            "x": self.format_coordinate(vertex.x),
            "y": self.format_coordinate(vertex.y),
            "edge_ids": vertex.edge_ids
        }

    def edge_to_dict(self, edge: Edge) -> Dict[str, Any]:
        """Convert Edge to dictionary.
        
        Args:
            edge: Edge object
            
        Returns:
            Dict representation of edge
        """
        return {
            "id": edge.id,
            "vertex_ids": edge.vertex_ids,
            "face_ids": edge.face_ids
        }

    def face_to_dict(self, face: Face) -> Dict[str, Any]:
        """Convert Face to dictionary.
        
        Args:
            face: Face object
            
        Returns:
            Dict representation of face
        """
        return {
            "id": face.id,
            "edge_ids": face.edge_ids,
            "edge_order": face.edge_order
        }

    def geometry_to_dict(self, geometry: Geometry) -> Dict[str, Any]:
        """Convert Geometry to dictionary.
        
        Args:
            geometry: Geometry object
            
        Returns:
            Dict representation of geometry
        """
        return {
            "id": geometry.id,
            "vertices": [self.vertex_to_dict(v) for v in geometry.vertices],
            "edges": [self.edge_to_dict(e) for e in geometry.edges],
            "faces": [self.face_to_dict(f) for f in geometry.faces]
        }

    def space_to_dict(self, space: Space) -> Dict[str, Any]:
        """Convert Space to dictionary.
        
        Args:
            space: Space object
            
        Returns:
            Dict representation of space
        """
        return {
            "id": space.id,
            "handle": None,
            "name": space.name,
            "face_id": space.face_id,
            "building_unit_id": None,
            "thermal_zone_id": None,
            "space_type_id": None,
            "construction_set_id": None,
            "pitched_roof_id": None,
            "daylighting_controls": [],
            "below_floor_plenum_height": None,
            "floor_to_ceiling_height": None,
            "above_ceiling_plenum_height": None,
            "floor_offset": None,
            "open_to_below": None,
            "building_type_id": None,
            "template": None,
            "color": space.color,
            "type": space.type
        }

    def window_definition_to_dict(self, window_def: WindowDefinition) -> Dict[str, Any]:
        """Convert WindowDefinition to dictionary with formatted dimensions.
        
        Args:
            window_def: WindowDefinition object
            
        Returns:
            Dict representation of window definition
        """
        return {
            "id": window_def.id,
            "name": window_def.name,
            "window_definition_mode": "Single Window",
            "wwr": None,
            "sill_height": self.format_coordinate(window_def.sill_height),
            "window_spacing": None,
            "height": self.format_coordinate(window_def.height),
            "width": self.format_coordinate(window_def.width),
            "window_type": window_def.window_type,
            "overhang_projection_factor": None,
            "fin_projection_factor": None,
            "texture": "circles-5"
        }

    def door_definition_to_dict(self, door_def: DoorDefinition) -> Dict[str, Any]:
        """Convert DoorDefinition to dictionary with formatted dimensions.
        
        Args:
            door_def: DoorDefinition object
            
        Returns:
            Dict representation of door definition
        """
        return {
            "id": door_def.id,
            "name": door_def.name,
            "height": self.format_coordinate(door_def.height),
            "width": self.format_coordinate(door_def.width),
            "door_type": door_def.door_type,
            "texture": "circles-5"
        }

    def window_instance_to_dict(self, window: WindowInstance) -> Dict[str, Any]:
        """Convert WindowInstance to dictionary with formatted alpha.
        
        Args:
            window: WindowInstance object
            
        Returns:
            Dict representation of window instance
        """
        return {
            "window_definition_id": window.window_definition_id,
            "edge_id": window.edge_id,
            "alpha": self.format_coordinate(window.alpha),
            "id": window.id,
            "name": window.name
        }

    def door_instance_to_dict(self, door: DoorInstance) -> Dict[str, Any]:
        """Convert DoorInstance to dictionary with formatted alpha.
        
        Args:
            door: DoorInstance object
            
        Returns:
            Dict representation of door instance
        """
        return {
            "door_definition_id": door.door_definition_id,
            "edge_id": door.edge_id,
            "alpha": self.format_coordinate(door.alpha),
            "id": door.id,
            "name": door.name
        }

    def story_to_dict(self, story: Story) -> Dict[str, Any]:
        """Convert Story to dictionary with formatted height.
        
        Args:
            story: Story object
            
        Returns:
            Dict representation of story
        """
        return {
            "id": story.id,
            "handle": None,
            "name": story.name,
            "image_visible": True,
            "below_floor_plenum_height": 0,
            "floor_to_ceiling_height": self.format_coordinate(story.floor_to_ceiling_height),
            "above_ceiling_plenum_height": 0,
            "multiplier": story.multiplier,
            "color": story.color,
            "geometry": self.geometry_to_dict(story.geometry),
            "images": [],
            "spaces": [self.space_to_dict(s) for s in story.spaces],
            "shading": [],
            "windows": [self.window_instance_to_dict(w) for w in story.windows],
            "doors": [self.door_instance_to_dict(d) for d in story.doors]
        }

    def export_to_dict(self, model: FloorspaceModel) -> Dict[str, Any]:
        """Export FloorspaceModel to dictionary.
        
        Args:
            model: FloorspaceModel to export
            
        Returns:
            Dict representation ready for JSON serialization
        """
        # Use provided application config or build default
        application = model.application if model.application else self.build_application_config()
        
        # Use provided project config or build default
        project = model.project if model.project else self.build_project_config()
        
        return {
            "application": application,
            "project": project,
            "stories": [self.story_to_dict(s) for s in model.stories],
            "building_units": model.building_units,
            "thermal_zones": model.thermal_zones,
            "space_types": model.space_types,
            "construction_sets": model.construction_sets,
            "window_definitions": [self.window_definition_to_dict(w) for w in model.window_definitions],
            "daylighting_control_definitions": [],
            "pitched_roofs": [],
            "door_definitions": [self.door_definition_to_dict(d) for d in model.door_definitions],
            "version": model.version
        }

    def validate_and_export_to_dict(self, model: FloorspaceModel) -> tuple[Dict[str, Any], ValidationResult]:
        """Export FloorspaceModel to dictionary with validation.
        
        Args:
            model: FloorspaceModel to export
            
        Returns:
            Tuple of (dict representation, validation result)
        """
        # Validate version compatibility first
        if not self.validate_version_compatibility(model.version):
            return {}, ValidationResult(False, [f"Unsupported version: {model.version}"])
        
        # Export to dictionary
        try:
            data = self.export_to_dict(model)
        except (ValueError, TypeError) as e:
            return {}, ValidationResult(False, [f"Export error: {str(e)}"])
        
        # Validate the exported data
        validation_result = self.validator.validate_json_structure(data)
        
        return data, validation_result

    def export_to_json(self, model: FloorspaceModel, indent: Optional[int] = None, 
                      validate: bool = True) -> Union[str, tuple[str, ValidationResult]]:
        """Export FloorspaceModel to JSON string with optional validation.
        
        Args:
            model: FloorspaceModel to export
            indent: Number of spaces for indentation (None for compact)
            validate: Whether to validate the output
            
        Returns:
            JSON string if validate=False, or tuple of (JSON string, ValidationResult) if validate=True
        """
        if validate:
            data, validation_result = self.validate_and_export_to_dict(model)
            if not validation_result.is_valid:
                return "", validation_result
            json_str = self.format_json(data, indent)
            return json_str, validation_result
        else:
            data = self.export_to_dict(model)
            return self.format_json(data, indent)

    def format_json(self, data: Dict[str, Any], indent: Optional[int] = None) -> str:
        """Format JSON data with proper indentation and formatting.
        
        Args:
            data: Dictionary to format
            indent: Number of spaces for indentation (None for compact)
            
        Returns:
            Formatted JSON string
        """
        return json.dumps(
            data, 
            indent=indent, 
            ensure_ascii=False,
            separators=(',', ': ') if indent else (',', ':'),
            sort_keys=False
        )

    def validate_json_string(self, json_string: str) -> ValidationResult:
        """Validate a JSON string against Floorspace schema.
        
        Args:
            json_string: JSON string to validate
            
        Returns:
            ValidationResult indicating success or failure with errors
        """
        return self.validator.validate_json_string(json_string)