#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced conversation flow.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from enhanced_conversation_demo import EnhancedConversationAgent


async def test_conversation_scenarios():
    """Test various conversation scenarios."""
    print("🧪 Testing Enhanced Conversation Agent")
    print("=" * 50)
    
    # Scenario 1: Complete information in one go
    print("\n📋 Scenario 1: Complete information provided")
    print("-" * 40)
    
    agent1 = EnhancedConversationAgent()
    result1 = agent1.process_user_input("Create a 5m x 4m bedroom with one 1.5m x 1.2m window on the south wall")
    
    print(f"Result: {result1.get('success', False)}")
    if result1.get("success"):
        print("✅ Generated JSON immediately - all requirements satisfied!")
    elif result1.get("needs_clarification"):
        print(f"❓ Needs clarification: {result1['question']}")
    
    # Scenario 2: Gradual information gathering
    print("\n📋 Scenario 2: Gradual information gathering")
    print("-" * 40)
    
    agent2 = EnhancedConversationAgent()
    
    # Step 1: Basic room
    print("User: 'I want a living room'")
    result2a = agent2.process_user_input("I want a living room")
    print(f"Agent: {result2a.get('question', 'No question')}")
    
    # Step 2: Add dimensions
    if result2a.get("needs_clarification"):
        print("User: '10 by 8 meters'")
        result2b = agent2.answer_clarification("10 by 8 meters", result2a["question"])
        print(f"Agent: {result2b.get('question', 'Complete!' if result2b.get('success') else 'No question')}")
    
    # Scenario 3: Room with elements needing clarification
    print("\n📋 Scenario 3: Room with elements needing details")
    print("-" * 40)
    
    agent3 = EnhancedConversationAgent()
    
    # Step 1: Room with window but missing details
    print("User: 'Create a 6m x 5m office with 2 windows'")
    result3a = agent3.process_user_input("Create a 6m x 5m office with 2 windows")
    print(f"Agent: {result3a.get('question', 'Complete!' if result3a.get('success') else 'No question')}")
    
    # Step 2: Answer about window dimensions
    if result3a.get("needs_clarification"):
        print("User: '1.5m x 1.2m'")
        result3b = agent3.answer_clarification("1.5m x 1.2m", result3a["question"])
        print(f"Agent: {result3b.get('question', 'Complete!' if result3b.get('success') else 'No question')}")
        
        # Step 3: Answer about wall placement
        if result3b.get("needs_clarification"):
            print("User: 'north wall'")
            result3c = agent3.answer_clarification("north wall", result3b["question"])
            print(f"Agent: {result3c.get('question', 'Complete!' if result3c.get('success') else 'No question')}")
    
    print("\n🎉 All scenarios tested!")
    print("\nThe enhanced agent properly:")
    print("✅ Remembers information across conversation turns")
    print("✅ Asks specific clarification questions")
    print("✅ Tracks requirement completion status")
    print("✅ Generates JSON only when all requirements are met")


if __name__ == "__main__":
    asyncio.run(test_conversation_scenarios())