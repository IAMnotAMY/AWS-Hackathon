"""Main FloorspaceAgent orchestrator."""

from typing import Dict, Any, Optional, List
import logging
import asyncio
import traceback
from datetime import datetime

from .models import ConversationState, SpaceRequirement
from .parser import NaturalLanguageParser
from .conversation import ConversationManager
from .geometry import GeometryGenerator
from .storage import SessionStorage
from .export import FloorspaceJSONExporter
from .workflow import WorkflowCoordinator, WorkflowTask, TaskStatus, RecoveryAction, RecoveryStrategy

logger = logging.getLogger(__name__)


class FloorspaceAgentError(Exception):
    """Base exception for FloorspaceAgent errors."""
    pass


class SessionError(FloorspaceAgentError):
    """Exception for session-related errors."""
    pass


class ParsingError(FloorspaceAgentError):
    """Exception for natural language parsing errors."""
    pass


class GeometryError(FloorspaceAgentError):
    """Exception for geometry generation errors."""
    pass


class ExportError(FloorspaceAgentError):
    """Exception for JSON export errors."""
    pass


class ConversationError(FloorspaceAgentError):
    """Exception for conversation management errors."""
    pass


class FloorspaceAgent:
    """Main agent that orchestrates the natural language to Floorspace JSON conversion."""
    
    def __init__(self, aws_region: str = "us-east-1"):
        """Initialize the FloorspaceAgent.
        
        Args:
            aws_region: AWS region for Bedrock access
        """
        try:
            self.parser = NaturalLanguageParser()
            self.conversation_manager = ConversationManager(aws_region=aws_region)
            self.geometry_generator = GeometryGenerator()
            self.session_storage = SessionStorage()
            self.json_exporter = FloorspaceJSONExporter()
            
            # Initialize workflow coordinator
            self.workflow_coordinator = WorkflowCoordinator()
            self._setup_workflow_tasks()
            self._configure_error_recovery()
            
            # Error tracking
            self._error_counts = {
                "parsing_errors": 0,
                "conversation_errors": 0,
                "geometry_errors": 0,
                "export_errors": 0,
                "session_errors": 0,
                "total_errors": 0
            }
            self._last_error_time = None
            
            logger.info("FloorspaceAgent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize FloorspaceAgent: {e}")
            raise FloorspaceAgentError(f"Initialization failed: {str(e)}")
    
    def _handle_error(self, error: Exception, operation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Centralized error handling with logging and user-friendly messages.
        
        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            context: Additional context information
            
        Returns:
            Error response dictionary
        """
        self._error_counts["total_errors"] += 1
        self._last_error_time = datetime.now()
        
        # Log the full error with traceback
        logger.error(f"Error in {operation}: {error}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        
        # Categorize error and increment specific counter
        error_type = type(error).__name__
        user_message = "An unexpected error occurred. Please try again."
        recovery_suggestions = []
        
        if isinstance(error, (ParsingError, ValueError)):
            self._error_counts["parsing_errors"] += 1
            user_message = "I couldn't understand your input. Please rephrase your description."
            recovery_suggestions = [
                "Try using simpler language",
                "Include specific dimensions (e.g., '5m x 4m')",
                "Mention room type and any windows/doors clearly"
            ]
        elif isinstance(error, ConversationError):
            self._error_counts["conversation_errors"] += 1
            user_message = "There was an issue with the conversation flow. Let me try to recover."
            recovery_suggestions = [
                "Try rephrasing your answer",
                "Start a new session if the problem persists",
                "Check your internet connection"
            ]
        elif isinstance(error, GeometryError):
            self._error_counts["geometry_errors"] += 1
            user_message = "I couldn't generate the building geometry. Please check your specifications."
            recovery_suggestions = [
                "Verify that dimensions are reasonable",
                "Check that windows/doors fit within walls",
                "Ensure no overlapping elements"
            ]
        elif isinstance(error, ExportError):
            self._error_counts["export_errors"] += 1
            user_message = "The building was created but couldn't be exported to JSON format."
            recovery_suggestions = [
                "Try the export again",
                "Check if the building geometry is valid",
                "Contact support if the issue persists"
            ]
        elif isinstance(error, SessionError):
            self._error_counts["session_errors"] += 1
            user_message = "There was an issue with your session. Please try starting a new one."
            recovery_suggestions = [
                "Start a new conversation session",
                "Clear your browser cache if using web interface",
                "Try again in a few minutes"
            ]
        elif isinstance(error, (ConnectionError, TimeoutError)):
            user_message = "Service temporarily unavailable. Please try again in a moment."
            recovery_suggestions = [
                "Check your internet connection",
                "Wait a moment and try again",
                "The service may be experiencing high load"
            ]
        
        # Build error response
        error_response = {
            "error": str(error),
            "error_type": error_type,
            "operation": operation,
            "message": user_message,
            "timestamp": self._last_error_time.isoformat(),
            "recovery_suggestions": recovery_suggestions
        }
        
        # Add context if provided
        if context:
            error_response["context"] = context
        
        # Add session recovery info if session_id is in context
        if context and "session_id" in context:
            error_response["session_id"] = context["session_id"]
            error_response["can_recover_session"] = True
        
        return error_response
    
    def _validate_input(self, description: str) -> None:
        """Validate user input before processing.
        
        Args:
            description: User input to validate
            
        Raises:
            ParsingError: If input is invalid
        """
        if not description or not description.strip():
            raise ParsingError("Empty description provided")
        
        if len(description.strip()) < 3:
            raise ParsingError("Description too short - please provide more details")
        
        if len(description) > 10000:
            raise ParsingError("Description too long - please keep it under 10,000 characters")
        
        # Check for potentially problematic content
        suspicious_patterns = ["<script", "javascript:", "data:"]
        description_lower = description.lower()
        for pattern in suspicious_patterns:
            if pattern in description_lower:
                raise ParsingError("Invalid characters detected in description")
    
    def _validate_session_id(self, session_id: str) -> None:
        """Validate session ID format.
        
        Args:
            session_id: Session ID to validate
            
        Raises:
            SessionError: If session ID is invalid
        """
        if not session_id or not session_id.strip():
            raise SessionError("Empty session ID provided")
        
        if len(session_id) > 100:
            raise SessionError("Session ID too long")
        
        # Basic format validation (alphanumeric, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise SessionError("Invalid session ID format")
        
    def _setup_workflow_tasks(self):
        """Set up the workflow tasks for processing requests."""
        
        # Task 1: Parse natural language input
        parse_task = WorkflowTask(
            name="parse_input",
            execute_func=self._parse_input_task,
            dependencies=set(),
            max_retries=2,
            timeout=30.0
        )
        
        # Task 2: Process through conversation manager
        conversation_task = WorkflowTask(
            name="process_conversation",
            execute_func=self._process_conversation_task,
            dependencies={"parse_input"},
            max_retries=3,
            timeout=60.0
        )
        
        # Task 3: Generate geometry (if specification is complete)
        geometry_task = WorkflowTask(
            name="generate_geometry",
            execute_func=self._generate_geometry_task,
            dependencies={"process_conversation"},
            max_retries=2,
            timeout=45.0,
            required=False  # Optional - only runs if specification is complete
        )
        
        # Task 4: Export to JSON (if geometry was generated)
        export_task = WorkflowTask(
            name="export_json",
            execute_func=self._export_json_task,
            dependencies={"generate_geometry"},
            max_retries=2,
            timeout=30.0,
            required=False  # Optional - only runs if geometry exists
        )
        
        # Task 5: Save session state
        save_task = WorkflowTask(
            name="save_state",
            execute_func=self._save_state_task,
            dependencies={"process_conversation"},
            max_retries=3,
            timeout=15.0
        )
        
        # Add tasks to coordinator
        self.workflow_coordinator.add_task(parse_task)
        self.workflow_coordinator.add_task(conversation_task)
        self.workflow_coordinator.add_task(geometry_task)
        self.workflow_coordinator.add_task(export_task)
        self.workflow_coordinator.add_task(save_task)
    
    def _configure_error_recovery(self):
        """Configure error recovery strategies for different exception types."""
        
        # Network and AWS-related errors - retry with exponential backoff
        self.workflow_coordinator.configure_error_recovery(
            ConnectionError,
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                max_attempts=5,
                wait_strategy="exponential"
            )
        )
        
        # Timeout errors - retry with shorter attempts
        self.workflow_coordinator.configure_error_recovery(
            TimeoutError,
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                max_attempts=3,
                wait_strategy="exponential"
            )
        )
        
        # Value errors in parsing - skip and continue
        self.workflow_coordinator.configure_error_recovery(
            ValueError,
            RecoveryAction(
                strategy=RecoveryStrategy.SKIP,
                max_attempts=1
            )
        )
        
        # Permission errors - retry briefly then skip
        self.workflow_coordinator.configure_error_recovery(
            PermissionError,
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                max_attempts=2,
                wait_strategy="fixed"
            )
        )
    
    async def _parse_input_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Task to parse natural language input."""
        description = context.get("description")
        if not description:
            raise ValueError("No description provided for parsing")
        
        space_requirement = self.parser.parse_space_description(description)
        return {"space_requirement": space_requirement}
    
    async def _process_conversation_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Task to process through conversation manager."""
        space_requirement = context.get("space_requirement")
        conversation_state = context.get("conversation_state")
        
        if not space_requirement:
            raise ValueError("No space requirement available for conversation processing")
        
        result = await self.conversation_manager.process_requirement(
            space_requirement, conversation_state
        )
        
        return {
            "conversation_result": result,
            "updated_conversation_state": conversation_state
        }
    
    async def _generate_geometry_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Task to generate geometry if specification is complete."""
        conversation_result = context.get("conversation_result", {})
        conversation_state = context.get("updated_conversation_state")
        
        # Only generate geometry if specification is complete
        if not conversation_result.get("specification_complete", False):
            logger.info("Specification not complete, skipping geometry generation")
            return {"geometry_generated": False}
        
        # Generate geometry using the geometry generator
        building_model = conversation_state.building_model if conversation_state else None
        if building_model:
            # Geometry generation is handled by the conversation manager
            # This task validates and potentially enhances the geometry
            return {"geometry_generated": True, "building_model": building_model}
        
        return {"geometry_generated": False}
    
    async def _export_json_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Task to export building model to JSON."""
        building_model = context.get("building_model")
        
        if not building_model:
            logger.info("No building model available for JSON export")
            return {"json_exported": False}
        
        json_output = self.json_exporter.export_to_json(building_model)
        return {"json_exported": True, "json_output": json_output}
    
    async def _save_state_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Task to save conversation state."""
        conversation_state = context.get("updated_conversation_state")
        session_id = context.get("session_id")
        
        if conversation_state:
            self.session_storage.save_conversation_state(conversation_state, session_id)
            return {"state_saved": True}
        
        return {"state_saved": False}
        
    async def process_description(self, description: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a natural language description and return Floorspace JSON.
        
        Args:
            description: Natural language description of the space
            session_id: Optional session ID for conversation continuity
            
        Returns:
            Dictionary containing the response and any generated JSON
        """
        operation = "process_description"
        context = {"description": description, "session_id": session_id}
        
        try:
            # Validate input
            self._validate_input(description)
            
            if session_id:
                self._validate_session_id(session_id)
            
            # Get or create session context
            if session_id:
                try:
                    session_context = await self.session_storage.get_session(session_id)
                    if not session_context:
                        logger.warning(f"Session {session_id} not found, creating new session")
                        session_context = await self.conversation_manager.start_conversation()
                except Exception as e:
                    logger.error(f"Error retrieving session {session_id}: {e}")
                    raise SessionError(f"Failed to retrieve session: {str(e)}")
            else:
                try:
                    session_context = await self.conversation_manager.start_conversation()
                    session_id = session_context.session_id
                    context["session_id"] = session_id
                except Exception as e:
                    logger.error(f"Error creating new session: {e}")
                    raise SessionError(f"Failed to create new session: {str(e)}")
            
            # Use conversation manager to orchestrate the flow
            try:
                response = await self.conversation_manager.orchestrate_conversation_flow(
                    user_input=description,
                    session_id=session_id
                )
            except Exception as e:
                logger.error(f"Error in conversation flow: {e}")
                raise ConversationError(f"Conversation processing failed: {str(e)}")
            
            # If ready for generation, trigger geometry and JSON export
            if response.get("ready_for_generation", False) or response.get("action") == "generate":
                try:
                    # Generate geometry using collected specifications
                    building_model = await self._generate_building_geometry(session_context)
                    
                    if building_model:
                        try:
                            # Export to JSON
                            json_output = self.json_exporter.export_to_json(building_model)
                            response["floorspace_json"] = json_output
                            response["generation_complete"] = True
                            
                            # Update session with generated model
                            session_context.conversation_state.building_model = building_model
                            await self.session_storage.save_session(session_context)
                        except Exception as e:
                            logger.error(f"Error exporting to JSON: {e}")
                            raise ExportError(f"JSON export failed: {str(e)}")
                    else:
                        raise GeometryError("Failed to generate building geometry from specifications")
                        
                except GeometryError:
                    raise  # Re-raise geometry errors as-is
                except ExportError:
                    raise  # Re-raise export errors as-is
                except Exception as e:
                    logger.error(f"Error during geometry generation: {e}")
                    raise GeometryError(f"Geometry generation failed: {str(e)}")
            
            return response
            
        except (ParsingError, SessionError, ConversationError, GeometryError, ExportError) as e:
            # Handle our custom exceptions
            return self._handle_error(e, operation, context)
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error in {operation}: {e}")
            return self._handle_error(e, operation, context)
    
    def get_workflow_diagnostics(self) -> Dict[str, Any]:
        """Get detailed workflow diagnostics for troubleshooting.
        
        Returns:
            Dictionary containing detailed workflow information
        """
        status = self.workflow_coordinator.get_workflow_status()
        
        # Add additional diagnostic information
        diagnostics = {
            "workflow_status": status,
            "error_details": [
                {
                    "error": str(error_entry["error"]),
                    "task": error_entry.get("task"),
                    "timestamp": error_entry["timestamp"].isoformat()
                }
                for error_entry in self.workflow_coordinator.state.get_errors()
            ],
            "task_execution_times": {},
            "circuit_breaker_details": {}
        }
        
        # Get task execution times
        for task_name, task in self.workflow_coordinator.tasks.items():
            if task.start_time and task.end_time:
                execution_time = (task.end_time - task.start_time).total_seconds()
                diagnostics["task_execution_times"][task_name] = execution_time
        
        # Get detailed circuit breaker information
        for task_name in self.workflow_coordinator.tasks:
            cb_status = self.workflow_coordinator.get_circuit_breaker_status(task_name)
            if cb_status:
                diagnostics["circuit_breaker_details"][task_name] = cb_status
        
        return diagnostics
    
    async def answer_clarification(self, answer: str, session_id: str) -> Dict[str, Any]:
        """Answer a clarification question from the agent.
        
        Args:
            answer: User's answer to the clarification question
            session_id: Session ID for conversation continuity
            
        Returns:
            Dictionary containing the response and any generated JSON
        """
        operation = "answer_clarification"
        context = {"answer": answer, "session_id": session_id}
        
        try:
            # Validate inputs
            self._validate_input(answer)
            self._validate_session_id(session_id)
            
            # Use conversation manager to handle clarification
            try:
                response = await self.conversation_manager.orchestrate_conversation_flow(
                    user_input=answer,
                    session_id=session_id
                )
            except Exception as e:
                logger.error(f"Error in conversation flow during clarification: {e}")
                raise ConversationError(f"Failed to process clarification: {str(e)}")
            
            # If ready for generation after clarification, trigger geometry and JSON export
            if response.get("ready_for_generation", False) or response.get("action") == "generate":
                try:
                    session_context = await self.session_storage.get_session(session_id)
                    if not session_context:
                        raise SessionError(f"Session {session_id} not found during generation")
                    
                    # Generate geometry using collected specifications
                    building_model = await self._generate_building_geometry(session_context)
                    
                    if building_model:
                        try:
                            # Export to JSON
                            json_output = self.json_exporter.export_to_json(building_model)
                            response["floorspace_json"] = json_output
                            response["generation_complete"] = True
                            
                            # Update session with generated model
                            session_context.conversation_state.building_model = building_model
                            await self.session_storage.save_session(session_context)
                        except Exception as e:
                            logger.error(f"Error exporting to JSON during clarification: {e}")
                            raise ExportError(f"JSON export failed: {str(e)}")
                    else:
                        raise GeometryError("Failed to generate building geometry from clarification")
                        
                except (SessionError, GeometryError, ExportError):
                    raise  # Re-raise our custom exceptions
                except Exception as e:
                    logger.error(f"Error during geometry generation in clarification: {e}")
                    raise GeometryError(f"Generation failed: {str(e)}")
            
            return response
            
        except (ParsingError, SessionError, ConversationError, GeometryError, ExportError) as e:
            # Handle our custom exceptions
            return self._handle_error(e, operation, context)
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error in {operation}: {e}")
            return self._handle_error(e, operation, context)
    
    async def _process_clarification_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Task to process clarification answer."""
        answer = context.get("answer")
        conversation_state = context.get("conversation_state")
        
        if not answer:
            raise ValueError("No answer provided for clarification")
        
        result = await self.conversation_manager.process_clarification_answer(
            answer, conversation_state
        )
        
        return {
            "conversation_result": result,
            "updated_conversation_state": conversation_state
        }
    
    def get_building_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the current building state.
        
        Args:
            session_id: Session ID for the conversation
            
        Returns:
            Dictionary containing building summary information
        """
        try:
            # This method needs to be async to properly call session storage
            # For now, we'll use a synchronous wrapper
            import asyncio
            
            async def _get_summary():
                session_context = await self.session_storage.get_session(session_id)
                if not session_context or not session_context.conversation_state:
                    return {
                        "error": "Session not found",
                        "session_id": session_id
                    }
                
                building_model = session_context.conversation_state.building_model
                
                if not building_model or not building_model.stories:
                    return {
                        "spaces_count": 0,
                        "windows_count": 0,
                        "doors_count": 0,
                        "session_id": session_id,
                        "message": "No building model generated yet"
                    }
                
                story = building_model.stories[0]  # Assuming single story for now
                
                return {
                    "spaces_count": len(story.spaces),
                    "windows_count": len(story.windows),
                    "doors_count": len(story.doors),
                    "session_id": session_id,
                    "building_model": building_model
                }
            
            # Run the async function
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a task
                task = asyncio.create_task(_get_summary())
                return {"message": "Building summary request submitted", "session_id": session_id}
            else:
                return loop.run_until_complete(_get_summary())
            
        except Exception as e:
            logger.error(f"Error getting building summary: {e}")
            return {
                "error": str(e),
                "message": "An error occurred while retrieving building summary.",
                "session_id": session_id
            }
    
    async def _generate_building_geometry(self, session_context) -> Optional[Any]:
        """Generate building geometry from collected specifications.
        
        Args:
            session_context: Session context with conversation state
            
        Returns:
            Generated building model or None if generation fails
            
        Raises:
            GeometryError: If geometry generation fails
        """
        try:
            if not session_context:
                raise GeometryError("No session context provided for geometry generation")
            
            if not session_context.conversation_state:
                raise GeometryError("No conversation state available for geometry generation")
            
            state = session_context.conversation_state
            
            # Extract space requirements from conversation state
            space_requirements = self._extract_space_requirements_from_state(state)
            
            if not space_requirements:
                raise GeometryError("No space requirements found in conversation state")
            
            # Generate geometry for each space requirement
            building_model = None
            for i, requirement in enumerate(space_requirements):
                try:
                    if building_model is None:
                        # Create new building model for first space
                        building_model = self.geometry_generator.create_building_model(requirement)
                    else:
                        # Add space to existing building model
                        self.geometry_generator.add_space_to_building(building_model, requirement)
                except Exception as e:
                    raise GeometryError(f"Failed to generate geometry for space {i + 1}: {str(e)}")
            
            if not building_model:
                raise GeometryError("No building model was generated")
            
            return building_model
            
        except GeometryError:
            raise  # Re-raise geometry errors as-is
        except Exception as e:
            logger.error(f"Unexpected error generating building geometry: {e}")
            raise GeometryError(f"Geometry generation failed: {str(e)}")
    
    def _extract_space_requirements_from_state(self, conversation_state) -> List[Any]:
        """Extract space requirements from conversation state.
        
        Args:
            conversation_state: Current conversation state
            
        Returns:
            List of space requirements
            
        Raises:
            GeometryError: If space requirements cannot be extracted
        """
        try:
            space_requirements = []
            
            # Check if we have collected specs
            if conversation_state.collected_specs:
                from nl_floorspace_agent.models import SpaceRequirement, Dimensions, Units
                
                # Create a space requirement from collected specs
                # In a real implementation, this would be more sophisticated
                requirement = SpaceRequirement(
                    dimensions=Dimensions(
                        width=5.0,  # Default values - should be extracted from conversation
                        length=4.0,
                        height=3.0,
                        units=Units.SI
                    ),
                    elements=[],  # Would be populated from collected specs
                    room_type="room"
                )
                
                space_requirements.append(requirement)
            else:
                # Try to extract from answered questions if no collected specs
                logger.info("No collected specs found, checking for basic space information")
                
                # For now, create a basic space requirement if we have any conversation activity
                # This is a fallback - in production, this would be more sophisticated
                if hasattr(conversation_state, 'pending_questions') and len(conversation_state.pending_questions) == 0:
                    # If no pending questions, we might have processed something
                    from nl_floorspace_agent.models import SpaceRequirement, Dimensions, Units
                    
                    # Create a default space requirement
                    requirement = SpaceRequirement(
                        dimensions=Dimensions(
                            width=10.0,  # Use reasonable defaults
                            length=10.0,
                            height=3.0,
                            units=Units.SI
                        ),
                        elements=[],
                        room_type="living room"  # Default room type
                    )
                    
                    space_requirements.append(requirement)
                    logger.info("Created default space requirement for geometry generation")
            
            return space_requirements
            
        except Exception as e:
            logger.error(f"Error extracting space requirements: {e}")
            raise GeometryError(f"Failed to extract space requirements: {str(e)}")
    
    async def start_new_session(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Start a new conversation session.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            New session information
        """
        operation = "start_new_session"
        context = {"user_id": user_id}
        
        try:
            session_context = await self.conversation_manager.start_conversation(user_id)
            
            return {
                "session_id": session_context.session_id,
                "user_id": session_context.user_id,
                "message": "New conversation session started. Describe the space you'd like to create.",
                "created_at": session_context.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error starting new session: {e}")
            return self._handle_error(SessionError(f"Failed to start new session: {str(e)}"), operation, context)
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the current status of a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session status information
        """
        operation = "get_session_status"
        context = {"session_id": session_id}
        
        try:
            self._validate_session_id(session_id)
            return await self.conversation_manager.get_session_status(session_id)
            
        except SessionError as e:
            return self._handle_error(e, operation, context)
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return self._handle_error(SessionError(f"Failed to get session status: {str(e)}"), operation, context)
    
    async def reset_session(self, session_id: str) -> Dict[str, Any]:
        """Reset a conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Reset confirmation
        """
        operation = "reset_session"
        context = {"session_id": session_id}
        
        try:
            self._validate_session_id(session_id)
            return await self.conversation_manager.reset_conversation(session_id)
            
        except SessionError as e:
            return self._handle_error(e, operation, context)
        except Exception as e:
            logger.error(f"Error resetting session: {e}")
            return self._handle_error(SessionError(f"Failed to reset session: {str(e)}"), operation, context)
    
    async def recover_session(self, session_id: str) -> Dict[str, Any]:
        """Recover a session from error state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Recovery result
        """
        operation = "recover_session"
        context = {"session_id": session_id}
        
        try:
            self._validate_session_id(session_id)
            return await self.conversation_manager.recover_session(session_id)
            
        except SessionError as e:
            return self._handle_error(e, operation, context)
        except Exception as e:
            logger.error(f"Error recovering session: {e}")
            return self._handle_error(SessionError(f"Failed to recover session: {str(e)}"), operation, context)
    
    async def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up expired sessions.
        
        Returns:
            Cleanup result
        """
        operation = "cleanup_expired_sessions"
        
        try:
            cleaned_count = await self.conversation_manager.cleanup_expired_sessions()
            
            return {
                "cleaned_sessions": cleaned_count,
                "message": f"Cleaned up {cleaned_count} expired sessions"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return self._handle_error(SessionError(f"Failed to cleanup sessions: {str(e)}"), operation)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring and debugging.
        
        Returns:
            Error statistics
        """
        return {
            "error_counts": self._error_counts.copy(),
            "last_error_time": self._last_error_time.isoformat() if self._last_error_time else None,
            "error_rate": self._calculate_error_rate()
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate the current error rate.
        
        Returns:
            Error rate as a percentage
        """
        # This is a simplified calculation - in a real implementation,
        # you would track total requests and calculate a proper rate
        total_operations = sum(self._error_counts.values()) + 100  # Assume some successful operations
        return (self._error_counts["total_errors"] / total_operations) * 100 if total_operations > 0 else 0.0
    
    def reset_error_statistics(self) -> None:
        """Reset error statistics."""
        self._error_counts = {
            "parsing_errors": 0,
            "conversation_errors": 0,
            "geometry_errors": 0,
            "export_errors": 0,
            "session_errors": 0,
            "total_errors": 0
        }
        self._last_error_time = None
        logger.info("Error statistics reset")