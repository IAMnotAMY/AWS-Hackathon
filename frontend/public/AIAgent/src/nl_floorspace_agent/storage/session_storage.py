"""Session storage for conversation state management."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path

from ..models.core import SessionContext, ConversationState

logger = logging.getLogger(__name__)


class SessionStorage:
    """In-memory session storage with optional file persistence."""
    
    def __init__(self, storage_dir: Optional[str] = None, enable_persistence: bool = False):
        """Initialize session storage.
        
        Args:
            storage_dir: Directory for persistent storage (optional)
            enable_persistence: Whether to enable file-based persistence
        """
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = asyncio.Lock()
        self.enable_persistence = enable_persistence
        
        if enable_persistence and storage_dir:
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.storage_dir = None
    
    async def save_session(self, session_context: SessionContext) -> None:
        """Save a session context.
        
        Args:
            session_context: Session context to save
        """
        async with self._lock:
            session_context.update_activity()
            self._sessions[session_context.session_id] = session_context
            
            if self.enable_persistence and self.storage_dir:
                await self._persist_session(session_context)
            
            logger.debug(f"Saved session: {session_context.session_id}")
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get a session context by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session context if found, None otherwise
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None and self.enable_persistence and self.storage_dir:
                # Try to load from persistent storage
                session = await self._load_session(session_id)
                if session:
                    self._sessions[session_id] = session
            
            if session:
                session.update_activity()
                logger.debug(f"Retrieved session: {session_id}")
            
            return session
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was deleted, False if not found
        """
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            
            if self.enable_persistence and self.storage_dir:
                await self._delete_persisted_session(session_id)
            
            if session:
                logger.debug(f"Deleted session: {session_id}")
                return True
            
            return False
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[SessionContext]:
        """List all sessions, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of session contexts
        """
        async with self._lock:
            sessions = list(self._sessions.values())
            
            if user_id:
                sessions = [s for s in sessions if s.user_id == user_id]
            
            return sessions
    
    async def cleanup_expired_sessions(self, timeout_minutes: int = 30) -> int:
        """Clean up expired sessions.
        
        Args:
            timeout_minutes: Session timeout in minutes
            
        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        expired_sessions = []
        
        async with self._lock:
            for session_id, session in list(self._sessions.items()):
                if session.last_activity < cutoff_time:
                    expired_sessions.append(session_id)
            
            # Remove expired sessions
            for session_id in expired_sessions:
                del self._sessions[session_id]
                
                if self.enable_persistence and self.storage_dir:
                    await self._delete_persisted_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    async def get_session_count(self) -> int:
        """Get the total number of active sessions.
        
        Returns:
            Number of active sessions
        """
        async with self._lock:
            return len(self._sessions)
    
    async def clear_all_sessions(self) -> int:
        """Clear all sessions.
        
        Returns:
            Number of sessions cleared
        """
        async with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            
            if self.enable_persistence and self.storage_dir:
                # Clear persistent storage
                for file_path in self.storage_dir.glob("session_*.json"):
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete session file {file_path}: {e}")
            
            logger.info(f"Cleared {count} sessions")
            return count
    
    async def _persist_session(self, session_context: SessionContext) -> None:
        """Persist a session to file storage.
        
        Args:
            session_context: Session context to persist
        """
        if not self.storage_dir:
            return
        
        try:
            file_path = self.storage_dir / f"session_{session_context.session_id}.json"
            
            # Convert session to serializable format
            session_data = {
                "session_id": session_context.session_id,
                "user_id": session_context.user_id,
                "metadata": session_context.metadata,
                "created_at": session_context.created_at.isoformat(),
                "last_activity": session_context.last_activity.isoformat(),
                "conversation_state": None
            }
            
            if session_context.conversation_state:
                conv_state = session_context.conversation_state
                session_data["conversation_state"] = {
                    "current_step": conv_state.current_step.value,
                    "pending_questions": conv_state.pending_questions,
                    "collected_specs": [
                        {
                            "width": spec.width,
                            "height": spec.height,
                            "wall": spec.wall,
                            "alpha": spec.alpha
                        }
                        for spec in conv_state.collected_specs
                    ],
                    "session_id": conv_state.session_id,
                    "created_at": conv_state.created_at.isoformat(),
                    "last_updated": conv_state.last_updated.isoformat()
                }
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(session_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to persist session {session_context.session_id}: {e}")
    
    async def _load_session(self, session_id: str) -> Optional[SessionContext]:
        """Load a session from file storage.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session context if found, None otherwise
        """
        if not self.storage_dir:
            return None
        
        try:
            file_path = self.storage_dir / f"session_{session_id}.json"
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                session_data = json.load(f)
            
            # Reconstruct session context
            session_context = SessionContext(
                session_id=session_data["session_id"],
                user_id=session_data.get("user_id"),
                metadata=session_data.get("metadata", {}),
                created_at=datetime.fromisoformat(session_data["created_at"]),
                last_activity=datetime.fromisoformat(session_data["last_activity"])
            )
            
            # Reconstruct conversation state if present
            if session_data.get("conversation_state"):
                conv_data = session_data["conversation_state"]
                from ..models.core import ConversationStep, ElementSpec
                
                conversation_state = ConversationState(
                    current_step=ConversationStep(conv_data["current_step"]),
                    pending_questions=conv_data.get("pending_questions", []),
                    collected_specs=[
                        ElementSpec(
                            width=spec.get("width"),
                            height=spec.get("height"),
                            wall=spec.get("wall"),
                            alpha=spec.get("alpha")
                        )
                        for spec in conv_data.get("collected_specs", [])
                    ],
                    session_id=conv_data["session_id"],
                    created_at=datetime.fromisoformat(conv_data["created_at"]),
                    last_updated=datetime.fromisoformat(conv_data["last_updated"])
                )
                
                session_context.conversation_state = conversation_state
            
            return session_context
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    async def _delete_persisted_session(self, session_id: str) -> None:
        """Delete a persisted session file.
        
        Args:
            session_id: Session identifier
        """
        if not self.storage_dir:
            return
        
        try:
            file_path = self.storage_dir / f"session_{session_id}.json"
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.error(f"Failed to delete persisted session {session_id}: {e}")