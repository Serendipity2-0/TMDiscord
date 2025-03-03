# TMDiscord Bot - Financial Simulation Game

A Discord bot that allows users to play a financial simulation game where they make decisions as historical financial figures. The bot is built with discord.py and uses a modular cog-based architecture.

## Features

- Character-based financial simulation game
- Interactive UI with buttons, dropdowns, and modals
- Database for storing user progress and statistics
- Leaderboards and statistics tracking
- User feedback collection
- Dynamic character loading from YAML files

## Requirements

- Python 3.8+
- discord.py 2.0+
- pyyaml
- python-dotenv

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/TMDiscord.git
cd TMDiscord
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Discord bot token and channel ID:
```
DISCORD_TOKEN=your_discord_bot_token
DISCORD_V1SIM_CHANNEL_ID=your_channel_id
```

4. Run the bot:
```bash
python main.py
```

## Game Structure

The game is based on characters defined in YAML files in the `characters/` directory. Each character has:

- Basic information (name, title, starting year, initial capital)
- Key principles
- A series of decisions with multiple choices
- Analysis templates for different performance levels

Players select a character, make decisions at key moments in their career, and receive a score and analysis at the end.

## Adding New Characters

To add a new character, create a new YAML file in the `characters/` directory with the following structure:

```yaml
name: "Character Name"
title: "Character Title"
starting_year: YYYY
initial_capital: AMOUNT
key_principles:
  - "Principle 1"
  - "Principle 2"
  # etc.

decisions:
  1:
    year: YYYY
    context: "Decision context"
    question: "Decision question"
    choices:
      a:
        text: "Option A"
        outcome: "Outcome description"
        score: SCORE
      # options b, c, etc.
    correct_choice: "a"
    historical_context: "What actually happened"
    
  # additional decisions...

analysis_templates:
  excellent:
    text: "Analysis for excellent performance"
    principles:
      - "Principle 1"
      # etc.
  good:
    text: "Analysis for good performance"
    principles:
      - "Principle 1"
      # etc.
  needs_improvement:
    text: "Analysis for poor performance"
    principles:
      - "Principle 1"
      # etc.
```

## Commands

- `/play` - Start a new game
- `/play [character]` - Start a game with a specific character
- `/stats` - View your game statistics
- `/stats [user]` - View another user's statistics
- `/leaderboard` - View the global leaderboard
- `/leaderboard [character]` - View the leaderboard for a specific character
- `/feedback` - Provide feedback on your current game
- `/help` - Show help information

## Project Structure

```
TMDiscord/
├── main.py                  # Bot entry point
├── config.py                # Configuration settings
├── .env                     # Environment variables
├── requirements.txt         # Dependencies
├── README.md                # Documentation
├── characters/              # Character YAML files
├── DB/                      # Database directory
│   └── game_data.db         # SQLite database
└── cogs/
    ├── database.py          # Database operations
    ├── character_loader.py  # YAML parsing and character loading
    ├── game_manager.py      # Game session management
    ├── user_interface.py    # Commands and interactions
    └── feedback.py          # User feedback collection
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
