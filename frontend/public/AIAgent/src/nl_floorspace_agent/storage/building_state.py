"""Building state management for storing and retrieving building models."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from pathlib import Path
from copy import deepcopy

from ..models.floorspace import FloorspaceModel, Story, Space, WindowInstance, DoorInstance, WindowDefinition, DoorDefinition, Geometry
from ..models.core import BuildingContext, ConversationState

logger = logging.getLogger(__name__)


class BuildingState:
    """Manages building model storage and retrieval with conversation history."""
    
    def __init__(self, storage_dir: Optional[str] = None, enable_persistence: bool = False):
        """Initialize building state storage.
        
        Args:
            storage_dir: Directory for persistent storage (optional)
            enable_persistence: Whether to enable file-based persistence
        """
        self._buildings: Dict[str, FloorspaceModel] = {}
        self._building_contexts: Dict[str, BuildingContext] = {}
        self._conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self.enable_persistence = enable_persistence
        
        if enable_persistence and storage_dir:
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.storage_dir = None
    
    async def save_building_model(self, building_id: str, model: FloorspaceModel, 
                                context: Optional[BuildingContext] = None) -> None:
        """Save a building model with optional context.
        
        Args:
            building_id: Unique identifier for the building
            model: FloorspaceModel to save
            context: Optional BuildingContext for metadata
        """
        async with self._lock:
            # Deep copy to prevent external modifications
            self._buildings[building_id] = deepcopy(model)
            
            if context:
                context.update_modified_time()
                self._building_contexts[building_id] = deepcopy(context)
            elif building_id not in self._building_contexts:
                # Create default context if none provided
                self._building_contexts[building_id] = BuildingContext(
                    building_id=building_id,
                    total_spaces=len(model.stories[0].spaces) if model.stories else 0,
                    total_windows=sum(len(story.windows) for story in model.stories),
                    total_doors=sum(len(story.doors) for story in model.stories)
                )
            
            if self.enable_persistence and self.storage_dir:
                await self._persist_building(building_id, model, self._building_contexts[building_id])
            
            logger.debug(f"Saved building model: {building_id}")
    
    async def get_building_model(self, building_id: str) -> Optional[FloorspaceModel]:
        """Get a building model by ID.
        
        Args:
            building_id: Building identifier
            
        Returns:
            FloorspaceModel if found, None otherwise
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            
            if model is None and self.enable_persistence and self.storage_dir:
                # Try to load from persistent storage
                model = await self._load_building(building_id)
                if model:
                    self._buildings[building_id] = model
            
            if model:
                logger.debug(f"Retrieved building model: {building_id}")
                return deepcopy(model)  # Return copy to prevent external modifications
            
            return None
    
    async def get_building_context(self, building_id: str) -> Optional[BuildingContext]:
        """Get building context by ID.
        
        Args:
            building_id: Building identifier
            
        Returns:
            BuildingContext if found, None otherwise
        """
        async with self._lock:
            context = self._building_contexts.get(building_id)
            
            if context:
                return deepcopy(context)
            
            return None
    
    async def update_building_context(self, building_id: str, context: BuildingContext) -> bool:
        """Update building context.
        
        Args:
            building_id: Building identifier
            context: Updated BuildingContext
            
        Returns:
            True if updated, False if building not found
        """
        async with self._lock:
            if building_id in self._buildings:
                context.update_modified_time()
                self._building_contexts[building_id] = deepcopy(context)
                
                if self.enable_persistence and self.storage_dir:
                    model = self._buildings[building_id]
                    await self._persist_building(building_id, model, context)
                
                logger.debug(f"Updated building context: {building_id}")
                return True
            
            return False
    
    async def delete_building(self, building_id: str) -> bool:
        """Delete a building model and its context.
        
        Args:
            building_id: Building identifier
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            model = self._buildings.pop(building_id, None)
            context = self._building_contexts.pop(building_id, None)
            history = self._conversation_history.pop(building_id, None)
            
            if self.enable_persistence and self.storage_dir:
                await self._delete_persisted_building(building_id)
            
            if model:
                logger.debug(f"Deleted building: {building_id}")
                return True
            
            return False
    
    async def list_buildings(self) -> List[Dict[str, Any]]:
        """List all buildings with their contexts.
        
        Returns:
            List of building summaries
        """
        async with self._lock:
            summaries = []
            
            for building_id, model in self._buildings.items():
                context = self._building_contexts.get(building_id)
                summary = {
                    "building_id": building_id,
                    "story_count": len(model.stories),
                    "total_spaces": sum(len(story.spaces) for story in model.stories),
                    "total_windows": sum(len(story.windows) for story in model.stories),
                    "total_doors": sum(len(story.doors) for story in model.stories),
                    "version": model.version
                }
                
                if context:
                    summary.update({
                        "name": context.name,
                        "description": context.description,
                        "units": context.units.value,
                        "created_at": context.created_at.isoformat(),
                        "last_modified": context.last_modified.isoformat()
                    })
                
                summaries.append(summary)
            
            return summaries
    
    async def add_conversation_entry(self, building_id: str, entry: Dict[str, Any]) -> None:
        """Add an entry to the conversation history for a building.
        
        Args:
            building_id: Building identifier
            entry: Conversation entry with timestamp, action, details
        """
        async with self._lock:
            if building_id not in self._conversation_history:
                self._conversation_history[building_id] = []
            
            entry_with_timestamp = {
                "timestamp": datetime.now().isoformat(),
                **entry
            }
            
            self._conversation_history[building_id].append(entry_with_timestamp)
            
            # Keep only last 100 entries to prevent unbounded growth
            if len(self._conversation_history[building_id]) > 100:
                self._conversation_history[building_id] = self._conversation_history[building_id][-100:]
            
            logger.debug(f"Added conversation entry for building: {building_id}")
    
    async def get_conversation_history(self, building_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history for a building.
        
        Args:
            building_id: Building identifier
            limit: Optional limit on number of entries to return
            
        Returns:
            List of conversation entries
        """
        async with self._lock:
            history = self._conversation_history.get(building_id, [])
            
            if limit:
                history = history[-limit:]
            
            return deepcopy(history)
    
    async def clear_conversation_history(self, building_id: str) -> bool:
        """Clear conversation history for a building.
        
        Args:
            building_id: Building identifier
            
        Returns:
            True if cleared, False if building not found
        """
        async with self._lock:
            if building_id in self._conversation_history:
                self._conversation_history[building_id] = []
                logger.debug(f"Cleared conversation history for building: {building_id}")
                return True
            
            return False
    
    async def get_building_summary(self, building_id: str) -> Optional[Dict[str, Any]]:
        """Get a comprehensive summary of a building.
        
        Args:
            building_id: Building identifier
            
        Returns:
            Building summary with model and context information
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            context = self._building_contexts.get(building_id)
            
            if not model:
                return None
            
            summary = {
                "building_id": building_id,
                "model": {
                    "version": model.version,
                    "story_count": len(model.stories),
                    "total_spaces": sum(len(story.spaces) for story in model.stories),
                    "total_windows": sum(len(story.windows) for story in model.stories),
                    "total_doors": sum(len(story.doors) for story in model.stories),
                    "window_definitions": len(model.window_definitions),
                    "door_definitions": len(model.door_definitions)
                },
                "conversation_entries": len(self._conversation_history.get(building_id, []))
            }
            
            if context:
                summary["context"] = context.get_summary()
            
            return summary
    
    async def _persist_building(self, building_id: str, model: FloorspaceModel, 
                              context: BuildingContext) -> None:
        """Persist a building model and context to file storage.
        
        Args:
            building_id: Building identifier
            model: FloorspaceModel to persist
            context: BuildingContext to persist
        """
        if not self.storage_dir:
            return
        
        try:
            # Create building-specific directory
            building_dir = self.storage_dir / f"building_{building_id}"
            building_dir.mkdir(exist_ok=True)
            
            # Save model as JSON
            model_file = building_dir / "model.json"
            model_data = self._serialize_floorspace_model(model)
            
            with open(model_file, 'w') as f:
                json.dump(model_data, f, indent=2)
            
            # Save context
            context_file = building_dir / "context.json"
            context_data = {
                "building_id": context.building_id,
                "name": context.name,
                "description": context.description,
                "units": context.units.value,
                "total_spaces": context.total_spaces,
                "total_windows": context.total_windows,
                "total_doors": context.total_doors,
                "created_at": context.created_at.isoformat(),
                "last_modified": context.last_modified.isoformat()
            }
            
            with open(context_file, 'w') as f:
                json.dump(context_data, f, indent=2)
            
            # Save conversation history
            history = self._conversation_history.get(building_id, [])
            if history:
                history_file = building_dir / "conversation_history.json"
                with open(history_file, 'w') as f:
                    json.dump(history, f, indent=2)
                    
        except Exception as e:
            logger.error(f"Failed to persist building {building_id}: {e}")
    
    async def _load_building(self, building_id: str) -> Optional[FloorspaceModel]:
        """Load a building model from file storage.
        
        Args:
            building_id: Building identifier
            
        Returns:
            FloorspaceModel if found, None otherwise
        """
        if not self.storage_dir:
            return None
        
        try:
            building_dir = self.storage_dir / f"building_{building_id}"
            model_file = building_dir / "model.json"
            
            if not model_file.exists():
                return None
            
            with open(model_file, 'r') as f:
                model_data = json.load(f)
            
            # Deserialize FloorspaceModel
            model = self._deserialize_floorspace_model(model_data)
            
            # Load context if available
            context_file = building_dir / "context.json"
            if context_file.exists():
                with open(context_file, 'r') as f:
                    context_data = json.load(f)
                
                from ..models.core import Units
                context = BuildingContext(
                    building_id=context_data["building_id"],
                    name=context_data.get("name"),
                    description=context_data.get("description"),
                    units=Units(context_data.get("units", "si")),
                    total_spaces=context_data.get("total_spaces", 0),
                    total_windows=context_data.get("total_windows", 0),
                    total_doors=context_data.get("total_doors", 0),
                    created_at=datetime.fromisoformat(context_data["created_at"]),
                    last_modified=datetime.fromisoformat(context_data["last_modified"])
                )
                
                self._building_contexts[building_id] = context
            
            # Load conversation history if available
            history_file = building_dir / "conversation_history.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
                
                self._conversation_history[building_id] = history
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load building {building_id}: {e}")
            return None
    
    async def _delete_persisted_building(self, building_id: str) -> None:
        """Delete a persisted building directory.
        
        Args:
            building_id: Building identifier
        """
        if not self.storage_dir:
            return
        
        try:
            building_dir = self.storage_dir / f"building_{building_id}"
            if building_dir.exists():
                import shutil
                shutil.rmtree(building_dir)
        except Exception as e:
            logger.error(f"Failed to delete persisted building {building_id}: {e}")
    
    def _serialize_floorspace_model(self, model: FloorspaceModel) -> Dict[str, Any]:
        """Convert FloorspaceModel to serializable dictionary.
        
        Args:
            model: FloorspaceModel to serialize
            
        Returns:
            Serializable dictionary representation
        """
        return {
            "application": model.application,
            "project": model.project,
            "stories": [self._serialize_story(story) for story in model.stories],
            "window_definitions": [self._serialize_window_definition(wd) for wd in model.window_definitions],
            "door_definitions": [self._serialize_door_definition(dd) for dd in model.door_definitions],
            "building_units": model.building_units,
            "thermal_zones": model.thermal_zones,
            "space_types": model.space_types,
            "construction_sets": model.construction_sets,
            "version": model.version
        }
    
    def _serialize_story(self, story: Story) -> Dict[str, Any]:
        """Serialize a Story object."""
        return {
            "id": story.id,
            "name": story.name,
            "geometry": {
                "id": story.geometry.id,
                "vertices": [
                    {
                        "id": v.id,
                        "x": v.x,
                        "y": v.y,
                        "edge_ids": v.edge_ids
                    }
                    for v in story.geometry.vertices
                ],
                "edges": [
                    {
                        "id": e.id,
                        "vertex_ids": e.vertex_ids,
                        "face_ids": e.face_ids
                    }
                    for e in story.geometry.edges
                ],
                "faces": [
                    {
                        "id": f.id,
                        "edge_ids": f.edge_ids,
                        "edge_order": f.edge_order
                    }
                    for f in story.geometry.faces
                ]
            },
            "spaces": [
                {
                    "id": s.id,
                    "name": s.name,
                    "face_id": s.face_id,
                    "color": s.color,
                    "type": s.type
                }
                for s in story.spaces
            ],
            "windows": [
                {
                    "id": w.id,
                    "name": w.name,
                    "window_definition_id": w.window_definition_id,
                    "edge_id": w.edge_id,
                    "alpha": w.alpha
                }
                for w in story.windows
            ],
            "doors": [
                {
                    "id": d.id,
                    "name": d.name,
                    "door_definition_id": d.door_definition_id,
                    "edge_id": d.edge_id,
                    "alpha": d.alpha
                }
                for d in story.doors
            ],
            "floor_to_ceiling_height": story.floor_to_ceiling_height,
            "multiplier": story.multiplier,
            "color": story.color
        }
    
    def _serialize_window_definition(self, wd) -> Dict[str, Any]:
        """Serialize a WindowDefinition object."""
        return {
            "id": wd.id,
            "name": wd.name,
            "height": wd.height,
            "width": wd.width,
            "window_type": wd.window_type,
            "sill_height": wd.sill_height
        }
    
    def _serialize_door_definition(self, dd) -> Dict[str, Any]:
        """Serialize a DoorDefinition object."""
        return {
            "id": dd.id,
            "name": dd.name,
            "height": dd.height,
            "width": dd.width,
            "door_type": dd.door_type
        }
    
    async def update_space(self, building_id: str, space_id: str, 
                          updated_space: Space) -> bool:
        """Update an existing space while preserving other spaces.
        
        Args:
            building_id: Building identifier
            space_id: Space identifier to update
            updated_space: New space data
            
        Returns:
            True if updated, False if space or building not found
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return False
            
            # Find and update the space in the appropriate story
            for story in model.stories:
                for i, space in enumerate(story.spaces):
                    if space.id == space_id:
                        story.spaces[i] = deepcopy(updated_space)
                        
                        # Update building context
                        context = self._building_contexts.get(building_id)
                        if context:
                            context.update_modified_time()
                        
                        # Add conversation entry
                        self._add_conversation_entry_internal(building_id, {
                            "action": "space_updated",
                            "space_id": space_id,
                            "space_name": updated_space.name
                        })
                        
                        if self.enable_persistence and self.storage_dir:
                            await self._persist_building(building_id, model, context)
                        
                        logger.debug(f"Updated space {space_id} in building {building_id}")
                        return True
            
            return False
    
    def _add_conversation_entry_internal(self, building_id: str, entry: Dict[str, Any]) -> None:
        """Add conversation entry without acquiring lock (internal use only)."""
        if building_id not in self._conversation_history:
            self._conversation_history[building_id] = []
        
        entry_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            **entry
        }
        
        self._conversation_history[building_id].append(entry_with_timestamp)
        
        # Keep only last 100 entries to prevent unbounded growth
        if len(self._conversation_history[building_id]) > 100:
            self._conversation_history[building_id] = self._conversation_history[building_id][-100:]

    async def add_space(self, building_id: str, story_id: str, new_space: Space) -> bool:
        """Add a new space to an existing building story.
        
        Args:
            building_id: Building identifier
            story_id: Story identifier to add space to
            new_space: New space to add
            
        Returns:
            True if added, False if story or building not found
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return False
            
            # Find the story and add the space
            for story in model.stories:
                if story.id == story_id:
                    story.spaces.append(deepcopy(new_space))
                    
                    # Update building context
                    context = self._building_contexts.get(building_id)
                    if context:
                        context.increment_space_count()
                    
                    # Add conversation entry
                    self._add_conversation_entry_internal(building_id, {
                        "action": "space_added",
                        "story_id": story_id,
                        "space_id": new_space.id,
                        "space_name": new_space.name
                    })
                    
                    if self.enable_persistence and self.storage_dir:
                        await self._persist_building(building_id, model, context)
                    
                    logger.debug(f"Added space {new_space.id} to story {story_id} in building {building_id}")
                    return True
            
            return False
    
    async def remove_space(self, building_id: str, space_id: str) -> bool:
        """Remove a space from a building while preserving other spaces.
        
        Args:
            building_id: Building identifier
            space_id: Space identifier to remove
            
        Returns:
            True if removed, False if space or building not found
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return False
            
            # Find and remove the space
            for story in model.stories:
                for i, space in enumerate(story.spaces):
                    if space.id == space_id:
                        removed_space = story.spaces.pop(i)
                        
                        # Update building context
                        context = self._building_contexts.get(building_id)
                        if context:
                            context.total_spaces = max(0, context.total_spaces - 1)
                            context.update_modified_time()
                        
                        # Add conversation entry
                        self._add_conversation_entry_internal(building_id, {
                            "action": "space_removed",
                            "space_id": space_id,
                            "space_name": removed_space.name
                        })
                        
                        if self.enable_persistence and self.storage_dir:
                            await self._persist_building(building_id, model, context)
                        
                        logger.debug(f"Removed space {space_id} from building {building_id}")
                        return True
            
            return False
    
    async def add_window_to_space(self, building_id: str, story_id: str, 
                                 window_instance: WindowInstance, 
                                 window_definition: Optional[WindowDefinition] = None) -> bool:
        """Add a window to a space while preserving other elements.
        
        Args:
            building_id: Building identifier
            story_id: Story identifier
            window_instance: Window instance to add
            window_definition: Optional window definition (added if not exists)
            
        Returns:
            True if added, False if story or building not found
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return False
            
            # Find the story
            for story in model.stories:
                if story.id == story_id:
                    # Add window definition if provided and doesn't exist
                    if window_definition:
                        existing_def = next(
                            (wd for wd in model.window_definitions if wd.id == window_definition.id),
                            None
                        )
                        if not existing_def:
                            model.window_definitions.append(deepcopy(window_definition))
                    
                    # Add window instance
                    story.windows.append(deepcopy(window_instance))
                    
                    # Update building context
                    context = self._building_contexts.get(building_id)
                    if context:
                        context.increment_window_count()
                    
                    # Add conversation entry
                    self._add_conversation_entry_internal(building_id, {
                        "action": "window_added",
                        "story_id": story_id,
                        "window_id": window_instance.id,
                        "window_name": window_instance.name,
                        "edge_id": window_instance.edge_id
                    })
                    
                    if self.enable_persistence and self.storage_dir:
                        await self._persist_building(building_id, model, context)
                    
                    logger.debug(f"Added window {window_instance.id} to story {story_id} in building {building_id}")
                    return True
            
            return False
    
    async def add_door_to_space(self, building_id: str, story_id: str, 
                               door_instance: DoorInstance, 
                               door_definition: Optional[DoorDefinition] = None) -> bool:
        """Add a door to a space while preserving other elements.
        
        Args:
            building_id: Building identifier
            story_id: Story identifier
            door_instance: Door instance to add
            door_definition: Optional door definition (added if not exists)
            
        Returns:
            True if added, False if story or building not found
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return False
            
            # Find the story
            for story in model.stories:
                if story.id == story_id:
                    # Add door definition if provided and doesn't exist
                    if door_definition:
                        existing_def = next(
                            (dd for dd in model.door_definitions if dd.id == door_definition.id),
                            None
                        )
                        if not existing_def:
                            model.door_definitions.append(deepcopy(door_definition))
                    
                    # Add door instance
                    story.doors.append(deepcopy(door_instance))
                    
                    # Update building context
                    context = self._building_contexts.get(building_id)
                    if context:
                        context.increment_door_count()
                    
                    # Add conversation entry
                    self._add_conversation_entry_internal(building_id, {
                        "action": "door_added",
                        "story_id": story_id,
                        "door_id": door_instance.id,
                        "door_name": door_instance.name,
                        "edge_id": door_instance.edge_id
                    })
                    
                    if self.enable_persistence and self.storage_dir:
                        await self._persist_building(building_id, model, context)
                    
                    logger.debug(f"Added door {door_instance.id} to story {story_id} in building {building_id}")
                    return True
            
            return False
    
    async def remove_window(self, building_id: str, window_id: str) -> bool:
        """Remove a window from a building while preserving other elements.
        
        Args:
            building_id: Building identifier
            window_id: Window identifier to remove
            
        Returns:
            True if removed, False if window or building not found
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return False
            
            # Find and remove the window
            for story in model.stories:
                for i, window in enumerate(story.windows):
                    if window.id == window_id:
                        removed_window = story.windows.pop(i)
                        
                        # Update building context
                        context = self._building_contexts.get(building_id)
                        if context:
                            context.total_windows = max(0, context.total_windows - 1)
                            context.update_modified_time()
                        
                        # Add conversation entry
                        self._add_conversation_entry_internal(building_id, {
                            "action": "window_removed",
                            "window_id": window_id,
                            "window_name": removed_window.name
                        })
                        
                        if self.enable_persistence and self.storage_dir:
                            await self._persist_building(building_id, model, context)
                        
                        logger.debug(f"Removed window {window_id} from building {building_id}")
                        return True
            
            return False
    
    async def remove_door(self, building_id: str, door_id: str) -> bool:
        """Remove a door from a building while preserving other elements.
        
        Args:
            building_id: Building identifier
            door_id: Door identifier to remove
            
        Returns:
            True if removed, False if door or building not found
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return False
            
            # Find and remove the door
            for story in model.stories:
                for i, door in enumerate(story.doors):
                    if door.id == door_id:
                        removed_door = story.doors.pop(i)
                        
                        # Update building context
                        context = self._building_contexts.get(building_id)
                        if context:
                            context.total_doors = max(0, context.total_doors - 1)
                            context.update_modified_time()
                        
                        # Add conversation entry
                        self._add_conversation_entry_internal(building_id, {
                            "action": "door_removed",
                            "door_id": door_id,
                            "door_name": removed_door.name
                        })
                        
                        if self.enable_persistence and self.storage_dir:
                            await self._persist_building(building_id, model, context)
                        
                        logger.debug(f"Removed door {door_id} from building {building_id}")
                        return True
            
            return False
    
    async def get_space_by_id(self, building_id: str, space_id: str) -> Optional[Space]:
        """Get a specific space by ID.
        
        Args:
            building_id: Building identifier
            space_id: Space identifier
            
        Returns:
            Space if found, None otherwise
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return None
            
            for story in model.stories:
                for space in story.spaces:
                    if space.id == space_id:
                        return deepcopy(space)
            
            return None
    
    async def list_spaces_in_building(self, building_id: str) -> List[Dict[str, Any]]:
        """List all spaces in a building with their story information.
        
        Args:
            building_id: Building identifier
            
        Returns:
            List of space information dictionaries
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return []
            
            spaces_info = []
            for story in model.stories:
                for space in story.spaces:
                    space_info = {
                        "space_id": space.id,
                        "space_name": space.name,
                        "space_type": space.type,
                        "space_color": space.color,
                        "face_id": space.face_id,
                        "story_id": story.id,
                        "story_name": story.name
                    }
                    spaces_info.append(space_info)
            
            return spaces_info
    
    async def update_space_geometry(self, building_id: str, story_id: str, 
                                  updated_geometry: Geometry) -> bool:
        """Update the geometry of a story while preserving space relationships.
        
        Args:
            building_id: Building identifier
            story_id: Story identifier
            updated_geometry: New geometry data
            
        Returns:
            True if updated, False if story or building not found
        """
        async with self._lock:
            model = self._buildings.get(building_id)
            if not model:
                return False
            
            # Find and update the story geometry
            for story in model.stories:
                if story.id == story_id:
                    story.geometry = deepcopy(updated_geometry)
                    
                    # Update building context
                    context = self._building_contexts.get(building_id)
                    if context:
                        context.update_modified_time()
                    
                    # Add conversation entry
                    self._add_conversation_entry_internal(building_id, {
                        "action": "geometry_updated",
                        "story_id": story_id,
                        "vertex_count": len(updated_geometry.vertices),
                        "edge_count": len(updated_geometry.edges),
                        "face_count": len(updated_geometry.faces)
                    })
                    
                    if self.enable_persistence and self.storage_dir:
                        await self._persist_building(building_id, model, context)
                    
                    logger.debug(f"Updated geometry for story {story_id} in building {building_id}")
                    return True
            
            return False

    def _deserialize_floorspace_model(self, data: Dict[str, Any]) -> FloorspaceModel:
        """Convert dictionary back to FloorspaceModel.
        
        Args:
            data: Serialized model data
            
        Returns:
            FloorspaceModel instance
        """
        from ..models.floorspace import (
            FloorspaceModel, Story, Geometry, Vertex, Edge, Face, Space,
            WindowInstance, DoorInstance, WindowDefinition, DoorDefinition
        )
        
        stories = []
        for story_data in data.get("stories", []):
            # Deserialize geometry
            geometry_data = story_data["geometry"]
            vertices = [
                Vertex(
                    id=v["id"],
                    x=v["x"],
                    y=v["y"],
                    edge_ids=v["edge_ids"]
                )
                for v in geometry_data["vertices"]
            ]
            
            edges = [
                Edge(
                    id=e["id"],
                    vertex_ids=e["vertex_ids"],
                    face_ids=e["face_ids"]
                )
                for e in geometry_data["edges"]
            ]
            
            faces = [
                Face(
                    id=f["id"],
                    edge_ids=f["edge_ids"],
                    edge_order=f["edge_order"]
                )
                for f in geometry_data["faces"]
            ]
            
            geometry = Geometry(
                id=geometry_data["id"],
                vertices=vertices,
                edges=edges,
                faces=faces
            )
            
            # Deserialize spaces, windows, doors
            spaces = [
                Space(
                    id=s["id"],
                    name=s["name"],
                    face_id=s["face_id"],
                    color=s["color"],
                    type=s["type"]
                )
                for s in story_data["spaces"]
            ]
            
            windows = [
                WindowInstance(
                    id=w["id"],
                    name=w["name"],
                    window_definition_id=w["window_definition_id"],
                    edge_id=w["edge_id"],
                    alpha=w["alpha"]
                )
                for w in story_data["windows"]
            ]
            
            doors = [
                DoorInstance(
                    id=d["id"],
                    name=d["name"],
                    door_definition_id=d["door_definition_id"],
                    edge_id=d["edge_id"],
                    alpha=d["alpha"]
                )
                for d in story_data["doors"]
            ]
            
            story = Story(
                id=story_data["id"],
                name=story_data["name"],
                geometry=geometry,
                spaces=spaces,
                windows=windows,
                doors=doors,
                floor_to_ceiling_height=story_data["floor_to_ceiling_height"],
                multiplier=story_data["multiplier"],
                color=story_data["color"]
            )
            
            stories.append(story)
        
        # Deserialize window and door definitions
        window_definitions = [
            WindowDefinition(
                id=wd["id"],
                name=wd["name"],
                height=wd["height"],
                width=wd["width"],
                window_type=wd["window_type"],
                sill_height=wd["sill_height"]
            )
            for wd in data.get("window_definitions", [])
        ]
        
        door_definitions = [
            DoorDefinition(
                id=dd["id"],
                name=dd["name"],
                height=dd["height"],
                width=dd["width"],
                door_type=dd["door_type"]
            )
            for dd in data.get("door_definitions", [])
        ]
        
        return FloorspaceModel(
            application=data.get("application", {}),
            project=data.get("project", {}),
            stories=stories,
            window_definitions=window_definitions,
            door_definitions=door_definitions,
            building_units=data.get("building_units", []),
            thermal_zones=data.get("thermal_zones", []),
            space_types=data.get("space_types", []),
            construction_sets=data.get("construction_sets", []),
            version=data.get("version", "1.4.3")
        )