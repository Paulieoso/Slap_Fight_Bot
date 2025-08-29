# 🥊 Slap Fight Bot

A fun Telegram game bot where players battle by slapping each other!

## Features
- Create and customize your character with South Park style
- Turn-based slap battles with guessing mechanics
- Special moves: Club and Flinch
- Global rankings and player statistics
- SQLite database to track players and games

## Setup

### Local Development
1. Clone this repository
2. Run `setup.bat` (Windows) or `setup.sh` (Linux/Mac)
3. Edit `.env` and add your bot token from @BotFather
4. Run `python bot.py`

### Heroku Deployment
1. Create a new Heroku app
2. Set environment variables:
   - `BOT_TOKEN`: Your Telegram bot token
3. Deploy using Git:
   ```bash
   git push heroku main
