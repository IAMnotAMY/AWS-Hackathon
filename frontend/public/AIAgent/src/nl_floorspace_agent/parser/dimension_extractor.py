"""Dimension extraction from natural language."""

import re
from typing import Optional, Tuple, List, Dict
from ..models import Dimensions, Units
from .validation import InputValidator, ValidationResult


class DimensionExtractor:
    """Extracts spatial dimensions from natural language text."""
    
    def __init__(self):
        """Initialize the dimension extractor."""
        self.validator = InputValidator()
        
        # Unit conversion patterns and mappings
        self.unit_patterns = {
            # Metric units
            'meters': Units.SI,
            'meter': Units.SI,
            'metres': Units.SI,
            'metre': Units.SI,
            'm': Units.SI,
            'cm': Units.SI,
            'centimeters': Units.SI,
            'centimetres': Units.SI,
            'mm': Units.SI,
            'millimeters': Units.SI,
            'millimetres': Units.SI,
            
            # Imperial units
            'feet': Units.IP,
            'foot': Units.IP,
            'ft': Units.IP,
            'inches': Units.IP,
            'inch': Units.IP,
            'in': Units.IP,
            "'": Units.IP,  # foot symbol
            '"': Units.IP,  # inch symbol
        }
        
        # Conversion factors to base units (meters for SI, feet for IP)
        self.unit_conversions = {
            # SI conversions to meters
            'm': 1.0,
            'meters': 1.0,
            'meter': 1.0,
            'metres': 1.0,
            'metre': 1.0,
            'cm': 0.01,
            'centimeters': 0.01,
            'centimetres': 0.01,
            'mm': 0.001,
            'millimeters': 0.001,
            'millimetres': 0.001,
            
            # IP conversions to feet
            'feet': 1.0,
            'foot': 1.0,
            'ft': 1.0,
            "'": 1.0,
            'inches': 1.0/12.0,
            'inch': 1.0/12.0,
            'in': 1.0/12.0,
            '"': 1.0/12.0,
        }
    
    def extract_dimensions_with_validation(self, text: str) -> Tuple[Optional[Dimensions], ValidationResult]:
        """Extract dimensions from text with validation.
        
        Args:
            text: Natural language text containing dimensions
            
        Returns:
            Tuple of (Dimensions object or None, ValidationResult)
        """
        # First validate the input text
        text_validation = self.validator.validate_input_text(text)
        if not text_validation.is_valid:
            return None, text_validation
        
        text = text.lower().strip()
        
        # Try different dimension patterns
        dimensions = self._extract_by_x_pattern(text)
        if not dimensions:
            dimensions = self._extract_width_length_pattern(text)
        if not dimensions:
            dimensions = self._extract_single_dimension_pattern(text)
        
        if dimensions:
            # Validate the extracted dimensions
            validation_result = self.validator.validate_dimensions(dimensions, "room")
            return dimensions, validation_result
        else:
            # No dimensions found
            from .validation import ValidationError
            validation_result = ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    message="Could not find any dimensions in the input",
                    error_type="no_dimensions_found",
                    suggested_fix="Please include dimensions like '5m x 4m' or 'width 5 meters length 4 meters'"
                )],
                warnings=[]
            )
            return None, validation_result
    
    def extract_dimensions(self, text: str) -> Optional[Dimensions]:
        """Extract dimensions from text (backward compatibility method).
        
        Args:
            text: Natural language text containing dimensions
            
        Returns:
            Dimensions object or None if no dimensions found
        """
        dimensions, _ = self.extract_dimensions_with_validation(text)
        return dimensions
    
    def _extract_by_x_pattern(self, text: str) -> Optional[Dimensions]:
        """Extract dimensions from 'X by Y' or 'X x Y' patterns."""
        # Pattern for "5m x 4m", "10 feet by 8 feet", "3.5m by 2.7m", etc.
        patterns = [
            r'(\d+(?:\.\d+)?)\s*([a-z\'\"]+)?\s*(?:x|by)\s*(\d+(?:\.\d+)?)\s*([a-z\'\"]+)?',
            r'(\d+(?:\.\d+)?)\s*([a-z\'\"]+)?\s*[×]\s*(\d+(?:\.\d+)?)\s*([a-z\'\"]+)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                width_val, width_unit, length_val, length_unit = match.groups()
                
                # Convert to float
                try:
                    width = float(width_val)
                    length = float(length_val)
                except ValueError:
                    continue
                
                # Determine units
                unit = self._determine_unit(width_unit or length_unit)
                
                # Convert to base units
                width = self._convert_to_base_unit(width, width_unit, unit)
                length = self._convert_to_base_unit(length, length_unit, unit)
                
                if width > 0 and length > 0:
                    return Dimensions(width=width, length=length, units=unit)
        
        return None
    
    def _extract_width_length_pattern(self, text: str) -> Optional[Dimensions]:
        """Extract dimensions from 'width X, length Y' patterns."""
        width_match = re.search(r'width\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*([a-z\'\"]+)?', text)
        length_match = re.search(r'length\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*([a-z\'\"]+)?', text)
        
        if width_match and length_match:
            try:
                width_val = float(width_match.group(1))
                length_val = float(length_match.group(1))
                
                width_unit = width_match.group(2)
                length_unit = length_match.group(2)
                
                # Determine units
                unit = self._determine_unit(width_unit or length_unit)
                
                # Convert to base units
                width = self._convert_to_base_unit(width_val, width_unit, unit)
                length = self._convert_to_base_unit(length_val, length_unit, unit)
                
                if width > 0 and length > 0:
                    return Dimensions(width=width, length=length, units=unit)
            except ValueError:
                pass
        
        return None
    
    def _extract_single_dimension_pattern(self, text: str) -> Optional[Dimensions]:
        """Extract dimensions from single dimension mentions (assume square)."""
        # Pattern for "5 meter room", "10ft space", etc.
        pattern = r'(\d+(?:\.\d+)?)\s*([a-z\'\"]+)?\s*(?:room|space|area)'
        match = re.search(pattern, text)
        
        if match:
            try:
                dimension_val = float(match.group(1))
                unit_str = match.group(2)
                
                # Determine units
                unit = self._determine_unit(unit_str)
                
                # Convert to base units
                dimension = self._convert_to_base_unit(dimension_val, unit_str, unit)
                
                if dimension > 0:
                    # Assume square room
                    return Dimensions(width=dimension, length=dimension, units=unit)
            except ValueError:
                pass
        
        return None
    
    def _determine_unit(self, unit_str: Optional[str]) -> Units:
        """Determine the unit system from a unit string."""
        if not unit_str:
            return Units.SI  # Default to metric
        
        unit_str = unit_str.lower().strip()
        return self.unit_patterns.get(unit_str, Units.SI)
    
    def _convert_to_base_unit(self, value: float, unit_str: Optional[str], target_unit: Units) -> float:
        """Convert a value to the base unit of the target unit system."""
        if not unit_str:
            return value  # No conversion needed
        
        unit_str = unit_str.lower().strip()
        conversion_factor = self.unit_conversions.get(unit_str, 1.0)
        
        return value * conversion_factor
    
    def validate_dimensions(self, dimensions: Dimensions) -> bool:
        """Validate that dimensions are positive and reasonable."""
        if dimensions.width <= 0 or dimensions.length <= 0:
            return False
        
        if dimensions.height is not None and dimensions.height <= 0:
            return False
        
        # Check for reasonable maximum values (100m or 300ft)
        max_dimension = 100.0 if dimensions.units == Units.SI else 300.0
        
        if (dimensions.width > max_dimension or 
            dimensions.length > max_dimension or 
            (dimensions.height is not None and dimensions.height > max_dimension)):
            return False
        
        return True