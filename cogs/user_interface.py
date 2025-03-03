"""
User Interface Cog for TMDiscord Bot

This cog handles all user interactions, commands, and UI elements, including:
- Game commands (play, stats, leaderboard)
- Character selection UI
- Decision UI
- Game completion UI
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union

import discord
from discord import app_commands
from discord.ext import commands
from discord import ui

import config
from cogs.character_loader import Character

# Set up logging
logger = logging.getLogger("discord_bot.user_interface")

class CharacterSelectView(ui.View):
    """View for character selection."""
    
    def __init__(self, characters: List[Dict[str, Any]], user_id: int, game_manager_cog, channel_id: int):
        """Initialize the CharacterSelectView.
        
        Args:
            characters: List of character dictionaries
            user_id: The Discord user ID
            game_manager_cog: The GameManager cog
            channel_id: The Discord channel ID
        """
        super().__init__(timeout=120)  # 2 minute timeout
        self.characters = characters
        self.user_id = user_id
        self.game_manager_cog = game_manager_cog
        self.channel_id = channel_id
        
        # Add character select dropdown
        self.add_item(CharacterDropdown(characters))
    
    async def on_timeout(self):
        """Handle view timeout."""
        # Disable all items
        for item in self.children:
            item.disabled = True
        
        # Try to edit the message
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
        except:
            pass

class CharacterDropdown(ui.Select):
    """Dropdown for character selection."""
    
    def __init__(self, characters: List[Dict[str, Any]]):
        """Initialize the CharacterDropdown.
        
        Args:
            characters: List of character dictionaries
        """
        # Create options from characters
        options = []
        for character in characters:
            option = discord.SelectOption(
                label=character['name'],
                description=character['title'],
                value=character['id']
            )
            options.append(option)
        
        super().__init__(
            placeholder="Select a character to play as...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle dropdown selection.
        
        Args:
            interaction: The Discord interaction
        """
        # Get the view
        view = self.view
        
        # Check if the user is the one who initiated the command
        if interaction.user.id != view.user_id:
            await interaction.response.send_message("This isn't your game session!", ephemeral=True)
            return
        
        # Get selected character
        character_id = self.values[0]
        
        # Disable the dropdown
        self.disabled = True
        await interaction.response.edit_message(view=view)
        
        # Create game session
        session = await view.game_manager_cog.create_game_session(
            view.user_id,
            character_id,
            view.channel_id
        )
        
        if not session:
            await interaction.followup.send("Failed to create game session. Please try again.")
            return
        
        # Get character loader cog
        character_loader = interaction.client.get_cog('CharacterLoader')
        if not character_loader:
            await interaction.followup.send("Failed to load character data. Please try again.")
            return
        
        # Get character
        character = character_loader.get_character(character_id)
        if not character:
            await interaction.followup.send("Failed to load character data. Please try again.")
            return
        
        # Create character intro embed
        embed = discord.Embed(
            title=f"Playing as {character.name}",
            description=f"**{character.title}**\n\nStarting Year: {character.starting_year}\nInitial Capital: ${character.initial_capital:,}",
            color=config.EMBED_COLOR
        )
        
        # Add key principles
        if character.key_principles:
            principles = "\n".join([f"• {principle}" for principle in character.key_principles])
            embed.add_field(name="Key Principles", value=principles, inline=False)
        
        # Add game info
        embed.add_field(
            name="Game Information",
            value=f"You'll face {character.get_total_decisions()} key decisions that shaped {character.name}'s career.\nMake your choices wisely!",
            inline=False
        )
        
        # Send character intro
        await interaction.followup.send(embed=embed)
        
        # Start the game with the first decision
        await send_decision(interaction.client, session, 1)

class DecisionView(ui.View):
    """View for decision choices."""
    
    def __init__(self, session_id: str, decision_number: int, choices: Dict[str, Dict[str, Any]], game_manager_cog):
        """Initialize the DecisionView.
        
        Args:
            session_id: The game session ID
            decision_number: The decision number
            choices: Dictionary of choices
            game_manager_cog: The GameManager cog
        """
        super().__init__(timeout=300)  # 5 minute timeout
        self.session_id = session_id
        self.decision_number = decision_number
        self.choices = choices
        self.game_manager_cog = game_manager_cog
        
        # Add buttons for each choice
        for choice_id, choice_data in choices.items():
            button = ui.Button(
                label=f"Option {choice_id.upper()}",
                style=discord.ButtonStyle.primary,
                custom_id=f"choice_{choice_id}"
            )
            button.callback = self.create_callback(choice_id)
            self.add_item(button)
    
    def create_callback(self, choice_id: str):
        """Create a callback for a choice button.
        
        Args:
            choice_id: The choice ID
            
        Returns:
            The callback function
        """
        async def callback(interaction: discord.Interaction):
            # Get the session
            session = self.game_manager_cog.active_sessions.get(self.session_id)
            if not session:
                await interaction.response.send_message("Game session not found. Please start a new game.", ephemeral=True)
                return
            
            # Check if the user is the one who initiated the game
            if interaction.user.id != session.user_id:
                await interaction.response.send_message("This isn't your game session!", ephemeral=True)
                return
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Update the message
            await interaction.response.edit_message(view=self)
            
            # Process the decision
            score, is_completed = await self.game_manager_cog.make_decision(self.session_id, choice_id)
            
            # Get the choice data
            choice_data = self.choices.get(choice_id, {})
            
            # Create outcome embed
            embed = discord.Embed(
                title=f"Decision {self.decision_number} Outcome",
                description=f"You chose: **Option {choice_id.upper()}**\n\n{choice_data.get('text', 'No description')}",
                color=config.EMBED_COLOR
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
            decision = session.character.get_decision(self.decision_number)
            if decision and 'historical_context' in decision:
                embed.add_field(name="Historical Context", value=decision['historical_context'], inline=False)
            
            # Send outcome
            await interaction.followup.send(embed=embed)
            
            # If game is completed, show final results
            if is_completed:
                await show_game_results(interaction.client, session)
            else:
                # Send next decision after a short delay
                await asyncio.sleep(2)
                await send_decision(interaction.client, session, self.decision_number + 1)
        
        return callback
    
    async def on_timeout(self):
        """Handle view timeout."""
        # Disable all items
        for item in self.children:
            item.disabled = True
        
        # Try to edit the message
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
        except:
            pass

class UserInterface(commands.Cog):
    """Cog for handling user interface and commands."""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the UserInterface cog.
        
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
    
    async def get_character_loader_cog(self):
        """Get the CharacterLoader cog.
        
        Returns:
            The CharacterLoader cog
        """
        return self.bot.get_cog('CharacterLoader')
    
    async def get_database_cog(self):
        """Get the Database cog.
        
        Returns:
            The Database cog
        """
        return self.bot.get_cog('Database')
    
    @commands.hybrid_command(name="play", description="Start a new financial simulation game")
    @app_commands.describe(character="Optional character to play as")
    async def play_command(self, ctx: commands.Context, character: Optional[str] = None):
        """Command to start a new game.
        
        Args:
            ctx: The command context
            character: Optional character ID to play as
        """
        # Check if command is used in the correct channel
        if ctx.channel.id != config.V1SIM_CHANNEL_ID:
            await ctx.send(f"This game is only available in <#{config.V1SIM_CHANNEL_ID}>.", ephemeral=True)
            return
        
        # Get character loader cog
        character_loader = await self.get_character_loader_cog()
        if not character_loader:
            await ctx.send("Failed to load character data. Please try again later.", ephemeral=True)
            return
        
        # Get game manager cog
        game_manager = await self.get_game_manager_cog()
        if not game_manager:
            await ctx.send("Failed to start game. Please try again later.", ephemeral=True)
            return
        
        # Check if user already has an active session
        existing_session = await game_manager.get_user_session(ctx.author.id)
        if existing_session:
            # Ask if they want to end the current game
            confirm_view = ui.View(timeout=30)
            
            async def confirm_callback(interaction: discord.Interaction, end_game: bool):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message("This isn't your game session!", ephemeral=True)
                    return
                
                # Disable all buttons
                for item in confirm_view.children:
                    item.disabled = True
                
                await interaction.response.edit_message(view=confirm_view)
                
                if end_game:
                    # End the current session
                    await game_manager.end_game_session(existing_session.id, completed=False)
                    await interaction.followup.send("Previous game ended. Starting a new game...")
                    
                    # Start new game
                    await self.start_new_game(ctx, character_loader, game_manager, character)
                else:
                    await interaction.followup.send("Continuing your current game. Use `/play` again if you want to start a new game.")
            
            # Add buttons
            yes_button = ui.Button(label="Yes, end current game", style=discord.ButtonStyle.danger)
            no_button = ui.Button(label="No, continue current game", style=discord.ButtonStyle.secondary)
            
            yes_button.callback = lambda i: confirm_callback(i, True)
            no_button.callback = lambda i: confirm_callback(i, False)
            
            confirm_view.add_item(yes_button)
            confirm_view.add_item(no_button)
            
            await ctx.send(
                "You already have an active game session. Do you want to end it and start a new one?",
                view=confirm_view,
                ephemeral=True
            )
        else:
            # Start new game
            await self.start_new_game(ctx, character_loader, game_manager, character)
    
    async def start_new_game(self, ctx, character_loader, game_manager, character_id: Optional[str] = None):
        """Start a new game.
        
        Args:
            ctx: The command context
            character_loader: The CharacterLoader cog
            game_manager: The GameManager cog
            character_id: Optional character ID to play as
        """
        if character_id:
            # Check if character exists
            character = character_loader.get_character(character_id)
            if not character:
                await ctx.send(f"Character '{character_id}' not found. Use `/play` without a character to see available options.", ephemeral=True)
                return
            
            # Create game session
            session = await game_manager.create_game_session(
                ctx.author.id,
                character_id,
                ctx.channel.id
            )
            
            if not session:
                await ctx.send("Failed to create game session. Please try again.", ephemeral=True)
                return
            
            # Create character intro embed
            embed = discord.Embed(
                title=f"Playing as {character.name}",
                description=f"**{character.title}**\n\nStarting Year: {character.starting_year}\nInitial Capital: ${character.initial_capital:,}",
                color=config.EMBED_COLOR
            )
            
            # Add key principles
            if character.key_principles:
                principles = "\n".join([f"• {principle}" for principle in character.key_principles])
                embed.add_field(name="Key Principles", value=principles, inline=False)
            
            # Add game info
            embed.add_field(
                name="Game Information",
                value=f"You'll face {character.get_total_decisions()} key decisions that shaped {character.name}'s career.\nMake your choices wisely!",
                inline=False
            )
            
            # Send character intro
            await ctx.send(embed=embed)
            
            # Start the game with the first decision
            await send_decision(self.bot, session, 1)
        else:
            # Show character selection
            characters = character_loader.get_character_list()
            
            # Create embed
            embed = discord.Embed(
                title="Financial Simulation Game",
                description="Select a character to play as:",
                color=config.EMBED_COLOR
            )
            
            # Create view with character dropdown
            view = CharacterSelectView(characters, ctx.author.id, game_manager, ctx.channel.id)
            
            # Send message
            message = await ctx.send(embed=embed, view=view)
            
            # Store message reference in view for timeout handling
            view.message = message
    
    @commands.hybrid_command(name="stats", description="View your game statistics")
    @app_commands.describe(user="User to view stats for (defaults to yourself)")
    async def stats_command(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        """Command to view game statistics.
        
        Args:
            ctx: The command context
            user: Optional user to view stats for
        """
        # Check if command is used in the correct channel
        if ctx.channel.id != config.V1SIM_CHANNEL_ID and not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send(f"This command can only be used in <#{config.V1SIM_CHANNEL_ID}> or DMs.", ephemeral=True)
            return
        
        # Get target user
        target_user = user or ctx.author
        
        # Get database cog
        database = await self.get_database_cog()
        if not database:
            await ctx.send("Failed to load statistics. Please try again later.", ephemeral=True)
            return
        
        # Get user stats
        stats = database.get_user_stats(target_user.id)
        
        # Create embed
        embed = discord.Embed(
            title=f"{target_user.display_name}'s Statistics",
            color=config.EMBED_COLOR
        )
        
        # Add stats
        embed.add_field(name="Games Played", value=stats['games_played'], inline=True)
        embed.add_field(name="Total Score", value=stats['total_score'], inline=True)
        embed.add_field(name="Top Score", value=stats['top_score'], inline=True)
        embed.add_field(name="Average Score", value=stats['avg_score'], inline=True)
        embed.add_field(name="Favorite Character", value=stats['favorite_character'], inline=True)
        
        # Add recent games if available
        if stats['recent_games']:
            recent_games_text = ""
            for game in stats['recent_games']:
                recent_games_text += f"• {game['character_id']}: {game['total_score']} points\n"
            embed.add_field(name="Recent Games", value=recent_games_text, inline=False)
        
        # Add last played
        if stats['last_played']:
            embed.set_footer(text=f"Last played: {stats['last_played']}")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="leaderboard", description="View the game leaderboard")
    @app_commands.describe(character="Optional character to filter by")
    async def leaderboard_command(self, ctx: commands.Context, character: Optional[str] = None):
        """Command to view the leaderboard.
        
        Args:
            ctx: The command context
            character: Optional character ID to filter by
        """
        # Check if command is used in the correct channel
        if ctx.channel.id != config.V1SIM_CHANNEL_ID and not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send(f"This command can only be used in <#{config.V1SIM_CHANNEL_ID}> or DMs.", ephemeral=True)
            return
        
        # Get database cog
        database = await self.get_database_cog()
        if not database:
            await ctx.send("Failed to load leaderboard. Please try again later.", ephemeral=True)
            return
        
        # Get character loader cog if character filter is specified
        character_name = None
        if character:
            character_loader = await self.get_character_loader_cog()
            if character_loader:
                char_obj = character_loader.get_character(character)
                if char_obj:
                    character_name = char_obj.name
        
        # Get leaderboard
        leaderboard = database.get_leaderboard(limit=10, character_id=character)
        
        # Create embed
        embed = discord.Embed(
            title=f"Leaderboard{f' - {character_name}' if character_name else ''}",
            description="Top players by highest score",
            color=config.EMBED_COLOR
        )
        
        # Add leaderboard entries
        if leaderboard:
            leaderboard_text = ""
            for i, entry in enumerate(leaderboard, 1):
                leaderboard_text += f"{i}. **{entry['username']}**: {entry['high_score']} points\n"
            embed.description = leaderboard_text
        else:
            embed.description = "No games have been completed yet. Be the first on the leaderboard!"
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="help", description="Show help information")
    async def help_command(self, ctx: commands.Context):
        """Command to show help information.
        
        Args:
            ctx: The command context
        """
        embed = discord.Embed(
            title="Financial Simulation Game - Help",
            description="Welcome to the Financial Simulation Game! Here's how to play:",
            color=config.EMBED_COLOR
        )
        
        # Add command information
        commands_text = (
            "• `/play` - Start a new game\n"
            "• `/play [character]` - Start a game with a specific character\n"
            "• `/stats` - View your game statistics\n"
            "• `/stats [user]` - View another user's statistics\n"
            "• `/leaderboard` - View the global leaderboard\n"
            "• `/leaderboard [character]` - View the leaderboard for a specific character\n"
            "• `/feedback` - Provide feedback on your current game\n"
            "• `/help` - Show this help information"
        )
        embed.add_field(name="Commands", value=commands_text, inline=False)
        
        # Add gameplay information
        gameplay_text = (
            "1. Select a character to play as\n"
            "2. Make decisions at key moments in their career\n"
            "3. Earn points based on your choices\n"
            "4. Complete all decisions to finish the game\n"
            "5. Provide feedback to help improve the game"
        )
        embed.add_field(name="How to Play", value=gameplay_text, inline=False)
        
        # Add note about channel restriction
        embed.set_footer(text=f"Note: This game can only be played in the designated channel.")
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Event triggered when the bot is ready."""
        logger.info("UserInterface cog is ready")

async def send_decision(bot, session, decision_number: int):
    """Send a decision message to the user.
    
    Args:
        bot: The Discord bot
        session: The GameSession object
        decision_number: The decision number
    """
    # Get the decision
    decision = session.character.get_decision(decision_number)
    if not decision:
        logger.error(f"Decision {decision_number} not found for character {session.character.id}")
        return
    
    # Get the channel
    channel = bot.get_channel(session.channel_id)
    if not channel:
        logger.error(f"Channel {session.channel_id} not found")
        return
    
    # Create embed
    embed = discord.Embed(
        title=f"Decision {decision_number}: {session.character.name} ({decision['year']})",
        description=decision['context'],
        color=config.EMBED_COLOR
    )
    
    # Add question
    embed.add_field(name="Decision", value=decision['question'], inline=False)
    
    # Add choices
    choices_text = ""
    for choice_id, choice_data in decision['choices'].items():
        choices_text += f"**Option {choice_id.upper()}**: {choice_data['text']}\n\n"
    
    embed.add_field(name="Options", value=choices_text, inline=False)
    
    # Add progress
    total_decisions = session.character.get_total_decisions()
    progress = f"Decision {decision_number} of {total_decisions} | Score: {session.total_score}"
    embed.set_footer(text=progress)
    
    # Get game manager cog
    game_manager = bot.get_cog('GameManager')
    if not game_manager:
        logger.error("GameManager cog not found")
        return
    
    # Create view with decision buttons
    view = DecisionView(session.id, decision_number, decision['choices'], game_manager)
    
    # Send message
    message = await channel.send(content=f"<@{session.user_id}>, it's time to make a decision:", embed=embed, view=view)
    
    # Store message ID in session
    session.message_id = message.id
    
    # Store message reference in view for timeout handling
    view.message = message

async def show_game_results(bot, session):
    """Show the final results of a game.
    
    Args:
        bot: The Discord bot
        session: The GameSession object
    """
    # Get the channel
    channel = bot.get_channel(session.channel_id)
    if not channel:
        logger.error(f"Channel {session.channel_id} not found")
        return
    
    # Generate analysis
    analysis = session.get_analysis()
    
    # Create embed
    embed = discord.Embed(
        title=f"Game Completed: {session.character.name}",
        description=f"You've completed all decisions as {session.character.name}!",
        color=config.EMBED_COLOR
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
    
    # Get feedback cog
    feedback_cog = bot.get_cog('Feedback')
    if not feedback_cog:
        logger.error("Feedback cog not found")
        # Send results without feedback button
        await channel.send(content=f"<@{session.user_id}>, your game has concluded:", embed=embed)
        return
    
    # Create feedback view
    view = await feedback_cog.create_feedback_view(session.id)
    
    # Send results with feedback button
    await channel.send(
        content=f"<@{session.user_id}>, your game has concluded:",
        embed=embed,
        view=view
    )

async def setup(bot: commands.Bot) -> None:
    """Set up the UserInterface cog."""
    await bot.add_cog(UserInterface(bot))
