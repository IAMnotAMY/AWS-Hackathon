"""Natural language parser for spatial descriptions."""

from typing import List, Optional, Tuple
from ..models import SpaceRequirement, Dimensions, BuildingElement, Units, ElementType
from .dimension_extractor import DimensionExtractor
from .element_detector import ElementDetector
from .terminology import TerminologyRecognizer, RoomType
from .validation import InputValidator, ValidationResult, ValidationError


class ParseResult:
    """Result of parsing natural language input."""
    
    def __init__(self, space_requirement: Optional[SpaceRequirement] = None, 
                 validation_result: Optional[ValidationResult] = None,
                 raw_text: str = ""):
        """Initialize parse result.
        
        Args:
            space_requirement: Parsed space requirement (None if parsing failed)
            validation_result: Validation result with errors/warnings
            raw_text: Original input text
        """
        self.space_requirement = space_requirement
        self.validation_result = validation_result or ValidationResult(is_valid=True, errors=[])
        self.raw_text = raw_text
        self.terminology_matches = []
        self.extracted_dimensions = None
        self.extracted_elements = []
    
    @property
    def is_valid(self) -> bool:
        """Check if parsing was successful."""
        return self.space_requirement is not None and self.validation_result.is_valid
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.validation_result.warnings) > 0
    
    @property
    def elements(self) -> List[BuildingElement]:
        """Get extracted building elements."""
        return self.extracted_elements if self.extracted_elements else []

    def get_error_message(self) -> str:
        """Get formatted error message."""
        if self.validation_result:
            return InputValidator().format_error_message(self.validation_result)
        return "Unknown parsing error occurred."


class NaturalLanguageParser:
    """Parses natural language descriptions into structured requirements."""
    
    def __init__(self):
        """Initialize the parser with all component parsers."""
        self.dimension_extractor = DimensionExtractor()
        self.element_detector = ElementDetector()
        self.terminology_recognizer = TerminologyRecognizer()
        self.validator = InputValidator()
    
    def parse_space_description(self, text: str) -> ParseResult:
        """Parse a natural language description into a SpaceRequirement.
        
        Args:
            text: Natural language description of the space
            
        Returns:
            ParseResult containing the parsed space requirement and validation info
        """
        # Create parse result to track the process
        result = ParseResult(raw_text=text)
        
        # Step 1: Validate input text
        text_validation = self.validator.validate_input_text(text)
        if not text_validation.is_valid:
            result.validation_result = text_validation
            return result
        
        # Step 2: Extract dimensions
        dimensions, dim_validation = self.dimension_extractor.extract_dimensions_with_validation(text)
        result.extracted_dimensions = dimensions
        
        # Step 3: Detect building elements
        elements, elem_validation = self.element_detector.detect_elements_with_validation(text)
        result.extracted_elements = elements
        
        # Step 4: Recognize terminology (room type, directions, etc.)
        terminology_matches = self.terminology_recognizer.recognize_all_terminology(text)
        result.terminology_matches = terminology_matches
        
        # Step 5: Extract room type from terminology
        room_type = self.terminology_recognizer.get_room_type(text)
        room_type_str = room_type.value if room_type else "room"
        
        # Step 6: Comprehensive validation of the parsing result
        comprehensive_validation = self.validator.validate_parsing_result(text, dimensions, elements)
        
        # Combine all validation results
        all_errors = []
        all_warnings = []
        
        # Add dimension validation errors if dimensions were found but invalid
        if dimensions and not dim_validation.is_valid:
            all_errors.extend(dim_validation.errors)
            all_warnings.extend(dim_validation.warnings)
        
        # Add element validation errors if elements were found but invalid
        if elements and not elem_validation.is_valid:
            all_errors.extend(elem_validation.errors)
            all_warnings.extend(elem_validation.warnings)
        
        # Add comprehensive validation results
        all_errors.extend(comprehensive_validation.errors)
        all_warnings.extend(comprehensive_validation.warnings)
        
        # Create final validation result
        final_validation = ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
        
        result.validation_result = final_validation
        
        # Step 7: Create SpaceRequirement if parsing was successful
        if final_validation.is_valid and (dimensions or elements):
            # Use default dimensions if none were found but elements were detected
            if not dimensions and elements:
                # Create reasonable default dimensions
                dimensions = Dimensions(width=5.0, length=4.0, units=Units.SI)
                all_warnings.append("No dimensions specified, using default 5m x 4m room size")
                final_validation.warnings = all_warnings
            
            # Create the space requirement
            space_requirement = SpaceRequirement(
                dimensions=dimensions,
                elements=elements,
                room_type=room_type_str
            )
            
            result.space_requirement = space_requirement
        
        return result
    
    def parse_space_description_simple(self, text: str) -> SpaceRequirement:
        """Parse a natural language description into a SpaceRequirement (simple interface).
        
        This method provides backward compatibility and a simpler interface.
        For detailed error handling, use parse_space_description() instead.
        
        Args:
            text: Natural language description of the space
            
        Returns:
            SpaceRequirement object with extracted information
            
        Raises:
            ValueError: If parsing fails or input is invalid
        """
        result = self.parse_space_description(text)
        
        if not result.is_valid:
            error_message = result.get_error_message()
            raise ValueError(f"Failed to parse space description: {error_message}")
        
        return result.space_requirement
    
    def extract_dimensions_only(self, text: str) -> Tuple[Optional[Dimensions], ValidationResult]:
        """Extract only dimensions from text.
        
        Args:
            text: Natural language text
            
        Returns:
            Tuple of (dimensions, validation_result)
        """
        return self.dimension_extractor.extract_dimensions_with_validation(text)
    
    def detect_elements_only(self, text: str) -> Tuple[List[BuildingElement], ValidationResult]:
        """Detect only building elements from text.
        
        Args:
            text: Natural language text
            
        Returns:
            Tuple of (elements, validation_result)
        """
        return self.element_detector.detect_elements_with_validation(text)
    
    def recognize_terminology_only(self, text: str) -> List:
        """Recognize only terminology from text.
        
        Args:
            text: Natural language text
            
        Returns:
            List of terminology matches
        """
        return self.terminology_recognizer.recognize_all_terminology(text)
    
    def validate_input_only(self, text: str) -> ValidationResult:
        """Validate only the input text.
        
        Args:
            text: Natural language text
            
        Returns:
            ValidationResult
        """
        return self.validator.validate_input_text(text)
    
    def get_parsing_summary(self, text: str) -> dict:
        """Get a detailed summary of what was parsed from the text.
        
        Args:
            text: Natural language text
            
        Returns:
            Dictionary with parsing details
        """
        result = self.parse_space_description(text)
        
        summary = {
            "input_text": text,
            "is_valid": result.is_valid,
            "has_warnings": result.has_warnings,
            "extracted_dimensions": None,
            "extracted_elements": [],
            "recognized_terminology": [],
            "room_type": None,
            "errors": [error.message for error in result.validation_result.errors],
            "warnings": result.validation_result.warnings
        }
        
        # Add dimensions info
        if result.extracted_dimensions:
            summary["extracted_dimensions"] = {
                "width": result.extracted_dimensions.width,
                "length": result.extracted_dimensions.length,
                "height": result.extracted_dimensions.height,
                "units": result.extracted_dimensions.units.value
            }
        
        # Add elements info
        for element in result.extracted_elements:
            element_info = {
                "type": element.type.value,
                "count": element.count
            }
            if element.specifications:
                element_info["specifications"] = {
                    "width": element.specifications.width,
                    "height": element.specifications.height,
                    "wall": element.specifications.wall,
                    "alpha": element.specifications.alpha
                }
            summary["extracted_elements"].append(element_info)
        
        # Add terminology info
        for match in result.terminology_matches:
            summary["recognized_terminology"].append({
                "original_text": match.original_text,
                "normalized_term": match.normalized_term,
                "category": match.category,
                "confidence": match.confidence
            })
        
        # Add room type
        if result.space_requirement:
            summary["room_type"] = result.space_requirement.room_type
        
        return summary
    
    def can_parse_text(self, text: str) -> bool:
        """Check if the text can be successfully parsed.
        
        Args:
            text: Natural language text
            
        Returns:
            True if text can be parsed successfully
        """
        try:
            result = self.parse_space_description(text)
            return result.is_valid
        except Exception:
            return False
    
    def get_supported_room_types(self) -> List[str]:
        """Get list of supported room types.
        
        Returns:
            List of supported room type strings
        """
        return [room_type.value for room_type in RoomType]
    
    def get_supported_element_types(self) -> List[str]:
        """Get list of supported building element types.
        
        Returns:
            List of supported element type strings
        """
        return [element_type.value for element_type in ElementType]
    
    def get_supported_units(self) -> List[str]:
        """Get list of supported unit systems.
        
        Returns:
            List of supported unit system strings
        """
        return [units.value for units in Units]