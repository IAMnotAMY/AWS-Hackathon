#!/usr/bin/env python3
"""
Enhanced conversation demo that properly handles requirements gathering.
This implements the full conversational flow with memory and clarification.
"""

import asyncio
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nl_floorspace_agent.parser.nl_parser import NaturalLanguageParser
from nl_floorspace_agent.geometry.generator import GeometryGenerator
from nl_floorspace_agent.export.json_exporter import FloorspaceJSONExporter
from nl_floorspace_agent.models import SpaceRequirement, Dimensions, Units, BuildingElement, ElementType, ElementSpec


class RequirementStatus(Enum):
    MISSING = "missing"
    PARTIAL = "partial"
    COMPLETE = "complete"


@dataclass
class ConversationMemory:
    """Stores conversation memory and tracks requirements."""
    
    # Core requirements
    room_dimensions: Optional[Dimensions] = None
    room_position: Optional[str] = None  # e.g., "at origin", "next to bedroom"
    room_type: Optional[str] = None
    
    # Elements (windows/doors)
    elements: List[BuildingElement] = field(default_factory=list)
    
    # Conversation history
    user_inputs: List[str] = field(default_factory=list)
    clarification_history: List[Dict[str, str]] = field(default_factory=list)
    
    def add_user_input(self, text: str):
        """Add user input to memory."""
        self.user_inputs.append(text)
    
    def add_clarification(self, question: str, answer: str):
        """Add clarification Q&A to memory."""
        self.clarification_history.append({"question": question, "answer": answer})
    
    def get_requirement_status(self) -> Dict[str, RequirementStatus]:
        """Check status of all requirements."""
        status = {}
        
        # 1. Room dimensions
        if self.room_dimensions and self.room_dimensions.width > 0 and self.room_dimensions.length > 0:
            status["dimensions"] = RequirementStatus.COMPLETE
        else:
            status["dimensions"] = RequirementStatus.MISSING
        
        # 2. Room position (optional for first room)
        if self.room_position:
            status["position"] = RequirementStatus.COMPLETE
        else:
            status["position"] = RequirementStatus.MISSING
        
        # 3. Elements (windows/doors) - check if any are incomplete
        if not self.elements:
            status["elements"] = RequirementStatus.COMPLETE  # No elements is valid
        else:
            all_complete = True
            for element in self.elements:
                if not element.specifications:
                    all_complete = False
                    break
                spec = element.specifications
                if not spec.width or not spec.height or not spec.wall:
                    all_complete = False
                    break
            
            status["elements"] = RequirementStatus.COMPLETE if all_complete else RequirementStatus.PARTIAL
        
        return status
    
    def is_complete(self) -> bool:
        """Check if all requirements are satisfied."""
        status = self.get_requirement_status()
        # Position is optional for first room
        required_complete = ["dimensions", "elements"]
        return all(status.get(req) == RequirementStatus.COMPLETE for req in required_complete)
    
    def get_missing_requirements(self) -> List[str]:
        """Get list of missing requirements."""
        status = self.get_requirement_status()
        missing = []
        
        if status["dimensions"] != RequirementStatus.COMPLETE:
            missing.append("room dimensions (width x length)")
        
        if status["elements"] == RequirementStatus.PARTIAL:
            missing.append("window/door specifications (dimensions and wall placement)")
        
        return missing


class EnhancedConversationAgent:
    """Enhanced agent with proper conversation flow and memory."""
    
    def __init__(self):
        """Initialize the enhanced agent."""
        self.parser = NaturalLanguageParser()
        self.geometry_generator = GeometryGenerator()
        self.json_exporter = FloorspaceJSONExporter()
        self.memory = ConversationMemory()
        self.session_id = "enhanced_session_001"
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input and return response with next steps."""
        if user_input:  # Only print if there's actual input
            print(f"\n🔄 Processing: '{user_input}'")
        
        # Add to memory
        if user_input:
            self.memory.add_user_input(user_input)
        
        # Parse the input if provided
        if user_input:
            parse_result = self.parser.parse_space_description(user_input)
            
            # Update memory with parsed information
            if parse_result.is_valid and parse_result.space_requirement:
                req = parse_result.space_requirement
                
                # Update dimensions if found
                if req.dimensions and req.dimensions.width > 0:
                    self.memory.room_dimensions = req.dimensions
                    print(f"   📏 Captured dimensions: {req.dimensions.width}x{req.dimensions.length}m")
                
                # Update room type if found
                if req.room_type:
                    self.memory.room_type = req.room_type
                    print(f"   🏠 Captured room type: {req.room_type}")
                
                # Update elements if found
                if req.elements:
                    for element in req.elements:
                        # Check if we already have this type of element
                        existing = next((e for e in self.memory.elements if e.type == element.type), None)
                        if existing:
                            # Update existing element with more complete specifications
                            if element.specifications and element.specifications.width:
                                if not existing.specifications:
                                    existing.specifications = ElementSpec()
                                existing.specifications.width = element.specifications.width
                                existing.specifications.height = element.specifications.height
                                existing.specifications.wall = element.specifications.wall
                                existing.specifications.alpha = element.specifications.alpha
                        else:
                            # Add new element
                            self.memory.elements.append(element)
                    
                    print(f"   🪟 Captured elements: {len(req.elements)} items")
                    
                    # Show element details
                    for elem in req.elements:
                        if elem.specifications:
                            spec = elem.specifications
                            details = []
                            if spec.width and spec.height:
                                details.append(f"{spec.width}x{spec.height}m")
                            if spec.wall:
                                details.append(f"{spec.wall} wall")
                            if details:
                                print(f"      • {elem.type.value}: {', '.join(details)}")
        
        # Check requirement status
        status = self.memory.get_requirement_status()
        missing = self.memory.get_missing_requirements()
        
        if user_input:  # Only print status if there was input
            print(f"   📊 Status: Dimensions={status['dimensions'].value}, Elements={status['elements'].value}")
        
        if self.memory.is_complete():
            # All requirements satisfied - generate output
            return self._generate_final_output()
        else:
            # Generate clarification questions
            return self._generate_clarification_questions(missing)
    
    def _generate_clarification_questions(self, missing: List[str]) -> Dict[str, Any]:
        """Generate appropriate clarification questions."""
        questions = []
        
        # Check what's missing and ask specific questions
        status = self.memory.get_requirement_status()
        
        if status["dimensions"] != RequirementStatus.COMPLETE:
            if not self.memory.room_dimensions:
                questions.append("What are the dimensions of the room? (e.g., '5m x 4m' or '10 by 8 feet')")
            elif self.memory.room_dimensions.width <= 0:
                questions.append("What is the width and length of the room?")
        
        if status["elements"] == RequirementStatus.PARTIAL:
            # Check each element for missing specifications
            for i, element in enumerate(self.memory.elements):
                if not element.specifications:
                    element_name = f"{element.type.value} #{i+1}" if element.count > 1 else element.type.value
                    questions.append(f"What are the dimensions of the {element_name}? (width x height)")
                    questions.append(f"Which wall should the {element_name} be placed on? (north, south, east, west)")
                else:
                    spec = element.specifications
                    if not spec.width or not spec.height:
                        element_name = f"{element.type.value} #{i+1}" if element.count > 1 else element.type.value
                        questions.append(f"What are the dimensions of the {element_name}? (width x height)")
                    if not spec.wall:
                        element_name = f"{element.type.value} #{i+1}" if element.count > 1 else element.type.value
                        questions.append(f"Which wall should the {element_name} be placed on? (north, south, east, west)")
        
        # Return the first question (ask one at a time for better UX)
        if questions:
            return {
                "needs_clarification": True,
                "question": questions[0],
                "all_questions": questions,
                "memory_summary": self._get_memory_summary(),
                "session_id": self.session_id
            }
        else:
            return self._generate_final_output()
    
    def _get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of what's been captured so far."""
        summary = {
            "room_type": self.memory.room_type,
            "dimensions": None,
            "elements": [],
            "conversation_turns": len(self.memory.user_inputs)
        }
        
        if self.memory.room_dimensions:
            summary["dimensions"] = f"{self.memory.room_dimensions.width}x{self.memory.room_dimensions.length}m"
        
        for element in self.memory.elements:
            element_info = {
                "type": element.type.value,
                "count": element.count,
                "specifications": None
            }
            if element.specifications:
                spec = element.specifications
                element_info["specifications"] = {
                    "dimensions": f"{spec.width}x{spec.height}m" if spec.width and spec.height else "missing",
                    "wall": spec.wall or "missing"
                }
            summary["elements"].append(element_info)
        
        return summary
    
    def _generate_final_output(self) -> Dict[str, Any]:
        """Generate the final Floorspace JSON output."""
        print("\n🎉 All requirements satisfied! Generating Floorspace JSON...")
        
        try:
            # Create space requirement from memory
            space_requirement = SpaceRequirement(
                dimensions=self.memory.room_dimensions,
                elements=self.memory.elements,
                room_type=self.memory.room_type or "room",
                placement=self.memory.room_position
            )
            
            # Generate geometry
            building_model = self.geometry_generator.generate_geometry(space_requirement)
            
            # Export to JSON
            floorspace_json = self.json_exporter.export_to_dict(building_model)
            
            # Save to file
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"room_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(floorspace_json, f, indent=2)
            
            return {
                "success": True,
                "message": f"🎉 Room created successfully! Saved to {filename}",
                "floorspace_json": floorspace_json,
                "filename": filename,
                "memory_summary": self._get_memory_summary(),
                "session_id": self.session_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate room: {str(e)}",
                "session_id": self.session_id
            }
    
    def answer_clarification(self, answer: str, previous_question: str) -> Dict[str, Any]:
        """Process an answer to a clarification question."""
        print(f"\n💬 Answer: '{answer}'")
        
        # Add to clarification history
        self.memory.add_clarification(previous_question, answer)
        
        # Parse the answer to extract information
        parse_result = self.parser.parse_space_description(answer)
        
        # Try to extract specific information based on the question type
        if "dimensions" in previous_question.lower():
            # Extract dimensions
            if parse_result.is_valid and parse_result.space_requirement and parse_result.space_requirement.dimensions:
                dims = parse_result.space_requirement.dimensions
                if "room" in previous_question.lower():
                    self.memory.room_dimensions = dims
                    print(f"   📏 Updated room dimensions: {dims.width}x{dims.length}m")
                else:
                    # Update element dimensions
                    self._update_element_dimensions(answer, dims)
        
        elif "wall" in previous_question.lower():
            # Extract wall information
            wall = self._extract_wall_from_answer(answer)
            if wall:
                self._update_element_wall(previous_question, wall)
                print(f"   🧱 Updated wall placement: {wall}")
        
        # Continue the conversation flow
        return self.process_user_input("")  # Empty input to just check status
    
    def _update_element_dimensions(self, answer: str, dimensions: Dimensions):
        """Update element dimensions based on answer."""
        # Find the most recent element without complete dimensions
        for element in reversed(self.memory.elements):
            if not element.specifications:
                element.specifications = ElementSpec()
            
            if not element.specifications.width or not element.specifications.height:
                element.specifications.width = dimensions.width
                element.specifications.height = dimensions.length  # Use length as height
                print(f"   📏 Updated {element.type.value} dimensions: {dimensions.width}x{dimensions.length}m")
                break
    
    def _update_element_wall(self, question: str, wall: str):
        """Update element wall placement."""
        # Find the element mentioned in the question or the most recent one without wall
        for element in reversed(self.memory.elements):
            if not element.specifications:
                element.specifications = ElementSpec()
            
            if not element.specifications.wall:
                element.specifications.wall = wall
                print(f"   🧱 Updated {element.type.value} wall: {wall}")
                break
    
    def _extract_wall_from_answer(self, answer: str) -> Optional[str]:
        """Extract wall direction from answer."""
        answer_lower = answer.lower()
        walls = ["north", "south", "east", "west"]
        for wall in walls:
            if wall in answer_lower:
                return wall
        return None


async def enhanced_conversation_demo():
    """Run the enhanced conversation demo."""
    print("🏠 Enhanced Natural Language to Floorspace JSON Agent")
    print("=" * 60)
    print("This agent will gather all required information through conversation:")
    print("1. Room dimensions and position")
    print("2. Window/door specifications (if any)")
    print("3. Wall placement for elements")
    print()
    print("Type 'quit' to exit, 'reset' to start over, 'memory' to see current state")
    print()
    
    agent = EnhancedConversationAgent()
    current_question = None
    
    while True:
        try:
            if current_question:
                # We're in clarification mode
                print(f"❓ {current_question}")
                user_input = input("💬 Your answer: ").strip()
            else:
                # Initial input mode
                user_input = input("🏠 Describe your space: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == 'reset':
                agent = EnhancedConversationAgent()
                current_question = None
                print("🔄 Session reset. Start with a new room description.")
                continue
            
            if user_input.lower() == 'memory':
                memory_summary = agent._get_memory_summary()
                print("\n📋 Current Memory:")
                print(f"   Room Type: {memory_summary['room_type'] or 'Not specified'}")
                print(f"   Dimensions: {memory_summary['dimensions'] or 'Not specified'}")
                print(f"   Elements: {len(memory_summary['elements'])} items")
                for elem in memory_summary['elements']:
                    specs = elem['specifications']
                    if specs:
                        print(f"     • {elem['type']}: {specs['dimensions']}, wall: {specs['wall']}")
                    else:
                        print(f"     • {elem['type']}: incomplete")
                print(f"   Conversation turns: {memory_summary['conversation_turns']}")
                continue
            
            if not user_input:
                continue
            
            # Process the input
            if current_question:
                # Answer to clarification
                result = agent.answer_clarification(user_input, current_question)
            else:
                # Initial or follow-up input
                result = agent.process_user_input(user_input)
            
            # Handle the result
            if result.get("success"):
                # Final output generated
                print("\n" + "="*60)
                print(result["message"])
                
                # Show summary
                summary = result["memory_summary"]
                print(f"\n📋 Final Room Summary:")
                print(f"   • Type: {summary['room_type']}")
                print(f"   • Dimensions: {summary['dimensions']}")
                print(f"   • Elements: {len(summary['elements'])} items")
                
                for elem in summary['elements']:
                    specs = elem['specifications']
                    if specs:
                        print(f"     - {elem['type']}: {specs['dimensions']}, {specs['wall']} wall")
                
                print(f"\n💾 File saved: {result['filename']}")
                print("🎉 Ready to import into Floorspace.js!")
                print("="*60)
                
                # Reset for next room
                agent = EnhancedConversationAgent()
                current_question = None
                
            elif result.get("needs_clarification"):
                # Need clarification
                current_question = result["question"]
                
                # Show what we have so far
                summary = result["memory_summary"]
                print(f"\n📋 Captured so far:")
                if summary["room_type"]:
                    print(f"   • Room type: {summary['room_type']}")
                if summary["dimensions"]:
                    print(f"   • Dimensions: {summary['dimensions']}")
                if summary["elements"]:
                    print(f"   • Elements: {len(summary['elements'])} items")
                
            elif result.get("error"):
                # Error occurred
                print(f"\n❌ Error: {result['error']}")
                current_question = None
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("Please try again.")


if __name__ == "__main__":
    asyncio.run(enhanced_conversation_demo())