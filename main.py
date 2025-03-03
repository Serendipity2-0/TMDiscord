#!/usr/bin/env python3
"""
TMDiscord Bot - Main Entry Point

This is the main entry point for the TMDiscord bot, which allows users to play
a financial simulation game using characters from YAML files.

The bot is built with discord.py and uses cogs for modularity.
"""

import os
import logging
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("discord_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("discord_bot")

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_V1SIM_CHANNEL_ID'))

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance with command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# List of cogs to load
initial_cogs = [
    'cogs.database',
    'cogs.character_loader',
    'cogs.game_manager',
    'cogs.user_interface',
    'cogs.feedback'
]

def get_help_embed():
    """
    Creates an embed with help information about the bot's commands and functionality.
    
    Returns:
        discord.Embed: An embed containing help information
    """
    embed = discord.Embed(
        title="📚 TradeMan Bot Help Guide",
        description="Welcome to the Financial Trading Simulator! Here's how to use the bot:",
        color=discord.Color.blue()
    )
    
    # Add command sections
    embed.add_field(
        name="🎮 Game Commands",
        value=(
            "• `/start` - Start a new trading session\n"
            "• `/end` - End your current trading session\n"
            "• `/status` - Check your current game status\n"
            "• `/buy <stock> <amount>` - Buy stocks\n"
            "• `/sell <stock> <amount>` - Sell stocks\n"
            "• `/portfolio` - View your current portfolio"
        ),
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Information Commands",
        value=(
            "• `/market` - View current market conditions\n"
            "• `/characters` - List available trading characters\n"
            "• `/leaderboard` - View the top traders\n"
            "• `/history` - View your trading history"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Settings",
        value=(
            "• `/settings` - Adjust your game settings\n"
            "• `/feedback <message>` - Send feedback to the developers"
        ),
        inline=False
    )
    
    # Add footer
    embed.set_footer(text="For more detailed help on any command, use /help <command>")
    
    return embed

@bot.event
async def on_ready():
    """Event triggered when the bot is ready and connected to Discord."""
    logger.info(f'{bot.user.name} has connected to Discord!')
    
    # Set bot activity
    await bot.change_presence(activity=discord.Game(name="Financial Simulator"))
    
    # Sync slash commands
    try:
        logger.info("Syncing slash commands...")
        await bot.tree.sync()
        logger.info("Slash commands synced successfully!")
    except Exception as e:
        logger.error(f"Error syncing slash commands: {e}")
    
    # Send a message to the designated channel
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            # Send online notification
            await channel.send(f"🚀 **{bot.user.name}** is now online and ready for trading! 📈")
            
            # Send help information
            help_embed = get_help_embed()
            await channel.send("Here's a quick guide to get you started:", embed=help_embed)
            
            logger.info(f"Sent online notification and help guide to channel {CHANNEL_ID}")
        else:
            logger.error(f"Could not find channel with ID {CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Error sending online message: {e}")

@bot.event
async def on_message(message):
    """Event triggered when a message is sent in a channel."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Only process commands in the designated channel
    if message.channel.id != CHANNEL_ID and not isinstance(message.channel, discord.DMChannel):
        return
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Event triggered when a command raises an error."""
    if isinstance(error, commands.CommandNotFound):
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param}")
        return
    
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        return
    
    # Log other errors
    logger.error(f"Command error: {error}")
    await ctx.send("An error occurred while processing the command.")

async def load_cogs():
    """Load all cogs for the bot."""
    for cog in initial_cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"Failed to load cog {cog}: {e}")

async def main():
    """Main function to start the bot."""
    # Create necessary directories if they don't exist
    os.makedirs("DB", exist_ok=True)
    
    # Load cogs
    await load_cogs()
    
    # Start the bot
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
