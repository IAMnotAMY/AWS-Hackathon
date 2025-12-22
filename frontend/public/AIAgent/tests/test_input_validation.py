"""Tests for input validation and error handling functionality."""

import pytest
from hypothesis import given, strategies as st
from src.nl_floorspace_agent.parser.validation import InputValidator, ValidationError, ValidationResult
from src.nl_floorspace_agent.parser.dimension_extractor import DimensionExtractor
from src.nl_floorspace_agent.parser.element_detector import ElementDetector
from src.nl_floorspace_agent.models import Dimensions, Units, BuildingElement, ElementType, ElementSpec


class TestInputValidation:
    """
    **Feature: nl-floorspace-agent, Property 3: Input Validation**
    **Validates: Requirements 1.5, 6.1**
    
    Tests for input validation and error handling.
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.dimension_extractor = DimensionExtractor()
        self.element_detector = ElementDetector()
    
    def test_empty_input_validation(self):
        """Test validation of empty input."""
        result = self.validator.validate_input_text("")
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "empty_input"
        assert "empty" in result.errors[0].message.lower()
    
    def test_whitespace_only_input_validation(self):
        """Test validation of whitespace-only input."""
        result = self.validator.validate_input_text("   \n\t  ")
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "empty_input"
    
    def test_too_short_input_validation(self):
        """Test validation of very short input."""
        result = self.validator.validate_input_text("hi")
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "insufficient_input"
    
    def test_valid_input_text(self):
        """Test validation of valid input text."""
        result = self.validator.validate_input_text("5m x 4m room with windows")
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_negative_dimension_validation(self):
        """Test validation rejects negative dimensions."""
        dimensions = Dimensions(width=-5.0, length=4.0, units=Units.SI)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert not result.is_valid
        assert any(error.error_type == "invalid_dimension" for error in result.errors)
        assert any("positive" in error.message.lower() for error in result.errors)
    
    def test_zero_dimension_validation(self):
        """Test validation rejects zero dimensions."""
        dimensions = Dimensions(width=0.0, length=4.0, units=Units.SI)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert not result.is_valid
        assert any(error.error_type == "invalid_dimension" for error in result.errors)
    
    def test_too_small_dimension_validation(self):
        """Test validation rejects unreasonably small dimensions."""
        dimensions = Dimensions(width=0.1, length=4.0, units=Units.SI)  # 10cm width
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert not result.is_valid
        assert any(error.error_type == "dimension_too_small" for error in result.errors)
    
    def test_too_large_dimension_validation(self):
        """Test validation rejects unreasonably large dimensions."""
        dimensions = Dimensions(width=200.0, length=4.0, units=Units.SI)  # 200m width
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert not result.is_valid
        assert any(error.error_type == "dimension_too_large" for error in result.errors)
    
    def test_valid_dimensions(self):
        """Test validation accepts reasonable dimensions."""
        dimensions = Dimensions(width=5.0, length=4.0, units=Units.SI)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_context_specific_validation(self):
        """Test that validation limits vary by context."""
        # Window dimensions that are valid for windows but not rooms
        window_dims = Dimensions(width=0.3, length=0.4, units=Units.SI)  # 30cm x 40cm
        
        window_result = self.validator.validate_dimensions(window_dims, "window")
        room_result = self.validator.validate_dimensions(window_dims, "room")
        
        assert window_result.is_valid
        assert not room_result.is_valid  # Too small for a room
    
    def test_element_count_validation(self):
        """Test validation of element counts."""
        # Valid element
        valid_element = BuildingElement(type=ElementType.WINDOW, count=2)
        result = self.validator.validate_elements([valid_element])
        assert result.is_valid
        
        # Invalid element (zero count)
        invalid_element = BuildingElement(type=ElementType.WINDOW, count=0)
        result = self.validator.validate_elements([invalid_element])
        assert not result.is_valid
        assert any(error.error_type == "invalid_count" for error in result.errors)
    
    def test_element_specification_validation(self):
        """Test validation of element specifications."""
        # Element with invalid alpha position
        spec = ElementSpec(width=1.0, height=1.5, alpha=1.5)  # Alpha > 1
        element = BuildingElement(type=ElementType.WINDOW, count=1, specifications=spec)
        
        result = self.validator.validate_elements([element])
        assert not result.is_valid
        assert any(error.error_type == "invalid_position" for error in result.errors)
    
    def test_dimension_extractor_with_validation(self):
        """Test dimension extractor with validation enabled."""
        # Valid input
        dimensions, validation = self.dimension_extractor.extract_dimensions_with_validation("5m x 4m room")
        assert dimensions is not None
        assert validation.is_valid
        
        # Invalid input (empty)
        dimensions, validation = self.dimension_extractor.extract_dimensions_with_validation("")
        assert dimensions is None
        assert not validation.is_valid
        
        # Input with no dimensions
        dimensions, validation = self.dimension_extractor.extract_dimensions_with_validation("just a room")
        assert dimensions is None
        assert not validation.is_valid
        assert any(error.error_type == "no_dimensions_found" for error in validation.errors)
    
    def test_element_detector_with_validation(self):
        """Test element detector with validation enabled."""
        # Valid input
        elements, validation = self.element_detector.detect_elements_with_validation("room with 2 windows")
        assert len(elements) == 1
        assert validation.is_valid
        
        # Invalid input (empty)
        elements, validation = self.element_detector.detect_elements_with_validation("")
        assert len(elements) == 0
        assert not validation.is_valid
    
    def test_error_message_formatting(self):
        """Test error message formatting."""
        # Create a validation result with errors
        errors = [
            ValidationError(
                message="Width must be positive",
                error_type="invalid_dimension",
                suggested_fix="Please provide a positive width value"
            ),
            ValidationError(
                message="Height is too large",
                error_type="dimension_too_large",
                suggested_fix="Maximum height is 10 meters"
            )
        ]
        warnings = ["This is a warning"]
        
        result = ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        formatted_message = self.validator.format_error_message(result)
        
        assert "I found some issues" in formatted_message
        assert "Width must be positive" in formatted_message
        assert "Please provide a positive width value" in formatted_message
        assert "Height is too large" in formatted_message
        assert "This is a warning" in formatted_message
    
    def test_backward_compatibility(self):
        """Test that old methods still work without validation."""
        # Old dimension extraction method should still work
        dimensions = self.dimension_extractor.extract_dimensions("5m x 4m room")
        assert dimensions is not None
        assert dimensions.width == 5.0
        assert dimensions.length == 4.0
        
        # Old element detection method should still work
        elements = self.element_detector.detect_elements("room with 2 windows")
        assert len(elements) == 1
        assert elements[0].count == 2
    
    @given(
        width=st.floats(min_value=-100, max_value=-0.1),
        length=st.floats(min_value=0.1, max_value=50.0)
    )
    def test_negative_dimensions_always_invalid(self, width: float, length: float):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any dimensions with negative values, validation should always fail.
        """
        dimensions = Dimensions(width=width, length=length, units=Units.SI)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert not result.is_valid
        assert any(error.error_type == "invalid_dimension" for error in result.errors)
        assert any("positive" in error.message.lower() for error in result.errors)
    
    @given(
        count=st.integers(min_value=-100, max_value=0)
    )
    def test_non_positive_element_counts_invalid(self, count: int):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any element count that is zero or negative, validation should fail.
        """
        element = BuildingElement(type=ElementType.WINDOW, count=count)
        result = self.validator.validate_elements([element])
        
        assert not result.is_valid
        assert any(error.error_type == "invalid_count" for error in result.errors)
    
    @given(
        alpha=st.floats(min_value=-10.0, max_value=-0.1) | st.floats(min_value=1.1, max_value=10.0)
    )
    def test_invalid_alpha_positions_rejected(self, alpha: float):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any alpha position outside the range [0, 1], validation should fail.
        """
        spec = ElementSpec(alpha=alpha)
        element = BuildingElement(type=ElementType.WINDOW, count=1, specifications=spec)
        result = self.validator.validate_elements([element])
        
        assert not result.is_valid
        assert any(error.error_type == "invalid_position" for error in result.errors)


class TestErrorHandling:
    """Tests for graceful error handling in parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dimension_extractor = DimensionExtractor()
        self.element_detector = ElementDetector()
    
    def test_graceful_handling_of_unparseable_input(self):
        """Test graceful handling of input that cannot be parsed."""
        # Input with no spatial information
        dimensions, validation = self.dimension_extractor.extract_dimensions_with_validation("hello world")
        
        assert dimensions is None
        assert not validation.is_valid
        assert any("dimensions" in error.message.lower() for error in validation.errors)
        assert any(error.suggested_fix is not None for error in validation.errors)
    
    def test_clear_error_messages(self):
        """Test that error messages are clear and helpful."""
        # Test with empty input
        dimensions, validation = self.dimension_extractor.extract_dimensions_with_validation("")
        
        assert not validation.is_valid
        error_message = validation.errors[0].message
        suggested_fix = validation.errors[0].suggested_fix
        
        # Error message should be clear
        assert len(error_message) > 10  # Not just a code
        assert "empty" in error_message.lower()
        
        # Should provide helpful suggestion
        assert suggested_fix is not None
        assert len(suggested_fix) > 10
    
    def test_validation_maintains_state(self):
        """Test that validation errors don't break the parser state."""
        # First, try invalid input
        dimensions1, validation1 = self.dimension_extractor.extract_dimensions_with_validation("")
        assert dimensions1 is None
        assert not validation1.is_valid
        
        # Then, try valid input - should work normally
        dimensions2, validation2 = self.dimension_extractor.extract_dimensions_with_validation("5m x 4m")
        assert dimensions2 is not None
        assert validation2.is_valid
        assert dimensions2.width == 5.0
        assert dimensions2.length == 4.0


class TestInputValidationProperties:
    """
    **Feature: nl-floorspace-agent, Property 3: Input Validation**
    **Validates: Requirements 1.5, 6.1**
    
    Property-based tests for comprehensive input validation.
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.dimension_extractor = DimensionExtractor()
        self.element_detector = ElementDetector()
    
    @given(
        width=st.floats(min_value=-1000.0, max_value=-0.001),
        length=st.floats(min_value=0.1, max_value=100.0),
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_negative_width_always_rejected(self, width: float, length: float, units: Units):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any dimensions with negative width, validation should always reject the input
        and provide clear error messages requesting valid values.
        """
        dimensions = Dimensions(width=width, length=length, units=units)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        # Should always be invalid
        assert not result.is_valid, f"Negative width {width} should be rejected"
        
        # Should have at least one error
        assert len(result.errors) >= 1, "Should have validation errors for negative width"
        
        # Should have an error about invalid dimensions
        dimension_errors = [e for e in result.errors if e.error_type == "invalid_dimension"]
        assert len(dimension_errors) >= 1, "Should have invalid_dimension error type"
        
        # Error message should mention positive values
        error_messages = " ".join([e.message.lower() for e in result.errors])
        assert "positive" in error_messages, "Error message should mention positive values"
        
        # Should provide suggested fix
        suggested_fixes = [e.suggested_fix for e in result.errors if e.suggested_fix]
        assert len(suggested_fixes) >= 1, "Should provide suggested fixes"
    
    @given(
        width=st.floats(min_value=0.1, max_value=100.0),
        length=st.floats(min_value=-1000.0, max_value=-0.001),
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_negative_length_always_rejected(self, width: float, length: float, units: Units):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any dimensions with negative length, validation should always reject the input
        and provide clear error messages requesting valid values.
        """
        dimensions = Dimensions(width=width, length=length, units=units)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        # Should always be invalid
        assert not result.is_valid, f"Negative length {length} should be rejected"
        
        # Should have at least one error about invalid dimensions
        dimension_errors = [e for e in result.errors if e.error_type == "invalid_dimension"]
        assert len(dimension_errors) >= 1, "Should have invalid_dimension error type"
        
        # Should provide helpful error message
        error_messages = " ".join([e.message.lower() for e in result.errors])
        assert "positive" in error_messages, "Error message should mention positive values"
    
    @given(
        width=st.just(0.0),
        length=st.floats(min_value=0.1, max_value=100.0),
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_zero_width_always_rejected(self, width: float, length: float, units: Units):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any dimensions with zero width, validation should always reject the input.
        """
        dimensions = Dimensions(width=width, length=length, units=units)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert not result.is_valid, "Zero width should be rejected"
        assert any(e.error_type == "invalid_dimension" for e in result.errors)
    
    @given(
        width=st.floats(min_value=0.1, max_value=100.0),
        length=st.just(0.0),
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_zero_length_always_rejected(self, width: float, length: float, units: Units):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any dimensions with zero length, validation should always reject the input.
        """
        dimensions = Dimensions(width=width, length=length, units=units)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert not result.is_valid, "Zero length should be rejected"
        assert any(e.error_type == "invalid_dimension" for e in result.errors)
    
    @given(
        width=st.floats(min_value=0.1, max_value=100.0),
        length=st.floats(min_value=0.1, max_value=100.0),
        height=st.floats(min_value=-1000.0, max_value=-0.001),
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_negative_height_always_rejected(self, width: float, length: float, height: float, units: Units):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any dimensions with negative height, validation should always reject the input.
        """
        dimensions = Dimensions(width=width, length=length, height=height, units=units)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert not result.is_valid, f"Negative height {height} should be rejected"
        assert any(e.error_type == "invalid_dimension" for e in result.errors)
    
    @given(
        width=st.floats(min_value=2.0, max_value=50.0),  # Safe for both SI (>0.5m) and IP (>1.5ft)
        length=st.floats(min_value=2.0, max_value=50.0),  # Safe for both SI (>0.5m) and IP (>1.5ft)
        units=st.sampled_from([Units.SI, Units.IP])
    )
    def test_reasonable_dimensions_always_accepted(self, width: float, length: float, units: Units):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any dimensions within reasonable ranges, validation should always accept the input.
        """
        dimensions = Dimensions(width=width, length=length, units=units)
        result = self.validator.validate_dimensions(dimensions, "room")
        
        assert result.is_valid, f"Reasonable dimensions {width}x{length} {units.value} should be accepted"
        assert len(result.errors) == 0, "Should have no validation errors for reasonable dimensions"
    
    @given(
        count=st.integers(min_value=-100, max_value=0)
    )
    def test_non_positive_element_counts_always_rejected(self, count: int):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any element count that is zero or negative, validation should always reject it
        and provide clear error messages.
        """
        element = BuildingElement(type=ElementType.WINDOW, count=count)
        result = self.validator.validate_elements([element])
        
        assert not result.is_valid, f"Non-positive count {count} should be rejected"
        
        # Should have invalid_count error
        count_errors = [e for e in result.errors if e.error_type == "invalid_count"]
        assert len(count_errors) >= 1, "Should have invalid_count error type"
        
        # Error message should mention positive count
        error_messages = " ".join([e.message.lower() for e in result.errors])
        assert "positive" in error_messages, "Error message should mention positive values"
    
    @given(
        count=st.integers(min_value=1, max_value=20)
    )
    def test_positive_element_counts_always_accepted(self, count: int):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any positive element count within reasonable range, validation should accept it.
        """
        element = BuildingElement(type=ElementType.WINDOW, count=count)
        result = self.validator.validate_elements([element])
        
        assert result.is_valid, f"Positive count {count} should be accepted"
        assert len(result.errors) == 0, "Should have no validation errors for positive counts"
    
    @given(
        alpha=st.floats(min_value=-10.0, max_value=-0.001) | st.floats(min_value=1.001, max_value=10.0)
    )
    def test_invalid_alpha_positions_always_rejected(self, alpha: float):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any alpha position outside [0, 1], validation should always reject it.
        """
        spec = ElementSpec(alpha=alpha)
        element = BuildingElement(type=ElementType.WINDOW, count=1, specifications=spec)
        result = self.validator.validate_elements([element])
        
        assert not result.is_valid, f"Alpha position {alpha} outside [0,1] should be rejected"
        
        # Should have invalid_position error
        position_errors = [e for e in result.errors if e.error_type == "invalid_position"]
        assert len(position_errors) >= 1, "Should have invalid_position error type"
    
    @given(
        alpha=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_valid_alpha_positions_always_accepted(self, alpha: float):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any alpha position within [0, 1], validation should accept it.
        """
        spec = ElementSpec(alpha=alpha)
        element = BuildingElement(type=ElementType.WINDOW, count=1, specifications=spec)
        result = self.validator.validate_elements([element])
        
        assert result.is_valid, f"Valid alpha position {alpha} should be accepted"
        assert len(result.errors) == 0, "Should have no validation errors for valid alpha"
    
    @given(
        text=st.text(min_size=0, max_size=2).filter(lambda x: x.strip() == "")
    )
    def test_empty_or_whitespace_text_always_rejected(self, text: str):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any empty or whitespace-only text, validation should always reject it.
        """
        result = self.validator.validate_input_text(text)
        
        assert not result.is_valid, f"Empty/whitespace text '{text}' should be rejected"
        
        # Should have empty_input error
        empty_errors = [e for e in result.errors if e.error_type == "empty_input"]
        assert len(empty_errors) >= 1, "Should have empty_input error type"
    
    @given(
        text=st.text(min_size=5, max_size=500).filter(lambda x: len(x.strip()) >= 5)
    )
    def test_reasonable_text_always_accepted(self, text: str):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any reasonable text input, validation should accept it.
        """
        result = self.validator.validate_input_text(text)
        
        assert result.is_valid, f"Reasonable text should be accepted: {text[:50]}..."
        assert len(result.errors) == 0, "Should have no validation errors for reasonable text"
    
    @given(
        width=st.floats(min_value=0.1, max_value=50.0),
        length=st.floats(min_value=0.1, max_value=50.0),
        context=st.sampled_from(["room", "window", "door"])
    )
    def test_context_specific_validation_consistency(self, width: float, length: float, context: str):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any valid dimensions, validation results should be consistent with context-specific rules.
        """
        dimensions = Dimensions(width=width, length=length, units=Units.SI)
        result = self.validator.validate_dimensions(dimensions, context)
        
        # Get the appropriate limits for this context
        limits = self.validator.dimension_limits[Units.SI]
        if context == "room":
            min_dim = limits['min_room_dimension']
            max_dim = limits['max_room_dimension']
        elif context == "window":
            min_dim = limits['min_window_dimension']
            max_dim = limits['max_window_dimension']
        elif context == "door":
            min_dim = limits['min_door_dimension']
            max_dim = limits['max_door_dimension']
        
        # Check if dimensions should be valid based on limits
        should_be_valid = (
            width >= min_dim and width <= max_dim and
            length >= min_dim and length <= max_dim
        )
        
        if should_be_valid:
            assert result.is_valid, f"Dimensions {width}x{length} should be valid for {context}"
        else:
            # If outside limits, should be invalid
            if width < min_dim or length < min_dim:
                assert not result.is_valid, f"Dimensions {width}x{length} too small for {context}"
                assert any(e.error_type == "dimension_too_small" for e in result.errors)
            elif width > max_dim or length > max_dim:
                assert not result.is_valid, f"Dimensions {width}x{length} too large for {context}"
                assert any(e.error_type == "dimension_too_large" for e in result.errors)
    
    @given(
        invalid_input=st.sampled_from([
            "",  # empty
            "   ",  # whitespace
            "hi",  # too short
            "no dimensions here",  # no spatial info
            "just some random text without any useful content"
        ])
    )
    def test_invalid_inputs_provide_helpful_suggestions(self, invalid_input: str):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any invalid input, validation should provide helpful suggestions for fixing the issue.
        """
        # Test dimension extraction with validation
        dimensions, validation = self.dimension_extractor.extract_dimensions_with_validation(invalid_input)
        
        assert dimensions is None, "Should not extract dimensions from invalid input"
        assert not validation.is_valid, "Validation should fail for invalid input"
        
        # Should provide helpful suggestions
        has_suggestions = any(error.suggested_fix is not None for error in validation.errors)
        assert has_suggestions, "Should provide suggested fixes for invalid input"
        
        # Suggestions should be meaningful (not empty)
        suggestions = [error.suggested_fix for error in validation.errors if error.suggested_fix]
        for suggestion in suggestions:
            assert len(suggestion) > 10, f"Suggestion should be meaningful: {suggestion}"
    
    @given(
        valid_input=st.sampled_from([
            "5m x 4m room",
            "10 feet by 8 feet bedroom",
            "3.5m by 2.7m office with windows",
            "12ft x 10ft living room with 2 doors",
            "width 6 meters length 5 meters kitchen"
        ])
    )
    def test_valid_inputs_extract_successfully(self, valid_input: str):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any valid input with dimensions, validation should succeed and extract dimensions.
        """
        dimensions, validation = self.dimension_extractor.extract_dimensions_with_validation(valid_input)
        
        assert dimensions is not None, f"Should extract dimensions from valid input: {valid_input}"
        assert validation.is_valid, f"Validation should succeed for valid input: {valid_input}"
        assert len(validation.errors) == 0, "Should have no validation errors for valid input"
        
        # Extracted dimensions should be positive
        assert dimensions.width > 0, "Extracted width should be positive"
        assert dimensions.length > 0, "Extracted length should be positive"
    
    @given(
        error_count=st.integers(min_value=1, max_value=5),
        warning_count=st.integers(min_value=0, max_value=3)
    )
    def test_error_message_formatting_completeness(self, error_count: int, warning_count: int):
        """
        **Feature: nl-floorspace-agent, Property 3: Input Validation**
        
        For any validation result with errors and warnings, formatted messages should be complete and helpful.
        """
        # Create mock errors and warnings
        errors = []
        for i in range(error_count):
            errors.append(ValidationError(
                message=f"Test error {i+1}",
                error_type="test_error",
                suggested_fix=f"Fix suggestion {i+1}"
            ))
        
        warnings = [f"Test warning {i+1}" for i in range(warning_count)]
        
        result = ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        formatted_message = self.validator.format_error_message(result)
        
        # Should contain all errors
        for error in errors:
            assert error.message in formatted_message, f"Should contain error message: {error.message}"
            if error.suggested_fix:
                assert error.suggested_fix in formatted_message, f"Should contain suggestion: {error.suggested_fix}"
        
        # Should contain all warnings
        for warning in warnings:
            assert warning in formatted_message, f"Should contain warning: {warning}"
        
        # Should have proper structure
        assert "I found some issues" in formatted_message, "Should have introductory text"
        if warnings:
            assert "Additional notes" in formatted_message or "notes:" in formatted_message.lower(), "Should have warning section"