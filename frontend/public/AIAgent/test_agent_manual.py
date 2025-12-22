#!/usr/bin/env python3
"""
Manual testing script for the Natural Language to Floorspace JSON Agent.

This script demonstrates how to test the agent with various scenarios.
You can run this script to interactively test the agent or run predefined test cases.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path so we can import the agent
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nl_floorspace_agent.agent import FloorspaceAgent


class AgentTester:
    """Interactive tester for the FloorspaceAgent."""
    
    def __init__(self):
        """Initialize the agent tester."""
        self.agent = None
        self.current_session_id = None
    
    async def setup_agent(self):
        """Set up the agent with proper configuration."""
        try:
            # Load environment variables if .env file exists
            env_file = Path(".env")
            if env_file.exists():
                print("Loading environment variables from .env file...")
                with open(env_file) as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            os.environ[key] = value
            
            # Initialize the agent
            aws_region = os.getenv("AWS_REGION", "us-east-1")
            print(f"Initializing FloorspaceAgent with AWS region: {aws_region}")
            
            self.agent = FloorspaceAgent(aws_region=aws_region)
            print("✅ Agent initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize agent: {e}")
            print("\nTroubleshooting tips:")
            print("1. Make sure AWS credentials are configured")
            print("2. Check that all dependencies are installed: pip install -r requirements.txt")
            print("3. Verify AWS Bedrock access in your region")
            return False
    
    async def start_new_session(self, user_id=None):
        """Start a new conversation session."""
        try:
            result = await self.agent.start_new_session(user_id)
            if "session_id" in result:
                self.current_session_id = result["session_id"]
                print(f"✅ New session started: {self.current_session_id}")
                print(f"Message: {result['message']}")
                return True
            else:
                print(f"❌ Failed to start session: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Exception starting session: {e}")
            return False
    
    async def test_simple_room(self):
        """Test creating a simple room."""
        print("\n🏠 Testing: Simple room creation")
        description = "Create a 5m x 4m bedroom with one window"
        
        try:
            result = await self.agent.process_description(description, self.current_session_id)
            self.print_result(result)
            return result
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None
    
    async def test_room_with_clarification(self):
        """Test a room that requires clarification."""
        print("\n🏠 Testing: Room requiring clarification")
        description = "Create a living room with windows and a door"
        
        try:
            result = await self.agent.process_description(description, self.current_session_id)
            self.print_result(result)
            
            # If clarification is needed, simulate answering questions
            if result.get("needs_clarification"):
                print("\n💬 Answering clarification questions...")
                
                # Answer first question (assuming it's about window dimensions)
                answer1 = "The windows should be 1.5m x 1.2m"
                print(f"Answer 1: {answer1}")
                result1 = await self.agent.answer_clarification(answer1, self.current_session_id)
                self.print_result(result1)
                
                # Answer second question if needed (assuming it's about wall placement)
                if result1.get("questions"):
                    answer2 = "Put the windows on the south wall and the door on the north wall"
                    print(f"Answer 2: {answer2}")
                    result2 = await self.agent.answer_clarification(answer2, self.current_session_id)
                    self.print_result(result2)
                    return result2
                
                return result1
            
            return result
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None
    
    async def test_error_handling(self):
        """Test error handling scenarios."""
        print("\n⚠️  Testing: Error handling")
        
        # Test empty input
        print("Testing empty input...")
        result = await self.agent.process_description("", self.current_session_id)
        print(f"Empty input result: {result.get('error', 'No error')}")
        
        # Test invalid session ID
        print("Testing invalid session ID...")
        result = await self.agent.answer_clarification("test", "invalid@session")
        print(f"Invalid session result: {result.get('error', 'No error')}")
        
        # Test very long input
        print("Testing very long input...")
        long_input = "x" * 10001
        result = await self.agent.process_description(long_input, self.current_session_id)
        print(f"Long input result: {result.get('error', 'No error')}")
    
    async def test_session_management(self):
        """Test session management features."""
        print("\n📋 Testing: Session management")
        
        # Get session status
        if self.current_session_id:
            status = await self.agent.get_session_status(self.current_session_id)
            print(f"Session status: {status}")
            
            # Get building summary
            summary = self.agent.get_building_summary(self.current_session_id)
            print(f"Building summary: {summary}")
            
            # Get error statistics
            stats = self.agent.get_error_statistics()
            print(f"Error statistics: {stats}")
    
    def print_result(self, result):
        """Pretty print a result from the agent."""
        if not result:
            print("❌ No result returned")
            return
        
        print("\n📋 Agent Response:")
        print("-" * 50)
        
        # Print main message
        if "message" in result:
            print(f"💬 Message: {result['message']}")
        
        # Print error if present
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            if "recovery_suggestions" in result:
                print("💡 Recovery suggestions:")
                for suggestion in result["recovery_suggestions"]:
                    print(f"   • {suggestion}")
        
        # Print questions if present
        if "questions" in result:
            print("❓ Questions:")
            for i, question in enumerate(result["questions"], 1):
                print(f"   {i}. {question}")
        
        # Print JSON output if present
        if "floorspace_json" in result:
            print("✅ Floorspace JSON generated!")
            json_output = result["floorspace_json"]
            if isinstance(json_output, dict):
                print(f"   • Version: {json_output.get('version', 'Unknown')}")
                stories = json_output.get('stories', [])
                if stories:
                    story = stories[0]
                    spaces = story.get('spaces', [])
                    windows = story.get('windows', [])
                    doors = story.get('doors', [])
                    print(f"   • Spaces: {len(spaces)}")
                    print(f"   • Windows: {len(windows)}")
                    print(f"   • Doors: {len(doors)}")
        
        # Print session info
        if "session_id" in result:
            print(f"🔗 Session ID: {result['session_id']}")
        
        print("-" * 50)
    
    async def interactive_mode(self):
        """Run in interactive mode where user can type descriptions."""
        print("\n🎯 Interactive Mode")
        print("Type room descriptions and see the agent respond!")
        print("Commands:")
        print("  'quit' or 'exit' - Exit interactive mode")
        print("  'status' - Show session status")
        print("  'summary' - Show building summary")
        print("  'reset' - Reset current session")
        print("  'new' - Start new session")
        print()
        
        while True:
            try:
                user_input = input("🏠 Describe your space: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    break
                elif user_input.lower() == 'status':
                    if self.current_session_id:
                        status = await self.agent.get_session_status(self.current_session_id)
                        print(f"Status: {status}")
                    else:
                        print("No active session")
                elif user_input.lower() == 'summary':
                    if self.current_session_id:
                        summary = self.agent.get_building_summary(self.current_session_id)
                        print(f"Summary: {summary}")
                    else:
                        print("No active session")
                elif user_input.lower() == 'reset':
                    if self.current_session_id:
                        result = await self.agent.reset_session(self.current_session_id)
                        print(f"Reset result: {result}")
                    else:
                        print("No active session to reset")
                elif user_input.lower() == 'new':
                    await self.start_new_session()
                elif user_input:
                    result = await self.agent.process_description(user_input, self.current_session_id)
                    self.print_result(result)
                    
                    # Handle clarification questions
                    while result and result.get("needs_clarification") or result.get("questions"):
                        if result.get("questions"):
                            print("\n❓ Please answer the questions:")
                            for i, question in enumerate(result["questions"], 1):
                                print(f"   {i}. {question}")
                        
                        answer = input("💬 Your answer: ").strip()
                        if answer:
                            result = await self.agent.answer_clarification(answer, self.current_session_id)
                            self.print_result(result)
                        else:
                            break
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def run_predefined_tests(self):
        """Run a series of predefined tests."""
        print("\n🧪 Running Predefined Tests")
        print("=" * 60)
        
        # Test 1: Simple room
        await self.test_simple_room()
        
        # Test 2: Room with clarification
        await self.test_room_with_clarification()
        
        # Test 3: Error handling
        await self.test_error_handling()
        
        # Test 4: Session management
        await self.test_session_management()
        
        print("\n✅ All predefined tests completed!")


async def main():
    """Main function to run the agent tester."""
    print("🏠 Natural Language to Floorspace JSON Agent Tester")
    print("=" * 60)
    
    tester = AgentTester()
    
    # Setup the agent
    if not await tester.setup_agent():
        print("\n❌ Cannot proceed without a working agent. Please check your configuration.")
        return
    
    # Start a session
    if not await tester.start_new_session("test_user"):
        print("\n❌ Cannot proceed without a session. Please check your configuration.")
        return
    
    # Ask user what they want to do
    print("\nWhat would you like to do?")
    print("1. Run predefined tests")
    print("2. Interactive mode")
    print("3. Both")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            await tester.run_predefined_tests()
        elif choice == "2":
            await tester.interactive_mode()
        elif choice == "3":
            await tester.run_predefined_tests()
            await tester.interactive_mode()
        else:
            print("Invalid choice. Running predefined tests...")
            await tester.run_predefined_tests()
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())