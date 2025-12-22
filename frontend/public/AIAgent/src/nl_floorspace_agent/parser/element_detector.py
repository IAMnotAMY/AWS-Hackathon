"""Building element detection from natural language."""

import re
from typing import List, Dict, Tuple
from ..models import BuildingElement, ElementType
from .validation import InputValidator, ValidationResult


class ElementDetector:
    """Detects building elements like windows and doors in natural language."""
    
    def __init__(self):
        """Initialize the element detector."""
        self.validator = InputValidator()
        
        # Define patterns for different element types
        self.element_patterns = {
            ElementType.WINDOW: {
                'keywords': [
                    'window', 'windows', 'opening', 'openings', 
                    'glazing', 'glass', 'fenestration'
                ],
                'patterns': [
                    # "2 windows", "three windows", "a window" (standalone)
                    r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+(?:large\s+|small\s+|big\s+)?(?:windows?|openings?)\b',
                    # "with 2 windows", "has windows" (with explicit count)
                    r'\b(?:with|has|have|including?)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:windows?|openings?)\b',
                    # "with a window", "has an opening" (singular with article)
                    r'\b(?:with|has|have|including?)\s+(a|an)\s+(?:large\s+|small\s+|big\s+)?(?:window|opening)\b',
                    # "window on the", "windows facing"
                    r'\b(?:windows?|openings?)\s+(?:on|facing|in|along)\b',
                    # "windowed wall", "glazed wall"
                    r'\b(?:windowed|glazed)\s+wall\b',
                ]
            },
            ElementType.DOOR: {
                'keywords': [
                    'door', 'doors', 'entrance', 'entrances', 
                    'entry', 'exit', 'doorway', 'doorways'
                ],
                'patterns': [
                    # "2 doors", "three doors", "a door" (standalone)
                    r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+(?:large\s+|small\s+|big\s+)?(?:doors?|entrances?|doorways?)\b',
                    # "with 2 doors", "has entrance" (with explicit count)
                    r'\b(?:with|has|have|including?)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:doors?|entrances?|doorways?)\b',
                    # "with a door", "has an entrance" (singular with article)
                    r'\b(?:with|has|have|including?)\s+(a|an)\s+(?:large\s+|small\s+|big\s+)?(?:door|entrance|doorway)\b',
                    # "door on the", "entrance facing"
                    r'\b(?:doors?|entrances?|doorways?)\s+(?:on|facing|in|along)\b',
                    # "main entrance", "front door"
                    r'\b(?:main|front|back|side|rear)\s+(?:door|entrance|doorway)\b',
                ]
            }
        }
        
        # Number word to digit mapping
        self.number_words = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'a': 1, 'an': 1
        }
    
    def detect_elements_with_validation(self, text: str) -> Tuple[List[BuildingElement], ValidationResult]:
        """Detect building elements in text with validation.
        
        Args:
            text: Natural language text
            
        Returns:
            Tuple of (List of detected building elements, ValidationResult)
        """
        # First validate the input text
        text_validation = self.validator.validate_input_text(text)
        if not text_validation.is_valid:
            return [], text_validation
        
        text = text.lower().strip()
        detected_elements = []
        
        # Detect each element type
        for element_type in ElementType:
            count = self._detect_element_count(text, element_type)
            if count > 0:
                detected_elements.append(BuildingElement(
                    type=element_type,
                    count=count,
                    specifications=None  # Will be filled in during clarification
                ))
        
        # Validate the detected elements
        validation_result = self.validator.validate_elements(detected_elements)
        
        return detected_elements, validation_result
    
    def detect_elements(self, text: str) -> List[BuildingElement]:
        """Detect building elements in text (backward compatibility method).
        
        Args:
            text: Natural language text
            
        Returns:
            List of detected building elements
        """
        elements, _ = self.detect_elements_with_validation(text)
        return elements
    
    def _detect_element_count(self, text: str, element_type: ElementType) -> int:
        """Detect the count of a specific element type in text.
        
        Args:
            text: Natural language text (lowercase)
            element_type: Type of element to detect
            
        Returns:
            Count of detected elements (0 if none found)
        """
        patterns_config = self.element_patterns[element_type]
        all_matches = []
        
        # Collect all matches from all patterns
        for pattern in patterns_config['patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                all_matches.append(match)
        
        # If no matches found, check for keywords as fallback
        if not all_matches:
            for keyword in patterns_config['keywords']:
                keyword_pattern = r'\b' + re.escape(keyword) + r'\b'
                keyword_matches = list(re.finditer(keyword_pattern, text, re.IGNORECASE))
                if keyword_matches:
                    # Found keyword, assume count of 1
                    return 1
            return 0
        
        # Remove overlapping matches (keep the longest/most specific one)
        non_overlapping_matches = self._remove_overlapping_matches(all_matches)
        
        # Sum up counts from all non-overlapping matches
        total_count = sum(self._extract_count_from_match(match) for match in non_overlapping_matches)
        
        return min(total_count, 20)  # Cap at reasonable maximum
    
    def _remove_overlapping_matches(self, matches: List[re.Match]) -> List[re.Match]:
        """Remove overlapping matches, keeping the longest/most specific ones.
        
        Args:
            matches: List of regex match objects
            
        Returns:
            List of non-overlapping matches
        """
        if not matches:
            return []
        
        # Sort matches by start position, then by length (longest first)
        sorted_matches = sorted(matches, key=lambda m: (m.start(), -(m.end() - m.start())))
        
        non_overlapping = []
        for match in sorted_matches:
            # Check if this match overlaps with any already selected match
            overlaps = False
            for selected in non_overlapping:
                if self._matches_overlap(match, selected):
                    overlaps = True
                    break
            
            if not overlaps:
                non_overlapping.append(match)
        
        return non_overlapping
    
    def _matches_overlap(self, match1: re.Match, match2: re.Match) -> bool:
        """Check if two matches overlap.
        
        Args:
            match1: First match
            match2: Second match
            
        Returns:
            True if matches overlap
        """
        return not (match1.end() <= match2.start() or match2.end() <= match1.start())
    
    def _extract_count_from_match(self, match: re.Match) -> int:
        """Extract numeric count from a regex match.
        
        Args:
            match: Regex match object
            
        Returns:
            Numeric count (defaults to 1 if no number found)
        """
        # Try to find a number in the captured groups
        for group in match.groups():
            if group:
                # Try to convert to int directly
                if group.isdigit():
                    return int(group)
                
                # Try number words
                if group.lower() in self.number_words:
                    return self.number_words[group.lower()]
        
        # If no explicit number found, assume 1
        return 1
    
    def get_element_summary(self, elements: List[BuildingElement]) -> Dict[str, int]:
        """Get a summary of detected elements.
        
        Args:
            elements: List of detected building elements
            
        Returns:
            Dictionary mapping element type names to counts
        """
        summary = {}
        for element in elements:
            element_name = element.type.value + ('s' if element.count > 1 else '')
            summary[element_name] = element.count
        
        return summary
    
    def has_elements(self, text: str) -> bool:
        """Check if text contains any building elements.
        
        Args:
            text: Natural language text
            
        Returns:
            True if any elements are detected
        """
        elements = self.detect_elements(text)
        return len(elements) > 0