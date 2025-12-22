"""Core data models for the Natural Language to Floorspace JSON Agent."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
import uuid
from datetime import datetime

if TYPE_CHECKING:
    from .floorspace import FloorspaceModel


class Units(Enum):
    """Units for measurements."""
    IP = "ip"  # imperial
    SI = "si"  # metric


class ElementType(Enum):
    """Types of building elements."""
    WINDOW = "window"
    DOOR = "door"


class ConversationStep(Enum):
    """Steps in the conversation flow."""
    PARSING = "parsing"
    CLARIFYING = "clarifying"
    GENERATING = "generating"


@dataclass
class Dimensions:
    """Spatial dimensions with units."""
    width: float
    length: float
    height: Optional[float] = None
    units: Units = Units.SI


@dataclass
class ElementSpec:
    """Specification for a building element."""
    width: Optional[float] = None
    height: Optional[float] = None
    wall: Optional[str] = None  # WallReference
    alpha: Optional[float] = None  # position along edge (0-1)


@dataclass
class BuildingElement:
    """A building element like window or door."""
    type: ElementType
    count: int
    specifications: Optional[ElementSpec] = None


@dataclass
class SpaceRequirement:
    """Requirements for a space to be created."""
    dimensions: Dimensions
    elements: List[BuildingElement]
    placement: Optional[str] = None  # PlacementHint
    room_type: Optional[str] = None


@dataclass
class ConversationState:
    """State of the conversation with the user."""
    current_step: ConversationStep
    pending_questions: List[dict] = field(default_factory=list)  # Question objects
    collected_specs: List[ElementSpec] = field(default_factory=list)
    building_model: Optional['FloorspaceModel'] = None  # Forward reference
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self) -> None:
        """Update the last_updated timestamp."""
        self.last_updated = datetime.now()
    
    def add_question(self, question: dict) -> None:
        """Add a question to the pending questions list."""
        self.pending_questions.append(question)
        self.update_timestamp()
    
    def remove_question(self, question_id: str) -> bool:
        """Remove a question by ID from pending questions."""
        original_length = len(self.pending_questions)
        self.pending_questions = [q for q in self.pending_questions if q.get('id') != question_id]
        if len(self.pending_questions) < original_length:
            self.update_timestamp()
            return True
        return False
    
    def add_element_spec(self, spec: ElementSpec) -> None:
        """Add an element specification to the collected specs."""
        self.collected_specs.append(spec)
        self.update_timestamp()
    
    def clear_pending_questions(self) -> None:
        """Clear all pending questions."""
        self.pending_questions.clear()
        self.update_timestamp()
    
    def has_pending_questions(self) -> bool:
        """Check if there are any pending questions."""
        return len(self.pending_questions) > 0
    
    def get_question_count(self) -> int:
        """Get the number of pending questions."""
        return len(self.pending_questions)
    
    def get_spec_count(self) -> int:
        """Get the number of collected element specifications."""
        return len(self.collected_specs)


@dataclass
class Question:
    """A clarification question for the user."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    question_type: str = ""  # 'dimension', 'placement', 'specification'
    element_id: Optional[str] = None
    options: List[str] = field(default_factory=list)
    required: bool = True
    answered: bool = False
    answer: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def mark_answered(self, answer: str) -> None:
        """Mark the question as answered with the provided answer."""
        self.answer = answer
        self.answered = True


@dataclass
class SessionContext:
    """Context information for a conversation session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    conversation_state: Optional[ConversationState] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the session context."""
        self.metadata[key] = value
        self.update_activity()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the session context."""
        return self.metadata.get(key, default)


@dataclass
class BuildingContext:
    """Context information about the current building being designed."""
    building_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    description: Optional[str] = None
    units: Units = Units.SI
    total_spaces: int = 0
    total_windows: int = 0
    total_doors: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    
    def update_modified_time(self) -> None:
        """Update the last modified timestamp."""
        self.last_modified = datetime.now()
    
    def increment_space_count(self) -> None:
        """Increment the total space count."""
        self.total_spaces += 1
        self.update_modified_time()
    
    def increment_window_count(self, count: int = 1) -> None:
        """Increment the total window count."""
        self.total_windows += count
        self.update_modified_time()
    
    def increment_door_count(self, count: int = 1) -> None:
        """Increment the total door count."""
        self.total_doors += count
        self.update_modified_time()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the building context."""
        return {
            "building_id": self.building_id,
            "name": self.name,
            "description": self.description,
            "units": self.units.value,
            "total_spaces": self.total_spaces,
            "total_windows": self.total_windows,
            "total_doors": self.total_doors,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat()
        }