"""Integration tests for the FloorspaceAgent end-to-end flows."""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.nl_floorspace_agent.agent import FloorspaceAgent, FloorspaceAgentError, SessionError, ParsingError
from src.nl_floorspace_agent.models import (
    SessionContext, ConversationState, ConversationStep, 
    SpaceRequirement, Dimensions, Units, ElementType, BuildingElement
)


class TestFloorspaceAgentIntegration:
    """Integration tests for complete conversation flows."""
    
    @pytest.fixture
    async def agent(self):
        """Create a FloorspaceAgent instance for testing."""
        with patch('src.nl_floorspace_agent.conversation.bedrock_client.BedrockClient'):
            agent = FloorspaceAgent(aws_region="us-east-1")
            return agent
    
    @pytest.fixture
    def mock_session_context(self):
        """Create a mock session context."""
        session_context = SessionContext(user_id="test_user")
        session_context.conversation_state = ConversationState(
            current_step=ConversationStep.PARSING,
            session_id=session_context.session_id
        )
        return session_context
    
    @pytest.mark.asyncio
    async def test_complete_conversation_flow_simple_room(self, agent, mock_session_context):
        """Test complete flow from description to JSON for a simple room."""
        # Mock the conversation manager to simulate a complete flow
        with patch.object(agent.conversation_manager, 'start_conversation', return_value=mock_session_context), \
             patch.object(agent.conversation_manager, 'orchestrate_conversation_flow') as mock_orchestrate, \
             patch.object(agent, '_generate_building_geometry') as mock_geometry, \
             patch.object(agent.json_exporter, 'export_to_json') as mock_export, \
             patch.object(agent.session_storage, 'save_session') as mock_save:
            
            # Setup mocks
            mock_orchestrate.return_value = {
                "message": "Space created successfully",
                "ready_for_generation": True,
                "session_id": mock_session_context.session_id
            }
            
            mock_building_model = Mock()
            mock_geometry.return_value = mock_building_model
            
            mock_json_output = {"version": "1.4.3", "stories": []}
            mock_export.return_value = mock_json_output
            
            # Test the flow
            description = "Create a 5m x 4m bedroom with one window"
            result = await agent.process_description(description)
            
            # Verify the flow
            assert "message" in result
            assert "floorspace_json" in result
            assert result["generation_complete"] is True
            assert result["floorspace_json"] == mock_json_output
            
            # Verify method calls
            mock_orchestrate.assert_called_once()
            mock_geometry.assert_called_once()
            mock_export.assert_called_once_with(mock_building_model)
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_conversation_flow_with_clarification(self, agent, mock_session_context):
        """Test flow that requires clarification questions."""
        with patch.object(agent.conversation_manager, 'start_conversation', return_value=mock_session_context), \
             patch.object(agent.conversation_manager, 'orchestrate_conversation_flow') as mock_orchestrate:
            
            # First call - needs clarification
            mock_orchestrate.return_value = {
                "message": "I need more information about the window.",
                "questions": ["What are the window dimensions?", "Which wall should the window be on?"],
                "needs_clarification": True,
                "session_id": mock_session_context.session_id
            }
            
            description = "Create a room with a window"
            result = await agent.process_description(description)
            
            # Verify clarification is requested
            assert result["needs_clarification"] is True
            assert "questions" in result
            assert len(result["questions"]) == 2
            assert "window dimensions" in result["questions"][0]
    
    @pytest.mark.asyncio
    async def test_clarification_answer_flow(self, agent, mock_session_context):
        """Test answering clarification questions."""
        with patch.object(agent.conversation_manager, 'orchestrate_conversation_flow') as mock_orchestrate, \
             patch.object(agent, '_generate_building_geometry') as mock_geometry, \
             patch.object(agent.json_exporter, 'export_to_json') as mock_export, \
             patch.object(agent.session_storage, 'get_session', return_value=mock_session_context), \
             patch.object(agent.session_storage, 'save_session') as mock_save:
            
            # Setup mocks for successful generation after clarification
            mock_orchestrate.return_value = {
                "message": "Thank you! Ready to generate your space.",
                "ready_for_generation": True,
                "session_id": mock_session_context.session_id
            }
            
            mock_building_model = Mock()
            mock_geometry.return_value = mock_building_model
            
            mock_json_output = {"version": "1.4.3", "stories": []}
            mock_export.return_value = mock_json_output
            
            # Test answering clarification
            answer = "The window should be 1.5m x 1.2m on the north wall"
            result = await agent.answer_clarification(answer, mock_session_context.session_id)
            
            # Verify successful completion
            assert result["ready_for_generation"] is True
            assert "floorspace_json" in result
            assert result["generation_complete"] is True
    
    @pytest.mark.asyncio
    async def test_multi_space_building_generation(self, agent, mock_session_context):
        """Test generating a building with multiple spaces."""
        with patch.object(agent.conversation_manager, 'start_conversation', return_value=mock_session_context), \
             patch.object(agent.conversation_manager, 'orchestrate_conversation_flow') as mock_orchestrate, \
             patch.object(agent, '_generate_building_geometry') as mock_geometry, \
             patch.object(agent.json_exporter, 'export_to_json') as mock_export, \
             patch.object(agent.session_storage, 'save_session') as mock_save:
            
            # Setup mocks for multi-space generation
            mock_orchestrate.return_value = {
                "message": "Multi-space building ready for generation",
                "ready_for_generation": True,
                "session_id": mock_session_context.session_id
            }
            
            # Mock building model with multiple spaces
            mock_building_model = Mock()
            mock_building_model.stories = [Mock()]
            mock_building_model.stories[0].spaces = [Mock(), Mock()]  # Two spaces
            mock_geometry.return_value = mock_building_model
            
            mock_json_output = {
                "version": "1.4.3", 
                "stories": [{
                    "spaces": [{"name": "bedroom"}, {"name": "bathroom"}]
                }]
            }
            mock_export.return_value = mock_json_output
            
            # Test multi-space description
            description = "Create a bedroom and bathroom connected by a hallway"
            result = await agent.process_description(description)
            
            # Verify multi-space generation
            assert result["generation_complete"] is True
            assert "floorspace_json" in result
            assert len(result["floorspace_json"]["stories"][0]["spaces"]) == 2
    
    @pytest.mark.asyncio
    async def test_error_recovery_during_conversation(self, agent, mock_session_context):
        """Test error recovery during conversation flow."""
        with patch.object(agent.conversation_manager, 'start_conversation', return_value=mock_session_context), \
             patch.object(agent.conversation_manager, 'orchestrate_conversation_flow') as mock_orchestrate:
            
            # Simulate conversation error
            mock_orchestrate.side_effect = Exception("Conversation service unavailable")
            
            description = "Create a 5m x 4m room"
            result = await agent.process_description(description)
            
            # Verify error handling
            assert "error" in result
            assert "message" in result
            assert "recovery_suggestions" in result
            assert result["error_type"] == "ConversationError"
            assert "Conversation processing failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_geometry_generation_error_recovery(self, agent, mock_session_context):
        """Test error recovery during geometry generation."""
        with patch.object(agent.conversation_manager, 'start_conversation', return_value=mock_session_context), \
             patch.object(agent.conversation_manager, 'orchestrate_conversation_flow') as mock_orchestrate, \
             patch.object(agent, '_generate_building_geometry') as mock_geometry, \
             patch.object(agent.session_storage, 'get_session', return_value=mock_session_context):
            
            # Setup mocks
            mock_orchestrate.return_value = {
                "ready_for_generation": True,
                "session_id": mock_session_context.session_id
            }
            
            # Simulate geometry generation error
            mock_geometry.side_effect = Exception("Invalid space dimensions")
            
            description = "Create a room"
            result = await agent.process_description(description)
            
            # Verify error handling
            assert "error" in result
            assert "geometry" in result["error"].lower()
            assert "recovery_suggestions" in result
    
    @pytest.mark.asyncio
    async def test_json_export_error_recovery(self, agent, mock_session_context):
        """Test error recovery during JSON export."""
        with patch.object(agent.conversation_manager, 'start_conversation', return_value=mock_session_context), \
             patch.object(agent.conversation_manager, 'orchestrate_conversation_flow') as mock_orchestrate, \
             patch.object(agent, '_generate_building_geometry') as mock_geometry, \
             patch.object(agent.json_exporter, 'export_to_json') as mock_export, \
             patch.object(agent.session_storage, 'get_session', return_value=mock_session_context):
            
            # Setup mocks
            mock_orchestrate.return_value = {
                "ready_for_generation": True,
                "session_id": mock_session_context.session_id
            }
            
            mock_building_model = Mock()
            mock_geometry.return_value = mock_building_model
            
            # Simulate JSON export error
            mock_export.side_effect = Exception("Invalid JSON structure")
            
            description = "Create a room"
            result = await agent.process_description(description)
            
            # Verify error handling
            assert "error" in result
            assert "export" in result["error"].lower()
            assert "recovery_suggestions" in result
    
    @pytest.mark.asyncio
    async def test_session_management_flow(self, agent):
        """Test session creation, status, and cleanup."""
        with patch.object(agent.conversation_manager, 'start_conversation') as mock_start, \
             patch.object(agent.conversation_manager, 'get_session_status') as mock_status, \
             patch.object(agent.conversation_manager, 'reset_conversation') as mock_reset, \
             patch.object(agent.conversation_manager, 'cleanup_expired_sessions') as mock_cleanup:
            
            # Test session creation
            mock_session = Mock()
            mock_session.session_id = "test_session_123"
            mock_session.user_id = "test_user"
            mock_session.created_at = datetime.now()
            mock_start.return_value = mock_session
            
            result = await agent.start_new_session("test_user")
            assert result["session_id"] == "test_session_123"
            assert result["user_id"] == "test_user"
            
            # Test session status
            mock_status.return_value = {
                "session_id": "test_session_123",
                "current_step": "parsing",
                "pending_questions": 0
            }
            
            status = await agent.get_session_status("test_session_123")
            assert status["session_id"] == "test_session_123"
            assert status["current_step"] == "parsing"
            
            # Test session reset
            mock_reset.return_value = {
                "message": "Session reset successfully",
                "session_id": "test_session_123"
            }
            
            reset_result = await agent.reset_session("test_session_123")
            assert reset_result["session_id"] == "test_session_123"
            
            # Test cleanup
            mock_cleanup.return_value = 5
            cleanup_result = await agent.cleanup_expired_sessions()
            assert cleanup_result["cleaned_sessions"] == 5
    
    @pytest.mark.asyncio
    async def test_input_validation_errors(self, agent):
        """Test input validation and error handling."""
        # Test empty description
        result = await agent.process_description("")
        assert "error" in result
        assert "Empty description" in result["error"]
        
        # Test too short description
        result = await agent.process_description("hi")
        assert "error" in result
        assert "too short" in result["error"]
        
        # Test too long description
        long_description = "x" * 10001
        result = await agent.process_description(long_description)
        assert "error" in result
        assert "too long" in result["error"]
        
        # Test invalid session ID
        result = await agent.answer_clarification("test answer", "invalid@session#id")
        assert "error" in result
        assert "Invalid session ID" in result["error"]
    
    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, agent):
        """Test error statistics tracking."""
        # Initial state
        stats = agent.get_error_statistics()
        assert stats["error_counts"]["total_errors"] == 0
        
        # Trigger some errors
        await agent.process_description("")  # Parsing error
        await agent.get_session_status("invalid@id")  # Session error
        
        # Check updated statistics
        stats = agent.get_error_statistics()
        assert stats["error_counts"]["total_errors"] == 2
        assert stats["error_counts"]["parsing_errors"] == 1
        assert stats["error_counts"]["session_errors"] == 1
        assert stats["last_error_time"] is not None
        
        # Reset statistics
        agent.reset_error_statistics()
        stats = agent.get_error_statistics()
        assert stats["error_counts"]["total_errors"] == 0
    
    @pytest.mark.asyncio
    async def test_building_summary_retrieval(self, agent, mock_session_context):
        """Test building summary retrieval."""
        # Mock building model
        mock_building_model = Mock()
        mock_building_model.stories = [Mock()]
        mock_building_model.stories[0].spaces = [Mock(), Mock()]
        mock_building_model.stories[0].windows = [Mock()]
        mock_building_model.stories[0].doors = [Mock()]
        
        mock_session_context.conversation_state.building_model = mock_building_model
        
        with patch.object(agent.session_storage, 'get_session', return_value=mock_session_context):
            # Test with async wrapper (simplified for testing)
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.is_running.return_value = False
                mock_loop.return_value.run_until_complete.return_value = {
                    "spaces_count": 2,
                    "windows_count": 1,
                    "doors_count": 1,
                    "session_id": mock_session_context.session_id
                }
                
                result = agent.get_building_summary(mock_session_context.session_id)
                assert result["spaces_count"] == 2
                assert result["windows_count"] == 1
                assert result["doors_count"] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self, agent):
        """Test handling multiple concurrent sessions."""
        with patch.object(agent.conversation_manager, 'start_conversation') as mock_start:
            
            # Create multiple sessions concurrently
            sessions = []
            for i in range(5):
                mock_session = Mock()
                mock_session.session_id = f"session_{i}"
                mock_session.user_id = f"user_{i}"
                mock_session.created_at = datetime.now()
                sessions.append(mock_session)
            
            mock_start.side_effect = sessions
            
            # Start sessions concurrently
            tasks = [agent.start_new_session(f"user_{i}") for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Verify all sessions were created
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result["session_id"] == f"session_{i}"
                assert result["user_id"] == f"user_{i}"
    
    @pytest.mark.asyncio
    async def test_workflow_diagnostics(self, agent):
        """Test workflow diagnostics and monitoring."""
        # Get initial diagnostics
        diagnostics = agent.get_workflow_diagnostics()
        
        # Verify diagnostic structure
        assert "workflow_status" in diagnostics
        assert "error_details" in diagnostics
        assert "task_execution_times" in diagnostics
        assert "circuit_breaker_details" in diagnostics
        
        # Verify workflow status structure
        workflow_status = diagnostics["workflow_status"]
        assert "total_tasks" in workflow_status
        assert "completed" in workflow_status
        assert "failed" in workflow_status
        assert "task_statuses" in workflow_status


class TestAgentErrorScenarios:
    """Test various error scenarios and recovery mechanisms."""
    
    @pytest.fixture
    async def agent(self):
        """Create a FloorspaceAgent instance for testing."""
        with patch('src.nl_floorspace_agent.conversation.bedrock_client.BedrockClient'):
            agent = FloorspaceAgent(aws_region="us-east-1")
            return agent
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test agent initialization failure handling."""
        with patch('src.nl_floorspace_agent.conversation.manager.ConversationManager.__init__', side_effect=Exception("AWS connection failed")):
            with pytest.raises(FloorspaceAgentError) as exc_info:
                FloorspaceAgent(aws_region="us-east-1")
            
            assert "Initialization failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_network_timeout_recovery(self, agent):
        """Test recovery from network timeouts."""
        with patch.object(agent.conversation_manager, 'start_conversation', side_effect=TimeoutError("Network timeout")):
            
            result = await agent.start_new_session("test_user")
            
            # Verify timeout error handling
            assert "error" in result
            assert "session" in result["message"].lower()
            assert len(result.get("recovery_suggestions", [])) > 0
            # Check that we have reasonable recovery suggestions
            suggestions = result.get("recovery_suggestions", [])
            assert any("session" in suggestion.lower() for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_service_unavailable_recovery(self, agent):
        """Test recovery from service unavailability."""
        with patch.object(agent.conversation_manager, 'orchestrate_conversation_flow', 
                         side_effect=ConnectionError("Service unavailable")):
            
            result = await agent.process_description("Create a room")
            
            # Verify service error handling
            assert "error" in result
            assert "conversation" in result["message"].lower()
            assert any("connection" in suggestion for suggestion in result["recovery_suggestions"])
    
    @pytest.mark.asyncio
    async def test_malformed_input_handling(self, agent):
        """Test handling of malformed or suspicious input."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:void(0)",
            "data:text/html,<script>alert(1)</script>"
        ]
        
        for malicious_input in malicious_inputs:
            result = await agent.process_description(malicious_input)
            assert "error" in result
            assert "Invalid characters" in result["error"]