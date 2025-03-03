"""
Configuration settings for the TMDiscord bot.

This module contains configuration settings and constants used throughout the bot.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
V1SIM_CHANNEL_ID = int(os.getenv('DISCORD_V1SIM_CHANNEL_ID'))

# Bot configuration
BOT_PREFIX = '!'
BOT_DESCRIPTION = 'A Discord bot for playing financial simulation games'
BOT_STATUS = 'Financial Simulator'

# Game configuration
CHARACTERS_DIR = 'characters'
DATABASE_PATH = 'DB/game_data.db'
GAME_TIMEOUT = 300  # Seconds before a game session times out due to inactivity

# Feedback configuration
FEEDBACK_COOLDOWN = 60  # Seconds before a user can submit feedback again
MIN_RATING = 1
MAX_RATING = 5

# UI configuration
EMBED_COLOR = 0x00AAFF  # Light blue color for embeds
ERROR_COLOR = 0xFF5555  # Red color for error embeds
SUCCESS_COLOR = 0x55FF55  # Green color for success embeds
INFO_COLOR = 0xFFAA00  # Orange color for info embeds

# Character validation
REQUIRED_CHARACTER_FIELDS = [
    'name', 'title', 'starting_year', 'initial_capital', 
    'key_principles', 'decisions', 'analysis_templates'
]

REQUIRED_DECISION_FIELDS = [
    'year', 'context', 'question', 'choices', 'correct_choice'
]

# Command cooldowns (in seconds)
COOLDOWNS = {
    'play': 5,
    'stats': 10,
    'leaderboard': 30,
}
