#!/usr/bin/env python3
"""
Test script to verify window and door generation in Floorspace JSON.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from enhanced_conversation_demo import EnhancedConversationAgent


async def test_window_door_generation():
    """Test that windows and doors are properly included in the generated JSON."""
    print("🧪 Testing Window and Door Generation")
    print("=" * 50)
    
    agent = EnhancedConversationAgent()
    
    # Step 1: Create room with window
    print("1. Creating room with window...")
    result1 = agent.process_user_input("Create a 5m x 4m bedroom with one window")
    
    if result1.get("needs_clarification"):
        print(f"   Question: {result1['question']}")
        
        # Answer window dimensions
        result2 = agent.answer_clarification("1.5m x 1.2m", result1["question"])
        
        if result2.get("needs_clarification"):
            print(f"   Question: {result2['question']}")
            
            # Answer wall placement
            result3 = agent.answer_clarification("south wall", result2["question"])
            
            if result3.get("success"):
                print("   ✅ Room with window generated successfully!")
                
                # Check the JSON output
                floorspace_json = result3["floorspace_json"]
                
                print("\n📋 Checking JSON Output:")
                print(f"   Stories: {len(floorspace_json.get('stories', []))}")
                
                if floorspace_json.get("stories"):
                    story = floorspace_json["stories"][0]
                    print(f"   Spaces: {len(story.get('spaces', []))}")
                    print(f"   Windows: {len(story.get('windows', []))}")
                    print(f"   Doors: {len(story.get('doors', []))}")
                    print(f"   Window Definitions: {len(floorspace_json.get('window_definitions', []))}")
                    print(f"   Door Definitions: {len(floorspace_json.get('door_definitions', []))}")
                    
                    # Show window details
                    if story.get('windows'):
                        for i, window in enumerate(story['windows']):
                            print(f"   Window {i+1}: {window}")
                    
                    if floorspace_json.get('window_definitions'):
                        for i, window_def in enumerate(floorspace_json['window_definitions']):
                            print(f"   Window Definition {i+1}: {window_def}")
                
                # Save for inspection
                with open("test_room_with_window.json", "w") as f:
                    json.dump(floorspace_json, f, indent=2)
                print(f"\n💾 Saved test output to: test_room_with_window.json")
                
                return True
    
    print("❌ Test failed - could not complete conversation")
    return False


async def test_room_with_door():
    """Test room with door generation."""
    print("\n🧪 Testing Room with Door")
    print("-" * 30)
    
    agent = EnhancedConversationAgent()
    
    # Create room with door in one go
    result = agent.process_user_input("Create a 4m x 3m bathroom with one 0.8m x 2.0m door on the east wall")
    
    if result.get("success"):
        print("✅ Room with door generated successfully!")
        
        floorspace_json = result["floorspace_json"]
        story = floorspace_json["stories"][0]
        
        print(f"   Doors: {len(story.get('doors', []))}")
        print(f"   Door Definitions: {len(floorspace_json.get('door_definitions', []))}")
        
        if story.get('doors'):
            for i, door in enumerate(story['doors']):
                print(f"   Door {i+1}: {door}")
        
        return True
    else:
        print(f"❌ Failed: {result}")
        return False


if __name__ == "__main__":
    asyncio.run(test_window_door_generation())
    asyncio.run(test_room_with_door())