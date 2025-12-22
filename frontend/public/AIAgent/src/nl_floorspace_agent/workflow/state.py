"""Workflow state management."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """State container for workflow execution."""
    
    # Shared context data
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Workflow metadata
    workflow_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Error tracking
    errors: list = field(default_factory=list)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the workflow context.
        
        Args:
            key: Context key
            value: Value to store
        """
        self.context[key] = value
        logger.debug(f"Workflow state updated: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the workflow context.
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Value from context or default
        """
        return self.context.get(key, default)
    
    def has(self, key: str) -> bool:
        """Check if a key exists in the context.
        
        Args:
            key: Context key
            
        Returns:
            True if key exists
        """
        return key in self.context
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple context values.
        
        Args:
            data: Dictionary of key-value pairs to update
        """
        self.context.update(data)
        logger.debug(f"Workflow state updated with {len(data)} items")
    
    def add_error(self, error: Exception, task_name: Optional[str] = None) -> None:
        """Add an error to the error log.
        
        Args:
            error: Exception that occurred
            task_name: Optional name of the task where error occurred
        """
        error_entry = {
            "error": error,
            "task": task_name,
            "timestamp": datetime.now()
        }
        self.errors.append(error_entry)
        logger.error(f"Error in workflow{f' (task: {task_name})' if task_name else ''}: {error}")
    
    def clear_errors(self) -> None:
        """Clear all errors from the log."""
        self.errors.clear()
    
    def get_errors(self) -> list:
        """Get all errors from the log.
        
        Returns:
            List of error entries
        """
        return self.errors.copy()
    
    def reset(self) -> None:
        """Reset the workflow state."""
        self.context.clear()
        self.errors.clear()
        self.start_time = None
        self.end_time = None
        logger.info("Workflow state reset")