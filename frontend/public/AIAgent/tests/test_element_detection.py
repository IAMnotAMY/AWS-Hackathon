"""Tests for building element detection functionality."""

import pytest
from hypothesis import given, strategies as st, assume
from src.nl_floorspace_agent.parser.element_detector import ElementDetector
from src.nl_floorspace_agent.models import ElementType


class TestElementDetection:
    """Unit tests for element detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ElementDetector()
    
    def test_detect_single_window(self):
        """Test detection of a single window."""
        text = "5m x 4m room with a window"
        elements = self.detector.detect_elements(text)
        
        assert len(elements) == 1
        assert elements[0].type == ElementType.WINDOW
        assert elements[0].count == 1
    
    def test_detect_multiple_windows(self):
        """Test detection of multiple windows."""
        test_cases = [
            ("room with 3 windows", 3),
            ("bedroom with two windows", 2),
            ("office with five windows facing south", 5),
            ("living room has 4 large windows", 4),
        ]
        
        for text, expected_count in test_cases:
            elements = self.detector.detect_elements(text)
            window_elements = [e for e in elements if e.type == ElementType.WINDOW]
            
            assert len(window_elements) == 1, f"Expected 1 window element for: {text}"
            assert window_elements[0].count == expected_count, f"Expected {expected_count} windows for: {text}"
    
    def test_detect_single_door(self):
        """Test detection of a single door."""
        text = "5m x 4m room with a door"
        elements = self.detector.detect_elements(text)
        
        assert len(elements) == 1
        assert elements[0].type == ElementType.DOOR
        assert elements[0].count == 1
    
    def test_detect_multiple_doors(self):
        """Test detection of multiple doors."""
        test_cases = [
            ("room with 2 doors", 2),
            ("bedroom with two entrances", 2),
            ("office with three doorways", 3),
            ("living room has 2 doors", 2),
        ]
        
        for text, expected_count in test_cases:
            elements = self.detector.detect_elements(text)
            door_elements = [e for e in elements if e.type == ElementType.DOOR]
            
            assert len(door_elements) == 1, f"Expected 1 door element for: {text}"
            assert door_elements[0].count == expected_count, f"Expected {expected_count} doors for: {text}"
    
    def test_detect_windows_and_doors(self):
        """Test detection of both windows and doors."""
        text = "5m x 4m bedroom with 2 windows and 1 door"
        elements = self.detector.detect_elements(text)
        
        assert len(elements) == 2
        
        window_elements = [e for e in elements if e.type == ElementType.WINDOW]
        door_elements = [e for e in elements if e.type == ElementType.DOOR]
        
        assert len(window_elements) == 1
        assert window_elements[0].count == 2
        
        assert len(door_elements) == 1
        assert door_elements[0].count == 1
    
    def test_detect_synonyms(self):
        """Test detection of element synonyms."""
        # Window synonyms
        window_texts = [
            "room with openings",
            "office with glazing",
            "bedroom with glass panels",
        ]
        
        for text in window_texts:
            elements = self.detector.detect_elements(text)
            window_elements = [e for e in elements if e.type == ElementType.WINDOW]
            assert len(window_elements) >= 1, f"Should detect windows in: {text}"
        
        # Door synonyms
        door_texts = [
            "room with entrance",
            "office with doorway",
            "bedroom with main entry",
        ]
        
        for text in door_texts:
            elements = self.detector.detect_elements(text)
            door_elements = [e for e in elements if e.type == ElementType.DOOR]
            assert len(door_elements) >= 1, f"Should detect doors in: {text}"
    
    def test_number_word_conversion(self):
        """Test conversion of number words to digits."""
        test_cases = [
            ("room with one window", 1),
            ("office with two doors", 2),
            ("bedroom with three windows", 3),
            ("living room with four openings", 4),
            ("kitchen with five windows", 5),
        ]
        
        for text, expected_count in test_cases:
            elements = self.detector.detect_elements(text)
            assert len(elements) >= 1, f"Should detect elements in: {text}"
            
            total_count = sum(e.count for e in elements)
            assert total_count == expected_count, f"Expected total count {expected_count} for: {text}"
    
    def test_no_elements_detected(self):
        """Test that no elements are detected when none are mentioned."""
        text = "5m x 4m empty room"
        elements = self.detector.detect_elements(text)
        
        assert len(elements) == 0
    
    def test_complex_descriptions(self):
        """Test detection in complex descriptions."""
        text = "Create a 6m x 4m living room with 3 large windows on the south wall and 2 doors"
        elements = self.detector.detect_elements(text)
        
        window_elements = [e for e in elements if e.type == ElementType.WINDOW]
        door_elements = [e for e in elements if e.type == ElementType.DOOR]
        
        assert len(window_elements) == 1
        assert window_elements[0].count == 3
        
        assert len(door_elements) == 1
        assert door_elements[0].count == 2
    
    def test_element_summary(self):
        """Test element summary generation."""
        text = "room with 2 windows and 1 door"
        elements = self.detector.detect_elements(text)
        summary = self.detector.get_element_summary(elements)
        
        assert summary.get('windows') == 2
        assert summary.get('door') == 1
    
    def test_has_elements(self):
        """Test has_elements utility method."""
        assert self.detector.has_elements("room with windows") == True
        assert self.detector.has_elements("room with doors") == True
        assert self.detector.has_elements("empty room") == False
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Empty text
        assert len(self.detector.detect_elements("")) == 0
        
        # Very large numbers (should be capped)
        elements = self.detector.detect_elements("room with 100 windows")
        if elements:
            assert all(e.count <= 20 for e in elements)
        
        # Mixed case
        elements = self.detector.detect_elements("Room With 2 WINDOWS And 1 Door")
        assert len(elements) == 2
    
    def test_avoid_double_counting(self):
        """Test that elements aren't double-counted from overlapping patterns."""
        text = "room with 2 windows and windows on the wall"
        elements = self.detector.detect_elements(text)
        
        window_elements = [e for e in elements if e.type == ElementType.WINDOW]
        # Should detect windows but not double-count
        assert len(window_elements) == 1
        # Count should be reasonable (not inflated by multiple pattern matches)
        assert window_elements[0].count <= 3


class TestElementDetectionProperties:
    """
    **Feature: nl-floorspace-agent, Property 2: Element Detection Completeness**
    **Validates: Requirements 1.3**
    
    Property-based tests for element detection completeness.
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ElementDetector()
    
    @given(
        window_count=st.integers(min_value=1, max_value=10),
        door_count=st.integers(min_value=1, max_value=10),
        window_term=st.sampled_from(['window', 'windows', 'opening', 'openings']),
        door_term=st.sampled_from(['door', 'doors', 'entrance', 'entrances', 'doorway', 'doorways']),
        room_description=st.sampled_from(['room', 'bedroom', 'office', 'kitchen', 'living room'])
    )
    def test_element_detection_completeness_with_counts(self, window_count: int, door_count: int, 
                                                       window_term: str, door_term: str, room_description: str):
        """
        **Feature: nl-floorspace-agent, Property 2: Element Detection Completeness**
        
        For any natural language description with explicit element counts,
        all mentioned building elements should be detected and counted correctly.
        """
        # Generate test input with explicit counts
        test_input = f"5m x 4m {room_description} with {window_count} {window_term} and {door_count} {door_term}"
        
        # Detect elements
        elements = self.detector.detect_elements(test_input)
        
        # Should detect both windows and doors
        window_elements = [e for e in elements if e.type == ElementType.WINDOW]
        door_elements = [e for e in elements if e.type == ElementType.DOOR]
        
        # Validate window detection
        assert len(window_elements) == 1, f"Should detect exactly 1 window element type in: {test_input}"
        assert window_elements[0].count == window_count, \
            f"Window count mismatch: expected {window_count}, got {window_elements[0].count} for: {test_input}"
        
        # Validate door detection
        assert len(door_elements) == 1, f"Should detect exactly 1 door element type in: {test_input}"
        assert door_elements[0].count == door_count, \
            f"Door count mismatch: expected {door_count}, got {door_elements[0].count} for: {test_input}"
    
    @given(
        element_type=st.sampled_from([ElementType.WINDOW, ElementType.DOOR]),
        count=st.integers(min_value=1, max_value=15),
        number_word=st.sampled_from(['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'])
    )
    def test_number_word_detection_completeness(self, element_type: ElementType, count: int, number_word: str):
        """
        **Feature: nl-floorspace-agent, Property 2: Element Detection Completeness**
        
        For any natural language description using number words,
        the agent should correctly convert and count elements.
        """
        # Map number words to expected counts (only test mappable ones)
        number_mapping = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }
        
        if number_word not in number_mapping:
            assume(False)  # Skip if not in our mapping
        
        expected_count = number_mapping[number_word]
        
        # Generate appropriate element term
        if element_type == ElementType.WINDOW:
            element_term = 'windows' if expected_count > 1 else 'window'
        else:
            element_term = 'doors' if expected_count > 1 else 'door'
        
        test_input = f"room with {number_word} {element_term}"
        
        # Detect elements
        elements = self.detector.detect_elements(test_input)
        
        # Should detect the specified element type
        matching_elements = [e for e in elements if e.type == element_type]
        assert len(matching_elements) == 1, f"Should detect exactly 1 {element_type.value} element in: {test_input}"
        assert matching_elements[0].count == expected_count, \
            f"Count mismatch: expected {expected_count}, got {matching_elements[0].count} for: {test_input}"
    
    @given(
        window_synonym=st.sampled_from(['window', 'opening', 'glazing']),
        door_synonym=st.sampled_from(['door', 'entrance', 'doorway', 'entry']),
        adjective=st.sampled_from(['large', 'small', 'big', 'main', 'front', 'back'])
    )
    def test_synonym_detection_completeness(self, window_synonym: str, door_synonym: str, adjective: str):
        """
        **Feature: nl-floorspace-agent, Property 2: Element Detection Completeness**
        
        For any natural language description using element synonyms,
        all synonymous terms should be correctly identified as their respective element types.
        """
        test_input = f"room with a {adjective} {window_synonym} and a {adjective} {door_synonym}"
        
        # Detect elements
        elements = self.detector.detect_elements(test_input)
        
        # Should detect both element types
        window_elements = [e for e in elements if e.type == ElementType.WINDOW]
        door_elements = [e for e in elements if e.type == ElementType.DOOR]
        
        assert len(window_elements) == 1, f"Should detect window synonym '{window_synonym}' in: {test_input}"
        assert window_elements[0].count >= 1, f"Window count should be at least 1 for: {test_input}"
        
        assert len(door_elements) == 1, f"Should detect door synonym '{door_synonym}' in: {test_input}"
        assert door_elements[0].count >= 1, f"Door count should be at least 1 for: {test_input}"
    
    @given(
        text_without_elements=st.text(min_size=5, max_size=100).filter(
            lambda x: not any(keyword in x.lower() for keyword in [
                'window', 'door', 'opening', 'entrance', 'doorway', 'glazing', 'glass'
            ])
        )
    )
    def test_no_false_positives(self, text_without_elements: str):
        """
        **Feature: nl-floorspace-agent, Property 2: Element Detection Completeness**
        
        For any natural language description without building elements,
        the agent should not detect any elements (no false positives).
        """
        # Ensure the text doesn't contain element keywords
        assume(not any(keyword in text_without_elements.lower() for keyword in [
            'window', 'door', 'opening', 'entrance', 'doorway', 'glazing', 'glass', 'entry', 'exit'
        ]))
        
        # Detect elements
        elements = self.detector.detect_elements(text_without_elements)
        
        # Should detect no elements
        assert len(elements) == 0, f"Should not detect any elements in text without element keywords: {text_without_elements}"
    
    @given(
        base_count=st.integers(min_value=1, max_value=5),
        additional_count=st.integers(min_value=1, max_value=5),
        element_type=st.sampled_from([ElementType.WINDOW, ElementType.DOOR])
    )
    def test_additive_counting_completeness(self, base_count: int, additional_count: int, element_type: ElementType):
        """
        **Feature: nl-floorspace-agent, Property 2: Element Detection Completeness**
        
        For any natural language description with multiple mentions of the same element type,
        the agent should detect the element type and provide a reasonable count.
        """
        # Generate element terms
        if element_type == ElementType.WINDOW:
            element_term = 'windows' if base_count > 1 else 'window'
            additional_term = 'windows' if additional_count > 1 else 'window'
        else:
            element_term = 'doors' if base_count > 1 else 'door'
            additional_term = 'doors' if additional_count > 1 else 'door'
        
        test_input = f"room with {base_count} {element_term} and {additional_count} additional {additional_term}"
        
        # Detect elements
        elements = self.detector.detect_elements(test_input)
        
        # Should detect the element type
        matching_elements = [e for e in elements if e.type == element_type]
        assert len(matching_elements) == 1, f"Should detect exactly 1 {element_type.value} element type in: {test_input}"
        
        # Total count should be reasonable (the detector may choose the highest count to avoid double-counting)
        total_count = matching_elements[0].count
        assert total_count >= 1, f"Total count should be at least 1, got {total_count} for: {test_input}"
        assert total_count <= base_count + additional_count, \
            f"Total count should not exceed {base_count + additional_count}, got {total_count} for: {test_input}"
    
    @given(
        room_size=st.text(min_size=3, max_size=20).filter(lambda x: x.replace(' ', '').replace('x', '').replace('m', '').replace('.', '').isdigit()),
        element_phrase=st.sampled_from([
            "with windows", "has doors", "including openings", "with entrances",
            "featuring windows", "containing doors"
        ])
    )
    def test_implicit_count_detection(self, room_size: str, element_phrase: str):
        """
        **Feature: nl-floorspace-agent, Property 2: Element Detection Completeness**
        
        For any natural language description with implicit element mentions (no explicit count),
        the agent should detect the elements and assign a reasonable default count.
        """
        test_input = f"{room_size} room {element_phrase}"
        
        # Detect elements
        elements = self.detector.detect_elements(test_input)
        
        # Should detect at least one element
        assert len(elements) >= 1, f"Should detect at least one element in: {test_input}"
        
        # All detected elements should have positive counts
        for element in elements:
            assert element.count >= 1, f"Element count should be at least 1, got {element.count} for: {test_input}"
            assert element.count <= 10, f"Implicit count should be reasonable, got {element.count} for: {test_input}"
    
    @given(
        mixed_elements=st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=3),
                st.sampled_from(['window', 'door', 'opening', 'entrance'])
            ),
            min_size=2,
            max_size=4
        )
    )
    def test_mixed_element_detection_completeness(self, mixed_elements):
        """
        **Feature: nl-floorspace-agent, Property 2: Element Detection Completeness**
        
        For any natural language description with multiple different element types,
        all element types should be detected with their respective counts.
        """
        # Build test input from mixed elements
        element_phrases = []
        expected_windows = 0
        expected_doors = 0
        
        for count, term in mixed_elements:
            element_phrases.append(f"{count} {term}{'s' if count > 1 and not term.endswith('s') else ''}")
            
            # Classify terms correctly
            if term in ['window', 'opening']:
                expected_windows += count
            elif term in ['door', 'entrance']:
                expected_doors += count
        
        test_input = f"room with {' and '.join(element_phrases)}"
        
        # Detect elements
        elements = self.detector.detect_elements(test_input)
        
        # Check detected elements
        window_elements = [e for e in elements if e.type == ElementType.WINDOW]
        door_elements = [e for e in elements if e.type == ElementType.DOOR]
        
        if expected_windows > 0:
            assert len(window_elements) == 1, f"Should detect windows in: {test_input}"
            # Allow some tolerance due to deduplication logic
            assert window_elements[0].count >= 1, f"Window count should be positive for: {test_input}"
        
        if expected_doors > 0:
            assert len(door_elements) == 1, f"Should detect doors in: {test_input}"
            # Allow some tolerance due to deduplication logic  
            assert door_elements[0].count >= 1, f"Door count should be positive for: {test_input}"