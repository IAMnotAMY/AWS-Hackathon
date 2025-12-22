"""Workflow coordinator for orchestrating task execution."""

import asyncio
from typing import Dict, List, Set, Optional, Any
import logging
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .tasks import WorkflowTask, TaskStatus, TaskResult
from .state import WorkflowState
from .recovery import ErrorRecoveryManager, CircuitBreaker

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Base exception for workflow errors."""
    pass


class TaskDependencyError(WorkflowError):
    """Raised when task dependencies cannot be resolved."""
    pass


class WorkflowCoordinator:
    """Coordinates execution of workflow tasks with dependency management and error recovery."""
    
    def __init__(self):
        self.tasks: Dict[str, WorkflowTask] = {}
        self.state = WorkflowState()
        self._execution_lock = asyncio.Lock()
        
        # Error recovery and circuit breaker
        self.error_recovery = ErrorRecoveryManager()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Workflow state tracking
        self.failed_workflows = 0
        self.successful_workflows = 0
    
    def add_task(self, task: WorkflowTask) -> None:
        """Add a task to the workflow.
        
        Args:
            task: WorkflowTask to add
        """
        self.tasks[task.name] = task
        # Create circuit breaker for this task
        self.circuit_breakers[task.name] = CircuitBreaker()
        logger.info(f"Added task to workflow: {task.name}")
    
    def remove_task(self, task_name: str) -> None:
        """Remove a task from the workflow.
        
        Args:
            task_name: Name of task to remove
        """
        if task_name in self.tasks:
            del self.tasks[task_name]
            # Remove circuit breaker
            if task_name in self.circuit_breakers:
                del self.circuit_breakers[task_name]
            logger.info(f"Removed task from workflow: {task_name}")
    
    def get_task(self, task_name: str) -> Optional[WorkflowTask]:
        """Get a task by name.
        
        Args:
            task_name: Name of the task
            
        Returns:
            WorkflowTask if found, None otherwise
        """
        return self.tasks.get(task_name)
    
    def _validate_dependencies(self) -> None:
        """Validate that all task dependencies can be resolved.
        
        Raises:
            TaskDependencyError: If circular dependencies or missing tasks are found
        """
        # Check for missing dependencies
        all_task_names = set(self.tasks.keys())
        for task in self.tasks.values():
            missing_deps = task.dependencies - all_task_names
            if missing_deps:
                raise TaskDependencyError(
                    f"Task '{task.name}' has missing dependencies: {missing_deps}"
                )
        
        # Check for circular dependencies using topological sort
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_name: str) -> bool:
            if task_name in rec_stack:
                return True
            if task_name in visited:
                return False
            
            visited.add(task_name)
            rec_stack.add(task_name)
            
            task = self.tasks.get(task_name)
            if task:
                for dep in task.dependencies:
                    if has_cycle(dep):
                        return True
            
            rec_stack.remove(task_name)
            return False
        
        for task_name in self.tasks:
            if task_name not in visited:
                if has_cycle(task_name):
                    raise TaskDependencyError(f"Circular dependency detected involving task: {task_name}")
    
    def _get_execution_order(self) -> List[str]:
        """Get the execution order of tasks based on dependencies.
        
        Returns:
            List of task names in execution order
            
        Raises:
            TaskDependencyError: If dependencies cannot be resolved
        """
        self._validate_dependencies()
        
        # Topological sort
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(task_name: str):
            if task_name in temp_visited:
                raise TaskDependencyError(f"Circular dependency detected at task: {task_name}")
            if task_name in visited:
                return
            
            temp_visited.add(task_name)
            task = self.tasks[task_name]
            
            for dep in task.dependencies:
                visit(dep)
            
            temp_visited.remove(task_name)
            visited.add(task_name)
            result.append(task_name)
        
        for task_name in self.tasks:
            if task_name not in visited:
                visit(task_name)
        
        return result
    
    async def _execute_task_with_recovery(self, task: WorkflowTask) -> TaskResult:
        """Execute a task with enhanced error recovery.
        
        Args:
            task: Task to execute
            
        Returns:
            TaskResult from execution
        """
        circuit_breaker = self.circuit_breakers.get(task.name)
        
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for task {task.name}, skipping execution")
            return TaskResult(
                status=TaskStatus.SKIPPED,
                error=Exception("Circuit breaker open")
            )
        
        try:
            # Use error recovery manager for execution
            result = await self.error_recovery.execute_with_recovery(
                task, self.state.context, self.state
            )
            
            # Update circuit breaker based on result
            if circuit_breaker:
                if result.status == TaskStatus.COMPLETED:
                    circuit_breaker.record_success()
                elif result.status == TaskStatus.FAILED:
                    circuit_breaker.record_failure()
            
            return result
            
        except Exception as e:
            # Fallback error handling
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            logger.error(f"Unexpected error in task {task.name}: {e}")
            return TaskResult(
                status=TaskStatus.FAILED,
                error=e,
                retry_count=task.max_retries
            )
    
    async def execute_workflow(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, TaskResult]:
        """Execute the entire workflow.
        
        Args:
            initial_context: Initial context data for the workflow
            
        Returns:
            Dictionary mapping task names to their results
        """
        async with self._execution_lock:
            logger.info("Starting workflow execution")
            
            # Initialize state
            self.state.start_time = datetime.now()
            if initial_context:
                self.state.update(initial_context)
            
            # Get execution order
            try:
                execution_order = self._get_execution_order()
            except TaskDependencyError as e:
                logger.error(f"Workflow execution failed due to dependency error: {e}")
                raise
            
            results: Dict[str, TaskResult] = {}
            completed_tasks: Set[str] = set()
            failed_required_tasks: Set[str] = set()
            
            # Execute tasks in order
            for task_name in execution_order:
                task = self.tasks[task_name]
                
                # Skip if dependencies failed and this is a required task
                if not task.can_execute(completed_tasks):
                    logger.warning(f"Skipping task {task_name} due to failed dependencies")
                    task.status = TaskStatus.SKIPPED
                    results[task_name] = TaskResult(status=TaskStatus.SKIPPED)
                    continue
                
                # Execute the task
                try:
                    result = await self._execute_task_with_recovery(task)
                    results[task_name] = result
                    
                    if result.status == TaskStatus.COMPLETED:
                        completed_tasks.add(task_name)
                        # Store task result in workflow state
                        if result.data:
                            self.state.set(f"task_result_{task_name}", result.data)
                    elif result.status == TaskStatus.FAILED:
                        self.state.add_error(result.error, task_name)
                        if task.required:
                            failed_required_tasks.add(task_name)
                            logger.error(f"Required task {task_name} failed, workflow may be compromised")
                        else:
                            logger.warning(f"Optional task {task_name} failed, continuing workflow")
                
                except Exception as e:
                    logger.error(f"Unexpected error executing task {task_name}: {e}")
                    self.state.add_error(e, task_name)
                    result = TaskResult(status=TaskStatus.FAILED, error=e)
                    results[task_name] = result
                    
                    if task.required:
                        failed_required_tasks.add(task_name)
            
            self.state.end_time = datetime.now()
            execution_time = (self.state.end_time - self.state.start_time).total_seconds()
            
            # Log workflow completion
            completed_count = len(completed_tasks)
            failed_count = len(failed_required_tasks)
            total_count = len(self.tasks)
            
            if failed_count == 0:
                self.successful_workflows += 1
                logger.info(
                    f"Workflow execution completed successfully in {execution_time:.2f}s. "
                    f"Completed: {completed_count}/{total_count}"
                )
            else:
                self.failed_workflows += 1
                logger.warning(
                    f"Workflow execution completed with failures in {execution_time:.2f}s. "
                    f"Completed: {completed_count}/{total_count}, "
                    f"Failed required: {failed_count}"
                )
            
            return results
    
    async def execute_task(self, task_name: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """Execute a single task.
        
        Args:
            task_name: Name of the task to execute
            context: Optional context data for execution
            
        Returns:
            TaskResult from execution
            
        Raises:
            ValueError: If task not found
        """
        if task_name not in self.tasks:
            raise ValueError(f"Task not found: {task_name}")
        
        task = self.tasks[task_name]
        
        # Update context if provided
        if context:
            self.state.update(context)
        
        # Check dependencies
        completed_tasks = {
            name for name, t in self.tasks.items() 
            if t.status == TaskStatus.COMPLETED
        }
        
        if not task.can_execute(completed_tasks):
            missing_deps = task.dependencies - completed_tasks
            raise TaskDependencyError(
                f"Cannot execute task {task_name}. Missing dependencies: {missing_deps}"
            )
        
        # Execute the task
        result = await self._execute_task_with_recovery(task)
        
        # Store result in workflow state
        if result.status == TaskStatus.COMPLETED and result.data:
            self.state.set(f"task_result_{task_name}", result.data)
        elif result.status == TaskStatus.FAILED:
            self.state.add_error(result.error, task_name)
        
        return result
    
    def reset_workflow(self) -> None:
        """Reset all tasks and workflow state."""
        for task in self.tasks.values():
            task.reset()
        
        # Reset circuit breakers
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.failure_count = 0
            circuit_breaker.state = "closed"
            circuit_breaker.last_failure_time = None
        
        # Clear error recovery history
        self.error_recovery.clear_history()
        
        self.state.reset()
        logger.info("Workflow reset completed")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get the current status of the workflow.
        
        Returns:
            Dictionary containing workflow status information
        """
        task_statuses = {name: task.status.value for name, task in self.tasks.items()}
        
        completed = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        failed = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        running = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)
        pending = sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING)
        
        # Get circuit breaker states
        circuit_breaker_states = {
            name: breaker.get_state() 
            for name, breaker in self.circuit_breakers.items()
        }
        
        return {
            "total_tasks": len(self.tasks),
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "task_statuses": task_statuses,
            "errors": len(self.state.errors),
            "start_time": self.state.start_time,
            "end_time": self.state.end_time,
            "successful_workflows": self.successful_workflows,
            "failed_workflows": self.failed_workflows,
            "circuit_breakers": circuit_breaker_states,
            "recovery_stats": self.error_recovery.get_recovery_statistics()
        }
    
    def configure_error_recovery(self, exception_type: type, recovery_action) -> None:
        """Configure error recovery for a specific exception type.
        
        Args:
            exception_type: Type of exception to handle
            recovery_action: RecoveryAction to take
        """
        self.error_recovery.add_recovery_rule(exception_type, recovery_action)
    
    def get_circuit_breaker_status(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker status for a specific task.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Circuit breaker state or None if task not found
        """
        breaker = self.circuit_breakers.get(task_name)
        return breaker.get_state() if breaker else None