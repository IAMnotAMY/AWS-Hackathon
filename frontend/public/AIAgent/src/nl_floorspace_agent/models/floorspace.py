"""Floorspace JSON data models."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import math


@dataclass
class Vertex:
    """A point in 2D space."""
    id: str
    x: float
    y: float
    edge_ids: List[str] = field(default_factory=list)


@dataclass
class Edge:
    """A line segment connecting two vertices."""
    id: str
    vertex_ids: List[str]  # exactly 2 elements
    face_ids: List[str] = field(default_factory=list)


@dataclass
class Face:
    """A closed polygon defined by edges."""
    id: str
    edge_ids: List[str]
    edge_order: List[int]  # 1 or -1 for edge direction


@dataclass
class Geometry:
    """Collection of geometric elements."""
    id: str
    vertices: List[Vertex] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    faces: List[Face] = field(default_factory=list)


@dataclass
class Space:
    """A room or space in the building."""
    id: str
    name: str
    face_id: str
    color: str
    type: str = "space"


@dataclass
class WindowDefinition:
    """Template for window specifications."""
    id: str
    name: str
    height: float
    width: float
    window_type: str
    sill_height: float


@dataclass
class DoorDefinition:
    """Template for door specifications."""
    id: str
    name: str
    height: float
    width: float
    door_type: str


@dataclass
class WindowInstance:
    """A window placed on an edge."""
    id: str
    name: str
    window_definition_id: str
    edge_id: str
    alpha: float  # position along edge (0-1)


@dataclass
class DoorInstance:
    """A door placed on an edge."""
    id: str
    name: str
    door_definition_id: str
    edge_id: str
    alpha: float  # position along edge (0-1)


@dataclass
class Story:
    """A floor/story in the building."""
    id: str
    name: str
    geometry: Geometry
    spaces: List[Space] = field(default_factory=list)
    windows: List[WindowInstance] = field(default_factory=list)
    doors: List[DoorInstance] = field(default_factory=list)
    floor_to_ceiling_height: float = 3.0
    multiplier: int = 1
    color: str = "#FFFFFF"


@dataclass
class FloorspaceModel:
    """Complete Floorspace JSON model."""
    application: Dict[str, Any] = field(default_factory=dict)
    project: Dict[str, Any] = field(default_factory=dict)
    stories: List[Story] = field(default_factory=list)
    window_definitions: List[WindowDefinition] = field(default_factory=list)
    door_definitions: List[DoorDefinition] = field(default_factory=list)
    building_units: List[Dict[str, Any]] = field(default_factory=list)
    thermal_zones: List[Dict[str, Any]] = field(default_factory=list)
    space_types: List[Dict[str, Any]] = field(default_factory=list)
    construction_sets: List[Dict[str, Any]] = field(default_factory=list)
    version: str = "1.4.3"


# Pydantic models for validation and serialization
class VertexModel(BaseModel):
    """Pydantic model for Vertex validation."""
    id: str = Field(..., description="Unique identifier for the vertex")
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    edge_ids: List[str] = Field(default_factory=list, description="List of edge IDs connected to this vertex")

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Vertex ID cannot be empty')
        return v

    @field_validator('x', 'y')
    @classmethod
    def validate_coordinates(cls, v):
        if math.isnan(v) or math.isinf(v):
            raise ValueError('Coordinates cannot be NaN or infinite')
        return v


class EdgeModel(BaseModel):
    """Pydantic model for Edge validation."""
    id: str = Field(..., description="Unique identifier for the edge")
    vertex_ids: List[str] = Field(..., description="Exactly 2 vertex IDs")
    face_ids: List[str] = Field(default_factory=list, description="List of face IDs that use this edge")

    @field_validator('vertex_ids')
    @classmethod
    def validate_vertex_ids(cls, v):
        if len(v) != 2:
            raise ValueError('Edge must connect exactly 2 vertices')
        if v[0] == v[1]:
            raise ValueError('Edge cannot connect a vertex to itself')
        return v

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Edge ID cannot be empty')
        return v


class FaceModel(BaseModel):
    """Pydantic model for Face validation."""
    id: str = Field(..., description="Unique identifier for the face")
    edge_ids: List[str] = Field(..., description="List of edge IDs forming the face")
    edge_order: List[int] = Field(..., description="Edge direction (1 or -1)")

    @field_validator('edge_order')
    @classmethod
    def validate_edge_order(cls, v, info):
        if 'edge_ids' in info.data and len(v) != len(info.data['edge_ids']):
            raise ValueError('edge_order must have same length as edge_ids')
        for order in v:
            if order not in [1, -1]:
                raise ValueError('edge_order values must be 1 or -1')
        return v

    @field_validator('edge_ids')
    @classmethod
    def validate_edge_ids(cls, v):
        if len(v) < 3:
            raise ValueError('Face must have at least 3 edges')
        return v

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Face ID cannot be empty')
        return v


class GeometryModel(BaseModel):
    """Pydantic model for Geometry validation."""
    id: str = Field(..., description="Unique identifier for the geometry")
    vertices: List[VertexModel] = Field(default_factory=list, description="List of vertices")
    edges: List[EdgeModel] = Field(default_factory=list, description="List of edges")
    faces: List[FaceModel] = Field(default_factory=list, description="List of faces")

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Geometry ID cannot be empty')
        return v


class SpaceModel(BaseModel):
    """Pydantic model for Space validation."""
    id: str = Field(..., description="Unique identifier for the space")
    name: str = Field(..., description="Human-readable name for the space")
    face_id: str = Field(..., description="ID of the face this space occupies")
    color: str = Field(..., description="Color for visualization")
    type: str = Field(default="space", description="Type of space")

    @field_validator('id', 'name', 'face_id')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v

    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        if not v.startswith('#') or len(v) != 7:
            raise ValueError('Color must be in hex format (#RRGGBB)')
        return v


class WindowDefinitionModel(BaseModel):
    """Pydantic model for WindowDefinition validation."""
    id: str = Field(..., description="Unique identifier for the window definition")
    name: str = Field(..., description="Human-readable name")
    height: float = Field(..., gt=0, description="Window height (must be positive)")
    width: float = Field(..., gt=0, description="Window width (must be positive)")
    window_type: str = Field(..., description="Type of window")
    sill_height: float = Field(..., ge=0, description="Height of window sill from floor")

    @field_validator('id', 'name', 'window_type')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v


class DoorDefinitionModel(BaseModel):
    """Pydantic model for DoorDefinition validation."""
    id: str = Field(..., description="Unique identifier for the door definition")
    name: str = Field(..., description="Human-readable name")
    height: float = Field(..., gt=0, description="Door height (must be positive)")
    width: float = Field(..., gt=0, description="Door width (must be positive)")
    door_type: str = Field(..., description="Type of door")

    @field_validator('id', 'name', 'door_type')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v


class WindowInstanceModel(BaseModel):
    """Pydantic model for WindowInstance validation."""
    id: str = Field(..., description="Unique identifier for the window instance")
    name: str = Field(..., description="Human-readable name")
    window_definition_id: str = Field(..., description="ID of the window definition")
    edge_id: str = Field(..., description="ID of the edge where window is placed")
    alpha: float = Field(..., ge=0, le=1, description="Position along edge (0-1)")

    @field_validator('id', 'name', 'window_definition_id', 'edge_id')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v


class DoorInstanceModel(BaseModel):
    """Pydantic model for DoorInstance validation."""
    id: str = Field(..., description="Unique identifier for the door instance")
    name: str = Field(..., description="Human-readable name")
    door_definition_id: str = Field(..., description="ID of the door definition")
    edge_id: str = Field(..., description="ID of the edge where door is placed")
    alpha: float = Field(..., ge=0, le=1, description="Position along edge (0-1)")

    @field_validator('id', 'name', 'door_definition_id', 'edge_id')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v


class StoryModel(BaseModel):
    """Pydantic model for Story validation."""
    id: str = Field(..., description="Unique identifier for the story")
    name: str = Field(..., description="Human-readable name")
    geometry: GeometryModel = Field(..., description="Geometric elements of the story")
    spaces: List[SpaceModel] = Field(default_factory=list, description="Spaces in this story")
    windows: List[WindowInstanceModel] = Field(default_factory=list, description="Window instances")
    doors: List[DoorInstanceModel] = Field(default_factory=list, description="Door instances")
    floor_to_ceiling_height: float = Field(default=3.0, gt=0, description="Height from floor to ceiling")
    multiplier: int = Field(default=1, ge=1, description="Number of identical floors")
    color: str = Field(default="#FFFFFF", description="Color for visualization")

    @field_validator('id', 'name')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v

    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        if not v.startswith('#') or len(v) != 7:
            raise ValueError('Color must be in hex format (#RRGGBB)')
        return v


class FloorspaceModelPydantic(BaseModel):
    """Pydantic model for complete Floorspace JSON validation."""
    model_config = ConfigDict(validate_assignment=True, extra="allow")
    
    application: Dict[str, Any] = Field(default_factory=dict, description="Application state")
    project: Dict[str, Any] = Field(default_factory=dict, description="Project configuration")
    stories: List[StoryModel] = Field(default_factory=list, description="Building stories")
    window_definitions: List[WindowDefinitionModel] = Field(default_factory=list, description="Window templates")
    door_definitions: List[DoorDefinitionModel] = Field(default_factory=list, description="Door templates")
    building_units: List[Dict[str, Any]] = Field(default_factory=list, description="Building units")
    thermal_zones: List[Dict[str, Any]] = Field(default_factory=list, description="Thermal zones")
    space_types: List[Dict[str, Any]] = Field(default_factory=list, description="Space type definitions")
    construction_sets: List[Dict[str, Any]] = Field(default_factory=list, description="Construction sets")
    version: str = Field(default="1.4.3", description="Floorspace JSON version")
    
    # Optional fields that may be present in Floorspace JSON
    daylighting_control_definitions: List[Dict[str, Any]] = Field(default_factory=list, description="Daylighting control definitions")
    pitched_roofs: List[Dict[str, Any]] = Field(default_factory=list, description="Pitched roof definitions")

    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        if not v or not v.strip():
            raise ValueError('Version cannot be empty')
        return v