"""
Character Loader Cog for TMDiscord Bot

This cog handles loading and managing character data from YAML files.
It provides functionality to:
- Load all characters from the characters directory
- Validate character data structure
- Provide character information to other cogs
"""

import os
import logging
import yaml
from typing import Dict, List, Optional, Any, Union

import discord
from discord.ext import commands

import config

# Set up logging
logger = logging.getLogger("discord_bot.character_loader")

class Character:
    """Class representing a character from a YAML file."""
    
    def __init__(self, character_id: str, data: Dict[str, Any]):
        """Initialize a Character object.
        
        Args:
            character_id: The character ID (filename without extension)
            data: The character data from the YAML file
        """
        self.id = character_id
        self.name = data.get('name', 'Unknown')
        self.title = data.get('title', '')
        self.starting_year = data.get('starting_year', 0)
        self.initial_capital = data.get('initial_capital', 0)
        self.key_principles = data.get('key_principles', [])
        self.decisions = data.get('decisions', {})
        self.analysis_templates = data.get('analysis_templates', {})
        
        # Sort decisions by key (which should be numeric)
        self.sorted_decisions = sorted(
            self.decisions.items(), 
            key=lambda x: int(x[0]) if isinstance(x[0], (int, str)) and str(x[0]).isdigit() else 0
        )
    
    def get_decision(self, number: int) -> Optional[Dict[str, Any]]:
        """Get a specific decision by number.
        
        Args:
            number: The decision number (1-based)
            
        Returns:
            The decision data or None if not found
        """
        if number <= 0 or number > len(self.sorted_decisions):
            return None
        
        # Decisions are 1-indexed in the list
        return self.sorted_decisions[number - 1][1]
    
    def get_total_decisions(self) -> int:
        """Get the total number of decisions for this character.
        
        Returns:
            The total number of decisions
        """
        return len(self.sorted_decisions)
    
    def get_choice_score(self, decision_number: int, choice: str) -> int:
        """Get the score for a specific choice in a decision.
        
        Args:
            decision_number: The decision number (1-based)
            choice: The choice identifier (e.g., 'a', 'b', 'c')
            
        Returns:
            The score for the choice or 0 if not found
        """
        decision = self.get_decision(decision_number)
        if not decision or 'choices' not in decision:
            return 0
        
        choices = decision.get('choices', {})
        if choice in choices and 'score' in choices[choice]:
            return choices[choice]['score']
        
        return 0
    
    def is_correct_choice(self, decision_number: int, choice: str) -> bool:
        """Check if a choice is the historically correct one.
        
        Args:
            decision_number: The decision number (1-based)
            choice: The choice identifier (e.g., 'a', 'b', 'c')
            
        Returns:
            True if the choice is correct, False otherwise
        """
        decision = self.get_decision(decision_number)
        if not decision or 'correct_choice' not in decision:
            return False
        
        return decision['correct_choice'] == choice
    
    def get_analysis(self, score_percentage: float) -> Dict[str, Any]:
        """Get the appropriate analysis template based on score percentage.
        
        Args:
            score_percentage: The score percentage (0-100)
            
        Returns:
            The analysis template data
        """
        if score_percentage >= 80:
            return self.analysis_templates.get('excellent', {'text': 'Excellent performance!', 'principles': []})
        elif score_percentage >= 60:
            return self.analysis_templates.get('good', {'text': 'Good performance!', 'principles': []})
        else:
            return self.analysis_templates.get('needs_improvement', {'text': 'Needs improvement.', 'principles': []})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the character to a dictionary.
        
        Returns:
            Dictionary representation of the character
        """
        return {
            'id': self.id,
            'name': self.name,
            'title': self.title,
            'starting_year': self.starting_year,
            'initial_capital': self.initial_capital,
            'key_principles': self.key_principles,
            'total_decisions': self.get_total_decisions()
        }
    
    def __str__(self) -> str:
        """String representation of the character.
        
        Returns:
            String representation
        """
        return f"{self.name} ({self.title})"

class CharacterLoader(commands.Cog):
    """Cog for loading and managing character data."""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the CharacterLoader cog.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.characters: Dict[str, Character] = {}
        self.characters_dir = config.CHARACTERS_DIR
        
        # Load all characters
        self._load_all_characters()
    
    def _load_all_characters(self) -> None:
        """Load all character YAML files from the characters directory."""
        logger.info(f"Loading characters from {self.characters_dir}")
        
        # Clear existing characters
        self.characters = {}
        
        # Get all YAML files in the characters directory
        try:
            files = [f for f in os.listdir(self.characters_dir) if f.endswith('.yml') or f.endswith('.yaml')]
        except FileNotFoundError:
            logger.error(f"Characters directory not found: {self.characters_dir}")
            return
        
        # Load each file
        for filename in files:
            character_id = os.path.splitext(filename)[0]
            filepath = os.path.join(self.characters_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                
                # Validate character data
                if self._validate_character(character_id, data):
                    # Create Character object
                    character = Character(character_id, data)
                    self.characters[character_id] = character
                    logger.info(f"Loaded character: {character.name} ({character_id})")
            except Exception as e:
                logger.error(f"Error loading character {character_id}: {e}")
        
        logger.info(f"Loaded {len(self.characters)} characters")
    
    def _validate_character(self, character_id: str, data: Dict[str, Any]) -> bool:
        """Validate character data structure.
        
        Args:
            character_id: The character ID (filename without extension)
            data: The character data from the YAML file
            
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        for field in config.REQUIRED_CHARACTER_FIELDS:
            if field not in data:
                logger.error(f"Character {character_id} missing required field: {field}")
                return False
        
        # Check decisions structure
        decisions = data.get('decisions', {})
        if not decisions:
            logger.error(f"Character {character_id} has no decisions")
            return False
        
        for decision_id, decision in decisions.items():
            for field in config.REQUIRED_DECISION_FIELDS:
                if field not in decision:
                    logger.error(f"Character {character_id}, decision {decision_id} missing required field: {field}")
                    return False
            
            # Check choices structure
            choices = decision.get('choices', {})
            if not choices:
                logger.error(f"Character {character_id}, decision {decision_id} has no choices")
                return False
            
            # Check correct_choice is valid
            correct_choice = decision.get('correct_choice')
            if correct_choice not in choices:
                logger.error(f"Character {character_id}, decision {decision_id} has invalid correct_choice: {correct_choice}")
                return False
        
        # Check analysis templates
        analysis_templates = data.get('analysis_templates', {})
        if not analysis_templates:
            logger.warning(f"Character {character_id} has no analysis templates")
        
        return True
    
    def get_character(self, character_id: str) -> Optional[Character]:
        """Get a character by ID.
        
        Args:
            character_id: The character ID (filename without extension)
            
        Returns:
            The Character object or None if not found
        """
        return self.characters.get(character_id)
    
    def get_all_characters(self) -> Dict[str, Character]:
        """Get all loaded characters.
        
        Returns:
            Dictionary of character ID to Character object
        """
        return self.characters
    
    def get_character_list(self) -> List[Dict[str, Any]]:
        """Get a list of all characters with basic information.
        
        Returns:
            List of character dictionaries
        """
        return [character.to_dict() for character in self.characters.values()]
    
    def reload_characters(self) -> int:
        """Reload all character data from files.
        
        Returns:
            The number of characters loaded
        """
        self._load_all_characters()
        return len(self.characters)
    
    @commands.command(name="reload_characters")
    @commands.is_owner()
    async def reload_characters_command(self, ctx: commands.Context) -> None:
        """Command to reload all character data (owner only).
        
        Args:
            ctx: The command context
        """
        count = self.reload_characters()
        await ctx.send(f"Reloaded {count} characters.")
    
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Event triggered when the bot is ready."""
        # Reload characters on startup
        self.reload_characters()

async def setup(bot: commands.Bot) -> None:
    """Set up the CharacterLoader cog."""
    await bot.add_cog(CharacterLoader(bot))
