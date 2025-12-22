"""Conversation management and orchestration."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .bedrock_client import BedrockClient
from .clarification import ClarificationGenerator
from ..models import (
    SpaceRequirement, ConversationState, ConversationStep, 
    Question, SessionContext, BuildingContext, ElementType
)
from ..storage.session_storage import SessionStorage

logger = logging.getLogger(__name__)


class ConversationError(Exception):
    """Base exception for conversation-related errors."""
    pass


class SessionNotFoundError(ConversationError):
    """Exception raised when a session is not found."""
    pass


class InvalidStateError(ConversationError):
    """Exception raised when conversation state is invalid."""
    pass


class BedrockServiceError(ConversationError):
    """Exception raised when Bedrock service is unavailable."""
    pass


class ConversationManager:
    """Manages conversation flow and state with AWS Bedrock integration."""
    
    def __init__(self, aws_region: str = "us-east-1", model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """Initialize the conversation manager.
        
        Args:
            aws_region: AWS region for Bedrock access
            model_id: Bedrock model ID to use
        """
        self.aws_region = aws_region
        self.model_id = model_id
        self.bedrock_client = BedrockClient(region=aws_region, model_id=model_id)
        self.clarification_generator = ClarificationGenerator()
        self.session_storage = SessionStorage()
        
        # Conversation flow configuration
        self.max_clarification_rounds = 5
        self.session_timeout_minutes = 30
        self.max_retry_attempts = 3
        self.retry_delay_seconds = 1.0
        
        # Error recovery state
        self._error_recovery_cache: Dict[str, Dict[str, Any]] = {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((BedrockServiceError, ConnectionError))
    )
    async def start_conversation(self, user_id: Optional[str] = None) -> SessionContext:
        """Start a new conversation session with retry logic.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            New session context
            
        Raises:
            ConversationError: If session creation fails after retries
        """
        try:
            session_context = SessionContext(user_id=user_id)
            conversation_state = ConversationState(
                current_step=ConversationStep.PARSING,
                session_id=session_context.session_id
            )
            session_context.conversation_state = conversation_state
            
            # Store session with error recovery
            await self._safe_session_operation(
                lambda: self.session_storage.save_session(session_context),
                session_context.session_id,
                "save_session"
            )
            
            logger.info(f"Started new conversation session: {session_context.session_id}")
            return session_context
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            raise ConversationError(f"Failed to start conversation: {str(e)}")
    
    async def process_requirement(self, requirement: SpaceRequirement, 
                                session_context: SessionContext) -> Dict[str, Any]:
        """Process a space requirement through conversation flow with error recovery.
        
        Args:
            requirement: The space requirement to process
            session_context: Current session context
            
        Returns:
            Dictionary containing response and any generated JSON
        """
        try:
            if not session_context.conversation_state:
                raise InvalidStateError("No conversation state in session context")
                
            state = session_context.conversation_state
            
            # Save current state for recovery
            await self._save_recovery_state(session_context, "process_requirement")
            
            state.current_step = ConversationStep.PARSING
            
            # Check if requirement needs clarification
            missing_specs = self._identify_missing_specifications(requirement)
            
            if missing_specs:
                # Generate clarification questions with retry
                questions = await self._generate_clarification_questions_with_retry(
                    requirement, missing_specs, session_context.session_id
                )
                
                # Add questions to state
                for question_text in questions:
                    question = Question(
                        text=question_text,
                        question_type="specification",
                        required=True
                    )
                    state.add_question(question.__dict__)
                
                state.current_step = ConversationStep.CLARIFYING
                
                # Save updated session with error recovery
                await self._safe_session_operation(
                    lambda: self.session_storage.save_session(session_context),
                    session_context.session_id,
                    "save_session"
                )
                
                return {
                    "message": "I need some additional information to create your space.",
                    "questions": [q["text"] for q in state.pending_questions],
                    "needs_clarification": True,
                    "session_id": session_context.session_id
                }
            else:
                # Requirement is complete, proceed to generation
                state.current_step = ConversationStep.GENERATING
                await self._safe_session_operation(
                    lambda: self.session_storage.save_session(session_context),
                    session_context.session_id,
                    "save_session"
                )
                
                return {
                    "message": "Space requirement is complete and ready for generation.",
                    "needs_clarification": False,
                    "ready_for_generation": True,
                    "session_id": session_context.session_id
                }
                
        except Exception as e:
            logger.error(f"Failed to process requirement: {e}")
            
            # Attempt recovery
            recovery_result = await self._attempt_error_recovery(
                session_context.session_id, "process_requirement", e
            )
            
            if recovery_result["recovered"]:
                return recovery_result["result"]
            else:
                return {
                    "error": f"Failed to process space requirement: {str(e)}",
                    "needs_clarification": False,
                    "session_id": session_context.session_id,
                    "recovery_available": recovery_result["recovery_available"]
                }
    
    async def process_clarification_answer(self, answer: str, question_id: str,
                                         session_context: SessionContext) -> Dict[str, Any]:
        """Process an answer to a clarification question with error recovery.
        
        Args:
            answer: User's answer
            question_id: ID of the question being answered
            session_context: Current session context
            
        Returns:
            Dictionary containing response and next steps
        """
        try:
            if not session_context.conversation_state:
                raise InvalidStateError("No conversation state in session context")
                
            state = session_context.conversation_state
            
            # Save current state for recovery
            await self._save_recovery_state(session_context, "process_clarification_answer")
            
            # Find the question
            question_dict = None
            for q in state.pending_questions:
                if q.get("id") == question_id:
                    question_dict = q
                    break
            
            if not question_dict:
                return {
                    "error": "Question not found",
                    "session_id": session_context.session_id
                }
            
            # Process the answer using Bedrock with retry
            processed_response = await self._process_user_response_with_retry(
                question_dict["text"], answer, session_context.session_id
            )
            
            if processed_response.get("understood", False):
                # Mark question as answered and remove from pending
                question_dict["answered"] = True
                question_dict["answer"] = answer
                question_dict["extracted_info"] = processed_response.get("extracted_info", {})
                
                # Remove from pending questions
                state.remove_question(question_id)
                
                # Check if we need follow-up
                if processed_response.get("needs_followup", False):
                    followup_question = Question(
                        text=processed_response.get("followup_question", "Could you please provide more details?"),
                        question_type="followup",
                        required=True
                    )
                    state.add_question(followup_question.__dict__)
                
                # Check if all questions are answered
                if not state.has_pending_questions():
                    state.current_step = ConversationStep.GENERATING
                    await self._safe_session_operation(
                        lambda: self.session_storage.save_session(session_context),
                        session_context.session_id,
                        "save_session"
                    )
                    
                    return {
                        "message": "Thank you! I have all the information needed to create your space.",
                        "complete": True,
                        "ready_for_generation": True,
                        "session_id": session_context.session_id
                    }
                else:
                    # More questions remain
                    next_questions = [q["text"] for q in state.pending_questions]
                    await self._safe_session_operation(
                        lambda: self.session_storage.save_session(session_context),
                        session_context.session_id,
                        "save_session"
                    )
                    
                    return {
                        "message": "Thank you for that information.",
                        "questions": next_questions,
                        "complete": False,
                        "session_id": session_context.session_id
                    }
            else:
                # Answer wasn't understood, ask for clarification
                return {
                    "message": "I didn't quite understand that. Could you please rephrase your answer?",
                    "questions": [question_dict["text"]],
                    "complete": False,
                    "session_id": session_context.session_id
                }
                
        except Exception as e:
            logger.error(f"Failed to process clarification answer: {e}")
            
            # Attempt recovery
            recovery_result = await self._attempt_error_recovery(
                session_context.session_id, "process_clarification_answer", e
            )
            
            if recovery_result["recovered"]:
                return recovery_result["result"]
            else:
                return {
                    "error": f"Failed to process answer: {str(e)}",
                    "session_id": session_context.session_id,
                    "recovery_available": recovery_result["recovery_available"]
                }
    
    async def _generate_clarification_questions_with_retry(self, requirement: SpaceRequirement,
                                                         missing_specs: List[str],
                                                         session_id: str) -> List[str]:
        """Generate clarification questions with retry logic.
        
        Args:
            requirement: Space requirement needing clarification
            missing_specs: List of missing specifications
            session_id: Session identifier for error tracking
            
        Returns:
            List of clarification questions
        """
        for attempt in range(self.max_retry_attempts):
            try:
                questions = await self._generate_clarification_questions(requirement, missing_specs)
                return questions
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed to generate clarification questions: {e}")
                
                if attempt == self.max_retry_attempts - 1:
                    # Final attempt failed, use fallback
                    logger.error(f"All attempts failed, using fallback questions for session {session_id}")
                    return self._generate_fallback_questions(missing_specs)
                
                # Wait before retry
                await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))
        
        # Should not reach here, but return fallback as safety
        return self._generate_fallback_questions(missing_specs)
    
    async def _process_user_response_with_retry(self, question: str, user_answer: str,
                                              session_id: str) -> Dict[str, Any]:
        """Process user response with retry logic.
        
        Args:
            question: The original question
            user_answer: User's response
            session_id: Session identifier for error tracking
            
        Returns:
            Processed response
        """
        for attempt in range(self.max_retry_attempts):
            try:
                return await self.bedrock_client.process_user_response(
                    question=question,
                    user_answer=user_answer,
                    context=f"Session: {session_id}"
                )
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed to process user response: {e}")
                
                if attempt == self.max_retry_attempts - 1:
                    # Final attempt failed, use fallback processing
                    logger.error(f"All attempts failed, using fallback processing for session {session_id}")
                    return self._fallback_response_processing(question, user_answer)
                
                # Wait before retry
                await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))
        
        # Should not reach here, but return fallback as safety
        return self._fallback_response_processing(question, user_answer)
    
    def _fallback_response_processing(self, question: str, user_answer: str) -> Dict[str, Any]:
        """Fallback response processing when Bedrock is unavailable.
        
        Args:
            question: The original question
            user_answer: User's response
            
        Returns:
            Fallback processed response
        """
        # Simple fallback processing
        return {
            "understood": True,
            "extracted_info": {"raw_answer": user_answer},
            "needs_followup": False,
            "followup_question": None
        }
    
    async def _safe_session_operation(self, operation, session_id: str, operation_name: str):
        """Safely execute a session operation with error handling.
        
        Args:
            operation: The operation to execute
            session_id: Session identifier
            operation_name: Name of the operation for logging
        """
        for attempt in range(self.max_retry_attempts):
            try:
                await operation()
                return
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {operation_name} on session {session_id}: {e}")
                
                if attempt == self.max_retry_attempts - 1:
                    logger.error(f"All attempts failed for {operation_name} on session {session_id}")
                    raise
                
                await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))
    
    async def _save_recovery_state(self, session_context: SessionContext, operation: str):
        """Save current state for error recovery.
        
        Args:
            session_context: Current session context
            operation: Name of the operation being performed
        """
        try:
            recovery_data = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "session_state": {
                    "session_id": session_context.session_id,
                    "user_id": session_context.user_id,
                    "conversation_step": session_context.conversation_state.current_step.value if session_context.conversation_state else None,
                    "pending_questions_count": len(session_context.conversation_state.pending_questions) if session_context.conversation_state else 0,
                    "collected_specs_count": len(session_context.conversation_state.collected_specs) if session_context.conversation_state else 0
                }
            }
            
            self._error_recovery_cache[session_context.session_id] = recovery_data
            
        except Exception as e:
            logger.warning(f"Failed to save recovery state: {e}")
    
    async def _attempt_error_recovery(self, session_id: str, operation: str, 
                                    error: Exception) -> Dict[str, Any]:
        """Attempt to recover from an error.
        
        Args:
            session_id: Session identifier
            operation: Operation that failed
            error: The error that occurred
            
        Returns:
            Recovery result
        """
        try:
            recovery_data = self._error_recovery_cache.get(session_id)
            
            if not recovery_data:
                return {
                    "recovered": False,
                    "recovery_available": False,
                    "reason": "No recovery data available"
                }
            
            # Check if we can recover based on error type
            if isinstance(error, (BedrockServiceError, ConnectionError)):
                # Service errors - try to continue with fallback
                return {
                    "recovered": True,
                    "recovery_available": True,
                    "result": {
                        "message": "Service temporarily unavailable. Using fallback processing.",
                        "session_id": session_id,
                        "fallback_mode": True
                    }
                }
            elif isinstance(error, InvalidStateError):
                # State errors - try to restore from recovery data
                try:
                    session_context = await self.session_storage.get_session(session_id)
                    if session_context:
                        return {
                            "recovered": True,
                            "recovery_available": True,
                            "result": {
                                "message": "Session state recovered. Please try your request again.",
                                "session_id": session_id,
                                "recovered": True
                            }
                        }
                except Exception as recovery_error:
                    logger.error(f"Recovery attempt failed: {recovery_error}")
            
            return {
                "recovered": False,
                "recovery_available": True,
                "reason": f"Could not recover from {type(error).__name__}"
            }
            
        except Exception as e:
            logger.error(f"Error recovery attempt failed: {e}")
            return {
                "recovered": False,
                "recovery_available": False,
                "reason": f"Recovery process failed: {str(e)}"
            }
    
    async def recover_session(self, session_id: str) -> Dict[str, Any]:
        """Manually recover a session from error state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Recovery result
        """
        try:
            # Try to get session from storage
            session_context = await self.session_storage.get_session(session_id)
            
            if not session_context:
                return {
                    "recovered": False,
                    "error": "Session not found",
                    "session_id": session_id
                }
            
            # Check recovery data
            recovery_data = self._error_recovery_cache.get(session_id)
            
            if recovery_data:
                logger.info(f"Recovering session {session_id} from {recovery_data['operation']}")
            
            # Validate session state
            if not session_context.conversation_state:
                # Create new conversation state
                session_context.conversation_state = ConversationState(
                    current_step=ConversationStep.PARSING,
                    session_id=session_id
                )
            
            # Save recovered session
            await self.session_storage.save_session(session_context)
            
            # Clear recovery cache
            self._error_recovery_cache.pop(session_id, None)
            
            return {
                "recovered": True,
                "message": "Session successfully recovered",
                "session_id": session_id,
                "current_step": session_context.conversation_state.current_step.value,
                "recovery_data": recovery_data
            }
            
        except Exception as e:
            logger.error(f"Failed to recover session {session_id}: {e}")
            return {
                "recovered": False,
                "error": f"Recovery failed: {str(e)}",
                "session_id": session_id
            }
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired conversation sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            cleaned_count = await self.session_storage.cleanup_expired_sessions(
                timeout_minutes=self.session_timeout_minutes
            )
            
            # Also cleanup recovery cache for expired sessions
            current_sessions = await self.session_storage.list_sessions()
            active_session_ids = {session.session_id for session in current_sessions}
            
            expired_recovery_keys = [
                session_id for session_id in self._error_recovery_cache.keys()
                if session_id not in active_session_ids
            ]
            
            for session_id in expired_recovery_keys:
                self._error_recovery_cache.pop(session_id, None)
            
            if expired_recovery_keys:
                logger.info(f"Cleaned up recovery cache for {len(expired_recovery_keys)} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the current status of a conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session status information
        """
        try:
            session_context = await self.session_storage.get_session(session_id)
            if not session_context or not session_context.conversation_state:
                return {"error": "Session not found", "session_id": session_id}
            
            state = session_context.conversation_state
            
            return {
                "session_id": session_id,
                "current_step": state.current_step.value,
                "pending_questions": len(state.pending_questions),
                "collected_specs": len(state.collected_specs),
                "created_at": session_context.created_at.isoformat(),
                "last_activity": session_context.last_activity.isoformat(),
                "ready_for_generation": state.current_step == ConversationStep.GENERATING
            }
            
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return {"error": f"Failed to get session status: {str(e)}", "session_id": session_id}
    
    async def reset_conversation(self, session_id: str) -> Dict[str, Any]:
        """Reset a conversation to start over.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Reset confirmation
        """
        try:
            session_context = await self.session_storage.get_session(session_id)
            if not session_context:
                return {"error": "Session not found", "session_id": session_id}
            
            # Reset conversation state
            conversation_state = ConversationState(
                current_step=ConversationStep.PARSING,
                session_id=session_id
            )
            session_context.conversation_state = conversation_state
            session_context.update_activity()
            
            # Save updated session
            await self.session_storage.save_session(session_context)
            
            return {
                "message": "Conversation has been reset. You can start over with a new space description.",
                "session_id": session_id,
                "reset": True
            }
            
        except Exception as e:
            logger.error(f"Failed to reset conversation: {e}")
            return {"error": f"Failed to reset conversation: {str(e)}", "session_id": session_id}
    
    def _identify_missing_specifications(self, requirement: SpaceRequirement) -> List[str]:
        """Identify which element specifications are missing or incomplete.
        
        Args:
            requirement: Space requirement to analyze
            
        Returns:
            List of missing specification types
        """
        missing = []
        
        for element in requirement.elements:
            if element.specifications is None:
                if element.type == ElementType.WINDOW:
                    missing.append(f"window specifications (count: {element.count})")
                elif element.type == ElementType.DOOR:
                    missing.append(f"door specifications (count: {element.count})")
            else:
                spec = element.specifications
                if spec.width is None or spec.height is None:
                    missing.append(f"{element.type.value} dimensions")
                if spec.wall is None:
                    missing.append(f"{element.type.value} wall placement")
        
        return missing
    
    async def _generate_clarification_questions(self, requirement: SpaceRequirement, 
                                              missing_specs: List[str]) -> List[str]:
        """Generate clarification questions using Bedrock.
        
        Args:
            requirement: Space requirement needing clarification
            missing_specs: List of missing specifications
            
        Returns:
            List of clarification questions
        """
        try:
            # Create a description of the space requirement
            space_desc = f"A {requirement.room_type or 'room'} that is "
            space_desc += f"{requirement.dimensions.width} x {requirement.dimensions.length}"
            if requirement.dimensions.height:
                space_desc += f" x {requirement.dimensions.height}"
            space_desc += f" {requirement.dimensions.units.value}"
            
            if requirement.elements:
                elements_desc = []
                for element in requirement.elements:
                    elements_desc.append(f"{element.count} {element.type.value}{'s' if element.count > 1 else ''}")
                space_desc += f" with {', '.join(elements_desc)}"
            
            questions = await self.bedrock_client.generate_clarification_questions(
                space_requirement=space_desc,
                missing_elements=missing_specs
            )
            
            return questions if questions else self._generate_fallback_questions(missing_specs)
            
        except Exception as e:
            logger.error(f"Failed to generate clarification questions: {e}")
            return self._generate_fallback_questions(missing_specs)
    
    def _generate_fallback_questions(self, missing_specs: List[str]) -> List[str]:
        """Generate fallback questions when Bedrock is unavailable.
        
        Args:
            missing_specs: List of missing specifications
            
        Returns:
            List of fallback questions
        """
        questions = []
        for spec in missing_specs:
            if "window" in spec.lower():
                if "dimensions" in spec:
                    questions.append("What are the dimensions of the window (width x height in meters)?")
                if "placement" in spec:
                    questions.append("Which wall should the window be placed on (north, south, east, or west)?")
            elif "door" in spec.lower():
                if "dimensions" in spec:
                    questions.append("What are the dimensions of the door (width x height in meters)?")
                if "placement" in spec:
                    questions.append("Which wall should the door be placed on (north, south, east, or west)?")
            else:
                questions.append(f"Could you provide more details about: {spec}?")
        
        return questions
    
    async def orchestrate_conversation_flow(self, user_input: str, 
                                           session_id: str) -> Dict[str, Any]:
        """Orchestrate the complete conversation flow from user input to response.
        
        Args:
            user_input: User's input text
            session_id: Session identifier
            
        Returns:
            Complete response with next steps
        """
        try:
            # Get or create session
            session_context = await self.session_storage.get_session(session_id)
            if not session_context:
                return {"error": "Session not found", "session_id": session_id}
            
            state = session_context.conversation_state
            if not state:
                return {"error": "No conversation state", "session_id": session_id}
            
            # Route based on current conversation step
            if state.current_step == ConversationStep.PARSING:
                return await self._handle_parsing_step(user_input, session_context)
            elif state.current_step == ConversationStep.CLARIFYING:
                return await self._handle_clarifying_step(user_input, session_context)
            elif state.current_step == ConversationStep.GENERATING:
                return await self._handle_generating_step(user_input, session_context)
            else:
                return {
                    "error": f"Unknown conversation step: {state.current_step}",
                    "session_id": session_id
                }
                
        except Exception as e:
            logger.error(f"Failed to orchestrate conversation flow: {e}")
            return {
                "error": f"Conversation flow error: {str(e)}",
                "session_id": session_id
            }
    
    async def _handle_parsing_step(self, user_input: str, 
                                 session_context: SessionContext) -> Dict[str, Any]:
        """Handle the parsing step of conversation flow.
        
        Args:
            user_input: User's space description
            session_context: Current session context
            
        Returns:
            Response for parsing step
        """
        try:
            # Parse the user input to extract space requirement
            from nl_floorspace_agent.parser.nl_parser import NaturalLanguageParser
            
            parser = NaturalLanguageParser()
            parse_result = parser.parse_space_description(user_input)
            
            if not parse_result.is_valid or not parse_result.space_requirement:
                return {
                    "message": "I couldn't understand your space description. Could you please rephrase it?",
                    "needs_clarification": False,
                    "session_id": session_context.session_id,
                    "suggestions": [
                        "Try describing dimensions like '5m x 4m room'",
                        "Mention any windows or doors you want",
                        "Specify the room type if relevant"
                    ],
                    "parsing_errors": [error.message for error in parse_result.validation_result.errors] if parse_result.validation_result else []
                }
            
            # Extract the space requirement from the parse result
            space_requirement = parse_result.space_requirement
            
            # Process the requirement
            return await self.process_requirement(space_requirement, session_context)
            
        except Exception as e:
            logger.error(f"Failed to handle parsing step: {e}")
            return {
                "error": f"Failed to parse space description: {str(e)}",
                "session_id": session_context.session_id
            }
    
    async def _handle_clarifying_step(self, user_input: str,
                                    session_context: SessionContext) -> Dict[str, Any]:
        """Handle the clarifying step of conversation flow.
        
        Args:
            user_input: User's answer to clarification question
            session_context: Current session context
            
        Returns:
            Response for clarifying step
        """
        try:
            state = session_context.conversation_state
            
            if not state.has_pending_questions():
                # No pending questions, move to generation
                state.current_step = ConversationStep.GENERATING
                await self.session_storage.save_session(session_context)
                
                return {
                    "message": "All information collected! Ready to generate your space.",
                    "ready_for_generation": True,
                    "session_id": session_context.session_id
                }
            
            # Get the next pending question
            current_question = state.pending_questions[0]
            question_id = current_question.get("id")
            
            if not question_id:
                return {
                    "error": "Invalid question format",
                    "session_id": session_context.session_id
                }
            
            # Process the answer
            return await self.process_clarification_answer(
                answer=user_input,
                question_id=question_id,
                session_context=session_context
            )
            
        except Exception as e:
            logger.error(f"Failed to handle clarifying step: {e}")
            return {
                "error": f"Failed to process clarification: {str(e)}",
                "session_id": session_context.session_id
            }
    
    async def _handle_generating_step(self, user_input: str,
                                    session_context: SessionContext) -> Dict[str, Any]:
        """Handle the generating step of conversation flow.
        
        Args:
            user_input: User's input during generation
            session_context: Current session context
            
        Returns:
            Response for generating step
        """
        try:
            # In the generating step, we might handle commands like:
            # - "generate" or "create" to start generation
            # - "modify" to go back to clarification
            # - "restart" to start over
            
            user_input_lower = user_input.lower().strip()
            
            if any(word in user_input_lower for word in ["generate", "create", "build", "make"]):
                return {
                    "message": "Starting space generation with collected specifications...",
                    "action": "generate",
                    "session_id": session_context.session_id,
                    "specifications": self._get_collected_specifications(session_context)
                }
            elif any(word in user_input_lower for word in ["modify", "change", "update"]):
                # Go back to clarification
                state = session_context.conversation_state
                state.current_step = ConversationStep.CLARIFYING
                await self.session_storage.save_session(session_context)
                
                return {
                    "message": "What would you like to modify?",
                    "action": "modify",
                    "session_id": session_context.session_id,
                    "current_specs": self._get_collected_specifications(session_context)
                }
            elif any(word in user_input_lower for word in ["restart", "start over", "reset"]):
                return await self.reset_conversation(session_context.session_id)
            else:
                return {
                    "message": "I'm ready to generate your space. Say 'generate' to proceed, 'modify' to make changes, or 'restart' to start over.",
                    "session_id": session_context.session_id,
                    "options": ["generate", "modify", "restart"]
                }
                
        except Exception as e:
            logger.error(f"Failed to handle generating step: {e}")
            return {
                "error": f"Failed to handle generation step: {str(e)}",
                "session_id": session_context.session_id
            }
    
    def _get_collected_specifications(self, session_context: SessionContext) -> Dict[str, Any]:
        """Get a summary of collected specifications.
        
        Args:
            session_context: Current session context
            
        Returns:
            Summary of collected specifications
        """
        try:
            state = session_context.conversation_state
            if not state:
                return {}
            
            # Extract information from answered questions
            answered_questions = []
            for question_dict in state.pending_questions:
                if question_dict.get("answered", False):
                    answered_questions.append({
                        "question": question_dict.get("text", ""),
                        "answer": question_dict.get("answer", ""),
                        "type": question_dict.get("question_type", ""),
                        "extracted_info": question_dict.get("extracted_info", {})
                    })
            
            return {
                "answered_questions": answered_questions,
                "collected_specs": [
                    {
                        "width": spec.width,
                        "height": spec.height,
                        "wall": spec.wall,
                        "alpha": spec.alpha
                    }
                    for spec in state.collected_specs
                ],
                "session_info": {
                    "session_id": state.session_id,
                    "current_step": state.current_step.value,
                    "created_at": state.created_at.isoformat(),
                    "last_updated": state.last_updated.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get collected specifications: {e}")
            return {}
    
    async def determine_conversation_completion(self, session_context: SessionContext) -> Dict[str, Any]:
        """Determine if the conversation is complete and ready for next steps.
        
        Args:
            session_context: Current session context
            
        Returns:
            Completion status and next steps
        """
        try:
            state = session_context.conversation_state
            if not state:
                return {"complete": False, "reason": "No conversation state"}
            
            # Check completion criteria
            completion_status = {
                "complete": False,
                "ready_for_generation": False,
                "missing_requirements": [],
                "session_id": session_context.session_id
            }
            
            # Check if we're in generating step
            if state.current_step == ConversationStep.GENERATING:
                completion_status["complete"] = True
                completion_status["ready_for_generation"] = True
                return completion_status
            
            # Check if all questions are answered
            if state.has_pending_questions():
                unanswered_count = len([q for q in state.pending_questions if not q.get("answered", False)])
                completion_status["missing_requirements"].append(f"{unanswered_count} unanswered questions")
            
            # Check if we have collected specifications
            if len(state.collected_specs) == 0:
                # Look for extracted info in answered questions
                extracted_specs = 0
                for question_dict in state.pending_questions:
                    if question_dict.get("answered", False) and question_dict.get("extracted_info"):
                        extracted_specs += 1
                
                if extracted_specs == 0:
                    completion_status["missing_requirements"].append("No element specifications collected")
            
            # Determine if complete
            if len(completion_status["missing_requirements"]) == 0:
                completion_status["complete"] = True
                completion_status["ready_for_generation"] = True
            
            return completion_status
            
        except Exception as e:
            logger.error(f"Failed to determine conversation completion: {e}")
            return {
                "complete": False,
                "error": f"Failed to check completion: {str(e)}",
                "session_id": session_context.session_id
            }
    
    async def handle_conversation_timeout(self, session_id: str) -> Dict[str, Any]:
        """Handle conversation timeout scenarios.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Timeout handling response
        """
        try:
            session_context = await self.session_storage.get_session(session_id)
            if not session_context:
                return {"error": "Session not found", "session_id": session_id}
            
            # Save current state before timeout
            timeout_metadata = {
                "timeout_at": datetime.now().isoformat(),
                "last_step": session_context.conversation_state.current_step.value if session_context.conversation_state else "unknown",
                "pending_questions": len(session_context.conversation_state.pending_questions) if session_context.conversation_state else 0
            }
            
            session_context.add_metadata("timeout_info", timeout_metadata)
            await self.session_storage.save_session(session_context)
            
            return {
                "message": "Your session has timed out, but your progress has been saved. You can resume where you left off.",
                "session_id": session_id,
                "can_resume": True,
                "timeout_info": timeout_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to handle conversation timeout: {e}")
            return {
                "error": f"Failed to handle timeout: {str(e)}",
                "session_id": session_id
            }