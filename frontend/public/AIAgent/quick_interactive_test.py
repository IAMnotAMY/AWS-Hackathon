#!/usr/bin/env python3
"""Quick interactive test to verify the fix."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nl_floorspace_agent.agent import FloorspaceAgent


async def quick_interactive_test():
    """Quick test of the interactive flow."""
    print("🧪 Quick Interactive Test")
    print("-" * 50)
    
    try:
        # Initialize agent
        print("1. Initializing agent...")
        agent = FloorspaceAgent(aws_region="us-east-1")
        print("   ✅ Agent initialized")
        
        # Start session
        print("\n2. Starting session...")
        session_result = await agent.start_new_session("test_user")
        session_id = session_result["session_id"]
        print(f"   ✅ Session: {session_id}")
        
        # Test description
        print("\n3. Processing: 'make a 10 x 10 living room'")
        result = await agent.process_description("make a 10 x 10 living room", session_id)
        
        print(f"\n📋 Result:")
        print(f"   Message: {result.get('message', 'No message')}")
        
        if result.get("error"):
            print(f"   ❌ Error: {result['error']}")
        else:
            print(f"   ✅ Success!")
        
        if result.get("needs_clarification"):
            print(f"   ❓ Needs clarification")
            for q in result.get("questions", []):
                print(f"      • {q}")
        
        if result.get("floorspace_json"):
            print(f"   🎉 JSON generated!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(quick_interactive_test())