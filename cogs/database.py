"""
Database Cog for TMDiscord Bot

This cog handles all database operations for the bot, including:
- Creating and initializing the database
- User data management
- Game session tracking
- Decision recording
- Feedback storage
"""

import os
import sqlite3
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union

import discord
from discord.ext import commands, tasks

import config

# Set up logging
logger = logging.getLogger("discord_bot.database")

class Database(commands.Cog):
    """Cog for handling database operations."""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the Database cog.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.db_path = config.DATABASE_PATH
        self.connection = None
        self.cursor = None
        
        # Create database if it doesn't exist
        self._init_database()
        
        # Start background task to clean up old sessions
        self.cleanup_old_sessions.start()
    
    def _init_database(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        logger.info(f"Initializing database at {self.db_path}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Connect to database
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.connection.cursor()
        
        # Create tables
        self._create_tables()
        
        logger.info("Database initialized successfully")
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        # Users table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            games_played INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            last_played TIMESTAMP
        )
        ''')
        
        # Games table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            character_id TEXT NOT NULL,
            total_score INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Decisions table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS decisions (
            decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            decision_number INTEGER NOT NULL,
            choice_made TEXT NOT NULL,
            score INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (game_id)
        )
        ''')
        
        # Feedback table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comments TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (game_id)
        )
        ''')
        
        # Active sessions table (for tracking ongoing games)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (game_id) REFERENCES games (game_id)
        )
        ''')
        
        # Commit changes
        self.connection.commit()
    
    def _get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a user from the database.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            User data dictionary or None if not found
        """
        self.cursor.execute(
            "SELECT * FROM users WHERE user_id = ?", 
            (user_id,)
        )
        return self.cursor.fetchone()
    
    def _create_user(self, user_id: int, username: str) -> None:
        """Create a new user in the database.
        
        Args:
            user_id: The Discord user ID
            username: The Discord username
        """
        self.cursor.execute(
            "INSERT INTO users (user_id, username, last_played) VALUES (?, ?, ?)",
            (user_id, username, datetime.now())
        )
        self.connection.commit()
        logger.info(f"Created new user: {username} ({user_id})")
    
    def get_or_create_user(self, user_id: int, username: str) -> Dict[str, Any]:
        """Get a user from the database or create if not exists.
        
        Args:
            user_id: The Discord user ID
            username: The Discord username
            
        Returns:
            User data dictionary
        """
        user = self._get_user(user_id)
        if not user:
            self._create_user(user_id, username)
            user = self._get_user(user_id)
        return user
    
    def create_game(self, user_id: int, character_id: str) -> int:
        """Create a new game session.
        
        Args:
            user_id: The Discord user ID
            character_id: The character ID (filename without extension)
            
        Returns:
            The game ID
        """
        # Update user's last_played timestamp
        self.cursor.execute(
            "UPDATE users SET last_played = ? WHERE user_id = ?",
            (datetime.now(), user_id)
        )
        
        # Create new game
        self.cursor.execute(
            "INSERT INTO games (user_id, character_id, timestamp) VALUES (?, ?, ?)",
            (user_id, character_id, datetime.now())
        )
        
        # Get the game ID
        game_id = self.cursor.lastrowid
        
        # Increment games_played counter
        self.cursor.execute(
            "UPDATE users SET games_played = games_played + 1 WHERE user_id = ?",
            (user_id,)
        )
        
        self.connection.commit()
        logger.info(f"Created new game: {game_id} for user {user_id} with character {character_id}")
        
        return game_id
    
    def create_session(self, session_id: str, user_id: int, game_id: int, channel_id: int) -> None:
        """Create a new active game session.
        
        Args:
            session_id: Unique session identifier
            user_id: The Discord user ID
            game_id: The game ID
            channel_id: The Discord channel ID
        """
        # First, check if user already has an active session
        self.cursor.execute(
            "SELECT * FROM active_sessions WHERE user_id = ?",
            (user_id,)
        )
        existing_session = self.cursor.fetchone()
        
        if existing_session:
            # Delete the existing session
            self.cursor.execute(
                "DELETE FROM active_sessions WHERE user_id = ?",
                (user_id,)
            )
        
        # Create new session
        self.cursor.execute(
            "INSERT INTO active_sessions (session_id, user_id, game_id, channel_id, last_activity) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, game_id, channel_id, datetime.now())
        )
        
        self.connection.commit()
        logger.info(f"Created new session: {session_id} for user {user_id}, game {game_id}")
    
    def update_session_activity(self, session_id: str) -> None:
        """Update the last activity timestamp for a session.
        
        Args:
            session_id: The session ID
        """
        self.cursor.execute(
            "UPDATE active_sessions SET last_activity = ? WHERE session_id = ?",
            (datetime.now(), session_id)
        )
        self.connection.commit()
    
    def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the active session for a user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            Session data dictionary or None if not found
        """
        self.cursor.execute(
            "SELECT * FROM active_sessions WHERE user_id = ?",
            (user_id,)
        )
        return self.cursor.fetchone()
    
    def end_session(self, session_id: str) -> None:
        """End an active game session.
        
        Args:
            session_id: The session ID
        """
        self.cursor.execute(
            "DELETE FROM active_sessions WHERE session_id = ?",
            (session_id,)
        )
        self.connection.commit()
        logger.info(f"Ended session: {session_id}")
    
    def record_decision(self, game_id: int, decision_number: int, choice: str, score: int) -> None:
        """Record a decision made in a game.
        
        Args:
            game_id: The game ID
            decision_number: The decision number (1-based)
            choice: The choice made (e.g., 'a', 'b', 'c')
            score: The score for this decision
        """
        self.cursor.execute(
            "INSERT INTO decisions (game_id, decision_number, choice_made, score, timestamp) VALUES (?, ?, ?, ?, ?)",
            (game_id, decision_number, choice, score, datetime.now())
        )
        
        # Update total score in games table
        self.cursor.execute(
            "UPDATE games SET total_score = total_score + ? WHERE game_id = ?",
            (score, game_id)
        )
        
        self.connection.commit()
        logger.info(f"Recorded decision {decision_number} for game {game_id}: choice {choice}, score {score}")
    
    def complete_game(self, game_id: int) -> int:
        """Mark a game as completed and update user's total score.
        
        Args:
            game_id: The game ID
            
        Returns:
            The final total score
        """
        # Get the game's total score
        self.cursor.execute(
            "SELECT total_score, user_id FROM games WHERE game_id = ?",
            (game_id,)
        )
        game = self.cursor.fetchone()
        total_score = game['total_score']
        user_id = game['user_id']
        
        # Mark game as completed
        self.cursor.execute(
            "UPDATE games SET completed = 1 WHERE game_id = ?",
            (game_id,)
        )
        
        # Update user's total score
        self.cursor.execute(
            "UPDATE users SET total_score = total_score + ? WHERE user_id = ?",
            (total_score, user_id)
        )
        
        self.connection.commit()
        logger.info(f"Completed game {game_id} with total score {total_score}")
        
        return total_score
    
    def record_feedback(self, game_id: int, rating: int, comments: Optional[str] = None) -> None:
        """Record feedback for a game.
        
        Args:
            game_id: The game ID
            rating: The rating (1-5)
            comments: Optional comments
        """
        self.cursor.execute(
            "INSERT INTO feedback (game_id, rating, comments, timestamp) VALUES (?, ?, ?, ?)",
            (game_id, rating, comments, datetime.now())
        )
        self.connection.commit()
        logger.info(f"Recorded feedback for game {game_id}: rating {rating}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            Dictionary with user statistics
        """
        # Get user data
        user = self.get_or_create_user(user_id, "Unknown")  # Fallback username
        
        # Get top score
        self.cursor.execute(
            "SELECT MAX(total_score) as top_score FROM games WHERE user_id = ? AND completed = 1",
            (user_id,)
        )
        top_score_result = self.cursor.fetchone()
        top_score = top_score_result['top_score'] if top_score_result and top_score_result['top_score'] else 0
        
        # Get favorite character
        self.cursor.execute(
            """
            SELECT character_id, COUNT(*) as count 
            FROM games 
            WHERE user_id = ? 
            GROUP BY character_id 
            ORDER BY count DESC 
            LIMIT 1
            """,
            (user_id,)
        )
        favorite_character_result = self.cursor.fetchone()
        favorite_character = favorite_character_result['character_id'] if favorite_character_result else "None"
        
        # Get average score
        self.cursor.execute(
            "SELECT AVG(total_score) as avg_score FROM games WHERE user_id = ? AND completed = 1",
            (user_id,)
        )
        avg_score_result = self.cursor.fetchone()
        avg_score = round(avg_score_result['avg_score']) if avg_score_result and avg_score_result['avg_score'] else 0
        
        # Get recent games
        self.cursor.execute(
            """
            SELECT game_id, character_id, total_score, timestamp 
            FROM games 
            WHERE user_id = ? AND completed = 1
            ORDER BY timestamp DESC 
            LIMIT 5
            """,
            (user_id,)
        )
        recent_games = self.cursor.fetchall()
        
        return {
            'user_id': user_id,
            'username': user['username'],
            'games_played': user['games_played'],
            'total_score': user['total_score'],
            'top_score': top_score,
            'avg_score': avg_score,
            'favorite_character': favorite_character,
            'recent_games': recent_games,
            'last_played': user['last_played']
        }
    
    def get_leaderboard(self, limit: int = 10, character_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get the leaderboard of top players.
        
        Args:
            limit: Maximum number of entries to return
            character_id: Optional character ID to filter by
            
        Returns:
            List of leaderboard entries
        """
        if character_id:
            # Get leaderboard for specific character
            self.cursor.execute(
                """
                SELECT g.user_id, u.username, MAX(g.total_score) as high_score 
                FROM games g
                JOIN users u ON g.user_id = u.user_id
                WHERE g.character_id = ? AND g.completed = 1
                GROUP BY g.user_id
                ORDER BY high_score DESC
                LIMIT ?
                """,
                (character_id, limit)
            )
        else:
            # Get overall leaderboard
            self.cursor.execute(
                """
                SELECT g.user_id, u.username, MAX(g.total_score) as high_score 
                FROM games g
                JOIN users u ON g.user_id = u.user_id
                WHERE g.completed = 1
                GROUP BY g.user_id
                ORDER BY high_score DESC
                LIMIT ?
                """,
                (limit,)
            )
        
        return self.cursor.fetchall()
    
    def get_game_decisions(self, game_id: int) -> List[Dict[str, Any]]:
        """Get all decisions made in a game.
        
        Args:
            game_id: The game ID
            
        Returns:
            List of decision dictionaries
        """
        self.cursor.execute(
            """
            SELECT decision_number, choice_made, score 
            FROM decisions 
            WHERE game_id = ? 
            ORDER BY decision_number
            """,
            (game_id,)
        )
        return self.cursor.fetchall()
    
    @tasks.loop(minutes=5.0)
    async def cleanup_old_sessions(self) -> None:
        """Background task to clean up inactive game sessions."""
        try:
            # Get current time
            now = datetime.now()
            
            # Find sessions that have been inactive for too long
            self.cursor.execute(
                "SELECT session_id, user_id, game_id FROM active_sessions WHERE strftime('%s', ?) - strftime('%s', last_activity) > ?",
                (now, config.GAME_TIMEOUT)
            )
            old_sessions = self.cursor.fetchall()
            
            for session in old_sessions:
                logger.info(f"Cleaning up inactive session: {session['session_id']} for user {session['user_id']}")
                
                # End the session
                self.end_session(session['session_id'])
                
                # Try to notify the user if possible
                user = self.bot.get_user(session['user_id'])
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
        
        # Close the database connection
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

async def setup(bot: commands.Bot) -> None:
    """Set up the Database cog."""
    await bot.add_cog(Database(bot))
