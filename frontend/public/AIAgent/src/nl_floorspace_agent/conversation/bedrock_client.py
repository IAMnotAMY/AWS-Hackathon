"""AWS Bedrock client for foundation model access."""

import boto3
import json
import asyncio
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError, BotoCoreError
import logging

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for AWS Bedrock foundation models."""
    
    def __init__(self, region: str = "us-east-1", model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """Initialize the Bedrock client.
        
        Args:
            region: AWS region
            model_id: Default model ID to use
        """
        self.region = region
        self.model_id = model_id
        self.client: Optional[Any] = None
        self._session_cache: Dict[str, Any] = {}
    
    def _get_client(self):
        """Get or create the Bedrock client."""
        if self.client is None:
            try:
                self.client = boto3.client('bedrock-runtime', region_name=self.region)
                logger.info(f"Initialized Bedrock client for region {self.region}")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock client: {e}")
                raise
        return self.client
    
    async def invoke_model(self, prompt: str, model_id: Optional[str] = None, 
                          max_tokens: int = 1000, temperature: float = 0.7,
                          system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Invoke a foundation model with a prompt.
        
        Args:
            prompt: The input prompt
            model_id: The model identifier (uses default if None)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system_prompt: Optional system prompt for context
            
        Returns:
            Model response with content and usage information
            
        Raises:
            ClientError: If AWS API call fails
            ValueError: If response format is invalid
        """
        if model_id is None:
            model_id = self.model_id
            
        try:
            client = self._get_client()
            
            # Prepare the request body based on model type
            if "anthropic.claude" in model_id:
                body = self._prepare_claude_request(prompt, max_tokens, temperature, system_prompt)
            else:
                # Default format for other models
                body = self._prepare_default_request(prompt, max_tokens, temperature, system_prompt)
            
            # Make the async call using asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType='application/json',
                    accept='application/json'
                )
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract content based on model type
            if "anthropic.claude" in model_id:
                return self._parse_claude_response(response_body)
            else:
                return self._parse_default_response(response_body)
                
        except ClientError as e:
            logger.error(f"AWS Bedrock API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response JSON: {e}")
            raise ValueError(f"Invalid JSON response from model: {e}")
        except Exception as e:
            logger.error(f"Unexpected error invoking model: {e}")
            raise
    
    def _prepare_claude_request(self, prompt: str, max_tokens: int, 
                               temperature: float, system_prompt: Optional[str]) -> Dict[str, Any]:
        """Prepare request body for Claude models."""
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "anthropic_version": "bedrock-2023-05-31"
        }
        
        if system_prompt:
            body["system"] = system_prompt
            
        return body
    
    def _prepare_default_request(self, prompt: str, max_tokens: int,
                                temperature: float, system_prompt: Optional[str]) -> Dict[str, Any]:
        """Prepare request body for other models."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
        return {
            "prompt": full_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    
    def _parse_claude_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        """Parse response from Claude models."""
        try:
            content = response_body.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                text = content[0].get("text", "")
            else:
                text = ""
                
            usage = response_body.get("usage", {})
            
            return {
                "response": text,
                "usage": {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0)
                },
                "model_id": response_body.get("model", "unknown"),
                "stop_reason": response_body.get("stop_reason", "unknown")
            }
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse Claude response: {e}")
            raise ValueError(f"Invalid Claude response format: {e}")
    
    def _parse_default_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        """Parse response from other models."""
        try:
            return {
                "response": response_body.get("completion", response_body.get("text", "")),
                "usage": response_body.get("usage", {"input_tokens": 0, "output_tokens": 0}),
                "model_id": response_body.get("model", "unknown"),
                "stop_reason": response_body.get("stop_reason", "unknown")
            }
        except (KeyError, TypeError) as e:
            logger.error(f"Failed to parse model response: {e}")
            raise ValueError(f"Invalid response format: {e}")
    
    async def generate_clarification_questions(self, space_requirement: str, 
                                             missing_elements: List[str]) -> List[str]:
        """Generate clarification questions for missing element specifications.
        
        Args:
            space_requirement: The original space requirement text
            missing_elements: List of elements needing clarification
            
        Returns:
            List of clarification questions
        """
        system_prompt = """You are an expert building designer assistant. Your job is to generate clear, specific clarification questions for building elements that need more details. Focus on dimensions, placement, and specifications that are essential for creating accurate building geometry."""
        
        prompt = f"""
        A user has requested a space with the following description:
        "{space_requirement}"
        
        The following elements need clarification:
        {', '.join(missing_elements)}
        
        Generate specific clarification questions for each element. Each question should ask for:
        1. Dimensions (width and height)
        2. Wall placement (which wall: north, south, east, west)
        3. Any other essential specifications
        
        Format your response as a JSON list of questions, where each question is a string.
        Example: ["What are the dimensions of the window (width x height)?", "Which wall should the window be placed on?"]
        
        Questions:
        """
        
        try:
            response = await self.invoke_model(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            # Try to parse JSON from response
            response_text = response["response"].strip()
            if response_text.startswith('[') and response_text.endswith(']'):
                questions = json.loads(response_text)
                return questions if isinstance(questions, list) else []
            else:
                # Fallback: split by lines and clean up
                lines = [line.strip() for line in response_text.split('\n') if line.strip()]
                return [line.strip('"').strip("'") for line in lines if line]
                
        except Exception as e:
            logger.error(f"Failed to generate clarification questions: {e}")
            # Fallback questions
            return [f"What are the dimensions for the {element}?" for element in missing_elements]
    
    async def process_user_response(self, question: str, user_answer: str, 
                                  context: str = "") -> Dict[str, Any]:
        """Process and validate a user's response to a clarification question.
        
        Args:
            question: The original question
            user_answer: User's response
            context: Additional context about the conversation
            
        Returns:
            Processed response with extracted information
        """
        system_prompt = """You are an expert at parsing user responses about building specifications. Extract structured information from user answers about dimensions, placement, and building elements."""
        
        prompt = f"""
        Question asked: "{question}"
        User's answer: "{user_answer}"
        Context: {context}
        
        Parse the user's answer and extract structured information. Return a JSON object with:
        - "understood": boolean indicating if the answer was clear
        - "extracted_info": object with any dimensions, placement, or specifications found
        - "needs_followup": boolean indicating if more clarification is needed
        - "followup_question": string with follow-up question if needed
        
        Example response:
        {{
            "understood": true,
            "extracted_info": {{"width": 1.2, "height": 1.5, "units": "meters", "wall": "north"}},
            "needs_followup": false,
            "followup_question": null
        }}
        """
        
        try:
            response = await self.invoke_model(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=300,
                temperature=0.2
            )
            
            # Try to parse JSON response
            response_text = response["response"].strip()
            if response_text.startswith('{') and response_text.endswith('}'):
                return json.loads(response_text)
            else:
                # Fallback response
                return {
                    "understood": True,
                    "extracted_info": {"raw_answer": user_answer},
                    "needs_followup": False,
                    "followup_question": None
                }
                
        except Exception as e:
            logger.error(f"Failed to process user response: {e}")
            return {
                "understood": False,
                "extracted_info": {"raw_answer": user_answer},
                "needs_followup": True,
                "followup_question": "Could you please clarify your answer?"
            }
    
    def clear_session_cache(self, session_id: Optional[str] = None) -> None:
        """Clear session cache for memory management.
        
        Args:
            session_id: Specific session to clear, or None to clear all
        """
        if session_id:
            self._session_cache.pop(session_id, None)
        else:
            self._session_cache.clear()
        logger.info(f"Cleared session cache for: {session_id or 'all sessions'}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available Bedrock models.
        
        Returns:
            List of model IDs available in the region
        """
        try:
            client = self._get_client()
            # Note: This would require bedrock (not bedrock-runtime) client
            # For now, return common model IDs
            return [
                "anthropic.claude-3-sonnet-20240229-v1:0",
                "anthropic.claude-3-haiku-20240307-v1:0",
                "anthropic.claude-instant-v1",
                "amazon.titan-text-express-v1"
            ]
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return [self.model_id]  # Return default model as fallback