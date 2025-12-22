"""Schema validator for Floorspace JSON."""

import json
import math
from typing import Dict, Any, List, Optional, Tuple
from pydantic import ValidationError
from ..models.floorspace import (
    FloorspaceModelPydantic,
    StoryModel,
    GeometryModel,
    VertexModel,
    EdgeModel,
    FaceModel,
    SpaceModel,
    WindowDefinitionModel,
    DoorDefinitionModel,
    WindowInstanceModel,
    DoorInstanceModel,
)


class ValidationResult:
    """Result of validation operation."""
    
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        """Initialize validation result.
        
        Args:
            is_valid: Whether validation passed
            errors: List of error messages (if any)
        """
        self.is_valid = is_valid
        self.errors = errors or []
    
    def __bool__(self) -> bool:
        """Allow boolean evaluation of validation result."""
        return self.is_valid
    
    def __str__(self) -> str:
        """String representation of validation result."""
        if self.is_valid:
            return "Validation passed"
        return f"Validation failed: {'; '.join(self.errors)}"


class SchemaValidator:
    """Validates Floorspace JSON against schema and constraints."""

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []

    def validate_coordinates(self, value: float, field_name: str) -> bool:
        """Validate that coordinate values are valid numbers.
        
        Args:
            value: Coordinate value to validate
            field_name: Name of the field for error messages
            
        Returns:
            True if valid, False otherwise
        """
        if math.isnan(value):
            self.errors.append(f"{field_name} cannot be NaN")
            return False
        if math.isinf(value):
            self.errors.append(f"{field_name} cannot be infinite")
            return False
        return True

    def validate_unique_ids(self, items: List[Dict[str, Any]], item_type: str) -> bool:
        """Validate that all IDs in a list are unique.
        
        Args:
            items: List of items with 'id' field
            item_type: Type of items for error messages
            
        Returns:
            True if all IDs are unique, False otherwise
        """
        ids = [item.get('id') for item in items if 'id' in item]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            self.errors.append(f"Duplicate {item_type} IDs found: {set(duplicates)}")
            return False
        return True

    def validate_references(self, data: Dict[str, Any]) -> bool:
        """Validate that all ID references are valid.
        
        Args:
            data: Complete Floorspace JSON data
            
        Returns:
            True if all references are valid, False otherwise
        """
        valid = True
        
        for story in data.get('stories', []):
            geometry = story.get('geometry', {})
            
            # Collect all valid IDs
            vertex_ids = {v['id'] for v in geometry.get('vertices', [])}
            edge_ids = {e['id'] for e in geometry.get('edges', [])}
            face_ids = {f['id'] for f in geometry.get('faces', [])}
            window_def_ids = {w['id'] for w in data.get('window_definitions', [])}
            door_def_ids = {d['id'] for d in data.get('door_definitions', [])}
            
            # Validate vertex edge references
            for vertex in geometry.get('vertices', []):
                for edge_id in vertex.get('edge_ids', []):
                    if edge_id not in edge_ids:
                        self.errors.append(f"Vertex {vertex['id']} references non-existent edge {edge_id}")
                        valid = False
            
            # Validate edge vertex and face references
            for edge in geometry.get('edges', []):
                for vertex_id in edge.get('vertex_ids', []):
                    if vertex_id not in vertex_ids:
                        self.errors.append(f"Edge {edge['id']} references non-existent vertex {vertex_id}")
                        valid = False
                for face_id in edge.get('face_ids', []):
                    if face_id not in face_ids:
                        self.errors.append(f"Edge {edge['id']} references non-existent face {face_id}")
                        valid = False
            
            # Validate face edge references
            for face in geometry.get('faces', []):
                for edge_id in face.get('edge_ids', []):
                    if edge_id not in edge_ids:
                        self.errors.append(f"Face {face['id']} references non-existent edge {edge_id}")
                        valid = False
            
            # Validate space face references
            for space in story.get('spaces', []):
                face_id = space.get('face_id')
                if face_id and face_id not in face_ids:
                    self.errors.append(f"Space {space['id']} references non-existent face {face_id}")
                    valid = False
            
            # Validate window instance references
            for window in story.get('windows', []):
                window_def_id = window.get('window_definition_id')
                if window_def_id and window_def_id not in window_def_ids:
                    self.errors.append(f"Window {window['id']} references non-existent window definition {window_def_id}")
                    valid = False
                edge_id = window.get('edge_id')
                if edge_id and edge_id not in edge_ids:
                    self.errors.append(f"Window {window['id']} references non-existent edge {edge_id}")
                    valid = False
            
            # Validate door instance references
            for door in story.get('doors', []):
                door_def_id = door.get('door_definition_id')
                if door_def_id and door_def_id not in door_def_ids:
                    self.errors.append(f"Door {door['id']} references non-existent door definition {door_def_id}")
                    valid = False
                edge_id = door.get('edge_id')
                if edge_id and edge_id not in edge_ids:
                    self.errors.append(f"Door {door['id']} references non-existent edge {edge_id}")
                    valid = False
        
        return valid

    def validate_version_compatibility(self, version: str) -> bool:
        """Validate version string format and compatibility.
        
        Args:
            version: Version string (e.g., "1.4.3")
            
        Returns:
            True if version is valid, False otherwise
        """
        if not version:
            self.errors.append("Version string cannot be empty")
            return False
        
        parts = version.split('.')
        if len(parts) != 3:
            self.errors.append(f"Version must be in format X.Y.Z, got: {version}")
            return False
        
        try:
            for part in parts:
                int(part)
        except ValueError:
            self.errors.append(f"Version parts must be integers, got: {version}")
            return False
        
        return True

    def validate_json_structure(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate complete JSON structure using Pydantic models.
        
        Args:
            data: Dictionary representation of Floorspace JSON
            
        Returns:
            ValidationResult indicating success or failure with errors
        """
        self.errors = []
        
        try:
            # Validate using Pydantic model
            FloorspaceModelPydantic(**data)
            
            # Additional validations
            self.validate_unique_ids(data.get('window_definitions', []), 'window_definition')
            self.validate_unique_ids(data.get('door_definitions', []), 'door_definition')
            
            for story in data.get('stories', []):
                geometry = story.get('geometry', {})
                self.validate_unique_ids(geometry.get('vertices', []), 'vertex')
                self.validate_unique_ids(geometry.get('edges', []), 'edge')
                self.validate_unique_ids(geometry.get('faces', []), 'face')
                self.validate_unique_ids(story.get('spaces', []), 'space')
                self.validate_unique_ids(story.get('windows', []), 'window')
                self.validate_unique_ids(story.get('doors', []), 'door')
            
            # Validate references
            self.validate_references(data)
            
            # Validate version
            self.validate_version_compatibility(data.get('version', ''))
            
            if self.errors:
                return ValidationResult(False, self.errors)
            
            return ValidationResult(True)
            
        except ValidationError as e:
            # Extract error messages from Pydantic validation
            for error in e.errors():
                loc = ' -> '.join(str(l) for l in error['loc'])
                msg = error['msg']
                self.errors.append(f"{loc}: {msg}")
            
            return ValidationResult(False, self.errors)
        except Exception as e:
            self.errors.append(f"Unexpected validation error: {str(e)}")
            return ValidationResult(False, self.errors)

    def validate_json_string(self, json_string: str) -> ValidationResult:
        """Validate JSON string.
        
        Args:
            json_string: JSON string to validate
            
        Returns:
            ValidationResult indicating success or failure with errors
        """
        self.errors = []
        
        try:
            data = json.loads(json_string)
            return self.validate_json_structure(data)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {str(e)}")
            return ValidationResult(False, self.errors)

    def format_json(self, data: Dict[str, Any], indent: int = 2) -> str:
        """Format JSON data with proper indentation.
        
        Args:
            data: Dictionary to format
            indent: Number of spaces for indentation
            
        Returns:
            Formatted JSON string
        """
        return json.dumps(data, indent=indent, ensure_ascii=False)