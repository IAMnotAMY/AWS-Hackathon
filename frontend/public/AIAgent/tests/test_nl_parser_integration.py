"""Tests for integrated natural language parser."""

import pytest
from hypothesis import given, strategies as st
from src.nl_floorspace_agent.parser.nl_parser import NaturalLanguageParser, ParseResult
from src.nl_floorspace_agent.models import SpaceRequirement, Dimensions, BuildingElement, ElementType, Units


class TestNaturalLanguageParserIntegration:
    """Unit tests for integrated natural language parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = NaturalLanguageParser()
    
    def test_parse_complete_room_description(self):
        """Test parsing a complete room description with dimensions and elements."""
        text = "Create a 5m x 4m bedroom with 2 windows and 1 door"
        result = self.parser.parse_space_description(text)
        
        assert result.is_valid, f"Parsing should succeed: {result.get_error_message()}"
        assert result.space_requirement is not None
        
        # Check dimensions
        dims = result.space_requirement.dimensions
        assert dims.width == 5.0
        assert dims.length == 4.0
        assert dims.units == Units.SI
        
        # Check elements
        elements = result.space_requirement.elements
        assert len(elements) == 2  # windows and doors
        
        window_element = next((e for e in elements if e.type == ElementType.WINDOW), None)
        door_element = next((e for e in elements if e.type == ElementType.DOOR), None)
        
        assert window_element is not None
        assert window_element.count == 2
        assert door_element is not None
        assert door_element.count == 1
        
        # Check room type
        assert result.space_requirement.room_type == "bedroom"
    
    def test_parse_dimensions_only(self):
        """Test parsing text with only dimensions."""
        text = "Make a 10ft by 8ft room"
        result = self.parser.parse_space_description(text)
        
        assert result.is_valid
        assert result.space_requirement is not None
        
        dims = result.space_requirement.dimensions
        assert dims.width == 10.0
        assert dims.length == 8.0
        assert dims.units == Units.IP
        
        # Should have no elements
        assert len(result.space_requirement.elements) == 0
        
        # Should default to generic room type
        assert result.space_requirement.room_type == "room"
    
    def test_parse_elements_only(self):
        """Test parsing text with only building elements."""
        text = "Kitchen with 3 windows and 2 doors"
        result = self.parser.parse_space_description(text)
        
        assert result.is_valid
        assert result.space_requirement is not None
        
        # Should use default dimensions
        dims = result.space_requirement.dimensions
        assert dims.width == 5.0
        assert dims.length == 4.0
        assert dims.units == Units.SI
        
        # Should have warning about default dimensions
        assert result.has_warnings
        assert any("default" in warning.lower() for warning in result.validation_result.warnings)
        
        # Check elements
        elements = result.space_requirement.elements
        assert len(elements) == 2
        
        window_element = next((e for e in elements if e.type == ElementType.WINDOW), None)
        door_element = next((e for e in elements if e.type == ElementType.DOOR), None)
        
        assert window_element.count == 3
        assert door_element.count == 2
        
        # Should recognize kitchen
        assert result.space_requirement.room_type == "kitchen"
    
    def test_parse_room_type_recognition(self):
        """Test recognition of different room types."""
        test_cases = [
            ("5m x 4m master bedroom", "bedroom"),
            ("3m x 3m bathroom with shower", "bathroom"),
            ("6m x 5m living room", "living_room"),
            ("4m x 3m home office", "office"),
            ("5m x 4m kitchen area", "kitchen"),
            ("2m x 2m closet space", "closet"),
            ("8m x 3m hallway", "hallway"),
        ]
        
        for text, expected_room_type in test_cases:
            result = self.parser.parse_space_description(text)
            assert result.is_valid, f"Should parse: {text}"
            assert result.space_requirement.room_type == expected_room_type, \
                f"Expected {expected_room_type}, got {result.space_requirement.room_type} for: {text}"
    
    def test_parse_with_synonyms(self):
        """Test parsing with room type and element synonyms."""
        text = "Create a 4m x 3m powder room with glazing and entrance"
        result = self.parser.parse_space_description(text)
        
        assert result.is_valid
        
        # powder room should be recognized as bathroom
        assert result.space_requirement.room_type == "bathroom"
        
        # Should detect elements (glazing=window, entrance=door)
        elements = result.space_requirement.elements
        assert len(elements) >= 1  # Should detect at least some elements
    
    def test_parse_invalid_input(self):
        """Test parsing invalid input."""
        invalid_inputs = [
            "",  # Empty
            "   ",  # Whitespace only
            "x",  # Too short
            "room with -5m width",  # Negative dimensions
            "room with 1000m x 1000m",  # Unreasonably large
        ]
        
        for text in invalid_inputs:
            result = self.parser.parse_space_description(text)
            assert not result.is_valid, f"Should reject invalid input: {text}"
            assert len(result.validation_result.errors) > 0
    
    def test_parse_result_structure(self):
        """Test that ParseResult has correct structure."""
        text = "5m x 4m bedroom with window"
        result = self.parser.parse_space_description(text)
        
        # Check ParseResult attributes
        assert hasattr(result, 'space_requirement')
        assert hasattr(result, 'validation_result')
        assert hasattr(result, 'raw_text')
        assert hasattr(result, 'terminology_matches')
        assert hasattr(result, 'extracted_dimensions')
        assert hasattr(result, 'extracted_elements')
        
        # Check properties
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'has_warnings')
        
        # Check methods
        assert callable(result.get_error_message)
        
        assert result.raw_text == text
        assert result.extracted_dimensions is not None
        assert len(result.extracted_elements) > 0
        assert len(result.terminology_matches) > 0
    
    def test_simple_interface_backward_compatibility(self):
        """Test the simple interface for backward compatibility."""
        text = "5m x 4m bedroom"
        
        # Should work without exceptions
        space_req = self.parser.parse_space_description_simple(text)
        assert isinstance(space_req, SpaceRequirement)
        assert space_req.dimensions.width == 5.0
        assert space_req.room_type == "bedroom"
        
        # Should raise exception for invalid input
        with pytest.raises(ValueError):
            self.parser.parse_space_description_simple("")
    
    def test_component_methods(self):
        """Test individual component methods."""
        text = "5m x 4m bedroom with 2 windows"
        
        # Test dimension extraction only
        dims, dim_validation = self.parser.extract_dimensions_only(text)
        assert dims is not None
        assert dims.width == 5.0
        assert dim_validation.is_valid
        
        # Test element detection only
        elements, elem_validation = self.parser.detect_elements_only(text)
        assert len(elements) > 0
        assert elem_validation.is_valid
        
        # Test terminology recognition only
        terminology = self.parser.recognize_terminology_only(text)
        assert len(terminology) > 0
        
        # Test input validation only
        validation = self.parser.validate_input_only(text)
        assert validation.is_valid
    
    def test_parsing_summary(self):
        """Test detailed parsing summary."""
        text = "Create a 5m x 4m master bedroom with 2 windows on north wall"
        summary = self.parser.get_parsing_summary(text)
        
        # Check summary structure
        required_keys = [
            "input_text", "is_valid", "has_warnings", "extracted_dimensions",
            "extracted_elements", "recognized_terminology", "room_type",
            "errors", "warnings"
        ]
        
        for key in required_keys:
            assert key in summary, f"Summary should contain {key}"
        
        assert summary["input_text"] == text
        assert summary["is_valid"] is True
        assert summary["extracted_dimensions"] is not None
        assert len(summary["extracted_elements"]) > 0
        assert len(summary["recognized_terminology"]) > 0
        assert summary["room_type"] == "bedroom"
    
    def test_utility_methods(self):
        """Test utility methods."""
        # Test can_parse_text
        assert self.parser.can_parse_text("5m x 4m room")
        assert not self.parser.can_parse_text("")
        
        # Test get_supported_* methods
        room_types = self.parser.get_supported_room_types()
        assert isinstance(room_types, list)
        assert "bedroom" in room_types
        assert "kitchen" in room_types
        
        element_types = self.parser.get_supported_element_types()
        assert isinstance(element_types, list)
        assert "window" in element_types
        assert "door" in element_types
        
        units = self.parser.get_supported_units()
        assert isinstance(units, list)
        assert "si" in units
        assert "ip" in units
    
    def test_complex_descriptions(self):
        """Test parsing complex room descriptions."""
        complex_texts = [
            "Design a spacious 8m by 6m master bedroom with walk-in closet, featuring 3 large windows on the south wall and 2 doors",
            "Create a modern 4m x 5m kitchen with island, including 4 windows for natural light and main entrance",
            "Build a cozy 3m by 4m home office study with built-in bookshelves, 2 windows facing east, and side door",
            "Plan a luxurious 6m x 7m living room with fireplace, 5 windows for panoramic views, and french doors to patio"
        ]
        
        for text in complex_texts:
            result = self.parser.parse_space_description(text)
            assert result.is_valid, f"Should parse complex description: {text[:50]}..."
            assert result.space_requirement is not None
            assert result.space_requirement.dimensions is not None
            
            # Should recognize some room type
            assert result.space_requirement.room_type is not None
            assert result.space_requirement.room_type != ""
    
    def test_error_handling_robustness(self):
        """Test that parser handles various edge cases gracefully."""
        edge_cases = [
            "room",  # Minimal input
            "5m room",  # Single dimension
            "bedroom with windows",  # No specific counts
            "large space",  # Vague description
            "5.5m x 3.2m area",  # Decimal dimensions
            "10 foot by 8 foot room",  # Spelled out units
        ]
        
        for text in edge_cases:
            result = self.parser.parse_space_description(text)
            # Should either succeed or fail gracefully with clear errors
            if not result.is_valid:
                assert len(result.validation_result.errors) > 0
                error_msg = result.get_error_message()
                assert isinstance(error_msg, str)
                assert len(error_msg) > 0


class TestNaturalLanguageParserProperties:
    """
    **Feature: nl-floorspace-agent, Property 14: Natural Language Parser Integration**
    **Validates: Requirements 1.1, 1.2, 1.3, 1.5**
    
    Property-based tests for integrated natural language parser.
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = NaturalLanguageParser()
    
    @given(
        width=st.floats(min_value=1.0, max_value=50.0),
        length=st.floats(min_value=1.0, max_value=50.0),
        unit=st.sampled_from(['m', 'ft', 'meters', 'feet'])
    )
    def test_dimension_parsing_consistency(self, width: float, length: float, unit: str):
        """
        **Feature: nl-floorspace-agent, Property 14: Natural Language Parser Integration**
        
        For any valid dimensions, the parser should extract them correctly.
        """
        text = f"{width:.1f}{unit} x {length:.1f}{unit} room"
        result = self.parser.parse_space_description(text)
        
        if result.is_valid:
            dims = result.space_requirement.dimensions
            # Allow for small floating point differences
            assert abs(dims.width - width) < 0.1, f"Width mismatch for: {text}"
            assert abs(dims.length - length) < 0.1, f"Length mismatch for: {text}"
    
    @given(
        room_type=st.sampled_from(['bedroom', 'kitchen', 'bathroom', 'office', 'living room']),
        window_count=st.integers(min_value=0, max_value=10),
        door_count=st.integers(min_value=0, max_value=5)
    )
    def test_element_detection_consistency(self, room_type: str, window_count: int, door_count: int):
        """
        **Feature: nl-floorspace-agent, Property 14: Natural Language Parser Integration**
        
        For any room with specified elements, the parser should detect them correctly.
        """
        # Build text with elements
        text_parts = [f"5m x 4m {room_type}"]
        
        if window_count > 0:
            text_parts.append(f"{window_count} windows")
        if door_count > 0:
            text_parts.append(f"{door_count} doors")
        
        text = " with ".join(text_parts)
        result = self.parser.parse_space_description(text)
        
        if result.is_valid and result.space_requirement:
            elements = result.space_requirement.elements
            
            # Check window count
            window_elements = [e for e in elements if e.type == ElementType.WINDOW]
            if window_count > 0:
                assert len(window_elements) > 0, f"Should detect windows in: {text}"
                assert window_elements[0].count == window_count, f"Window count mismatch in: {text}"
            
            # Check door count
            door_elements = [e for e in elements if e.type == ElementType.DOOR]
            if door_count > 0:
                assert len(door_elements) > 0, f"Should detect doors in: {text}"
                assert door_elements[0].count == door_count, f"Door count mismatch in: {text}"
    
    @given(
        room_type=st.sampled_from(['bedroom', 'kitchen', 'bathroom', 'living room', 'office']),
        prefix=st.sampled_from(['', 'large ', 'small ', 'spacious ', 'cozy ']),
        suffix=st.sampled_from(['', ' area', ' space', ' room'])
    )
    def test_room_type_recognition_robustness(self, room_type: str, prefix: str, suffix: str):
        """
        **Feature: nl-floorspace-agent, Property 14: Natural Language Parser Integration**
        
        For any room type with modifiers, the parser should recognize the base room type.
        """
        text = f"5m x 4m {prefix}{room_type}{suffix}"
        result = self.parser.parse_space_description(text)
        
        if result.is_valid and result.space_requirement:
            recognized_type = result.space_requirement.room_type
            
            # Should recognize the base room type or a reasonable mapping
            expected_mappings = {
                'bedroom': 'bedroom',
                'kitchen': 'kitchen', 
                'bathroom': 'bathroom',
                'living room': 'living_room',
                'office': 'office'
            }
            
            expected = expected_mappings.get(room_type, room_type)
            assert recognized_type == expected, f"Room type mismatch for: {text}"
    
    @given(
        text_input=st.text(min_size=1, max_size=50)
    )
    def test_parsing_never_crashes(self, text_input: str):
        """
        **Feature: nl-floorspace-agent, Property 14: Natural Language Parser Integration**
        
        For any text input, the parser should never crash and always return a result.
        """
        try:
            result = self.parser.parse_space_description(text_input)
            
            # Should always return a ParseResult
            assert isinstance(result, ParseResult)
            assert hasattr(result, 'is_valid')
            assert hasattr(result, 'validation_result')
            
            # If invalid, should have error messages
            if not result.is_valid:
                assert len(result.validation_result.errors) > 0
                
        except Exception as e:
            pytest.fail(f"Parser crashed on input '{text_input}': {e}")
    
    @given(
        valid_input=st.sampled_from([
            "5m x 4m bedroom",
            "10ft by 8ft kitchen with 2 windows",
            "3m x 3m bathroom with door",
            "6m by 5m living room with 3 windows and 2 doors"
        ])
    )
    def test_valid_input_always_succeeds(self, valid_input: str):
        """
        **Feature: nl-floorspace-agent, Property 14: Natural Language Parser Integration**
        
        For any known valid input, parsing should always succeed.
        """
        result = self.parser.parse_space_description(valid_input)
        
        assert result.is_valid, f"Should parse valid input: {valid_input}"
        assert result.space_requirement is not None
        assert result.space_requirement.dimensions is not None
        
        # Dimensions should be positive
        dims = result.space_requirement.dimensions
        assert dims.width > 0
        assert dims.length > 0
    
    @given(
        invalid_input=st.sampled_from([
            "",  # Empty
            "   ",  # Whitespace
            "x",  # Too short
            "invalid text without dimensions or elements"
        ])
    )
    def test_invalid_input_always_fails_gracefully(self, invalid_input: str):
        """
        **Feature: nl-floorspace-agent, Property 14: Natural Language Parser Integration**
        
        For any known invalid input, parsing should fail gracefully with clear errors.
        """
        result = self.parser.parse_space_description(invalid_input)
        
        assert not result.is_valid, f"Should reject invalid input: {invalid_input}"
        assert len(result.validation_result.errors) > 0
        
        # Should provide meaningful error message
        error_msg = result.get_error_message()
        assert isinstance(error_msg, str)
        assert len(error_msg) > 0
        assert "issue" in error_msg.lower() or "error" in error_msg.lower()