# bot.py - Add support for both polling and webhook
import logging
import io
import os
import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from PIL import Image, ImageDraw

from config import config
from database import db
from models import Player, Gender, SkinTone, BodyStyle, GameState
from game_logic import GameLogic, ActionType
from image_generator import ImageGenerator, ImageGeneratorError
from utils import (
    safe_send_message, safe_edit_message, safe_send_photo,
    create_main_menu_keyboard, create_character_gender_keyboard,
    create_skin_tone_keyboard, create_body_style_keyboard,
    create_game_keyboard, cleanup_timed_out_games
)

logger = logging.getLogger(__name__)

# Conversation states
GENDER, SKIN_TONE, BODY_STYLE, SELFIE = range(4)

class SlapFightBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        # ... (your existing handler setup code)
        pass
    
    # ... (all your existing methods)
    
    async def start_polling(self):
        """Start the bot in polling mode (for development)"""
        logger.info("Starting bot in polling mode...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Bot is now polling for updates...")
        
        # Keep the application running
        await asyncio.Event().wait()
    
    async def start_webhook(self):
        """Start the bot in webhook mode (for production)"""
        from webhook_server import WebhookServer
        
        logger.info("Starting bot in webhook mode...")
        
        # Initialize the application
        await self.application.initialize()
        await self.application.start()
        
        # Create and start webhook server
        server = WebhookServer(self.application)
        await server.start_server()

async def main():
    try:
        config.validate()
        
        token = os.getenv("BOT_TOKEN", "")
        if not token:
            raise RuntimeError("BOT_TOKEN is missing. Set it in .env or environment.")
        
        bot = SlapFightBot(token)
        
        # Choose between polling and webhook mode
        if config.USE_WEBHOOK:
            logger.info("Starting in webhook mode...")
            await bot.start_webhook()
        else:
            logger.info("Starting in polling mode...")
            await bot.start_polling()
            
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
