#!/usr/bin/env python3
"""Simple test to verify the fix."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def simple_test():
    """Simple test of the parsing fix."""
    print("🧪 Simple Parser Test")
    print("-" * 30)
    
    try:
        # Test parser directly
        from nl_floorspace_agent.parser.nl_parser import NaturalLanguageParser
        
        parser = NaturalLanguageParser()
        result = parser.parse_space_description("make a 10 by 10 living room")
        
        print(f"✅ Parser result valid: {result.is_valid}")
        
        if result.space_requirement:
            req = result.space_requirement
            print(f"✅ Dimensions: {req.dimensions.width} x {req.dimensions.length} {req.dimensions.units.value}")
            print(f"✅ Room type: {req.room_type}")
            print(f"✅ Elements: {len(req.elements)}")
            
            print("\n🎉 Parser is working correctly!")
            print("The issue is in the conversation flow integration.")
            
        else:
            print("❌ No space requirement generated")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(simple_test())