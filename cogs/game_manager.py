"""
Game Manager Cog for TMDiscord Bot

This cog handles the game session management and game logic, including:
- Creating and managing game sessions
- Processing player decisions
- Calculating scores
- Generating game analysis
"""

import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union

import discord
from discord.ext import commands, tasks

import config
from cogs.character_loader import Character

# Set up logging
logger = logging.getLogger("discord_bot.game_manager")

class GameSession:
    """Class representing an active game session."""
    
    def __init__(self, user_id: int, character: Character, game_id: int, channel_id: int):
        """Initialize a GameSession object.
        
        Args:
            user_id: The Discord user ID
            character: The Character object
            game_id: The database game ID
            channel_id: The Discord channel ID
        """
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.character = character
        self.game_id = game_id
        self.channel_id = channel_id
        self.current_decision = 1
        self.total_score = 0
        self.decisions_made: Dict[int, str] = {}  # Decision number -> choice
        self.last_activity = datetime.now()
        self.message_id: Optional[int] = None  # ID of the last decision message
    
    def make_decision(self, decision_number: int, choice: str) -> int:
        """Record a decision made by the player.
        
        Args:
            decision_number: The decision number (1-based)
            choice: The choice made (e.g., 'a', 'b', 'c')
            
        Returns:
            The score for this decision
        """
        # Validate decision number
        if decision_number != self.current_decision:
            logger.warning(f"Invalid decision number: {decision_number}, expected {self.current_decision}")
            return 0
        
        # Get score for this choice
        score = self.character.get_choice_score(decision_number, choice)
        
        # Record decision
        self.decisions_made[decision_number] = choice
        self.total_score += score
        
        # Move to next decision
        self.current_decision += 1
        
        # Update last activity
        self.last_activity = datetime.now()
        
        return score
    
    def is_completed(self) -> bool:
        """Check if the game is completed.
        
        Returns:
            True if all decisions have been made, False otherwise
        """
        return self.current_decision > self.character.get_total_decisions()
    
    def get_max_possible_score(self) -> int:
        """Calculate the maximum possible score for this character.
        
        Returns:
            The maximum possible score
        """
        max_score = 0
        for i in range(1, self.character.get_total_decisions() + 1):
            decision = self.character.get_decision(i)
            if decision and 'choices' in decision:
                # Find the highest scoring choice
                highest_score = 0
                for choice_id, choice_data in decision['choices'].items():
                    if 'score' in choice_data and choice_data['score'] > highest_score:
                        highest_score = choice_data['score']
                max_score += highest_score
        return max_score
    
    def get_score_percentage(self) -> float:
        """Calculate the score percentage.
        
        Returns:
            The score percentage (0-100)
        """
        max_score = self.get_max_possible_score()
        if max_score == 0:
            return 0
        return (self.total_score / max_score) * 100
    
    def get_analysis(self) -> Dict[str, Any]:
        """Generate an analysis of the player's performance.
        
        Returns:
            Analysis data dictionary
        """
        score_percentage = self.get_score_percentage()
        analysis_template = self.character.get_analysis(score_percentage)
        
        # Count correct decisions
        correct_decisions = 0
        for decision_num, choice in self.decisions_made.items():
            if self.character.is_correct_choice(decision_num, choice):
                correct_decisions += 1
        
        # Calculate accuracy
        total_decisions = self.character.get_total_decisions()
        accuracy = (correct_decisions / total_decisions) * 100 if total_decisions > 0 else 0
        
        return {
            'text': analysis_template.get('text', ''),
            'principles': analysis_template.get('principles', []),
            'score': self.total_score,
            'max_score': self.get_max_possible_score(),
            'percentage': score_percentage,
            'correct_decisions': correct_decisions,
            'total_decisions': total_decisions,
            'accuracy': accuracy
        }
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()

class GameManager(commands.Cog):
    """Cog for managing game sessions and game logic."""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the GameManager cog.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.active_sessions: Dict[str, GameSession] = {}
        self.user_sessions: Dict[int, str] = {}  # user_id -> session_id
        
        # Start background task to clean up old sessions
        self.cleanup_old_sessions.start()
    
    async def get_database_cog(self):
        """Get the Database cog.
        
        Returns:
            The Database cog
        """
        return self.bot.get_cog('Database')
    
    async def get_character_loader_cog(self):
        """Get the CharacterLoader cog.
        
        Returns:
            The CharacterLoader cog
        """
        return self.bot.get_cog('CharacterLoader')
    
    async def create_game_session(self, user_id: int, character_id: str, channel_id: int) -> Optional[GameSession]:
        """Create a new game session.
        
        Args:
            user_id: The Discord user ID
            character_id: The character ID
            channel_id: The Discord channel ID
            
        Returns:
            The GameSession object or None if creation failed
        """
        # Get character loader cog
        character_loader = await self.get_character_loader_cog()
        if not character_loader:
            logger.error("CharacterLoader cog not found")
            return None
        
        # Get character
        character = character_loader.get_character(character_id)
        if not character:
            logger.error(f"Character not found: {character_id}")
            return None
        
        # Get database cog
        database = await self.get_database_cog()
        if not database:
            logger.error("Database cog not found")
            return None
        
        # Get or create user
        user = self.bot.get_user(user_id)
        username = user.name if user else "Unknown"
        database.get_or_create_user(user_id, username)
        
        # Create game in database
        game_id = database.create_game(user_id, character_id)
        
        # Create game session
        session = GameSession(user_id, character, game_id, channel_id)
        
        # Store session
        self.active_sessions[session.id] = session
        
        # If user already has a session, end it
        if user_id in self.user_sessions:
            old_session_id = self.user_sessions[user_id]
            if old_session_id in self.active_sessions:
                await self.end_game_session(old_session_id, completed=False)
        
        # Associate user with session
        self.user_sessions[user_id] = session.id
        
        # Create session in database
        database.create_session(session.id, user_id, game_id, channel_id)
        
        logger.info(f"Created game session: {session.id} for user {user_id} with character {character_id}")
        
        return session
    
    async def get_user_session(self, user_id: int) -> Optional[GameSession]:
        """Get the active game session for a user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            The GameSession object or None if not found
        """
        if user_id not in self.user_sessions:
            return None
        
        session_id = self.user_sessions[user_id]
        if session_id not in self.active_sessions:
            # Session ID exists but session doesn't - clean up
            del self.user_sessions[user_id]
            return None
        
        return self.active_sessions[session_id]
    
    async def make_decision(self, session_id: str, choice: str) -> Tuple[int, bool]:
        """Process a decision made by the player.
        
        Args:
            session_id: The session ID
            choice: The choice made (e.g., 'a', 'b', 'c')
            
        Returns:
            Tuple of (score, is_completed)
        """
        if session_id not in self.active_sessions:
            logger.error(f"Session not found: {session_id}")
            return (0, False)
        
        session = self.active_sessions[session_id]
        
        # Get database cog
        database = await self.get_database_cog()
        if not database:
            logger.error("Database cog not found")
            return (0, False)
        
        # Make decision
        score = session.make_decision(session.current_decision - 1, choice)
        
        # Record decision in database
        database.record_decision(
            session.game_id, 
            session.current_decision - 1, 
            choice, 
            score
        )
        
        # Update session activity
        database.update_session_activity(session_id)
        
        # Check if game is completed
        is_completed = session.is_completed()
        if is_completed:
            # Complete game in database
            database.complete_game(session.game_id)
        
        return (score, is_completed)
    
    async def end_game_session(self, session_id: str, completed: bool = True) -> None:
        """End a game session.
        
        Args:
            session_id: The session ID
            completed: Whether the game was completed normally
        """
        if session_id not in self.active_sessions:
            logger.error(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        
        # Get database cog
        database = await self.get_database_cog()
        if not database:
            logger.error("Database cog not found")
            return
        
        # If game was completed, mark as completed in database
        if completed and not session.is_completed():
            database.complete_game(session.game_id)
        
        # Remove session from database
        database.end_session(session_id)
        
        # Remove user association
        if session.user_id in self.user_sessions and self.user_sessions[session.user_id] == session_id:
            del self.user_sessions[session.user_id]
        
        # Remove session
        del self.active_sessions[session_id]
        
        logger.info(f"Ended game session: {session_id} for user {session.user_id}")
    
    async def record_feedback(self, session_id: str, rating: int, comments: Optional[str] = None) -> bool:
        """Record feedback for a game.
        
        Args:
            session_id: The session ID
            rating: The rating (1-5)
            comments: Optional comments
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.active_sessions:
            logger.error(f"Session not found: {session_id}")
            return False
        
        session = self.active_sessions[session_id]
        
        # Get database cog
        database = await self.get_database_cog()
        if not database:
            logger.error("Database cog not found")
            return False
        
        # Record feedback
        database.record_feedback(session.game_id, rating, comments)
        
        logger.info(f"Recorded feedback for session {session_id}: rating {rating}")
        
        return True
    
    @tasks.loop(minutes=1.0)
    async def cleanup_old_sessions(self) -> None:
        """Background task to clean up inactive game sessions."""
        try:
            # Get current time
            now = datetime.now()
            
            # Find sessions that have been inactive for too long
            sessions_to_remove = []
            for session_id, session in self.active_sessions.items():
                time_diff = (now - session.last_activity).total_seconds()
                if time_diff > config.GAME_TIMEOUT:
                    sessions_to_remove.append(session_id)
            
            # End each inactive session
            for session_id in sessions_to_remove:
                logger.info(f"Cleaning up inactive session: {session_id}")
                await self.end_game_session(session_id, completed=False)
                
                # Try to notify the user if possible
                if session_id in self.active_sessions:  # Double-check it still exists
                    session = self.active_sessions[session_id]
                    user = self.bot.get_user(session.user_id)
                    if user:
                        try:
                            await user.send("Your game session has expired due to inactivity. You can start a new game anytime!")
                        except discord.errors.Forbidden:
                            # Can't send DM to this user
                            pass
        
        except Exception as e:
            logger.error(f"Error in cleanup_old_sessions task: {e}")
    
    @cleanup_old_sessions.before_loop
    async def before_cleanup(self) -> None:
        """Wait until the bot is ready before starting the cleanup task."""
        await self.bot.wait_until_ready()
    
    def cog_unload(self) -> None:
        """Clean up when the cog is unloaded."""
        # Stop the background task
        self.cleanup_old_sessions.cancel()

async def setup(bot: commands.Bot) -> None:
    """Set up the GameManager cog."""
    await bot.add_cog(GameManager(bot))
