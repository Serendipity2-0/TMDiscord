"""
YAML Parser Utility for TMDiscord Bot

This module provides utility functions for parsing and validating YAML files
for character data.
"""

import os
import logging
import yaml
from typing import Dict, List, Optional, Any, Union

import config

# Set up logging
logger = logging.getLogger("discord_bot.yaml_parser")

def load_yaml_file(filepath: str) -> Optional[Dict[str, Any]]:
    """Load a YAML file and return its contents.
    
    Args:
        filepath: Path to the YAML file
        
    Returns:
        Dictionary of YAML contents or None if loading failed
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        return data
    except Exception as e:
        logger.error(f"Error loading YAML file {filepath}: {e}")
        return None

def validate_character_data(character_id: str, data: Dict[str, Any]) -> bool:
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

def get_all_character_files() -> List[str]:
    """Get all character YAML files from the characters directory.
    
    Returns:
        List of character file paths
    """
    try:
        files = [
            os.path.join(config.CHARACTERS_DIR, f) 
            for f in os.listdir(config.CHARACTERS_DIR) 
            if f.endswith('.yml') or f.endswith('.yaml')
        ]
        return files
    except FileNotFoundError:
        logger.error(f"Characters directory not found: {config.CHARACTERS_DIR}")
        return []

def load_all_characters() -> Dict[str, Dict[str, Any]]:
    """Load all character YAML files from the characters directory.
    
    Returns:
        Dictionary of character ID to character data
    """
    characters = {}
    
    # Get all YAML files in the characters directory
    files = get_all_character_files()
    
    # Load each file
    for filepath in files:
        filename = os.path.basename(filepath)
        character_id = os.path.splitext(filename)[0]
        
        data = load_yaml_file(filepath)
        if data and validate_character_data(character_id, data):
            characters[character_id] = data
            logger.info(f"Loaded character: {data.get('name', 'Unknown')} ({character_id})")
    
    logger.info(f"Loaded {len(characters)} characters")
    return characters

def save_character_file(character_id: str, data: Dict[str, Any]) -> bool:
    """Save character data to a YAML file.
    
    Args:
        character_id: The character ID (filename without extension)
        data: The character data to save
        
    Returns:
        True if successful, False otherwise
    """
    filepath = os.path.join(config.CHARACTERS_DIR, f"{character_id}.yml")
    
    try:
        # Validate data before saving
        if not validate_character_data(character_id, data):
            logger.error(f"Invalid character data for {character_id}")
            return False
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved character: {data.get('name', 'Unknown')} ({character_id})")
        return True
    except Exception as e:
        logger.error(f"Error saving character {character_id}: {e}")
        return False
