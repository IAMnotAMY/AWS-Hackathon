"""Clarification question generation."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from ..models import SpaceRequirement, BuildingElement, ElementType, ElementSpec, Question

logger = logging.getLogger(__name__)


class ClarificationGenerator:
    """Generates clarification questions for incomplete specifications."""
    
    def __init__(self):
        """Initialize the clarification generator."""
        self.wall_options = ["north", "south", "east", "west"]
        self.common_window_sizes = [
            (1.2, 1.5),  # Standard window
            (0.8, 1.2),  # Small window
            (1.5, 1.8),  # Large window
            (2.0, 1.5),  # Wide window
        ]
        self.common_door_sizes = [
            (0.8, 2.0),  # Standard door
            (0.9, 2.1),  # Wide door
            (1.2, 2.1),  # Double door
            (0.7, 2.0),  # Narrow door
        ]
    
    def generate_questions(self, requirement: SpaceRequirement) -> List[Question]:
        """Generate clarification questions for a space requirement.
        
        Args:
            requirement: The space requirement needing clarification
            
        Returns:
            List of question objects
        """
        questions = []
        
        try:
            for i, element in enumerate(requirement.elements):
                element_questions = self._generate_element_questions(element, i)
                questions.extend(element_questions)
            
            # Add placement questions if needed
            placement_questions = self._generate_placement_questions(requirement)
            questions.extend(placement_questions)
            
            logger.debug(f"Generated {len(questions)} clarification questions")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate clarification questions: {e}")
            return []
    
    def _generate_element_questions(self, element: BuildingElement, element_index: int) -> List[Question]:
        """Generate questions for a specific building element.
        
        Args:
            element: Building element needing clarification
            element_index: Index of the element in the list
            
        Returns:
            List of questions for this element
        """
        questions = []
        element_name = element.type.value
        element_id = f"{element_name}_{element_index}"
        
        # Check if specifications exist
        if element.specifications is None:
            # Need all specifications
            questions.extend(self._create_dimension_questions(element, element_id))
            questions.extend(self._create_placement_questions(element, element_id))
        else:
            spec = element.specifications
            
            # Check for missing dimensions
            if spec.width is None or spec.height is None:
                questions.extend(self._create_dimension_questions(element, element_id))
            
            # Check for missing wall placement
            if spec.wall is None:
                questions.extend(self._create_placement_questions(element, element_id))
            
            # Check for missing alpha positioning (optional)
            if spec.alpha is None and spec.wall is not None:
                questions.append(self._create_position_question(element, element_id))
        
        return questions
    
    def _create_dimension_questions(self, element: BuildingElement, element_id: str) -> List[Question]:
        """Create dimension-related questions for an element.
        
        Args:
            element: Building element
            element_id: Unique identifier for the element
            
        Returns:
            List of dimension questions
        """
        questions = []
        element_name = element.type.value
        count_text = f"the {element_name}" if element.count == 1 else f"each {element_name}"
        
        # Get common sizes for suggestions
        if element.type == ElementType.WINDOW:
            common_sizes = self.common_window_sizes
            size_examples = "1.2m x 1.5m (standard), 0.8m x 1.2m (small), 1.5m x 1.8m (large)"
        else:  # DOOR
            common_sizes = self.common_door_sizes
            size_examples = "0.8m x 2.0m (standard), 0.9m x 2.1m (wide), 1.2m x 2.1m (double)"
        
        # Create dimension question
        question_text = f"What are the dimensions for {count_text}? Please specify width x height in meters."
        if element.count > 1:
            question_text += f" (You have {element.count} {element_name}s - specify if they're all the same size or different)"
        
        question_text += f"\n\nCommon sizes: {size_examples}"
        
        dimension_question = Question(
            text=question_text,
            question_type="dimension",
            element_id=element_id,
            options=[f"{w}m x {h}m" for w, h in common_sizes[:3]],  # Top 3 common sizes
            required=True
        )
        
        questions.append(dimension_question)
        return questions
    
    def _create_placement_questions(self, element: BuildingElement, element_id: str) -> List[Question]:
        """Create wall placement questions for an element.
        
        Args:
            element: Building element
            element_id: Unique identifier for the element
            
        Returns:
            List of placement questions
        """
        questions = []
        element_name = element.type.value
        count_text = f"the {element_name}" if element.count == 1 else f"the {element_name}s"
        
        question_text = f"Which wall should {count_text} be placed on?"
        if element.count > 1:
            question_text += f" (You have {element.count} {element_name}s - specify wall for each or if they should be distributed)"
        
        placement_question = Question(
            text=question_text,
            question_type="placement",
            element_id=element_id,
            options=self.wall_options,
            required=True
        )
        
        questions.append(placement_question)
        return questions
    
    def _create_position_question(self, element: BuildingElement, element_id: str) -> Question:
        """Create position along wall question for an element.
        
        Args:
            element: Building element
            element_id: Unique identifier for the element
            
        Returns:
            Position question
        """
        element_name = element.type.value
        count_text = f"the {element_name}" if element.count == 1 else f"each {element_name}"
        
        question_text = f"Where along the wall should {count_text} be positioned? "
        question_text += "You can specify 'center', 'left', 'right', or a specific position (0.0 = start of wall, 1.0 = end of wall)."
        
        return Question(
            text=question_text,
            question_type="position",
            element_id=element_id,
            options=["center", "left", "right", "0.25 (quarter)", "0.75 (three-quarters)"],
            required=False  # Position is optional, defaults to center
        )
    
    def _generate_placement_questions(self, requirement: SpaceRequirement) -> List[Question]:
        """Generate space placement questions if needed.
        
        Args:
            requirement: Space requirement
            
        Returns:
            List of placement questions
        """
        questions = []
        
        # If no placement hint is provided, we might need to ask
        if requirement.placement is None:
            # This would typically be handled by the geometry generator
            # For now, we don't generate placement questions here
            pass
        
        return questions
    
    def parse_dimension_answer(self, answer: str) -> Optional[Tuple[float, float]]:
        """Parse a dimension answer into width and height.
        
        Args:
            answer: User's dimension answer
            
        Returns:
            Tuple of (width, height) in meters, or None if parsing fails
        """
        try:
            # Clean up the answer
            answer = answer.lower().strip()
            
            # Remove common words
            answer = answer.replace("meters", "m").replace("meter", "m")
            answer = answer.replace("by", "x").replace("×", "x").replace("*", "x")
            
            # Look for patterns like "1.2 x 1.5", "1.2m x 1.5m", etc.
            import re
            
            # Pattern for dimensions with optional units
            pattern = r'(\d+\.?\d*)\s*m?\s*x\s*(\d+\.?\d*)\s*m?'
            match = re.search(pattern, answer)
            
            if match:
                width = float(match.group(1))
                height = float(match.group(2))
                
                # Validate reasonable dimensions
                if 0.1 <= width <= 10.0 and 0.1 <= height <= 5.0:
                    return (width, height)
            
            # Try alternative patterns
            # Pattern for "width 1.2 height 1.5"
            width_pattern = r'width\s*:?\s*(\d+\.?\d*)'
            height_pattern = r'height\s*:?\s*(\d+\.?\d*)'
            
            width_match = re.search(width_pattern, answer)
            height_match = re.search(height_pattern, answer)
            
            if width_match and height_match:
                width = float(width_match.group(1))
                height = float(height_match.group(1))
                
                if 0.1 <= width <= 10.0 and 0.1 <= height <= 5.0:
                    return (width, height)
            
            return None
            
        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to parse dimension answer '{answer}': {e}")
            return None
    
    def parse_wall_answer(self, answer: str) -> Optional[str]:
        """Parse a wall placement answer.
        
        Args:
            answer: User's wall answer
            
        Returns:
            Standardized wall name, or None if parsing fails
        """
        try:
            answer = answer.lower().strip()
            
            # Direct matches
            for wall in self.wall_options:
                if wall in answer:
                    return wall
            
            # Alternative names
            wall_aliases = {
                "n": "north",
                "s": "south", 
                "e": "east",
                "w": "west",
                "left": "west",
                "right": "east",
                "front": "south",
                "back": "north",
                "top": "north",
                "bottom": "south"
            }
            
            for alias, wall in wall_aliases.items():
                if alias in answer:
                    return wall
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse wall answer '{answer}': {e}")
            return None
    
    def parse_position_answer(self, answer: str) -> Optional[float]:
        """Parse a position along wall answer.
        
        Args:
            answer: User's position answer
            
        Returns:
            Position value (0.0 to 1.0), or None if parsing fails
        """
        try:
            answer = answer.lower().strip()
            
            # Direct position mappings
            position_mappings = {
                "center": 0.5,
                "centre": 0.5,
                "middle": 0.5,
                "left": 0.25,
                "right": 0.75,
                "start": 0.0,
                "beginning": 0.0,
                "end": 1.0,
                "quarter": 0.25,
                "three-quarters": 0.75,
                "half": 0.5
            }
            
            for key, value in position_mappings.items():
                if key in answer:
                    return value
            
            # Try to parse as decimal
            import re
            decimal_pattern = r'(\d+\.?\d*)'
            match = re.search(decimal_pattern, answer)
            
            if match:
                value = float(match.group(1))
                
                # If value is > 1, assume it's a percentage
                if value > 1:
                    value = value / 100
                
                # Clamp to valid range
                if 0.0 <= value <= 1.0:
                    return value
            
            return None
            
        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to parse position answer '{answer}': {e}")
            return None
    
    def create_element_spec_from_answers(self, dimension_answer: str, 
                                       wall_answer: str,
                                       position_answer: Optional[str] = None) -> Optional[ElementSpec]:
        """Create an ElementSpec from parsed answers.
        
        Args:
            dimension_answer: User's dimension answer
            wall_answer: User's wall answer
            position_answer: Optional position answer
            
        Returns:
            ElementSpec if parsing successful, None otherwise
        """
        try:
            # Parse dimensions
            dimensions = self.parse_dimension_answer(dimension_answer)
            if not dimensions:
                return None
            
            width, height = dimensions
            
            # Parse wall
            wall = self.parse_wall_answer(wall_answer)
            if not wall:
                return None
            
            # Parse position (optional)
            alpha = None
            if position_answer:
                alpha = self.parse_position_answer(position_answer)
            
            # Default to center if no position specified
            if alpha is None:
                alpha = 0.5
            
            return ElementSpec(
                width=width,
                height=height,
                wall=wall,
                alpha=alpha
            )
            
        except Exception as e:
            logger.error(f"Failed to create ElementSpec from answers: {e}")
            return None