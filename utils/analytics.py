"""
Analytics Utility for TMDiscord Bot

This module provides utility functions for analyzing game data and generating reports.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

import config

# Set up logging
logger = logging.getLogger("discord_bot.analytics")

class Analytics:
    """Class for analyzing game data."""
    
    def __init__(self, database_cog):
        """Initialize the Analytics class.
        
        Args:
            database_cog: The Database cog
        """
        self.database = database_cog
    
    def get_popular_characters(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the most popular characters.
        
        Args:
            limit: Maximum number of characters to return
            
        Returns:
            List of character dictionaries with play count
        """
        try:
            cursor = self.database.connection.cursor()
            cursor.execute(
                """
                SELECT character_id, COUNT(*) as count 
                FROM games 
                GROUP BY character_id 
                ORDER BY count DESC 
                LIMIT ?
                """,
                (limit,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting popular characters: {e}")
            return []
    
    def get_highest_scoring_games(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the highest scoring games.
        
        Args:
            limit: Maximum number of games to return
            
        Returns:
            List of game dictionaries
        """
        try:
            cursor = self.database.connection.cursor()
            cursor.execute(
                """
                SELECT g.game_id, g.character_id, g.total_score, u.username, g.timestamp
                FROM games g
                JOIN users u ON g.user_id = u.user_id
                WHERE g.completed = 1
                ORDER BY g.total_score DESC
                LIMIT ?
                """,
                (limit,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting highest scoring games: {e}")
            return []
    
    def get_recent_games(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent games.
        
        Args:
            limit: Maximum number of games to return
            
        Returns:
            List of game dictionaries
        """
        try:
            cursor = self.database.connection.cursor()
            cursor.execute(
                """
                SELECT g.game_id, g.character_id, g.total_score, u.username, g.timestamp, g.completed
                FROM games g
                JOIN users u ON g.user_id = u.user_id
                ORDER BY g.timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting recent games: {e}")
            return []
    
    def get_active_users(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get the most active users in the last X days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of user dictionaries with game count
        """
        try:
            cursor = self.database.connection.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute(
                """
                SELECT u.user_id, u.username, COUNT(*) as game_count
                FROM games g
                JOIN users u ON g.user_id = u.user_id
                WHERE g.timestamp > ?
                GROUP BY u.user_id
                ORDER BY game_count DESC
                """,
                (cutoff_date,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def get_average_score_by_character(self) -> List[Dict[str, Any]]:
        """Get the average score for each character.
        
        Returns:
            List of character dictionaries with average score
        """
        try:
            cursor = self.database.connection.cursor()
            cursor.execute(
                """
                SELECT character_id, AVG(total_score) as avg_score, COUNT(*) as play_count
                FROM games
                WHERE completed = 1
                GROUP BY character_id
                ORDER BY avg_score DESC
                """
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting average score by character: {e}")
            return []
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics.
        
        Returns:
            Dictionary with feedback statistics
        """
        try:
            cursor = self.database.connection.cursor()
            
            # Get average rating
            cursor.execute(
                """
                SELECT AVG(rating) as avg_rating, COUNT(*) as count
                FROM feedback
                """
            )
            rating_stats = cursor.fetchone()
            
            # Get rating distribution
            cursor.execute(
                """
                SELECT rating, COUNT(*) as count
                FROM feedback
                GROUP BY rating
                ORDER BY rating
                """
            )
            rating_distribution = cursor.fetchall()
            
            # Get recent feedback
            cursor.execute(
                """
                SELECT f.rating, f.comments, g.character_id, u.username, f.timestamp
                FROM feedback f
                JOIN games g ON f.game_id = g.game_id
                JOIN users u ON g.user_id = u.user_id
                ORDER BY f.timestamp DESC
                LIMIT 5
                """
            )
            recent_feedback = cursor.fetchall()
            
            return {
                'avg_rating': rating_stats['avg_rating'] if rating_stats and rating_stats['avg_rating'] else 0,
                'count': rating_stats['count'] if rating_stats else 0,
                'distribution': rating_distribution,
                'recent': recent_feedback
            }
        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return {
                'avg_rating': 0,
                'count': 0,
                'distribution': [],
                'recent': []
            }
    
    def get_decision_stats(self, character_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get statistics on decisions made.
        
        Args:
            character_id: Optional character ID to filter by
            
        Returns:
            List of decision statistics
        """
        try:
            cursor = self.database.connection.cursor()
            
            if character_id:
                # Get decision stats for a specific character
                cursor.execute(
                    """
                    SELECT d.decision_number, d.choice_made, COUNT(*) as count
                    FROM decisions d
                    JOIN games g ON d.game_id = g.game_id
                    WHERE g.character_id = ?
                    GROUP BY d.decision_number, d.choice_made
                    ORDER BY d.decision_number, count DESC
                    """,
                    (character_id,)
                )
            else:
                # Get overall decision stats
                cursor.execute(
                    """
                    SELECT g.character_id, d.decision_number, d.choice_made, COUNT(*) as count
                    FROM decisions d
                    JOIN games g ON d.game_id = g.game_id
                    GROUP BY g.character_id, d.decision_number, d.choice_made
                    ORDER BY g.character_id, d.decision_number, count DESC
                    """
                )
            
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting decision stats: {e}")
            return []
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a summary report of all game data.
        
        Returns:
            Dictionary with summary statistics
        """
        try:
            cursor = self.database.connection.cursor()
            
            # Get total users
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']
            
            # Get total games
            cursor.execute("SELECT COUNT(*) as count FROM games")
            total_games = cursor.fetchone()['count']
            
            # Get completed games
            cursor.execute("SELECT COUNT(*) as count FROM games WHERE completed = 1")
            completed_games = cursor.fetchone()['count']
            
            # Get average score
            cursor.execute("SELECT AVG(total_score) as avg_score FROM games WHERE completed = 1")
            avg_score = cursor.fetchone()['avg_score']
            
            # Get popular characters
            popular_characters = self.get_popular_characters(3)
            
            # Get highest scoring games
            highest_scoring = self.get_highest_scoring_games(3)
            
            # Get feedback stats
            feedback = self.get_feedback_stats()
            
            return {
                'total_users': total_users,
                'total_games': total_games,
                'completed_games': completed_games,
                'completion_rate': (completed_games / total_games * 100) if total_games > 0 else 0,
                'avg_score': avg_score or 0,
                'popular_characters': popular_characters,
                'highest_scoring': highest_scoring,
                'feedback': feedback
            }
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
            return {
                'total_users': 0,
                'total_games': 0,
                'completed_games': 0,
                'completion_rate': 0,
                'avg_score': 0,
                'popular_characters': [],
                'highest_scoring': [],
                'feedback': {
                    'avg_rating': 0,
                    'count': 0,
                    'distribution': [],
                    'recent': []
                }
            }
