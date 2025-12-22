"""Task definitions and execution framework for workflow coordination."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a workflow task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """Result of a task execution."""
    status: TaskStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    execution_time: Optional[float] = None
    retry_count: int = 0


@dataclass
class WorkflowTask:
    """A task in the workflow with dependencies and execution logic."""
    
    name: str
    execute_func: Callable[..., Awaitable[Any]]
    dependencies: Set[str] = field(default_factory=set)
    max_retries: int = 3
    timeout: Optional[float] = None
    required: bool = True
    
    # Runtime state
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[TaskResult] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize task state."""
        if self.result is None:
            self.result = TaskResult(status=TaskStatus.PENDING)
    
    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """Execute the task with the given context.
        
        Args:
            context: Execution context containing shared data
            
        Returns:
            TaskResult with execution outcome
        """
        self.status = TaskStatus.RUNNING
        self.start_time = datetime.now()
        
        try:
            logger.info(f"Executing task: {self.name}")
            
            if self.timeout:
                result_data = await asyncio.wait_for(
                    self.execute_func(context), 
                    timeout=self.timeout
                )
            else:
                result_data = await self.execute_func(context)
            
            self.end_time = datetime.now()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            self.result = TaskResult(
                status=TaskStatus.COMPLETED,
                data=result_data,
                execution_time=execution_time
            )
            self.status = TaskStatus.COMPLETED
            
            logger.info(f"Task {self.name} completed successfully in {execution_time:.2f}s")
            return self.result
            
        except Exception as e:
            self.end_time = datetime.now()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            self.result = TaskResult(
                status=TaskStatus.FAILED,
                error=e,
                execution_time=execution_time
            )
            self.status = TaskStatus.FAILED
            
            logger.error(f"Task {self.name} failed after {execution_time:.2f}s: {e}")
            return self.result
    
    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """Check if this task can be executed based on dependencies.
        
        Args:
            completed_tasks: Set of completed task names
            
        Returns:
            True if all dependencies are satisfied
        """
        return self.dependencies.issubset(completed_tasks)
    
    def reset(self):
        """Reset task state for re-execution."""
        self.status = TaskStatus.PENDING
        self.result = TaskResult(status=TaskStatus.PENDING)
        self.start_time = None
        self.end_time = None


class TaskBuilder:
    """Builder for creating workflow tasks with fluent interface."""
    
    def __init__(self, name: str, execute_func: Callable[..., Awaitable[Any]]):
        self.name = name
        self.execute_func = execute_func
        self.dependencies: Set[str] = set()
        self.max_retries = 3
        self.timeout: Optional[float] = None
        self.required = True
    
    def depends_on(self, *task_names: str) -> 'TaskBuilder':
        """Add dependencies to this task."""
        self.dependencies.update(task_names)
        return self
    
    def with_retries(self, max_retries: int) -> 'TaskBuilder':
        """Set maximum retry count."""
        self.max_retries = max_retries
        return self
    
    def with_timeout(self, timeout: float) -> 'TaskBuilder':
        """Set execution timeout in seconds."""
        self.timeout = timeout
        return self
    
    def optional(self) -> 'TaskBuilder':
        """Mark this task as optional (workflow continues if it fails)."""
        self.required = False
        return self
    
    def build(self) -> WorkflowTask:
        """Build the workflow task."""
        return WorkflowTask(
            name=self.name,
            execute_func=self.execute_func,
            dependencies=self.dependencies,
            max_retries=self.max_retries,
            timeout=self.timeout,
            required=self.required
        )


def task(name: str) -> Callable[[Callable[..., Awaitable[Any]]], TaskBuilder]:
    """Decorator for creating workflow tasks.
    
    Args:
        name: Name of the task
        
    Returns:
        Decorator function that creates a TaskBuilder
    """
    def decorator(func: Callable[..., Awaitable[Any]]) -> TaskBuilder:
        return TaskBuilder(name, func)
    
    return decorator