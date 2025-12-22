#!/usr/bin/env python3
"""
Fixed interactive demo that works around the conversation flow issues.
This demonstrates the agent working with direct API calls.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nl_floorspace_agent.parser.nl_parser import NaturalLanguageParser
from nl_floorspace_agent.geometry.generator import GeometryGenerator
from nl_floorspace_agent.export.json_exporter import FloorspaceJSONExporter


async def interactive_demo():
    """Interactive demo using direct API calls."""
    print("🏠 Fixed Interactive Demo - Natural Language to Floorspace JSON")
    print("=" * 70)
    print("This demo bypasses conversation flow issues and shows direct functionality.")
    print("Type 'quit' to exit.")
    print()
    
    # Initialize components
    parser = NaturalLanguageParser()
    geometry_generator = GeometryGenerator()
    json_exporter = FloorspaceJSONExporter()
    
    while True:
        try:
            # Get user input
            user_input = input("🏠 Describe your space: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            print(f"\n🔄 Processing: '{user_input}'")
            print("-" * 50)
            
            # Step 1: Parse natural language
            print("1. 🔤 Parsing natural language...")
            parse_result = parser.parse_space_description(user_input)
            
            if not parse_result.is_valid or not parse_result.space_requirement:
                print("   ❌ Could not parse the description")
                if parse_result.validation_result and parse_result.validation_result.errors:
                    for error in parse_result.validation_result.errors:
                        print(f"      • {error.message}")
                print("   💡 Try: 'Create a 5m x 4m bedroom' or 'Make a 10x8 kitchen'")
                continue
            
            requirement = parse_result.space_requirement
            print(f"   ✅ Parsed: {requirement.dimensions.width}x{requirement.dimensions.length}m {requirement.room_type}")
            print(f"      Elements: {len(requirement.elements)} (windows/doors)")
            
            # Step 2: Generate geometry
            print("\n2. 📐 Generating geometry...")
            try:
                building_model = geometry_generator.generate_geometry(requirement)
                
                if building_model and building_model.stories:
                    story = building_model.stories[0]
                    print(f"   ✅ Generated building:")
                    print(f"      • Spaces: {len(story.spaces)}")
                    print(f"      • Vertices: {len(story.geometry.vertices)}")
                    print(f"      • Edges: {len(story.geometry.edges)}")
                    print(f"      • Faces: {len(story.geometry.faces)}")
                else:
                    print("   ❌ Failed to generate geometry")
                    continue
                    
            except Exception as e:
                print(f"   ❌ Geometry error: {e}")
                continue
            
            # Step 3: Export to JSON
            print("\n3. 📄 Exporting to JSON...")
            try:
                floorspace_json = json_exporter.export_to_dict(building_model)
                
                print(f"   ✅ JSON generated:")
                print(f"      • Version: {floorspace_json.get('version')}")
                print(f"      • Stories: {len(floorspace_json.get('stories', []))}")
                
                # Save to file with timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%H%M%S")
                filename = f"room_{timestamp}.json"
                
                import json
                with open(filename, 'w') as f:
                    json.dump(floorspace_json, f, indent=2)
                
                print(f"   💾 Saved to: {filename}")
                
            except Exception as e:
                print(f"   ❌ Export error: {e}")
                continue
            
            print("\n🎉 Success! Your room is ready.")
            print("=" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("Please try again with a different description.")


if __name__ == "__main__":
    asyncio.run(interactive_demo())