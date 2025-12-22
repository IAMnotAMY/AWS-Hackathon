"""Input validation and error handling for natural language parsing."""

from typing import Optional, List, Tuple
from dataclasses import dataclass
from ..models import Dimensions, BuildingElement, ElementType, Units


@dataclass
class ValidationError:
    """Represents a validation error with details."""
    message: str
    error_type: str
    suggested_fix: Optional[str] = None
    invalid_value: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class InputValidator:
    """Validates natural language input and extracted data."""
    
    def __init__(self):
        """Initialize the validator."""
        # Reasonable dimension limits (in base units)
        self.dimension_limits = {
            Units.SI: {  # meters
                'min_room_dimension': 0.5,  # 50cm minimum
                'max_room_dimension': 100.0,  # 100m maximum
                'min_window_dimension': 0.2,  # 20cm minimum
                'max_window_dimension': 10.0,  # 10m maximum
                'min_door_dimension': 0.5,  # 50cm minimum
                'max_door_dimension': 5.0,  # 5m maximum
            },
            Units.IP: {  # feet
                'min_room_dimension': 1.5,  # 1.5ft minimum
                'max_room_dimension': 300.0,  # 300ft maximum
                'min_window_dimension': 0.5,  # 0.5ft minimum
                'max_window_dimension': 30.0,  # 30ft maximum
                'min_door_dimension': 1.5,  # 1.5ft minimum
                'max_door_dimension': 15.0,  # 15ft maximum
            }
        }
    
    def validate_input_text(self, text: str) -> ValidationResult:
        """Validate raw natural language input.
        
        Args:
            text: Natural language input text
            
        Returns:
            ValidationResult with any issues found
        """
        errors = []
        warnings = []
        
        # Check for empty or whitespace-only input
        if not text or not text.strip():
            errors.append(ValidationError(
                message="Input cannot be empty",
                error_type="empty_input",
                suggested_fix="Please provide a description of the space you want to create"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Check for extremely short input
        if len(text.strip()) < 3:
            errors.append(ValidationError(
                message="Input is too short to be meaningful",
                error_type="insufficient_input",
                suggested_fix="Please provide more details about the space (e.g., dimensions, room type)"
            ))
        
        # Check for extremely long input
        if len(text) > 1000:
            warnings.append("Input is very long. Consider breaking it into smaller, more specific requests.")
        
        # Check for potentially problematic characters
        if any(char in text for char in ['<', '>', '{', '}', '[', ']']):
            warnings.append("Input contains special characters that might not be processed correctly.")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_dimensions(self, dimensions: Dimensions, context: str = "room") -> ValidationResult:
        """Validate extracted dimensions.
        
        Args:
            dimensions: Extracted dimensions to validate
            context: Context for validation (room, window, door)
            
        Returns:
            ValidationResult with any issues found
        """
        errors = []
        warnings = []
        
        # Get appropriate limits based on context and units
        limits = self.dimension_limits[dimensions.units]
        
        if context == "room":
            min_dim = limits['min_room_dimension']
            max_dim = limits['max_room_dimension']
        elif context == "window":
            min_dim = limits['min_window_dimension']
            max_dim = limits['max_window_dimension']
        elif context == "door":
            min_dim = limits['min_door_dimension']
            max_dim = limits['max_door_dimension']
        else:
            min_dim = limits['min_room_dimension']
            max_dim = limits['max_room_dimension']
        
        unit_name = "meters" if dimensions.units == Units.SI else "feet"
        
        # Validate width
        if dimensions.width <= 0:
            errors.append(ValidationError(
                message=f"Width must be positive, got {dimensions.width}",
                error_type="invalid_dimension",
                suggested_fix=f"Please provide a positive width value in {unit_name}",
                invalid_value=str(dimensions.width)
            ))
        elif dimensions.width < min_dim:
            errors.append(ValidationError(
                message=f"Width {dimensions.width} {unit_name} is too small for a {context}",
                error_type="dimension_too_small",
                suggested_fix=f"Minimum {context} width is {min_dim} {unit_name}",
                invalid_value=str(dimensions.width)
            ))
        elif dimensions.width > max_dim:
            errors.append(ValidationError(
                message=f"Width {dimensions.width} {unit_name} is unreasonably large for a {context}",
                error_type="dimension_too_large",
                suggested_fix=f"Maximum reasonable {context} width is {max_dim} {unit_name}",
                invalid_value=str(dimensions.width)
            ))
        
        # Validate length
        if dimensions.length <= 0:
            errors.append(ValidationError(
                message=f"Length must be positive, got {dimensions.length}",
                error_type="invalid_dimension",
                suggested_fix=f"Please provide a positive length value in {unit_name}",
                invalid_value=str(dimensions.length)
            ))
        elif dimensions.length < min_dim:
            errors.append(ValidationError(
                message=f"Length {dimensions.length} {unit_name} is too small for a {context}",
                error_type="dimension_too_small",
                suggested_fix=f"Minimum {context} length is {min_dim} {unit_name}",
                invalid_value=str(dimensions.length)
            ))
        elif dimensions.length > max_dim:
            errors.append(ValidationError(
                message=f"Length {dimensions.length} {unit_name} is unreasonably large for a {context}",
                error_type="dimension_too_large",
                suggested_fix=f"Maximum reasonable {context} length is {max_dim} {unit_name}",
                invalid_value=str(dimensions.length)
            ))
        
        # Validate height if provided
        if dimensions.height is not None:
            if dimensions.height <= 0:
                errors.append(ValidationError(
                    message=f"Height must be positive, got {dimensions.height}",
                    error_type="invalid_dimension",
                    suggested_fix=f"Please provide a positive height value in {unit_name}",
                    invalid_value=str(dimensions.height)
                ))
            elif dimensions.height < min_dim:
                errors.append(ValidationError(
                    message=f"Height {dimensions.height} {unit_name} is too small for a {context}",
                    error_type="dimension_too_small",
                    suggested_fix=f"Minimum {context} height is {min_dim} {unit_name}",
                    invalid_value=str(dimensions.height)
                ))
            elif dimensions.height > max_dim:
                errors.append(ValidationError(
                    message=f"Height {dimensions.height} {unit_name} is unreasonably large for a {context}",
                    error_type="dimension_too_large",
                    suggested_fix=f"Maximum reasonable {context} height is {max_dim} {unit_name}",
                    invalid_value=str(dimensions.height)
                ))
        
        # Check for reasonable aspect ratios
        if dimensions.width > 0 and dimensions.length > 0:
            aspect_ratio = max(dimensions.width, dimensions.length) / min(dimensions.width, dimensions.length)
            if aspect_ratio > 20:
                warnings.append(f"Unusual aspect ratio ({aspect_ratio:.1f}:1). Very long, narrow {context}s can be difficult to use.")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_elements(self, elements: List[BuildingElement]) -> ValidationResult:
        """Validate detected building elements.
        
        Args:
            elements: List of detected building elements
            
        Returns:
            ValidationResult with any issues found
        """
        errors = []
        warnings = []
        
        for element in elements:
            # Validate element count
            if element.count <= 0:
                errors.append(ValidationError(
                    message=f"{element.type.value.title()} count must be positive, got {element.count}",
                    error_type="invalid_count",
                    suggested_fix="Please specify a positive number of elements",
                    invalid_value=str(element.count)
                ))
            elif element.count > 50:
                warnings.append(f"Very high {element.type.value} count ({element.count}). Consider if this is realistic.")
            
            # Validate element specifications if provided
            if element.specifications:
                spec = element.specifications
                
                # Create dimensions for validation if width/height are specified
                if spec.width is not None and spec.height is not None:
                    element_dims = Dimensions(
                        width=spec.width,
                        length=spec.height,  # Use height as length for validation
                        units=Units.SI  # Assume SI for now
                    )
                    
                    context = "window" if element.type == ElementType.WINDOW else "door"
                    spec_validation = self.validate_dimensions(element_dims, context)
                    
                    # Add any dimension validation errors
                    errors.extend(spec_validation.errors)
                    warnings.extend(spec_validation.warnings)
                
                # Validate alpha positioning
                if spec.alpha is not None:
                    if not (0 <= spec.alpha <= 1):
                        errors.append(ValidationError(
                            message=f"Element position (alpha) must be between 0 and 1, got {spec.alpha}",
                            error_type="invalid_position",
                            suggested_fix="Position should be a decimal between 0 (start of wall) and 1 (end of wall)",
                            invalid_value=str(spec.alpha)
                        ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_parsing_result(self, text: str, dimensions: Optional[Dimensions], 
                              elements: List[BuildingElement]) -> ValidationResult:
        """Validate the complete parsing result.
        
        Args:
            text: Original input text
            dimensions: Extracted dimensions (None if not found)
            elements: Extracted elements
            
        Returns:
            ValidationResult with comprehensive validation
        """
        errors = []
        warnings = []
        
        # Validate input text
        text_validation = self.validate_input_text(text)
        errors.extend(text_validation.errors)
        warnings.extend(text_validation.warnings)
        
        # If text validation failed, don't continue
        if not text_validation.is_valid:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Check if we found any meaningful content
        if dimensions is None and len(elements) == 0:
            errors.append(ValidationError(
                message="Could not extract any spatial information from the input",
                error_type="no_content_extracted",
                suggested_fix="Please include room dimensions (e.g., '5m x 4m') and/or building elements (windows, doors)"
            ))
        
        # Validate dimensions if found
        if dimensions is not None:
            dim_validation = self.validate_dimensions(dimensions, "room")
            errors.extend(dim_validation.errors)
            warnings.extend(dim_validation.warnings)
        
        # Validate elements if found
        if elements:
            element_validation = self.validate_elements(elements)
            errors.extend(element_validation.errors)
            warnings.extend(element_validation.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def format_error_message(self, validation_result: ValidationResult) -> str:
        """Format validation errors into a user-friendly message.
        
        Args:
            validation_result: Result from validation
            
        Returns:
            Formatted error message string
        """
        if validation_result.is_valid:
            return "Input is valid."
        
        message_parts = ["I found some issues with your input:"]
        
        for i, error in enumerate(validation_result.errors, 1):
            message_parts.append(f"{i}. {error.message}")
            if error.suggested_fix:
                message_parts.append(f"   → {error.suggested_fix}")
        
        if validation_result.warnings:
            message_parts.append("\nAdditional notes:")
            for warning in validation_result.warnings:
                message_parts.append(f"• {warning}")
        
        return "\n".join(message_parts)