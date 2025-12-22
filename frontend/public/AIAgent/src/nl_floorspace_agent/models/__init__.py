"""Data models for the Natural Language to Floorspace JSON Agent."""

from .core import (
    Dimensions,
    ElementSpec,
    BuildingElement,
    SpaceRequirement,
    ConversationState,
    Question,
    SessionContext,
    BuildingContext,
    Units,
    ElementType,
    ConversationStep,
)

from .floorspace import (
    Vertex,
    Edge,
    Face,
    Geometry,
    Space,
    WindowDefinition,
    DoorDefinition,
    WindowInstance,
    DoorInstance,
    Story,
    FloorspaceModel,
)

__all__ = [
    # Core models
    "Dimensions",
    "ElementSpec", 
    "BuildingElement",
    "SpaceRequirement",
    "ConversationState",
    "Question",
    "SessionContext",
    "BuildingContext",
    "Units",
    "ElementType",
    "ConversationStep",
    # Floorspace models
    "Vertex",
    "Edge",
    "Face",
    "Geometry",
    "Space",
    "WindowDefinition",
    "DoorDefinition",
    "WindowInstance",
    "DoorInstance",
    "Story",
    "FloorspaceModel",
]