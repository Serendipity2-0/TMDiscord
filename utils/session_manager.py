"""
Session Manager Utility for TMDiscord Bot

This module provides utility functions for managing game sessions.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

import discord

import config

# Set up logging
logger = logging.getLogger("discord_bot.session_manager")

class SessionManager:
    """Class for managing game sessions."""
    
    def __init__(self):
        """Initialize the SessionManager."""
        self.active_sessions: Dict[str, Any] = {}
        self.user_sessions: Dict[int, str] = {}  # user_id -> session_id
    
    def create_session(self, user_id: int, data: Any) -> str:
        """Create a new session.
        
        Args:
            user_id: The Discord user ID
            data: The session data
            
        Returns:
            The session ID
        """
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Create session with timestamp
        session = {
            'id': session_id,
            'user_id': user_id,
            'data': data,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        
        # Store session
        self.active_sessions[session_id] = session
        
        # If user already has a session, end it
        if user_id in self.user_sessions:
            old_session_id = self.user_sessions[user_id]
            if old_session_id in self.active_sessions:
                self.end_session(old_session_id)
        
        # Associate user with session
        self.user_sessions[user_id] = session_id
        
        logger.info(f"Created session: {session_id} for user {user_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            The session data or None if not found
        """
        return self.active_sessions.get(session_id)
    
    def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the active session for a user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            The session data or None if not found
        """
        if user_id not in self.user_sessions:
            return None
        
        session_id = self.user_sessions[user_id]
        if session_id not in self.active_sessions:
            # Session ID exists but session doesn't - clean up
            del self.user_sessions[user_id]
            return None
        
        return self.active_sessions[session_id]
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update the last activity timestamp for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.active_sessions:
            return False
        
        self.active_sessions[session_id]['last_activity'] = datetime.now()
        return True
    
    def update_session_data(self, session_id: str, data: Any) -> bool:
        """Update the data for a session.
        
        Args:
            session_id: The session ID
            data: The new session data
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.active_sessions:
            return False
        
        self.active_sessions[session_id]['data'] = data
        self.update_session_activity(session_id)
        return True
    
    def end_session(self, session_id: str) -> bool:
        """End a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Remove user association
        if session['user_id'] in self.user_sessions and self.user_sessions[session['user_id']] == session_id:
            del self.user_sessions[session['user_id']]
        
        # Remove session
        del self.active_sessions[session_id]
        
        logger.info(f"Ended session: {session_id}")
        
        return True
    
    def get_inactive_sessions(self, timeout: int = None) -> List[str]:
        """Get a list of inactive session IDs.
        
        Args:
            timeout: Optional timeout in seconds (defaults to config.GAME_TIMEOUT)
            
        Returns:
            List of inactive session IDs
        """
        if timeout is None:
            timeout = config.GAME_TIMEOUT
        
        now = datetime.now()
        inactive_sessions = []
        
        for session_id, session in self.active_sessions.items():
            time_diff = (now - session['last_activity']).total_seconds()
            if time_diff > timeout:
                inactive_sessions.append(session_id)
        
        return inactive_sessions
    
    def cleanup_inactive_sessions(self, timeout: int = None) -> int:
        """Clean up inactive sessions.
        
        Args:
            timeout: Optional timeout in seconds (defaults to config.GAME_TIMEOUT)
            
        Returns:
            Number of sessions cleaned up
        """
        inactive_sessions = self.get_inactive_sessions(timeout)
        
        for session_id in inactive_sessions:
            self.end_session(session_id)
        
        return len(inactive_sessions)
    
    def get_session_count(self) -> int:
        """Get the number of active sessions.
        
        Returns:
            Number of active sessions
        """
        return len(self.active_sessions)
