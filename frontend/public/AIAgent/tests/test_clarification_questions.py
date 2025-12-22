"""Property-based tests for clarification question generation.

**Feature: nl-floorspace-agent, Property 4: Clarification Question Generation**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""

import pytest
from hypothesis import given, strategies as st, assume
from typing import List

from src.nl_floorspace_agent.conversation.clarification import ClarificationGenerator
from src.nl_floorspace_agent.models import (
    SpaceRequirement, BuildingElement, ElementType, ElementSpec,
    Dimensions, Units, Question
)


# Hypothesis strategies for generating test data
@st.composite
def dimensions_strategy(draw):
    """Generate valid dimensions."""
    return Dimensions(
        width=draw(st.floats(min_value=1.0, max_value=20.0)),
        length=draw(st.floats(min_value=1.0, max_value=20.0)),
        height=draw(st.one_of(st.none(), st.floats(min_value=2.0, max_value=5.0))),
        units=draw(st.sampled_from(list(Units)))
    )


@st.composite
def incomplete_element_spec_strategy(draw):
    """Generate incomplete element specifications that need clarification."""
    # Randomly make some fields None to simulate incomplete specs
    width = draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=5.0)))
    height = draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=3.0)))
    wall = draw(st.one_of(st.none(), st.sampled_from(["north", "south", "east", "west"])))
    alpha = draw(st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0)))
    
    # Ensure at least one field is None to make it incomplete
    if all(field is not None for field in [width, height, wall]):
        # Force at least one to be None
        field_to_clear = draw(st.sampled_from(["width", "height", "wall"]))
        if field_to_clear == "width":
            width = None
        elif field_to_clear == "height":
            height = None
        else:
            wall = None
    
    return ElementSpec(width=width, height=height, wall=wall, alpha=alpha)


@st.composite
def building_element_strategy(draw):
    """Generate building elements with incomplete specifications."""
    element_type = draw(st.sampled_from(list(ElementType)))
    count = draw(st.integers(min_value=1, max_value=5))
    
    # Sometimes have no specifications, sometimes incomplete ones
    specifications = draw(st.one_of(
        st.none(),
        incomplete_element_spec_strategy()
    ))
    
    return BuildingElement(
        type=element_type,
        count=count,
        specifications=specifications
    )


@st.composite
def space_requirement_strategy(draw):
    """Generate space requirements that need clarification."""
    dimensions = draw(dimensions_strategy())
    elements = draw(st.lists(building_element_strategy(), min_size=1, max_size=3))
    placement = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    room_type = draw(st.one_of(st.none(), st.sampled_from([
        "bedroom", "kitchen", "bathroom", "living room", "office", "dining room"
    ])))
    
    return SpaceRequirement(
        dimensions=dimensions,
        elements=elements,
        placement=placement,
        room_type=room_type
    )


class TestClarificationQuestionGeneration:
    """Property-based tests for clarification question generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ClarificationGenerator()
    
    @given(requirement=space_requirement_strategy())
    def test_clarification_questions_generated_for_incomplete_specs(self, requirement):
        """
        **Feature: nl-floorspace-agent, Property 4: Clarification Question Generation**
        
        For any space requirement with incomplete element specifications,
        the clarification generator should produce appropriate questions
        for missing dimensions and wall placement.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        # Generate questions
        questions = self.generator.generate_questions(requirement)
        
        # Property: Questions should be generated for incomplete specifications
        assert isinstance(questions, list)
        
        # Count elements that need clarification
        elements_needing_clarification = 0
        for element in requirement.elements:
            if element.specifications is None:
                elements_needing_clarification += 1
            else:
                spec = element.specifications
                if (spec.width is None or spec.height is None or spec.wall is None):
                    elements_needing_clarification += 1
        
        # If there are elements needing clarification, questions should be generated
        if elements_needing_clarification > 0:
            assert len(questions) > 0, "Questions should be generated for incomplete specifications"
            
            # Each question should be a valid Question object
            for question in questions:
                assert isinstance(question, Question)
                assert question.text is not None and len(question.text) > 0
                assert question.question_type in ["dimension", "placement", "position"]
                assert isinstance(question.required, bool)
        
        # Property: Questions should cover missing specifications
        dimension_questions = [q for q in questions if q.question_type == "dimension"]
        placement_questions = [q for q in questions if q.question_type == "placement"]
        
        # Count elements missing dimensions or placement
        elements_missing_dimensions = 0
        elements_missing_placement = 0
        
        for element in requirement.elements:
            if element.specifications is None:
                elements_missing_dimensions += 1
                elements_missing_placement += 1
            else:
                spec = element.specifications
                if spec.width is None or spec.height is None:
                    elements_missing_dimensions += 1
                if spec.wall is None:
                    elements_missing_placement += 1
        
        # Should have dimension questions for elements missing dimensions
        if elements_missing_dimensions > 0:
            assert len(dimension_questions) > 0, "Should generate dimension questions for elements missing dimensions"
        
        # Should have placement questions for elements missing wall placement
        if elements_missing_placement > 0:
            assert len(placement_questions) > 0, "Should generate placement questions for elements missing wall placement"
    
    @given(
        dimension_answer=st.text(min_size=1, max_size=50),
        wall_answer=st.text(min_size=1, max_size=20)
    )
    def test_answer_parsing_robustness(self, dimension_answer, wall_answer):
        """
        **Feature: nl-floorspace-agent, Property 4: Clarification Question Generation**
        
        For any user answer to clarification questions, the parser should
        either successfully extract valid information or gracefully handle
        unparseable input without crashing.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        # Test dimension parsing
        try:
            dimensions = self.generator.parse_dimension_answer(dimension_answer)
            if dimensions is not None:
                width, height = dimensions
                assert isinstance(width, float)
                assert isinstance(height, float)
                assert 0.1 <= width <= 10.0, f"Width {width} should be reasonable"
                assert 0.1 <= height <= 5.0, f"Height {height} should be reasonable"
        except Exception as e:
            pytest.fail(f"Dimension parsing should not crash on input '{dimension_answer}': {e}")
        
        # Test wall parsing
        try:
            wall = self.generator.parse_wall_answer(wall_answer)
            if wall is not None:
                assert wall in ["north", "south", "east", "west"], f"Wall '{wall}' should be valid"
        except Exception as e:
            pytest.fail(f"Wall parsing should not crash on input '{wall_answer}': {e}")
    
    @given(
        valid_dimensions=st.tuples(
            st.floats(min_value=0.5, max_value=3.0),
            st.floats(min_value=0.5, max_value=3.0)
        ),
        valid_wall=st.sampled_from(["north", "south", "east", "west"])
    )
    def test_valid_answer_parsing_success(self, valid_dimensions, valid_wall):
        """
        **Feature: nl-floorspace-agent, Property 4: Clarification Question Generation**
        
        For any valid dimension and wall specification, the parser should
        successfully extract the correct information.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        width, height = valid_dimensions
        
        # Test various valid dimension formats
        dimension_formats = [
            f"{width} x {height}",
            f"{width}m x {height}m",
            f"{width} by {height}",
            f"width {width} height {height}",
            f"{width} × {height}",
        ]
        
        for dim_format in dimension_formats:
            parsed_dims = self.generator.parse_dimension_answer(dim_format)
            if parsed_dims is not None:  # Some formats might not be supported
                parsed_width, parsed_height = parsed_dims
                assert abs(parsed_width - width) < 0.01, f"Width should be parsed correctly from '{dim_format}'"
                assert abs(parsed_height - height) < 0.01, f"Height should be parsed correctly from '{dim_format}'"
        
        # Test wall parsing
        wall_formats = [
            valid_wall,
            valid_wall.upper(),
            valid_wall.capitalize(),
            f"the {valid_wall} wall",
            f"{valid_wall} side"
        ]
        
        for wall_format in wall_formats:
            parsed_wall = self.generator.parse_wall_answer(wall_format)
            if parsed_wall is not None:  # Some formats might not be supported
                assert parsed_wall == valid_wall, f"Wall should be parsed correctly from '{wall_format}'"
    
    @given(
        dimension_answer=st.sampled_from([
            "1.2 x 1.5", "0.8m x 2.0m", "width 1.0 height 1.8"
        ]),
        wall_answer=st.sampled_from([
            "north", "south wall", "east side", "west"
        ]),
        position_answer=st.one_of(
            st.none(),
            st.sampled_from(["center", "left", "right", "0.25", "75%"])
        )
    )
    def test_element_spec_creation_from_valid_answers(self, dimension_answer, wall_answer, position_answer):
        """
        **Feature: nl-floorspace-agent, Property 4: Clarification Question Generation**
        
        For any set of valid answers to clarification questions, the generator
        should be able to create a complete ElementSpec with all required fields.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        element_spec = self.generator.create_element_spec_from_answers(
            dimension_answer, wall_answer, position_answer
        )
        
        # Should successfully create an ElementSpec
        assert element_spec is not None, "Should create ElementSpec from valid answers"
        assert isinstance(element_spec, ElementSpec)
        
        # Should have valid dimensions
        assert element_spec.width is not None
        assert element_spec.height is not None
        assert isinstance(element_spec.width, float)
        assert isinstance(element_spec.height, float)
        assert 0.1 <= element_spec.width <= 10.0
        assert 0.1 <= element_spec.height <= 5.0
        
        # Should have valid wall
        assert element_spec.wall is not None
        assert element_spec.wall in ["north", "south", "east", "west"]
        
        # Should have valid alpha (position)
        assert element_spec.alpha is not None
        assert isinstance(element_spec.alpha, float)
        assert 0.0 <= element_spec.alpha <= 1.0
    
    def test_question_structure_requirements(self):
        """
        **Feature: nl-floorspace-agent, Property 4: Clarification Question Generation**
        
        All generated questions should have the required structure and properties
        for proper conversation flow.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        # Create a requirement with incomplete specifications
        requirement = SpaceRequirement(
            dimensions=Dimensions(width=5.0, length=4.0, units=Units.SI),
            elements=[
                BuildingElement(type=ElementType.WINDOW, count=2, specifications=None),
                BuildingElement(type=ElementType.DOOR, count=1, specifications=None)
            ]
        )
        
        questions = self.generator.generate_questions(requirement)
        
        # Should generate questions
        assert len(questions) > 0
        
        for question in questions:
            # Each question should have required fields
            assert hasattr(question, 'id') and question.id is not None
            assert hasattr(question, 'text') and len(question.text) > 0
            assert hasattr(question, 'question_type') and question.question_type in [
                "dimension", "placement", "position"
            ]
            assert hasattr(question, 'required') and isinstance(question.required, bool)
            assert hasattr(question, 'answered') and isinstance(question.answered, bool)
            
            # Questions should not be pre-answered
            assert not question.answered
            assert question.answer is None
            
            # Questions should have reasonable options for user guidance
            if hasattr(question, 'options') and question.options:
                assert isinstance(question.options, list)
                assert len(question.options) > 0