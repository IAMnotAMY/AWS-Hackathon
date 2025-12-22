"""Property-based tests for dimension parsing functionality.

**Feature: nl-floorspace-agent, Property 1: Natural Language Parsing Accuracy**
**Validates: Requirements 1.1, 1.2**
"""

import pytest
from hypothesis import given, strategies as st, assume
import re
from typing import Tuple

from src.nl_floorspace_agent.parser.dimension_extractor import DimensionExtractor
from src.nl_floorspace_agent.models import Dimensions, Units


class TestDimensionParsingProperties:
    """Property-based tests for dimension parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = DimensionExtractor()
    
    @given(
        width=st.floats(min_value=0.1, max_value=50.0),
        length=st.floats(min_value=0.1, max_value=50.0),
        unit=st.sampled_from(['m', 'meters', 'ft', 'feet', 'cm'])
    )
    def test_dimension_extraction_accuracy_x_pattern(self, width: float, length: float, unit: str):
        """
        **Feature: nl-floorspace-agent, Property 1: Natural Language Parsing Accuracy**
        
        For any natural language description containing spatial dimensions in 'X by Y' format,
        the agent should extract dimensions that match the embedded values within acceptable tolerance.
        """
        # Format to 2 decimal places to preserve more precision
        formatted_width = f"{width:.2f}"
        formatted_length = f"{length:.2f}"
        test_input = f"{formatted_width}{unit} x {formatted_length}{unit} room"
        
        # Extract dimensions
        result = self.extractor.extract_dimensions(test_input)
        
        # Should successfully extract dimensions
        assert result is not None, f"Failed to extract dimensions from: {test_input}"
        
        # Determine expected unit system
        expected_units = Units.IP if unit in ['ft', 'feet'] else Units.SI
        assert result.units == expected_units
        
        # The expected values should match what was actually formatted
        formatted_width_val = float(formatted_width)
        formatted_length_val = float(formatted_length)
        
        # Convert expected values to base units for comparison
        if unit == 'cm':
            expected_width = formatted_width_val * 0.01
            expected_length = formatted_length_val * 0.01
        elif unit in ['ft', 'feet']:
            expected_width = formatted_width_val
            expected_length = formatted_length_val
        else:  # meters
            expected_width = formatted_width_val
            expected_length = formatted_length_val
        
        # Check extracted values match within tolerance (0.01 units for precision)
        tolerance = 0.01
        assert abs(result.width - expected_width) <= tolerance, \
            f"Width mismatch: expected {expected_width}, got {result.width}, input: {test_input}"
        
        tolerance = 0.01
        assert abs(result.length - expected_length) <= tolerance, \
            f"Length mismatch: expected {expected_length}, got {result.length}, input: {test_input}"
    
    @given(
        width=st.floats(min_value=0.1, max_value=50.0),
        length=st.floats(min_value=0.1, max_value=50.0),
        unit=st.sampled_from(['m', 'meters', 'ft', 'feet'])
    )
    def test_dimension_extraction_accuracy_by_pattern(self, width: float, length: float, unit: str):
        """
        **Feature: nl-floorspace-agent, Property 1: Natural Language Parsing Accuracy**
        
        For any natural language description containing spatial dimensions in 'X by Y' format,
        the agent should extract dimensions that match the embedded values within acceptable tolerance.
        """
        # Format to 2 decimal places to preserve more precision
        formatted_width = f"{width:.2f}"
        formatted_length = f"{length:.2f}"
        test_input = f"{formatted_width} {unit} by {formatted_length} {unit}"
        
        # Extract dimensions
        result = self.extractor.extract_dimensions(test_input)
        
        # Should successfully extract dimensions
        assert result is not None, f"Failed to extract dimensions from: {test_input}"
        
        # Determine expected unit system
        expected_units = Units.IP if unit in ['ft', 'feet'] else Units.SI
        assert result.units == expected_units
        
        # The expected values should match what was actually formatted
        formatted_width_val = float(formatted_width)
        formatted_length_val = float(formatted_length)
        
        # Expected values are already in base units for these unit types
        expected_width = formatted_width_val
        expected_length = formatted_length_val
        
        # Check extracted values match within tolerance (0.01 units for precision)
        tolerance = 0.01
        assert abs(result.width - expected_width) <= tolerance, \
            f"Width mismatch: expected {expected_width}, got {result.width}, input: {test_input}"
        
        tolerance = 0.01
        assert abs(result.length - expected_length) <= tolerance, \
            f"Length mismatch: expected {expected_length}, got {result.length}, input: {test_input}"
    
    @given(
        width=st.floats(min_value=0.1, max_value=50.0),
        length=st.floats(min_value=0.1, max_value=50.0),
        width_unit=st.sampled_from(['m', 'meters', 'ft']),
        length_unit=st.sampled_from(['m', 'meters', 'ft'])
    )
    def test_dimension_extraction_width_length_pattern(self, width: float, length: float, 
                                                     width_unit: str, length_unit: str):
        """
        **Feature: nl-floorspace-agent, Property 1: Natural Language Parsing Accuracy**
        
        For any natural language description with separate width and length specifications,
        the agent should extract both dimensions correctly.
        """
        # Format to 2 decimal places to preserve more precision
        formatted_width = f"{width:.2f}"
        formatted_length = f"{length:.2f}"
        test_input = f"width {formatted_width} {width_unit} length {formatted_length} {length_unit}"
        
        # Extract dimensions
        result = self.extractor.extract_dimensions(test_input)
        
        # Should successfully extract dimensions
        assert result is not None, f"Failed to extract dimensions from: {test_input}"
        
        # Determine expected unit system (use first unit found)
        expected_units = Units.IP if width_unit == 'ft' else Units.SI
        
        # The expected values should match what was actually formatted
        formatted_width_val = float(formatted_width)
        formatted_length_val = float(formatted_length)
        
        # Convert expected values to base units
        expected_width = formatted_width_val
        expected_length = formatted_length_val
        
        # Check extracted values match within tolerance
        tolerance = 0.01
        assert abs(result.width - expected_width) <= tolerance, \
            f"Width mismatch: expected {expected_width}, got {result.width}, input: {test_input}"
        
        tolerance = 0.01
        assert abs(result.length - expected_length) <= tolerance, \
            f"Length mismatch: expected {expected_length}, got {result.length}, input: {test_input}"
    
    @given(
        dimension=st.floats(min_value=0.1, max_value=50.0),
        unit=st.sampled_from(['m', 'meter', 'ft', 'foot']),
        room_type=st.sampled_from(['room', 'space', 'area'])
    )
    def test_single_dimension_square_assumption(self, dimension: float, unit: str, room_type: str):
        """
        **Feature: nl-floorspace-agent, Property 1: Natural Language Parsing Accuracy**
        
        For any natural language description with a single dimension,
        the agent should assume a square room and extract equal width and length.
        """
        # Format to 2 decimal places to preserve more precision
        formatted_dimension = f"{dimension:.2f}"
        test_input = f"{formatted_dimension} {unit} {room_type}"
        
        # Extract dimensions
        result = self.extractor.extract_dimensions(test_input)
        
        # Should successfully extract dimensions
        assert result is not None, f"Failed to extract dimensions from: {test_input}"
        
        # Should assume square room (width == length)
        assert result.width == result.length, \
            f"Single dimension should create square room: width={result.width}, length={result.length}"
        
        # The expected value should match what was actually formatted
        formatted_dimension_val = float(formatted_dimension)
        
        # Check extracted value matches within tolerance
        expected_dimension = formatted_dimension_val
        tolerance = 0.01
        assert abs(result.width - expected_dimension) <= tolerance, \
            f"Dimension mismatch: expected {expected_dimension}, got {result.width}, input: {test_input}"
    
    @given(
        text=st.text(min_size=1, max_size=100).filter(
            lambda x: not re.search(r'\d+(?:\.\d+)?', x)
        )
    )
    def test_no_dimensions_returns_none(self, text: str):
        """
        **Feature: nl-floorspace-agent, Property 1: Natural Language Parsing Accuracy**
        
        For any natural language description without numeric dimensions,
        the agent should return None.
        """
        # Ensure text doesn't contain numbers
        assume(not re.search(r'\d+(?:\.\d+)?', text))
        
        # Extract dimensions
        result = self.extractor.extract_dimensions(text)
        
        # Should return None for text without dimensions
        assert result is None, f"Should return None for text without dimensions: {text}"
    
    def test_validation_rejects_invalid_dimensions(self):
        """
        **Feature: nl-floorspace-agent, Property 1: Natural Language Parsing Accuracy**
        
        The validation should reject dimensions that are zero, negative, or unreasonably large.
        """
        # Test zero dimensions
        zero_dims = Dimensions(width=0.0, length=5.0, units=Units.SI)
        assert not self.extractor.validate_dimensions(zero_dims)
        
        # Test negative dimensions
        negative_dims = Dimensions(width=-1.0, length=5.0, units=Units.SI)
        assert not self.extractor.validate_dimensions(negative_dims)
        
        # Test unreasonably large dimensions (SI)
        large_dims_si = Dimensions(width=200.0, length=5.0, units=Units.SI)
        assert not self.extractor.validate_dimensions(large_dims_si)
        
        # Test unreasonably large dimensions (IP)
        large_dims_ip = Dimensions(width=500.0, length=5.0, units=Units.IP)
        assert not self.extractor.validate_dimensions(large_dims_ip)
        
        # Test valid dimensions
        valid_dims = Dimensions(width=5.0, length=4.0, units=Units.SI)
        assert self.extractor.validate_dimensions(valid_dims)


class TestDimensionParsingExamples:
    """Example-based tests for specific dimension parsing cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = DimensionExtractor()
    
    def test_common_dimension_formats(self):
        """Test common dimension format examples."""
        test_cases = [
            ("5m x 4m room", 5.0, 4.0, Units.SI),
            ("10 feet by 8 feet", 10.0, 8.0, Units.IP),
            ("3.5m by 2.7m", 3.5, 2.7, Units.SI),
            ("12ft x 10ft", 12.0, 10.0, Units.IP),
            ("width 5m length 4m", 5.0, 4.0, Units.SI),
            ("6 meter room", 6.0, 6.0, Units.SI),
        ]
        
        for text, expected_width, expected_length, expected_units in test_cases:
            result = self.extractor.extract_dimensions(text)
            assert result is not None, f"Failed to parse: {text}"
            assert abs(result.width - expected_width) < 0.01
            assert abs(result.length - expected_length) < 0.01
            assert result.units == expected_units
    
    def test_unit_conversion_examples(self):
        """Test unit conversion examples."""
        # Test centimeter conversion
        result = self.extractor.extract_dimensions("500cm x 400cm")
        assert result is not None
        assert abs(result.width - 5.0) < 0.01  # 500cm = 5m
        assert abs(result.length - 4.0) < 0.01  # 400cm = 4m
        assert result.units == Units.SI
        
        # Test inch conversion
        result = self.extractor.extract_dimensions("120in x 96in")
        assert result is not None
        assert abs(result.width - 10.0) < 0.01  # 120in = 10ft
        assert abs(result.length - 8.0) < 0.01   # 96in = 8ft
        assert result.units == Units.IP