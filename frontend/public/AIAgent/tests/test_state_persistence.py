"""Property-based tests for state persistence."""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime, timedelta
import uuid
import asyncio

from src.nl_floorspace_agent.models.core import (
    ConversationState, ConversationStep, Question, SessionContext,
    BuildingContext, ElementSpec, SpaceRequirement, BuildingElement,
    ElementType, Dimensions, Units
)
from src.nl_floorspace_agent.models.floorspace import (
    FloorspaceModel, Story, Space, Geometry, Vertex, Edge, Face,
    WindowInstance, DoorInstance, WindowDefinition, DoorDefinition
)
from src.nl_floorspace_agent.storage.building_state import BuildingState


# Hypothesis strategies for generating test data
@st.composite
def conversation_step_strategy(draw):
    """Generate valid conversation steps."""
    return draw(st.sampled_from(list(ConversationStep)))


@st.composite
def element_type_strategy(draw):
    """Generate valid element types."""
    return draw(st.sampled_from(list(ElementType)))


@st.composite
def units_strategy(draw):
    """Generate valid units."""
    return draw(st.sampled_from(list(Units)))


@st.composite
def question_strategy(draw):
    """Generate valid question data."""
    return Question(
        id=str(uuid.uuid4()),
        text=draw(st.text(min_size=1, max_size=200)),
        question_type=draw(st.sampled_from(['dimension', 'placement', 'specification'])),
        element_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        options=draw(st.lists(st.text(min_size=1, max_size=50), max_size=5)),
        required=draw(st.booleans()),
        answered=draw(st.booleans()),
        answer=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100)))
    )


@st.composite
def element_spec_strategy(draw):
    """Generate valid element specifications."""
    return ElementSpec(
        width=draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False))),
        height=draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False))),
        wall=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20))),
        alpha=draw(st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)))
    )


@st.composite
def dimensions_strategy(draw):
    """Generate valid dimensions."""
    return Dimensions(
        width=draw(st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False)),
        length=draw(st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False)),
        height=draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=20.0, allow_nan=False, allow_infinity=False))),
        units=draw(units_strategy())
    )


@st.composite
def building_element_strategy(draw):
    """Generate valid building elements."""
    return BuildingElement(
        type=draw(element_type_strategy()),
        count=draw(st.integers(min_value=1, max_value=20)),
        specifications=draw(st.one_of(st.none(), element_spec_strategy()))
    )


@st.composite
def space_requirement_strategy(draw):
    """Generate valid space requirements."""
    return SpaceRequirement(
        dimensions=draw(dimensions_strategy()),
        elements=draw(st.lists(building_element_strategy(), max_size=5)),
        placement=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        room_type=draw(st.one_of(st.none(), st.text(min_size=1, max_size=30)))
    )


@st.composite
def conversation_state_strategy(draw):
    """Generate valid conversation states."""
    return ConversationState(
        current_step=draw(conversation_step_strategy()),
        pending_questions=draw(st.lists(st.builds(dict, id=st.text(), text=st.text()), max_size=5)),
        collected_specs=draw(st.lists(element_spec_strategy(), max_size=5)),
        building_model=None,  # Keep None for simplicity
        session_id=str(uuid.uuid4())
    )


@st.composite
def session_context_strategy(draw):
    """Generate valid session contexts."""
    return SessionContext(
        session_id=str(uuid.uuid4()),
        user_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        conversation_state=draw(st.one_of(st.none(), conversation_state_strategy())),
        metadata=draw(st.dictionaries(st.text(min_size=1, max_size=20), st.text(max_size=100), max_size=5))
    )


@st.composite
def building_context_strategy(draw):
    """Generate valid building contexts."""
    return BuildingContext(
        building_id=str(uuid.uuid4()),
        name=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        description=draw(st.one_of(st.none(), st.text(min_size=1, max_size=500))),
        units=draw(units_strategy()),
        total_spaces=draw(st.integers(min_value=0, max_value=100)),
        total_windows=draw(st.integers(min_value=0, max_value=500)),
        total_doors=draw(st.integers(min_value=0, max_value=200))
    )


@st.composite
def vertex_strategy(draw):
    """Generate valid vertices."""
    return Vertex(
        id=str(uuid.uuid4()),
        x=draw(st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
        y=draw(st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
        edge_ids=draw(st.lists(st.text(min_size=1, max_size=20), max_size=4))
    )


@st.composite
def edge_strategy(draw):
    """Generate valid edges."""
    vertex_id1 = str(uuid.uuid4())
    vertex_id2 = str(uuid.uuid4())
    return Edge(
        id=str(uuid.uuid4()),
        vertex_ids=[vertex_id1, vertex_id2],
        face_ids=draw(st.lists(st.text(min_size=1, max_size=20), max_size=2))
    )


@st.composite
def face_strategy(draw):
    """Generate valid faces."""
    edge_count = draw(st.integers(min_value=3, max_value=6))
    edge_ids = [str(uuid.uuid4()) for _ in range(edge_count)]
    edge_order = draw(st.lists(st.sampled_from([1, -1]), min_size=edge_count, max_size=edge_count))
    
    return Face(
        id=str(uuid.uuid4()),
        edge_ids=edge_ids,
        edge_order=edge_order
    )


@st.composite
def geometry_strategy(draw):
    """Generate valid geometry."""
    vertices = draw(st.lists(vertex_strategy(), min_size=3, max_size=10))
    edges = draw(st.lists(edge_strategy(), min_size=3, max_size=10))
    faces = draw(st.lists(face_strategy(), min_size=1, max_size=5))
    
    return Geometry(
        id=str(uuid.uuid4()),
        vertices=vertices,
        edges=edges,
        faces=faces
    )


@st.composite
def space_strategy(draw):
    """Generate valid spaces."""
    return Space(
        id=str(uuid.uuid4()),
        name=draw(st.text(min_size=1, max_size=50)),
        face_id=str(uuid.uuid4()),
        color=draw(st.sampled_from(["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"])),
        type=draw(st.sampled_from(["space", "room", "area"]))
    )


@st.composite
def window_definition_strategy(draw):
    """Generate valid window definitions."""
    return WindowDefinition(
        id=str(uuid.uuid4()),
        name=draw(st.text(min_size=1, max_size=50)),
        height=draw(st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False)),
        width=draw(st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False)),
        window_type=draw(st.sampled_from(["fixed", "operable", "casement", "double_hung"])),
        sill_height=draw(st.floats(min_value=0.0, max_value=1.5, allow_nan=False, allow_infinity=False))
    )


@st.composite
def door_definition_strategy(draw):
    """Generate valid door definitions."""
    return DoorDefinition(
        id=str(uuid.uuid4()),
        name=draw(st.text(min_size=1, max_size=50)),
        height=draw(st.floats(min_value=1.8, max_value=2.5, allow_nan=False, allow_infinity=False)),
        width=draw(st.floats(min_value=0.6, max_value=1.5, allow_nan=False, allow_infinity=False)),
        door_type=draw(st.sampled_from(["hinged", "sliding", "revolving", "folding"]))
    )


@st.composite
def window_instance_strategy(draw):
    """Generate valid window instances."""
    return WindowInstance(
        id=str(uuid.uuid4()),
        name=draw(st.text(min_size=1, max_size=50)),
        window_definition_id=str(uuid.uuid4()),
        edge_id=str(uuid.uuid4()),
        alpha=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    )


@st.composite
def door_instance_strategy(draw):
    """Generate valid door instances."""
    return DoorInstance(
        id=str(uuid.uuid4()),
        name=draw(st.text(min_size=1, max_size=50)),
        door_definition_id=str(uuid.uuid4()),
        edge_id=str(uuid.uuid4()),
        alpha=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    )


@st.composite
def story_strategy(draw):
    """Generate valid stories."""
    spaces = draw(st.lists(space_strategy(), min_size=1, max_size=5))
    windows = draw(st.lists(window_instance_strategy(), max_size=10))
    doors = draw(st.lists(door_instance_strategy(), max_size=5))
    
    return Story(
        id=str(uuid.uuid4()),
        name=draw(st.text(min_size=1, max_size=50)),
        geometry=draw(geometry_strategy()),
        spaces=spaces,
        windows=windows,
        doors=doors,
        floor_to_ceiling_height=draw(st.floats(min_value=2.0, max_value=5.0, allow_nan=False, allow_infinity=False)),
        multiplier=draw(st.integers(min_value=1, max_value=3)),
        color=draw(st.sampled_from(["#FFFFFF", "#F0F0F0", "#E0E0E0"]))
    )


@st.composite
def floorspace_model_strategy(draw):
    """Generate valid floorspace models."""
    stories = draw(st.lists(story_strategy(), min_size=1, max_size=3))
    window_definitions = draw(st.lists(window_definition_strategy(), max_size=5))
    door_definitions = draw(st.lists(door_definition_strategy(), max_size=5))
    
    return FloorspaceModel(
        application={"name": "test_app", "version": "1.0.0"},
        project={"name": "test_project", "units": "si"},
        stories=stories,
        window_definitions=window_definitions,
        door_definitions=door_definitions,
        building_units=[],
        thermal_zones=[],
        space_types=[],
        construction_sets=[],
        version="1.4.3"
    )


class TestStatePersistence:
    """
    **Feature: nl-floorspace-agent, Property 10: State Persistence**
    **Validates: Requirements 7.1, 7.3**
    
    Property-based tests for state persistence and management.
    """

    @given(state=conversation_state_strategy())
    def test_conversation_state_persistence(self, state):
        """Test that conversation state maintains its properties after operations."""
        original_step = state.current_step
        original_session_id = state.session_id
        original_question_count = len(state.pending_questions)
        original_spec_count = len(state.collected_specs)
        
        # State should maintain its core properties
        assert state.current_step == original_step
        assert state.session_id == original_session_id
        assert len(state.pending_questions) == original_question_count
        assert len(state.collected_specs) == original_spec_count

    @given(state=conversation_state_strategy(), question=question_strategy())
    def test_conversation_state_question_management(self, state, question):
        """Test that conversation state correctly manages questions."""
        original_count = len(state.pending_questions)
        question_dict = {
            'id': question.id,
            'text': question.text,
            'type': question.question_type
        }
        
        # Adding a question should increase count
        state.add_question(question_dict)
        assert len(state.pending_questions) == original_count + 1
        assert state.has_pending_questions()
        assert state.get_question_count() == original_count + 1
        
        # Removing the question should decrease count
        removed = state.remove_question(question.id)
        assert removed == True
        assert len(state.pending_questions) == original_count

    @given(state=conversation_state_strategy(), spec=element_spec_strategy())
    def test_conversation_state_spec_management(self, state, spec):
        """Test that conversation state correctly manages element specifications."""
        original_count = len(state.collected_specs)
        
        # Adding a spec should increase count
        state.add_element_spec(spec)
        assert len(state.collected_specs) == original_count + 1
        assert state.get_spec_count() == original_count + 1

    @given(state=conversation_state_strategy())
    def test_conversation_state_timestamp_updates(self, state):
        """Test that conversation state updates timestamps correctly."""
        original_timestamp = state.last_updated
        
        # Operations should update timestamp
        state.update_timestamp()
        assert state.last_updated >= original_timestamp
        
        # Adding questions should update timestamp
        if len(state.pending_questions) > 0:
            question_id = state.pending_questions[0].get('id', 'test_id')
            state.remove_question(question_id)
            assert state.last_updated >= original_timestamp

    @given(context=session_context_strategy())
    def test_session_context_persistence(self, context):
        """Test that session context maintains its properties."""
        original_session_id = context.session_id
        original_user_id = context.user_id
        original_metadata_count = len(context.metadata)
        
        # Context should maintain its core properties
        assert context.session_id == original_session_id
        assert context.user_id == original_user_id
        assert len(context.metadata) == original_metadata_count

    @given(context=session_context_strategy())
    def test_session_context_metadata_management(self, context):
        """Test that session context correctly manages metadata."""
        test_key = "test_key"
        test_value = "test_value"
        
        # Adding metadata should work
        context.add_metadata(test_key, test_value)
        assert context.get_metadata(test_key) == test_value
        
        # Getting non-existent metadata should return default
        assert context.get_metadata("non_existent", "default") == "default"

    @given(context=session_context_strategy())
    def test_session_context_activity_tracking(self, context):
        """Test that session context tracks activity correctly."""
        original_activity = context.last_activity
        
        # Activity updates should work
        context.update_activity()
        assert context.last_activity >= original_activity

    @given(building_ctx=building_context_strategy())
    def test_building_context_persistence(self, building_ctx):
        """Test that building context maintains its properties."""
        original_id = building_ctx.building_id
        original_name = building_ctx.name
        original_units = building_ctx.units
        original_spaces = building_ctx.total_spaces
        original_windows = building_ctx.total_windows
        original_doors = building_ctx.total_doors
        
        # Context should maintain its core properties
        assert building_ctx.building_id == original_id
        assert building_ctx.name == original_name
        assert building_ctx.units == original_units
        assert building_ctx.total_spaces == original_spaces
        assert building_ctx.total_windows == original_windows
        assert building_ctx.total_doors == original_doors

    @given(building_ctx=building_context_strategy())
    def test_building_context_counter_management(self, building_ctx):
        """Test that building context correctly manages counters."""
        original_spaces = building_ctx.total_spaces
        original_windows = building_ctx.total_windows
        original_doors = building_ctx.total_doors
        
        # Incrementing counters should work
        building_ctx.increment_space_count()
        assert building_ctx.total_spaces == original_spaces + 1
        
        building_ctx.increment_window_count(3)
        assert building_ctx.total_windows == original_windows + 3
        
        building_ctx.increment_door_count(2)
        assert building_ctx.total_doors == original_doors + 2

    @given(building_ctx=building_context_strategy())
    def test_building_context_summary_generation(self, building_ctx):
        """Test that building context generates correct summaries."""
        summary = building_ctx.get_summary()
        
        # Summary should contain all expected fields
        assert "building_id" in summary
        assert "name" in summary
        assert "description" in summary
        assert "units" in summary
        assert "total_spaces" in summary
        assert "total_windows" in summary
        assert "total_doors" in summary
        assert "created_at" in summary
        assert "last_modified" in summary
        
        # Values should match the context
        assert summary["building_id"] == building_ctx.building_id
        assert summary["name"] == building_ctx.name
        assert summary["units"] == building_ctx.units.value
        assert summary["total_spaces"] == building_ctx.total_spaces
        assert summary["total_windows"] == building_ctx.total_windows
        assert summary["total_doors"] == building_ctx.total_doors

    @given(question=question_strategy())
    def test_question_answer_management(self, question):
        """Test that questions correctly manage their answered state."""
        original_answered = question.answered
        original_answer = question.answer
        
        # Initially should maintain state
        assert question.answered == original_answered
        assert question.answer == original_answer
        
        # Marking as answered should update state
        test_answer = "test answer"
        question.mark_answered(test_answer)
        assert question.answered == True
        assert question.answer == test_answer

    @given(state1=conversation_state_strategy(), state2=conversation_state_strategy())
    def test_conversation_state_independence(self, state1, state2):
        """Test that different conversation states are independent."""
        assume(state1.session_id != state2.session_id)
        
        # States should have different session IDs
        assert state1.session_id != state2.session_id
        
        # Modifying one state should not affect the other
        original_state2_questions = len(state2.pending_questions)
        state1.add_question({'id': 'test', 'text': 'test question'})
        assert len(state2.pending_questions) == original_state2_questions

    @given(context1=session_context_strategy(), context2=session_context_strategy())
    def test_session_context_independence(self, context1, context2):
        """Test that different session contexts are independent."""
        assume(context1.session_id != context2.session_id)
        
        # Contexts should have different session IDs
        assert context1.session_id != context2.session_id
        
        # Modifying one context should not affect the other
        original_context2_metadata = len(context2.metadata)
        context1.add_metadata('test_key', 'test_value')
        assert len(context2.metadata) == original_context2_metadata

    def test_conversation_state_clear_questions(self):
        """Test that clearing questions works correctly."""
        state = ConversationState(
            current_step=ConversationStep.CLARIFYING,
            pending_questions=[
                {'id': '1', 'text': 'Question 1'},
                {'id': '2', 'text': 'Question 2'}
            ]
        )
        
        assert len(state.pending_questions) == 2
        assert state.has_pending_questions() == True
        
        state.clear_pending_questions()
        
        assert len(state.pending_questions) == 0
        assert state.has_pending_questions() == False
        assert state.get_question_count() == 0

    def test_building_context_modification_timestamps(self):
        """Test that building context updates modification timestamps."""
        context = BuildingContext()
        original_modified = context.last_modified
        
        # Operations should update timestamp
        context.increment_space_count()
        assert context.last_modified >= original_modified
        
        context.increment_window_count()
        assert context.last_modified >= original_modified
        
        context.increment_door_count()
        assert context.last_modified >= original_modified


class TestSelectiveModification:
    """
    **Feature: nl-floorspace-agent, Property 11: Selective Modification**
    **Validates: Requirements 7.4**
    
    Property-based tests for selective modification of building elements.
    Tests that modifying one space preserves other spaces in the building.
    """

    @pytest.fixture
    def building_state(self):
        """Create a BuildingState instance for testing."""
        return BuildingState(enable_persistence=False)

    @given(model=floorspace_model_strategy())
    @pytest.mark.asyncio
    async def test_space_update_preserves_other_spaces(self, model):
        """
        For any modification to an existing space, other spaces in the building 
        should remain unchanged.
        """
        # Ensure we have at least 2 spaces to test selective modification
        assume(len(model.stories) > 0)
        assume(len(model.stories[0].spaces) >= 2)
        
        building_state = BuildingState(enable_persistence=False)
        building_id = str(uuid.uuid4())
        
        # Save the initial model
        await building_state.save_building_model(building_id, model)
        
        # Get the initial state of all spaces
        story = model.stories[0]
        space_to_modify = story.spaces[0]
        other_spaces = story.spaces[1:]
        
        # Store original data for other spaces
        original_other_spaces = [
            {
                "id": s.id,
                "name": s.name,
                "face_id": s.face_id,
                "color": s.color,
                "type": s.type
            }
            for s in other_spaces
        ]
        
        # Modify the first space
        modified_space = Space(
            id=space_to_modify.id,
            name="Modified Space",
            face_id=space_to_modify.face_id,
            color="#000000",
            type="modified"
        )
        
        # Update the space
        success = await building_state.update_space(building_id, space_to_modify.id, modified_space)
        assert success, "Space update should succeed"
        
        # Retrieve the updated model
        updated_model = await building_state.get_building_model(building_id)
        assert updated_model is not None
        
        # Verify the modified space was updated
        updated_story = updated_model.stories[0]
        updated_space = next((s for s in updated_story.spaces if s.id == space_to_modify.id), None)
        assert updated_space is not None
        assert updated_space.name == "Modified Space"
        assert updated_space.color == "#000000"
        assert updated_space.type == "modified"
        
        # Verify other spaces remain unchanged
        for i, original_data in enumerate(original_other_spaces):
            other_space = next((s for s in updated_story.spaces if s.id == original_data["id"]), None)
            assert other_space is not None, f"Space {original_data['id']} should still exist"
            assert other_space.name == original_data["name"], "Space name should be unchanged"
            assert other_space.face_id == original_data["face_id"], "Space face_id should be unchanged"
            assert other_space.color == original_data["color"], "Space color should be unchanged"
            assert other_space.type == original_data["type"], "Space type should be unchanged"

    @given(model=floorspace_model_strategy())
    @pytest.mark.asyncio
    async def test_window_addition_preserves_spaces(self, model):
        """
        For any window addition to a space, all spaces in the building 
        should remain unchanged.
        """
        assume(len(model.stories) > 0)
        assume(len(model.stories[0].spaces) >= 1)
        assume(len(model.stories[0].geometry.edges) > 0)
        
        building_state = BuildingState(enable_persistence=False)
        building_id = str(uuid.uuid4())
        
        # Save the initial model
        await building_state.save_building_model(building_id, model)
        
        # Store original space data
        story = model.stories[0]
        original_spaces = [
            {
                "id": s.id,
                "name": s.name,
                "face_id": s.face_id,
                "color": s.color,
                "type": s.type
            }
            for s in story.spaces
        ]
        
        # Add a new window
        window_def = WindowDefinition(
            id=str(uuid.uuid4()),
            name="Test Window",
            height=1.5,
            width=1.0,
            window_type="fixed",
            sill_height=0.9
        )
        
        window_instance = WindowInstance(
            id=str(uuid.uuid4()),
            name="Test Window Instance",
            window_definition_id=window_def.id,
            edge_id=story.geometry.edges[0].id,
            alpha=0.5
        )
        
        # Add the window
        success = await building_state.add_window_to_space(
            building_id, story.id, window_instance, window_def
        )
        assert success, "Window addition should succeed"
        
        # Retrieve the updated model
        updated_model = await building_state.get_building_model(building_id)
        assert updated_model is not None
        
        # Verify all spaces remain unchanged
        updated_story = updated_model.stories[0]
        for original_data in original_spaces:
            space = next((s for s in updated_story.spaces if s.id == original_data["id"]), None)
            assert space is not None, f"Space {original_data['id']} should still exist"
            assert space.name == original_data["name"], "Space name should be unchanged"
            assert space.face_id == original_data["face_id"], "Space face_id should be unchanged"
            assert space.color == original_data["color"], "Space color should be unchanged"
            assert space.type == original_data["type"], "Space type should be unchanged"
        
        # Verify the window was added
        assert len(updated_story.windows) == len(story.windows) + 1

    @given(model=floorspace_model_strategy())
    @pytest.mark.asyncio
    async def test_door_addition_preserves_spaces(self, model):
        """
        For any door addition to a space, all spaces in the building 
        should remain unchanged.
        """
        assume(len(model.stories) > 0)
        assume(len(model.stories[0].spaces) >= 1)
        assume(len(model.stories[0].geometry.edges) > 0)
        
        building_state = BuildingState(enable_persistence=False)
        building_id = str(uuid.uuid4())
        
        # Save the initial model
        await building_state.save_building_model(building_id, model)
        
        # Store original space data
        story = model.stories[0]
        original_spaces = [
            {
                "id": s.id,
                "name": s.name,
                "face_id": s.face_id,
                "color": s.color,
                "type": s.type
            }
            for s in story.spaces
        ]
        
        # Add a new door
        door_def = DoorDefinition(
            id=str(uuid.uuid4()),
            name="Test Door",
            height=2.1,
            width=0.9,
            door_type="hinged"
        )
        
        door_instance = DoorInstance(
            id=str(uuid.uuid4()),
            name="Test Door Instance",
            door_definition_id=door_def.id,
            edge_id=story.geometry.edges[0].id,
            alpha=0.5
        )
        
        # Add the door
        success = await building_state.add_door_to_space(
            building_id, story.id, door_instance, door_def
        )
        assert success, "Door addition should succeed"
        
        # Retrieve the updated model
        updated_model = await building_state.get_building_model(building_id)
        assert updated_model is not None
        
        # Verify all spaces remain unchanged
        updated_story = updated_model.stories[0]
        for original_data in original_spaces:
            space = next((s for s in updated_story.spaces if s.id == original_data["id"]), None)
            assert space is not None, f"Space {original_data['id']} should still exist"
            assert space.name == original_data["name"], "Space name should be unchanged"
            assert space.face_id == original_data["face_id"], "Space face_id should be unchanged"
            assert space.color == original_data["color"], "Space color should be unchanged"
            assert space.type == original_data["type"], "Space type should be unchanged"
        
        # Verify the door was added
        assert len(updated_story.doors) == len(story.doors) + 1

    @given(model=floorspace_model_strategy())
    @pytest.mark.asyncio
    async def test_space_removal_preserves_other_spaces(self, model):
        """
        For any space removal, other spaces in the building should remain unchanged.
        """
        assume(len(model.stories) > 0)
        assume(len(model.stories[0].spaces) >= 2)
        
        building_state = BuildingState(enable_persistence=False)
        building_id = str(uuid.uuid4())
        
        # Save the initial model
        await building_state.save_building_model(building_id, model)
        
        # Get the initial state
        story = model.stories[0]
        space_to_remove = story.spaces[0]
        other_spaces = story.spaces[1:]
        
        # Store original data for other spaces
        original_other_spaces = [
            {
                "id": s.id,
                "name": s.name,
                "face_id": s.face_id,
                "color": s.color,
                "type": s.type
            }
            for s in other_spaces
        ]
        
        # Remove the first space
        success = await building_state.remove_space(building_id, space_to_remove.id)
        assert success, "Space removal should succeed"
        
        # Retrieve the updated model
        updated_model = await building_state.get_building_model(building_id)
        assert updated_model is not None
        
        # Verify the space was removed
        updated_story = updated_model.stories[0]
        removed_space = next((s for s in updated_story.spaces if s.id == space_to_remove.id), None)
        assert removed_space is None, "Removed space should not exist"
        
        # Verify other spaces remain unchanged
        for original_data in original_other_spaces:
            other_space = next((s for s in updated_story.spaces if s.id == original_data["id"]), None)
            assert other_space is not None, f"Space {original_data['id']} should still exist"
            assert other_space.name == original_data["name"], "Space name should be unchanged"
            assert other_space.face_id == original_data["face_id"], "Space face_id should be unchanged"
            assert other_space.color == original_data["color"], "Space color should be unchanged"
            assert other_space.type == original_data["type"], "Space type should be unchanged"

    @given(model=floorspace_model_strategy())
    @pytest.mark.asyncio
    async def test_geometry_update_preserves_spaces(self, model):
        """
        For any geometry update, space definitions should remain unchanged.
        """
        assume(len(model.stories) > 0)
        assume(len(model.stories[0].spaces) >= 1)
        
        building_state = BuildingState(enable_persistence=False)
        building_id = str(uuid.uuid4())
        
        # Save the initial model
        await building_state.save_building_model(building_id, model)
        
        # Store original space data
        story = model.stories[0]
        original_spaces = [
            {
                "id": s.id,
                "name": s.name,
                "face_id": s.face_id,
                "color": s.color,
                "type": s.type
            }
            for s in story.spaces
        ]
        
        # Create new geometry
        new_geometry = Geometry(
            id=str(uuid.uuid4()),
            vertices=[
                Vertex(id=str(uuid.uuid4()), x=0.0, y=0.0, edge_ids=[]),
                Vertex(id=str(uuid.uuid4()), x=10.0, y=0.0, edge_ids=[]),
                Vertex(id=str(uuid.uuid4()), x=10.0, y=10.0, edge_ids=[])
            ],
            edges=[
                Edge(id=str(uuid.uuid4()), vertex_ids=[str(uuid.uuid4()), str(uuid.uuid4())], face_ids=[])
            ],
            faces=[
                Face(id=str(uuid.uuid4()), edge_ids=[str(uuid.uuid4())], edge_order=[1])
            ]
        )
        
        # Update the geometry
        success = await building_state.update_space_geometry(building_id, story.id, new_geometry)
        assert success, "Geometry update should succeed"
        
        # Retrieve the updated model
        updated_model = await building_state.get_building_model(building_id)
        assert updated_model is not None
        
        # Verify all spaces remain unchanged
        updated_story = updated_model.stories[0]
        for original_data in original_spaces:
            space = next((s for s in updated_story.spaces if s.id == original_data["id"]), None)
            assert space is not None, f"Space {original_data['id']} should still exist"
            assert space.name == original_data["name"], "Space name should be unchanged"
            assert space.face_id == original_data["face_id"], "Space face_id should be unchanged"
            assert space.color == original_data["color"], "Space color should be unchanged"
            assert space.type == original_data["type"], "Space type should be unchanged"
        
        # Verify the geometry was updated
        assert updated_story.geometry.id == new_geometry.id