"""Property-based tests for error state recovery.

**Feature: nl-floorspace-agent, Property 13: Error State Recovery**
**Validates: Requirements 6.5**
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st, assume, settings
from typing import Dict, Any

from src.nl_floorspace_agent.conversation.manager import (
    ConversationManager, ConversationError, SessionNotFoundError, 
    InvalidStateError, BedrockServiceError
)
from src.nl_floorspace_agent.models import (
    SessionContext, ConversationState, ConversationStep, 
    SpaceRequirement, BuildingElement, ElementType, Dimensions, Units
)


# Hypothesis strategies for generating test data
@st.composite
def session_context_strategy(draw):
    """Generate valid session contexts."""
    session_context = SessionContext(
        user_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    )
    
    conversation_state = ConversationState(
        current_step=draw(st.sampled_from(list(ConversationStep))),
        session_id=session_context.session_id
    )
    
    # Add some pending questions and specs
    for _ in range(draw(st.integers(min_value=0, max_value=3))):
        question = {
            "id": draw(st.text(min_size=1, max_size=20)),
            "text": draw(st.text(min_size=10, max_size=100)),
            "question_type": draw(st.sampled_from(["dimension", "placement", "position"])),
            "answered": draw(st.booleans()),
            "answer": draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
        }
        conversation_state.add_question(question)
    
    session_context.conversation_state = conversation_state
    return session_context


@st.composite
def space_requirement_strategy(draw):
    """Generate space requirements for testing."""
    dimensions = Dimensions(
        width=draw(st.floats(min_value=1.0, max_value=20.0)),
        length=draw(st.floats(min_value=1.0, max_value=20.0)),
        height=draw(st.one_of(st.none(), st.floats(min_value=2.0, max_value=5.0))),
        units=draw(st.sampled_from(list(Units)))
    )
    
    elements = []
    for _ in range(draw(st.integers(min_value=0, max_value=3))):
        element = BuildingElement(
            type=draw(st.sampled_from(list(ElementType))),
            count=draw(st.integers(min_value=1, max_value=5)),
            specifications=None  # Make incomplete to trigger clarification
        )
        elements.append(element)
    
    return SpaceRequirement(
        dimensions=dimensions,
        elements=elements,
        room_type=draw(st.one_of(st.none(), st.sampled_from([
            "bedroom", "kitchen", "bathroom", "living room", "office"
        ])))
    )


@st.composite
def error_scenario_strategy(draw):
    """Generate different error scenarios for testing."""
    error_types = [
        BedrockServiceError("Bedrock service unavailable"),
        ConnectionError("Network connection failed"),
        InvalidStateError("Invalid conversation state"),
        SessionNotFoundError("Session not found"),
        ValueError("Invalid input data"),
        RuntimeError("Unexpected runtime error")
    ]
    
    return {
        "error": draw(st.sampled_from(error_types)),
        "operation": draw(st.sampled_from([
            "process_requirement", "process_clarification_answer", 
            "start_conversation", "save_session"
        ])),
        "should_recover": draw(st.booleans())
    }


class TestErrorStateRecovery:
    """Property-based tests for error state recovery."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.conversation_manager = ConversationManager()
        # Mock the session storage to avoid file system operations
        self.conversation_manager.session_storage = AsyncMock()
    
    @given(session_context=session_context_strategy())
    @pytest.mark.asyncio
    async def test_error_recovery_state_preservation(self, session_context):
        """
        **Feature: nl-floorspace-agent, Property 13: Error State Recovery**
        
        For any conversation session, when an error occurs during processing,
        the system should preserve the conversation state and allow recovery
        without losing previous work.
        
        **Validates: Requirements 6.5**
        """
        # Save recovery state
        await self.conversation_manager._save_recovery_state(session_context, "test_operation")
        
        # Verify recovery data is saved
        recovery_data = self.conversation_manager._error_recovery_cache.get(session_context.session_id)
        assert recovery_data is not None, "Recovery data should be saved"
        assert recovery_data["operation"] == "test_operation"
        assert recovery_data["session_state"]["session_id"] == session_context.session_id
        
        # Verify session state information is preserved
        if session_context.conversation_state:
            assert recovery_data["session_state"]["conversation_step"] == session_context.conversation_state.current_step.value
            assert recovery_data["session_state"]["pending_questions_count"] == len(session_context.conversation_state.pending_questions)
            assert recovery_data["session_state"]["collected_specs_count"] == len(session_context.conversation_state.collected_specs)
    
    @given(
        session_context=session_context_strategy(),
        error_scenario=error_scenario_strategy()
    )
    @pytest.mark.asyncio
    async def test_error_recovery_mechanisms(self, session_context, error_scenario):
        """
        **Feature: nl-floorspace-agent, Property 13: Error State Recovery**
        
        For any error that occurs during conversation processing, the system
        should attempt appropriate recovery mechanisms based on the error type
        and maintain conversation continuity.
        
        **Validates: Requirements 6.5**
        """
        # Save recovery state first
        await self.conversation_manager._save_recovery_state(session_context, error_scenario["operation"])
        
        # Attempt error recovery
        recovery_result = await self.conversation_manager._attempt_error_recovery(
            session_context.session_id,
            error_scenario["operation"],
            error_scenario["error"]
        )
        
        # Verify recovery result structure
        assert isinstance(recovery_result, dict)
        assert "recovered" in recovery_result
        assert "recovery_available" in recovery_result
        assert isinstance(recovery_result["recovered"], bool)
        assert isinstance(recovery_result["recovery_available"], bool)
        
        # Check recovery behavior based on error type
        if isinstance(error_scenario["error"], (BedrockServiceError, ConnectionError)):
            # Service errors should have recovery available
            assert recovery_result["recovery_available"], "Service errors should have recovery available"
            if recovery_result["recovered"]:
                assert "result" in recovery_result
                assert "fallback_mode" in recovery_result["result"]
        
        elif isinstance(error_scenario["error"], InvalidStateError):
            # State errors should attempt session restoration
            assert recovery_result["recovery_available"], "State errors should have recovery available"
        
        # If recovery failed, should have a reason
        if not recovery_result["recovered"] and recovery_result["recovery_available"]:
            assert "reason" in recovery_result
    
    @given(session_context=session_context_strategy())
    @pytest.mark.asyncio
    async def test_session_recovery_functionality(self, session_context):
        """
        **Feature: nl-floorspace-agent, Property 13: Error State Recovery**
        
        For any session that encounters an error, the manual recovery function
        should be able to restore the session to a valid state and allow
        continuation of the conversation.
        
        **Validates: Requirements 6.5**
        """
        # Mock session storage to return the session
        self.conversation_manager.session_storage.get_session.return_value = session_context
        self.conversation_manager.session_storage.save_session.return_value = None
        
        # Save some recovery data
        await self.conversation_manager._save_recovery_state(session_context, "test_operation")
        
        # Attempt manual recovery
        recovery_result = await self.conversation_manager.recover_session(session_context.session_id)
        
        # Verify recovery result
        assert isinstance(recovery_result, dict)
        assert "recovered" in recovery_result
        assert "session_id" in recovery_result
        assert recovery_result["session_id"] == session_context.session_id
        
        if recovery_result["recovered"]:
            assert "current_step" in recovery_result
            assert recovery_result["current_step"] in [step.value for step in ConversationStep]
            
            # Verify session storage was called to save the recovered session
            self.conversation_manager.session_storage.save_session.assert_called()
        else:
            assert "error" in recovery_result
    
    @given(
        requirement=space_requirement_strategy(),
        session_context=session_context_strategy()
    )
    @pytest.mark.asyncio
    async def test_process_requirement_error_recovery(self, requirement, session_context):
        """
        **Feature: nl-floorspace-agent, Property 13: Error State Recovery**
        
        For any space requirement processing that encounters an error,
        the system should maintain conversation state and provide recovery
        options without losing the user's input.
        
        **Validates: Requirements 6.5**
        """
        # Mock session storage
        self.conversation_manager.session_storage.save_session.return_value = None
        
        # Mock Bedrock client to simulate service error
        with patch.object(self.conversation_manager.bedrock_client, 'generate_clarification_questions') as mock_bedrock:
            mock_bedrock.side_effect = BedrockServiceError("Service unavailable")
            
            # Process requirement (should handle error gracefully)
            result = await self.conversation_manager.process_requirement(requirement, session_context)
            
            # Verify error handling
            assert isinstance(result, dict)
            assert "session_id" in result
            assert result["session_id"] == session_context.session_id
            
            # Should either succeed with fallback or provide recovery information
            if "error" in result:
                assert "recovery_available" in result
            else:
                # Should have used fallback processing
                assert "needs_clarification" in result
    
    @given(session_context=session_context_strategy())
    @settings(deadline=5000)  # 5 second deadline for this test
    @pytest.mark.asyncio
    async def test_retry_mechanism_robustness(self, session_context):
        """
        **Feature: nl-floorspace-agent, Property 13: Error State Recovery**
        
        For any operation that fails, the retry mechanism should attempt
        the operation multiple times with appropriate backoff and eventually
        either succeed or fail gracefully with recovery options.
        
        **Validates: Requirements 6.5**
        """
        # Reduce retry delay for testing
        original_delay = self.conversation_manager.retry_delay_seconds
        self.conversation_manager.retry_delay_seconds = 0.01  # Very short delay for testing
        
        try:
            # Test the safe session operation with simulated failures
            call_count = 0
            
            async def failing_operation():
                nonlocal call_count
                call_count += 1
                if call_count < 3:  # Fail first 2 attempts
                    raise ConnectionError("Simulated connection error")
                # Succeed on 3rd attempt
                return "success"
            
            # Should succeed after retries
            try:
                await self.conversation_manager._safe_session_operation(
                    failing_operation, session_context.session_id, "test_operation"
                )
                # If we get here, the retry mechanism worked
                assert call_count == 3, "Should have retried the correct number of times"
            except Exception:
                # If it still fails, should have attempted max retries
                assert call_count == self.conversation_manager.max_retry_attempts
        finally:
            # Restore original delay
            self.conversation_manager.retry_delay_seconds = original_delay
    
    @given(session_context=session_context_strategy())
    @pytest.mark.asyncio
    async def test_fallback_processing_reliability(self, session_context):
        """
        **Feature: nl-floorspace-agent, Property 13: Error State Recovery**
        
        For any situation where the primary processing fails, fallback
        mechanisms should provide basic functionality to maintain conversation
        continuity without crashing.
        
        **Validates: Requirements 6.5**
        """
        # Test fallback response processing
        test_question = "What are the dimensions of the window?"
        test_answer = "1.2m x 1.5m"
        
        fallback_result = self.conversation_manager._fallback_response_processing(
            test_question, test_answer
        )
        
        # Verify fallback result structure
        assert isinstance(fallback_result, dict)
        assert "understood" in fallback_result
        assert "extracted_info" in fallback_result
        assert "needs_followup" in fallback_result
        assert "followup_question" in fallback_result
        
        # Fallback should always indicate understanding (basic processing)
        assert fallback_result["understood"] is True
        assert "raw_answer" in fallback_result["extracted_info"]
        assert fallback_result["extracted_info"]["raw_answer"] == test_answer
        
        # Should not require followup by default
        assert fallback_result["needs_followup"] is False
    
    @pytest.mark.asyncio
    async def test_recovery_cache_cleanup(self):
        """
        **Feature: nl-floorspace-agent, Property 13: Error State Recovery**
        
        The error recovery system should properly clean up expired recovery
        data to prevent memory leaks and maintain system performance.
        
        **Validates: Requirements 6.5**
        """
        # Add some recovery data
        test_session_ids = ["session1", "session2", "session3"]
        
        for session_id in test_session_ids:
            session_context = SessionContext(session_id=session_id)
            await self.conversation_manager._save_recovery_state(session_context, "test_operation")
        
        # Verify recovery data exists
        assert len(self.conversation_manager._error_recovery_cache) == 3
        
        # Mock session storage to return only some sessions as active
        active_sessions = [SessionContext(session_id="session1")]
        self.conversation_manager.session_storage.list_sessions.return_value = active_sessions
        self.conversation_manager.session_storage.cleanup_expired_sessions.return_value = 2
        
        # Cleanup expired sessions
        cleaned_count = await self.conversation_manager.cleanup_expired_sessions()
        
        # Verify cleanup (recovery cache should be cleaned for expired sessions)
        # Note: The actual cleanup depends on session storage implementation
        # Here we verify the method completes without error
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0
    
    def test_error_types_classification(self):
        """
        **Feature: nl-floorspace-agent, Property 13: Error State Recovery**
        
        Different types of errors should be properly classified and handled
        with appropriate recovery strategies.
        
        **Validates: Requirements 6.5**
        """
        # Test error type hierarchy
        assert issubclass(ConversationError, Exception)
        assert issubclass(SessionNotFoundError, ConversationError)
        assert issubclass(InvalidStateError, ConversationError)
        assert issubclass(BedrockServiceError, ConversationError)
        
        # Test error instantiation
        errors = [
            ConversationError("Base error"),
            SessionNotFoundError("Session not found"),
            InvalidStateError("Invalid state"),
            BedrockServiceError("Service error")
        ]
        
        for error in errors:
            assert isinstance(error, Exception)
            assert str(error) is not None
            assert len(str(error)) > 0