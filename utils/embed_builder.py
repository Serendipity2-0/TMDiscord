"""
Embed Builder Utility for TMDiscord Bot

This module provides utility functions for creating consistent Discord embeds
throughout the bot.
"""

import discord
import config

def create_basic_embed(title: str, description: str = None, color: int = None) -> discord.Embed:
    """Create a basic embed with title, description, and color.
    
    Args:
        title: The embed title
        description: Optional embed description
        color: Optional embed color (defaults to config.EMBED_COLOR)
        
    Returns:
        The created embed
    """
    return discord.Embed(
        title=title,
        description=description,
        color=color or config.EMBED_COLOR
    )

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed with a red color.
    
    Args:
        title: The embed title
        description: The error description
        
    Returns:
        The created embed
    """
    return discord.Embed(
        title=title,
        description=description,
        color=config.ERROR_COLOR
    )

def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a success embed with a green color.
    
    Args:
        title: The embed title
        description: The success description
        
    Returns:
        The created embed
    """
    return discord.Embed(
        title=title,
        description=description,
        color=config.SUCCESS_COLOR
    )

def create_info_embed(title: str, description: str) -> discord.Embed:
    """Create an info embed with an orange color.
    
    Args:
        title: The embed title
        description: The info description
        
    Returns:
        The created embed
    """
    return discord.Embed(
        title=title,
        description=description,
        color=config.INFO_COLOR
    )

def create_character_embed(character) -> discord.Embed:
    """Create an embed for a character.
    
    Args:
        character: The Character object
        
    Returns:
        The created embed
    """
    embed = create_basic_embed(
        title=f"{character.name}",
        description=f"**{character.title}**\n\nStarting Year: {character.starting_year}\nInitial Capital: ${character.initial_capital:,}"
    )
    
    # Add key principles
    if character.key_principles:
        principles = "\n".join([f"• {principle}" for principle in character.key_principles])
        embed.add_field(name="Key Principles", value=principles, inline=False)
    
    # Add game info
    embed.add_field(
        name="Game Information",
        value=f"This character has {character.get_total_decisions()} key decisions that shaped their career.",
        inline=False
    )
    
    return embed

def create_decision_embed(character, decision_number: int, decision: dict) -> discord.Embed:
    """Create an embed for a decision.
    
    Args:
        character: The Character object
        decision_number: The decision number
        decision: The decision data
        
    Returns:
        The created embed
    """
    embed = create_basic_embed(
        title=f"Decision {decision_number}: {character.name} ({decision['year']})",
        description=decision['context']
    )
    
    # Add question
    embed.add_field(name="Decision", value=decision['question'], inline=False)
    
    # Add choices
    choices_text = ""
    for choice_id, choice_data in decision['choices'].items():
        choices_text += f"**Option {choice_id.upper()}**: {choice_data['text']}\n\n"
    
    embed.add_field(name="Options", value=choices_text, inline=False)
    
    # Add progress
    total_decisions = character.get_total_decisions()
    embed.set_footer(text=f"Decision {decision_number} of {total_decisions}")
    
    return embed

def create_outcome_embed(character, decision_number: int, choice_id: str, choice_data: dict, score: int) -> discord.Embed:
    """Create an embed for a decision outcome.
    
    Args:
        character: The Character object
        decision_number: The decision number
        choice_id: The choice ID
        choice_data: The choice data
        score: The score for this choice
        
    Returns:
        The created embed
    """
    embed = create_basic_embed(
        title=f"Decision {decision_number} Outcome",
        description=f"You chose: **Option {choice_id.upper()}**\n\n{choice_data.get('text', 'No description')}"
    )
    
    # Add outcome
    if 'outcome' in choice_data:
        embed.add_field(name="Outcome", value=choice_data['outcome'], inline=False)
    
    # Add score
    embed.add_field(name="Points Earned", value=f"+{score} points", inline=True)
    
    # Add V1 lesson if available
    if 'V1Lesson' in choice_data:
        embed.add_field(name="V1 Lesson", value=choice_data['V1Lesson'], inline=False)
    
    # Add historical context if available
    decision = character.get_decision(decision_number)
    if decision and 'historical_context' in decision:
        embed.add_field(name="Historical Context", value=decision['historical_context'], inline=False)
    
    return embed

def create_results_embed(character, analysis: dict) -> discord.Embed:
    """Create an embed for game results.
    
    Args:
        character: The Character object
        analysis: The analysis data
        
    Returns:
        The created embed
    """
    embed = create_basic_embed(
        title=f"Game Completed: {character.name}",
        description=f"You've completed all decisions as {character.name}!"
    )
    
    # Add score
    embed.add_field(
        name="Final Score",
        value=f"{analysis['score']} / {analysis['max_score']} points ({analysis['percentage']:.1f}%)",
        inline=False
    )
    
    # Add accuracy
    embed.add_field(
        name="Historical Accuracy",
        value=f"{analysis['correct_decisions']} / {analysis['total_decisions']} correct decisions ({analysis['accuracy']:.1f}%)",
        inline=False
    )
    
    # Add analysis text
    embed.add_field(name="Analysis", value=analysis['text'], inline=False)
    
    # Add principles if available
    if analysis['principles']:
        principles = "\n".join([f"• {principle}" for principle in analysis['principles']])
        embed.add_field(name="Key Takeaways", value=principles, inline=False)
    
    return embed
