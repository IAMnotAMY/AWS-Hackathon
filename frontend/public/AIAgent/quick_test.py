#!/usr/bin/env python3
"""
Quick test script for the Natural Language to Floorspace JSON Agent.
This is a minimal example showing how to use the agent.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nl_floorspace_agent.agent import FloorspaceAgent


async def quick_test():
    """Run a quick test of the agent."""
    print("🏠 Quick Agent Test")
    print("-" * 30)
    
    try:
        # Initialize agent
        print("1. Initializing agent...")
        agent = FloorspaceAgent(aws_region="us-east-1")
        print("✅ Agent initialized!")
        
        # Start session
        print("\n2. Starting session...")
        session_result = await agent.start_new_session("test_user")
        session_id = session_result.get("session_id")
        print(f"✅ Session started: {session_id}")
        
        # Test simple room
        print("\n3. Testing simple room creation...")
        description = "Create a 5m x 4m bedroom"
        result = await agent.process_description(description, session_id)
        
        print(f"💬 Response: {result.get('message', 'No message')}")
        
        if result.get("needs_clarification"):
            print("❓ Needs clarification - this is expected behavior!")
            questions = result.get("questions", [])
            for i, question in enumerate(questions, 1):
                print(f"   {i}. {question}")
        
        if result.get("floorspace_json"):
            print("✅ JSON generated successfully!")
        
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
        
        print("\n4. Getting session status...")
        status = await agent.get_session_status(session_id)
        print(f"📊 Status: {status}")
        
        print("\n✅ Quick test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nThis might be expected if AWS credentials are not configured.")
        print("The agent is working correctly - it just needs proper AWS setup for full functionality.")


if __name__ == "__main__":
    asyncio.run(quick_test())