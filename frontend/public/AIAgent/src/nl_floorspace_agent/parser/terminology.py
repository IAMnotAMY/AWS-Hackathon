"""Terminology recognition and normalization for natural language parsing."""

import re
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RoomType(Enum):
    """Standard room types."""
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    LIVING_ROOM = "living_room"
    OFFICE = "office"
    DINING_ROOM = "dining_room"
    FAMILY_ROOM = "family_room"
    STUDY = "study"
    LAUNDRY = "laundry"
    GARAGE = "garage"
    CLOSET = "closet"
    HALLWAY = "hallway"
    FOYER = "foyer"
    PANTRY = "pantry"
    UTILITY = "utility"
    GENERIC = "room"  # Generic room type


class Direction(Enum):
    """Directional references."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    LEFT = "left"
    RIGHT = "right"
    FRONT = "front"
    BACK = "back"
    REAR = "rear"


@dataclass
class TerminologyMatch:
    """Represents a matched terminology item."""
    original_text: str
    normalized_term: str
    category: str  # 'room_type', 'direction', 'synonym'
    confidence: float
    start_pos: int
    end_pos: int


class TerminologyRecognizer:
    """Recognizes and normalizes building-related terminology."""
    
    def __init__(self):
        """Initialize the terminology recognizer."""
        # Room type mappings with synonyms
        self.room_type_mappings = {
            # Bedroom variations
            'bedroom': RoomType.BEDROOM,
            'bed room': RoomType.BEDROOM,
            'master bedroom': RoomType.BEDROOM,
            'guest bedroom': RoomType.BEDROOM,
            'spare bedroom': RoomType.BEDROOM,
            'sleeping room': RoomType.BEDROOM,
            
            # Kitchen variations
            'kitchen': RoomType.KITCHEN,
            'kitchenette': RoomType.KITCHEN,
            'galley kitchen': RoomType.KITCHEN,
            'cooking area': RoomType.KITCHEN,
            'cook room': RoomType.KITCHEN,
            
            # Bathroom variations
            'bathroom': RoomType.BATHROOM,
            'bath room': RoomType.BATHROOM,
            'restroom': RoomType.BATHROOM,
            'washroom': RoomType.BATHROOM,
            'powder room': RoomType.BATHROOM,
            'half bath': RoomType.BATHROOM,
            'full bath': RoomType.BATHROOM,
            'toilet': RoomType.BATHROOM,
            'wc': RoomType.BATHROOM,
            'water closet': RoomType.BATHROOM,
            
            # Living room variations
            'living room': RoomType.LIVING_ROOM,
            'livingroom': RoomType.LIVING_ROOM,
            'lounge': RoomType.LIVING_ROOM,
            'sitting room': RoomType.LIVING_ROOM,
            'front room': RoomType.LIVING_ROOM,
            'parlor': RoomType.LIVING_ROOM,
            'parlour': RoomType.LIVING_ROOM,
            'great room': RoomType.LIVING_ROOM,
            
            # Office variations
            'office': RoomType.OFFICE,
            'home office': RoomType.OFFICE,
            'study': RoomType.STUDY,
            'den': RoomType.STUDY,
            'library': RoomType.STUDY,
            'work room': RoomType.OFFICE,
            'workspace': RoomType.OFFICE,
            
            # Dining room variations
            'dining room': RoomType.DINING_ROOM,
            'diningroom': RoomType.DINING_ROOM,
            'dining area': RoomType.DINING_ROOM,
            'breakfast room': RoomType.DINING_ROOM,
            'breakfast nook': RoomType.DINING_ROOM,
            'eating area': RoomType.DINING_ROOM,
            
            # Family room variations
            'family room': RoomType.FAMILY_ROOM,
            'familyroom': RoomType.FAMILY_ROOM,
            'rec room': RoomType.FAMILY_ROOM,
            'recreation room': RoomType.FAMILY_ROOM,
            'playroom': RoomType.FAMILY_ROOM,
            'game room': RoomType.FAMILY_ROOM,
            
            # Utility spaces
            'laundry': RoomType.LAUNDRY,
            'laundry room': RoomType.LAUNDRY,
            'utility room': RoomType.UTILITY,
            'utility': RoomType.UTILITY,
            'mud room': RoomType.UTILITY,
            'mudroom': RoomType.UTILITY,
            
            # Storage and access
            'garage': RoomType.GARAGE,
            'closet': RoomType.CLOSET,
            'walk-in closet': RoomType.CLOSET,
            'wardrobe': RoomType.CLOSET,
            'pantry': RoomType.PANTRY,
            'storage room': RoomType.CLOSET,
            
            # Circulation spaces
            'hallway': RoomType.HALLWAY,
            'hall': RoomType.HALLWAY,
            'corridor': RoomType.HALLWAY,
            'passage': RoomType.HALLWAY,
            'foyer': RoomType.FOYER,
            'entryway': RoomType.FOYER,
            'entrance': RoomType.FOYER,
            'vestibule': RoomType.FOYER,
            
            # Generic terms
            'room': RoomType.GENERIC,
            'space': RoomType.GENERIC,
            'area': RoomType.GENERIC,
            'chamber': RoomType.GENERIC,
        }
        
        # Direction mappings with synonyms
        self.direction_mappings = {
            # Cardinal directions
            'north': Direction.NORTH,
            'northern': Direction.NORTH,
            'n': Direction.NORTH,
            
            'south': Direction.SOUTH,
            'southern': Direction.SOUTH,
            's': Direction.SOUTH,
            
            'east': Direction.EAST,
            'eastern': Direction.EAST,
            'e': Direction.EAST,
            
            'west': Direction.WEST,
            'western': Direction.WEST,
            'w': Direction.WEST,
            
            # Relative directions
            'left': Direction.LEFT,
            'left-hand': Direction.LEFT,
            'lefthand': Direction.LEFT,
            
            'right': Direction.RIGHT,
            'right-hand': Direction.RIGHT,
            'righthand': Direction.RIGHT,
            
            'front': Direction.FRONT,
            'forward': Direction.FRONT,
            'fore': Direction.FRONT,
            
            'back': Direction.BACK,
            'rear': Direction.REAR,
            'behind': Direction.BACK,
            'aft': Direction.BACK,
        }
        
        # General synonyms for common terms
        self.general_synonyms = {
            # Space synonyms
            'room': ['space', 'area', 'chamber'],
            'space': ['room', 'area'],
            'area': ['space', 'room', 'zone'],
            
            # Wall synonyms
            'wall': ['side', 'partition', 'barrier'],
            'side': ['wall', 'edge'],
            
            # Opening synonyms (handled in element detector but included for completeness)
            'window': ['opening', 'glazing', 'fenestration'],
            'opening': ['window', 'aperture'],
            'door': ['entrance', 'doorway', 'entry', 'exit'],
            'entrance': ['door', 'doorway', 'entry'],
            'doorway': ['door', 'entrance', 'entry'],
            
            # Size synonyms
            'large': ['big', 'huge', 'massive', 'spacious'],
            'small': ['little', 'tiny', 'compact', 'cozy'],
            'medium': ['average', 'standard', 'regular', 'normal'],
        }
        
        # Compile regex patterns for efficient matching
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient terminology matching."""
        # Room type patterns
        room_terms = sorted(self.room_type_mappings.keys(), key=len, reverse=True)
        self.room_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in room_terms) + r')\b',
            re.IGNORECASE
        )
        
        # Direction patterns (with wall context)
        direction_terms = sorted(self.direction_mappings.keys(), key=len, reverse=True)
        self.direction_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in direction_terms) + r')\s+(?:wall|side|edge)\b',
            re.IGNORECASE
        )
        
        # Standalone direction patterns
        self.standalone_direction_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in direction_terms) + r')\b',
            re.IGNORECASE
        )
    
    def recognize_room_types(self, text: str) -> List[TerminologyMatch]:
        """Recognize room types in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of room type matches
        """
        matches = []
        text_lower = text.lower()
        
        for match in self.room_pattern.finditer(text_lower):
            matched_text = match.group(1)
            room_type = self.room_type_mappings.get(matched_text)
            
            if room_type:
                matches.append(TerminologyMatch(
                    original_text=matched_text,
                    normalized_term=room_type.value,
                    category='room_type',
                    confidence=1.0,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return matches
    
    def recognize_directions(self, text: str) -> List[TerminologyMatch]:
        """Recognize directional references in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of direction matches
        """
        matches = []
        text_lower = text.lower()
        
        # First, look for directions with wall context (higher confidence)
        for match in self.direction_pattern.finditer(text_lower):
            direction_text = match.group(1)
            direction = self.direction_mappings.get(direction_text)
            
            if direction:
                matches.append(TerminologyMatch(
                    original_text=match.group(0),
                    normalized_term=direction.value,
                    category='direction',
                    confidence=1.0,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        # Then look for standalone directions (lower confidence)
        covered_spans = {(m.start_pos, m.end_pos) for m in matches}
        
        for match in self.standalone_direction_pattern.finditer(text_lower):
            # Skip if already covered by wall context match
            if any(match.start() >= start and match.end() <= end for start, end in covered_spans):
                continue
                
            direction_text = match.group(1)
            direction = self.direction_mappings.get(direction_text)
            
            if direction:
                matches.append(TerminologyMatch(
                    original_text=direction_text,
                    normalized_term=direction.value,
                    category='direction',
                    confidence=0.7,  # Lower confidence for standalone
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return matches
    
    def recognize_synonyms(self, text: str) -> List[TerminologyMatch]:
        """Recognize and normalize synonyms in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of synonym matches
        """
        matches = []
        text_lower = text.lower()
        
        for base_term, synonyms in self.general_synonyms.items():
            # Create pattern for this synonym group
            all_terms = [base_term] + synonyms
            pattern = re.compile(
                r'\b(' + '|'.join(re.escape(term) for term in all_terms) + r')\b',
                re.IGNORECASE
            )
            
            for match in pattern.finditer(text_lower):
                matched_text = match.group(1)
                if matched_text != base_term:  # Only record actual synonyms
                    matches.append(TerminologyMatch(
                        original_text=matched_text,
                        normalized_term=base_term,
                        category='synonym',
                        confidence=0.9,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
        
        return matches
    
    def recognize_all_terminology(self, text: str) -> List[TerminologyMatch]:
        """Recognize all terminology in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of all terminology matches, sorted by position
        """
        all_matches = []
        
        # Collect all types of matches
        all_matches.extend(self.recognize_room_types(text))
        all_matches.extend(self.recognize_directions(text))
        all_matches.extend(self.recognize_synonyms(text))
        
        # Sort by position in text
        all_matches.sort(key=lambda m: m.start_pos)
        
        # Remove overlapping matches (keep higher confidence)
        filtered_matches = []
        for match in all_matches:
            # Check for overlap with existing matches
            overlaps = False
            for existing in filtered_matches:
                if (match.start_pos < existing.end_pos and 
                    match.end_pos > existing.start_pos):
                    # There's an overlap
                    if match.confidence > existing.confidence:
                        # Replace existing with higher confidence match
                        filtered_matches.remove(existing)
                        break
                    else:
                        # Keep existing, skip this match
                        overlaps = True
                        break
            
            if not overlaps:
                filtered_matches.append(match)
        
        return sorted(filtered_matches, key=lambda m: m.start_pos)
    
    def get_room_type(self, text: str) -> Optional[RoomType]:
        """Get the primary room type from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Primary room type or None if not found
        """
        room_matches = self.recognize_room_types(text)
        if room_matches:
            # Return the first (most confident) match
            room_type_str = room_matches[0].normalized_term
            return RoomType(room_type_str)
        return None
    
    def get_directions(self, text: str) -> List[Direction]:
        """Get all directions mentioned in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of directions found
        """
        direction_matches = self.recognize_directions(text)
        directions = []
        
        for match in direction_matches:
            try:
                direction = Direction(match.normalized_term)
                if direction not in directions:
                    directions.append(direction)
            except ValueError:
                continue
        
        return directions
    
    def normalize_text(self, text: str) -> str:
        """Normalize text by replacing synonyms with standard terms.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text with synonyms replaced
        """
        normalized = text
        matches = self.recognize_synonyms(text)
        
        # Apply replacements in reverse order to maintain positions
        for match in reversed(matches):
            normalized = (
                normalized[:match.start_pos] + 
                match.normalized_term + 
                normalized[match.end_pos:]
            )
        
        return normalized
    
    def get_terminology_summary(self, text: str) -> Dict[str, List[str]]:
        """Get a summary of all recognized terminology.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with categories and found terms
        """
        matches = self.recognize_all_terminology(text)
        summary = {
            'room_types': [],
            'directions': [],
            'synonyms': []
        }
        
        for match in matches:
            category_key = match.category
            if category_key == 'room_type':
                category_key = 'room_types'
            elif category_key == 'direction':
                category_key = 'directions'
            elif category_key == 'synonym':
                category_key = 'synonyms'
            
            if category_key in summary:
                term_info = f"{match.original_text} → {match.normalized_term}"
                if term_info not in summary[category_key]:
                    summary[category_key].append(term_info)
        
        return summary