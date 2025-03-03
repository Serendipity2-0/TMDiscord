"""
Feedback Cog for TMDiscord Bot

This cog handles collecting and processing user feedback after games, including:
- Feedback modal for rating and comments
- Feedback command
- Feedback button in game completion message
"""

import logging
from typing import Dict, List, Optional, Any, Union

import discord
from discord import ui
from discord.ext import commands

import config

# Set up logging
logger = logging.getLogger("discord_bot.feedback")

class FeedbackModal(ui.Modal):
    """Modal for collecting user feedback."""
    
    def __init__(self, session_id: str, game_manager_cog):
        """Initialize the FeedbackModal.
        
        Args:
            session_id: The game session ID
            game_manager_cog: The GameManager cog
        """
        super().__init__(title="Game Feedback")
        self.session_id = session_id
        self.game_manager_cog = game_manager_cog
        
        # Add rating input (text input)
        self.rating = ui.TextInput(
            label="Rating (1-5)",
            placeholder="Enter a number from 1 to 5 (1=Poor, 5=Excellent)",
            required=True,
            min_length=1,
            max_length=1,
            default="5"
        )
        self.add_item(self.rating)
        
        # Add comments input (text area)
        self.comments = ui.TextInput(
            label="Comments (optional)",
            placeholder="Share your thoughts about the game...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.comments)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission.
        
        Args:
            interaction: The Discord interaction
        """
        # Get rating value
        try:
            rating_value = int(self.rating.value)
            # Ensure rating is between 1 and 5
            rating_value = max(1, min(5, rating_value))
        except (ValueError, TypeError):
            rating_value = 3  # Default to 3 if invalid input
        
        # Get comments
        comments_value = self.comments.value if self.comments.value else None
        
        # Record feedback
        success = await self.game_manager_cog.record_feedback(
            self.session_id,
            rating_value,
            comments_value
        )
        
        if success:
            await interaction.response.send_message(
                "Thank you for your feedback! Your input helps us improve the game.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Sorry, there was an error recording your feedback. Please try again later.",
                ephemeral=True
            )

class FeedbackView(ui.View):
    """View with a feedback button."""
    
    def __init__(self, session_id: str, game_manager_cog):
        """Initialize the FeedbackView.
        
        Args:
            session_id: The game session ID
            game_manager_cog: The GameManager cog
        """
        super().__init__(timeout=None)  # No timeout
        self.session_id = session_id
        self.game_manager_cog = game_manager_cog
    
    @ui.button(label="Provide Feedback", style=discord.ButtonStyle.primary, emoji="📝")
    async def feedback_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle feedback button click.
        
        Args:
            interaction: The Discord interaction
            button: The button that was clicked
        """
        # Create and send feedback modal
        modal = FeedbackModal(self.session_id, self.game_manager_cog)
        await interaction.response.send_modal(modal)

class Feedback(commands.Cog):
    """Cog for handling user feedback."""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the Feedback cog.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
    
    async def get_game_manager_cog(self):
        """Get the GameManager cog.
        
        Returns:
            The GameManager cog
        """
        return self.bot.get_cog('GameManager')
    
    async def create_feedback_view(self, session_id: str) -> FeedbackView:
        """Create a feedback view for a game session.
        
        Args:
            session_id: The game session ID
            
        Returns:
            The FeedbackView
        """
        game_manager = await self.get_game_manager_cog()
        return FeedbackView(session_id, game_manager)
    
    @commands.hybrid_command(name="feedback", description="Provide feedback on your last game")
    async def feedback_command(self, ctx: commands.Context):
        """Command to provide feedback on the last game.
        
        Args:
            ctx: The command context
        """
        # Check if command is used in the correct channel
        if ctx.channel.id != config.V1SIM_CHANNEL_ID and not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("This command can only be used in the designated game channel or DMs.", ephemeral=True)
            return
        
        # Get game manager cog
        game_manager = await self.get_game_manager_cog()
        if not game_manager:
            await ctx.send("Sorry, the feedback system is currently unavailable.", ephemeral=True)
            return
        
        # Get user's active session
        session = await game_manager.get_user_session(ctx.author.id)
        if not session:
            await ctx.send("You don't have an active game session. Start a new game first!", ephemeral=True)
            return
        
        # Create and send feedback modal
        modal = FeedbackModal(session.id, game_manager)
        await ctx.send("Please provide your feedback:", view=FeedbackView(session.id, game_manager), ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    """Set up the Feedback cog."""
    await bot.add_cog(Feedback(bot))
