#!/usr/bin/env python3
"""
Offline testing script for the Natural Language to Floorspace JSON Agent.
This script tests the agent without requiring AWS credentials by mocking external dependencies.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nl_floorspace_agent.agent import FloorspaceAgent
from nl_floorspace_agent.models import SessionContext, ConversationState, ConversationStep


async def test_agent_offline():
    """Test the agent with mocked dependencies."""
    print("🏠 Offline Agent Test (No AWS Required)")
    print("-" * 50)
    
    try:
        # Mock the Bedrock client to avoid AWS dependency
        with patch('src.nl_floorspace_agent.conversation.bedrock_client.BedrockClient'):
            print("1. Initializing agent with mocked AWS...")
            agent = FloorspaceAgent(aws_region="us-east-1")
            print("✅ Agent initialized!")
            
            # Create a mock session context
            mock_session = SessionContext(user_id="test_user")
            mock_session.conversation_state = ConversationState(
                current_step=ConversationStep.PARSING,
                session_id=mock_session.session_id
            )
            
            # Test input validation
            print("\n2. Testing input validation...")
            
            # Test empty input
            result = await agent.process_description("")
            assert "error" in result
            assert "Empty description" in result["error"]
            print("✅ Empty input validation works")
            
            # Test too short input
            result = await agent.process_description("hi")
            assert "error" in result
            assert "too short" in result["error"]
            print("✅ Short input validation works")
            
            # Test too long input
            long_input = "x" * 10001
            result = await agent.process_description(long_input)
            assert "error" in result
            assert "too long" in result["error"]
            print("✅ Long input validation works")
            
            # Test invalid session ID
            result = await agent.answer_clarification("test", "invalid@session")
            assert "error" in result
            assert "Invalid session ID" in result["error"]
            print("✅ Session ID validation works")
            
            print("\n3. Testing error statistics...")
            stats = agent.get_error_statistics()
            assert "error_counts" in stats
            assert stats["error_counts"]["total_errors"] > 0
            print(f"✅ Error statistics: {stats['error_counts']['total_errors']} total errors tracked")
            
            # Reset statistics
            agent.reset_error_statistics()
            stats = agent.get_error_statistics()
            assert stats["error_counts"]["total_errors"] == 0
            print("✅ Error statistics reset works")
            
            print("\n4. Testing workflow diagnostics...")
            diagnostics = agent.get_workflow_diagnostics()
            assert "workflow_status" in diagnostics
            assert "error_details" in diagnostics
            print("✅ Workflow diagnostics available")
            
            print("\n5. Testing with mocked conversation flow...")
            
            # Mock the conversation manager methods
            with patch.object(agent.conversation_manager, 'start_conversation', return_value=mock_session), \
                 patch.object(agent.conversation_manager, 'orchestrate_conversation_flow') as mock_orchestrate:
                
                # Test successful flow
                mock_orchestrate.return_value = {
                    "message": "Space created successfully",
                    "needs_clarification": False,
                    "session_id": mock_session.session_id
                }
                
                result = await agent.process_description("Create a 5m x 4m room")
                assert "message" in result
                assert result["session_id"] == mock_session.session_id
                print("✅ Mocked conversation flow works")
                
                # Test clarification flow
                mock_orchestrate.return_value = {
                    "message": "I need more information",
                    "questions": ["What type of room?", "Any windows?"],
                    "needs_clarification": True,
                    "session_id": mock_session.session_id
                }
                
                result = await agent.process_description("Create a room")
                assert result["needs_clarification"] is True
                assert len(result["questions"]) == 2
                print("✅ Mocked clarification flow works")
            
            print("\n✅ All offline tests passed!")
            print("\n📋 Summary:")
            print("   • Input validation: Working ✅")
            print("   • Error handling: Working ✅")
            print("   • Error statistics: Working ✅")
            print("   • Workflow diagnostics: Working ✅")
            print("   • Conversation flow: Working ✅ (mocked)")
            print("\n💡 To test with real AWS integration:")
            print("   1. Set up AWS credentials")
            print("   2. Configure Bedrock access")
            print("   3. Run: python test_agent_manual.py")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agent_offline())