"""Error recovery and retry mechanisms for workflow execution."""

import asyncio
from typing import Dict, Any, Optional, Callable, List, Type
from enum import Enum
import logging
from datetime import datetime, timedelta
from tenacity import (
    retry, stop_after_attempt, wait_exponential, wait_fixed,
    retry_if_exception_type, retry_if_result, before_sleep_log
)

from .tasks import WorkflowTask, TaskResult, TaskStatus
from .state import WorkflowState

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies for failed tasks."""
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    ABORT = "abort"
    MANUAL = "manual"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction:
    """Defines a recovery action for a specific error type."""
    
    def __init__(
        self,
        strategy: RecoveryStrategy,
        max_attempts: int = 3,
        wait_strategy: str = "exponential",
        fallback_func: Optional[Callable] = None,
        condition: Optional[Callable[[Exception], bool]] = None
    ):
        self.strategy = strategy
        self.max_attempts = max_attempts
        self.wait_strategy = wait_strategy
        self.fallback_func = fallback_func
        self.condition = condition or (lambda e: True)


class ErrorRecoveryManager:
    """Manages error recovery strategies and retry logic."""
    
    def __init__(self):
        self.recovery_rules: Dict[Type[Exception], RecoveryAction] = {}
        self.global_recovery_action = RecoveryAction(RecoveryStrategy.RETRY, max_attempts=2)
        self.recovery_history: List[Dict[str, Any]] = []
        
        # Set up default recovery rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Set up default recovery rules for common exceptions."""
        
        # Network-related errors - retry with exponential backoff
        self.recovery_rules[ConnectionError] = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=5,
            wait_strategy="exponential"
        )
        
        self.recovery_rules[TimeoutError] = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=3,
            wait_strategy="exponential"
        )
        
        # Value errors - usually don't retry, skip or abort
        self.recovery_rules[ValueError] = RecoveryAction(
            strategy=RecoveryStrategy.SKIP,
            max_attempts=1
        )
        
        # Type errors - usually indicate programming errors, abort
        self.recovery_rules[TypeError] = RecoveryAction(
            strategy=RecoveryStrategy.ABORT,
            max_attempts=1
        )
        
        # Permission errors - retry a few times then skip
        self.recovery_rules[PermissionError] = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=2,
            wait_strategy="fixed"
        )
    
    def add_recovery_rule(self, exception_type: Type[Exception], action: RecoveryAction):
        """Add a recovery rule for a specific exception type.
        
        Args:
            exception_type: Type of exception to handle
            action: Recovery action to take
        """
        self.recovery_rules[exception_type] = action
        logger.info(f"Added recovery rule for {exception_type.__name__}: {action.strategy.value}")
    
    def get_recovery_action(self, exception: Exception) -> RecoveryAction:
        """Get the appropriate recovery action for an exception.
        
        Args:
            exception: Exception that occurred
            
        Returns:
            RecoveryAction to take
        """
        # Check for specific exception type rules
        for exc_type, action in self.recovery_rules.items():
            if isinstance(exception, exc_type) and action.condition(exception):
                return action
        
        # Fall back to global recovery action
        return self.global_recovery_action
    
    def record_recovery_attempt(self, task_name: str, exception: Exception, action: RecoveryAction, attempt: int):
        """Record a recovery attempt for analysis.
        
        Args:
            task_name: Name of the task that failed
            exception: Exception that occurred
            action: Recovery action taken
            attempt: Attempt number
        """
        record = {
            "timestamp": datetime.now(),
            "task_name": task_name,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "recovery_strategy": action.strategy.value,
            "attempt": attempt
        }
        self.recovery_history.append(record)
        logger.info(f"Recovery attempt {attempt} for task {task_name}: {action.strategy.value}")
    
    async def execute_with_recovery(
        self, 
        task: WorkflowTask, 
        context: Dict[str, Any],
        state: WorkflowState
    ) -> TaskResult:
        """Execute a task with error recovery.
        
        Args:
            task: Task to execute
            context: Execution context
            state: Workflow state
            
        Returns:
            TaskResult from execution
        """
        last_exception = None
        attempt = 0
        
        while attempt < task.max_retries + 1:
            try:
                attempt += 1
                logger.debug(f"Executing task {task.name}, attempt {attempt}")
                
                # Execute the task
                result = await task.execute(context)
                
                if result.status == TaskStatus.COMPLETED:
                    return result
                elif result.status == TaskStatus.FAILED and result.error:
                    last_exception = result.error
                    raise result.error
                else:
                    # Unexpected status
                    return result
                    
            except Exception as e:
                last_exception = e
                recovery_action = self.get_recovery_action(e)
                self.record_recovery_attempt(task.name, e, recovery_action, attempt)
                
                # Handle different recovery strategies
                if recovery_action.strategy == RecoveryStrategy.ABORT:
                    logger.error(f"Aborting task {task.name} due to {type(e).__name__}")
                    state.add_error(e, task.name)
                    return TaskResult(
                        status=TaskStatus.FAILED,
                        error=e,
                        retry_count=attempt
                    )
                
                elif recovery_action.strategy == RecoveryStrategy.SKIP:
                    if attempt >= recovery_action.max_attempts:
                        logger.warning(f"Skipping task {task.name} after {attempt} attempts")
                        return TaskResult(
                            status=TaskStatus.SKIPPED,
                            error=e,
                            retry_count=attempt
                        )
                
                elif recovery_action.strategy == RecoveryStrategy.FALLBACK:
                    if recovery_action.fallback_func:
                        try:
                            fallback_result = await recovery_action.fallback_func(context)
                            logger.info(f"Fallback successful for task {task.name}")
                            return TaskResult(
                                status=TaskStatus.COMPLETED,
                                data=fallback_result,
                                retry_count=attempt
                            )
                        except Exception as fallback_error:
                            logger.error(f"Fallback failed for task {task.name}: {fallback_error}")
                            last_exception = fallback_error
                
                elif recovery_action.strategy == RecoveryStrategy.MANUAL:
                    logger.error(f"Manual intervention required for task {task.name}: {e}")
                    state.add_error(e, task.name)
                    return TaskResult(
                        status=TaskStatus.FAILED,
                        error=e,
                        retry_count=attempt
                    )
                
                # For RETRY strategy or if other strategies haven't returned yet
                if attempt >= recovery_action.max_attempts:
                    logger.error(f"Task {task.name} failed after {attempt} attempts")
                    state.add_error(last_exception, task.name)
                    return TaskResult(
                        status=TaskStatus.FAILED,
                        error=last_exception,
                        retry_count=attempt
                    )
                
                # Wait before retry
                wait_time = self._calculate_wait_time(recovery_action, attempt)
                if wait_time > 0:
                    logger.info(f"Waiting {wait_time:.2f}s before retry {attempt + 1}")
                    await asyncio.sleep(wait_time)
        
        # Should not reach here, but handle gracefully
        return TaskResult(
            status=TaskStatus.FAILED,
            error=last_exception or Exception("Unknown error"),
            retry_count=attempt
        )
    
    def _calculate_wait_time(self, action: RecoveryAction, attempt: int) -> float:
        """Calculate wait time before retry.
        
        Args:
            action: Recovery action configuration
            attempt: Current attempt number
            
        Returns:
            Wait time in seconds
        """
        if action.wait_strategy == "exponential":
            return min(2 ** (attempt - 1), 60)  # Cap at 60 seconds
        elif action.wait_strategy == "fixed":
            return 2.0  # Fixed 2 second wait
        elif action.wait_strategy == "linear":
            return attempt * 1.0  # Linear increase
        else:
            return 1.0  # Default 1 second
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get statistics about recovery attempts.
        
        Returns:
            Dictionary containing recovery statistics
        """
        if not self.recovery_history:
            return {"total_attempts": 0}
        
        total_attempts = len(self.recovery_history)
        strategies_used = {}
        exception_types = {}
        
        for record in self.recovery_history:
            strategy = record["recovery_strategy"]
            strategies_used[strategy] = strategies_used.get(strategy, 0) + 1
            
            exc_type = record["exception_type"]
            exception_types[exc_type] = exception_types.get(exc_type, 0) + 1
        
        return {
            "total_attempts": total_attempts,
            "strategies_used": strategies_used,
            "exception_types": exception_types,
            "recent_attempts": self.recovery_history[-10:]  # Last 10 attempts
        }
    
    def clear_history(self):
        """Clear recovery history."""
        self.recovery_history.clear()
        logger.info("Recovery history cleared")


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit breaker state.
        
        Returns:
            True if execution is allowed
        """
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "half-open"
                return True
            return False
        elif self.state == "half-open":
            return True
        
        return False
    
    def record_success(self):
        """Record a successful execution."""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state.
        
        Returns:
            Dictionary containing circuit breaker state
        """
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout
        }