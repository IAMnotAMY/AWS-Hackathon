#!/usr/bin/env python3
"""
Debug script to trace the conversation flow.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nl_floorspace_agent.agent import FloorspaceAgent


async def debug_conversation():
    """Debug the conversation flow step by step."""
    print("🔍 Debugging Conversation Flow")
    print("=" * 50)
    
    try:
        # Initialize agent
        print("1. Initializing agent...")
        agent = FloorspaceAgent(aws_region="us-east-1")
        print("   ✅ Agent initialized")
        
        # Start session
        print("\n2. Starting session...")
        session_result = await agent.start_new_session("debug_user")
        session_id = session_result["session_id"]
        print(f"   ✅ Session ID: {session_id}")
        
        # Test the natural language parser directly
        print("\n3. Testing parser directly...")
        from nl_floorspace_agent.parser.nl_parser import NaturalLanguageParser
        
        parser = NaturalLanguageParser()
        parse_result = parser.parse_space_description("make a 10 by 10 living room")
        
        print(f"   Parse result valid: {parse_result.is_valid}")
        if parse_result.space_requirement:
            req = parse_result.space_requirement
            print(f"   Dimensions: {req.dimensions.width} x {req.dimensions.length}")
            print(f"   Room type: {req.room_type}")
            print(f"   Elements: {len(req.elements)}")
        else:
            print("   No space requirement generated")
            if parse_result.validation_result:
                for error in parse_result.validation_result.errors:
                    print(f"   Error: {error.message}")
        
        # Test conversation manager directly
        print("\n4. Testing conversation manager...")
        session_context = await agent.session_storage.get_session(session_id)
        if session_context:
            print(f"   Session found: {session_context.session_id}")
            print(f"   Conversation state: {session_context.conversation_state is not None}")
            
            if session_context.conversation_state:
                state = session_context.conversation_state
                print(f"   Current step: {state.current_step}")
                print(f"   Pending questions: {len(state.pending_questions)}")
                print(f"   Collected specs: {len(state.collected_specs)}")
        else:
            print("   ❌ Session not found!")
        
        # Test the full flow
        print("\n5. Testing full conversation flow...")
        result = await agent.process_description("make a 10 by 10 living room", session_id)
        
        print(f"   Result keys: {list(result.keys())}")
        print(f"   Message: {result.get('message', 'No message')}")
        print(f"   Error: {result.get('error', 'No error')}")
        print(f"   Needs clarification: {result.get('needs_clarification', False)}")
        
        # Check session state after processing
        print("\n6. Checking session state after processing...")
        session_context = await agent.session_storage.get_session(session_id)
        if session_context and session_context.conversation_state:
            state = session_context.conversation_state
            print(f"   Current step: {state.current_step}")
            print(f"   Pending questions: {len(state.pending_questions)}")
            print(f"   Collected specs: {len(state.collected_specs)}")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_conversation())