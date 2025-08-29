import logging
import io
import os
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
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stats", self.show_stats))
        self.application.add_handler(CommandHandler("rankings", self.show_rankings))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("about", self.about_command))
        
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.character_creation_start, pattern='^create_character$')],
            states={
                GENDER: [CallbackQueryHandler(self.set_gender, pattern='^gender_')],
                SKIN_TONE: [CallbackQueryHandler(self.set_skin_tone, pattern='^skin_')],
                BODY_STYLE: [CallbackQueryHandler(self.set_body_style, pattern='^body_')],
                SELFIE: [MessageHandler(filters.PHOTO, self.set_selfie),
                         CallbackQueryHandler(self.skip_selfie, pattern='^skip_selfie$')]
            },
            fallbacks=[CallbackQueryHandler(self.cancel_creation, pattern='^main_menu$')],
        )
        self.application.add_handler(conv_handler)
        
        self.application.add_handler(CallbackQueryHandler(self.main_menu, pattern='^main_menu$'))
        self.application.add_handler(CallbackQueryHandler(self.show_rankings, pattern='^rankings$'))
        self.application.add_handler(CallbackQueryHandler(self.show_stats, pattern='^stats$'))
        self.application.add_handler(CallbackQueryHandler(self.find_opponent, pattern='^fight$'))
        self.application.add_handler(CallbackQueryHandler(self.handle_slap, pattern='^slap_'))
        self.application.add_handler(CallbackQueryHandler(self.handle_guess, pattern='^guess_'))
        self.application.add_handler(CallbackQueryHandler(self.handle_club, pattern='^club_'))
        self.application.add_handler(CallbackQueryHandler(self.handle_flinch, pattern='^flinch_'))
        
        self.application.job_queue.run_repeating(cleanup_timed_out_games, interval=300, first=10)
        self.application.add_error_handler(self.error_handler)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        context.user_data['user_id'] = user.id
        context.user_data['username'] = user.username or user.first_name
        
        player = db.get_player(user.id)
        if not player:
            player = Player(
                user_id=user.id,
                username=context.user_data['username']
            )
            db.create_player(player)
        
        keyboard = create_main_menu_keyboard()
        await update.message.reply_text(
            f"Welcome to Slap Fight, {user.first_name}!\n\n"
            "Test your slapping skills in this intense 1v1 battle!\n"
            "Choose your action:",
            reply_markup=keyboard
        )
    
    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        keyboard = create_main_menu_keyboard()
        await safe_edit_message(update, "Main Menu:", reply_markup=keyboard)
    
    async def character_creation_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        player = db.get_player(context.user_data['user_id'])
        if player and player.gender and player.skin_tone and player.body_style:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Recreate Character", callback_data='create_character')],
                [InlineKeyboardButton("Main Menu", callback_data='main_menu')]
            ])
            await safe_edit_message(
                update, 
                "You already have a character. Would you like to recreate it?",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        
        keyboard = create_character_gender_keyboard()
        await safe_edit_message(
            update, 
            "Let's create your character!\nFirst, choose your gender:",
            reply_markup=keyboard
        )
        return GENDER
    
    async def set_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        gender_str = query.data.split('_')[1]
        gender = Gender(gender_str)
        
        context.user_data['character_gender'] = gender
        
        keyboard = create_skin_tone_keyboard()
        await safe_edit_message(
            update, 
            "Great! Now choose your skin tone:",
            reply_markup=keyboard
        )
        return SKIN_TONE
    
    async def set_skin_tone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        skin_str = query.data.split('_')[1]
        skin_tone = SkinTone(skin_str)
        
        context.user_data['character_skin_tone'] = skin_tone
        
        keyboard = create_body_style_keyboard()
        await safe_edit_message(
            update, 
            "Nice! Now choose your body style:",
            reply_markup=keyboard
        )
        return BODY_STYLE
    
    async def set_body_style(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        body_str = query.data.split('_')[1]
        body_style = BodyStyle(body_str)
        
        context.user_data['character_body_style'] = body_style
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Skip Selfie", callback_data='skip_selfie')],
            [InlineKeyboardButton("Back", callback_data='create_character')]
        ])
        await safe_edit_message(
            update, 
            "Perfect! Now you can add a selfie to your character. "
            "Send a photo or skip to continue:",
            reply_markup=keyboard
        )
        return SELFIE
    
    async def set_selfie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        context.user_data['character_selfie'] = bytes(photo_bytes)
        
        return await self.complete_character_creation(update, context)
    
    async def skip_selfie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        return await self.complete_character_creation(update, context)
    
    async def complete_character_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = context.user_data['user_id']
        
        player = db.get_player(user_id)
        player.gender = context.user_data.get('character_gender')
        player.skin_tone = context.user_data.get('character_skin_tone')
        player.body_style = context.user_data.get('character_body_style')
        player.selfie_image = context.user_data.get('character_selfie')
        
        if db.update_player(player):
            try:
                char_image = ImageGenerator.generate_character_image(player)
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=char_image,
                    caption="Your character has been created!",
                    reply_markup=create_main_menu_keyboard()
                )
                
                if isinstance(update, Update) and update.callback_query:
                    await update.callback_query.message.delete()
            
            except ImageGeneratorError as e:
                logger.error(f"Error generating character image: {e}")
                await safe_send_message(
                    user_id, context,
                    "Character created, but there was an error generating your image.",
                    reply_markup=create_main_menu_keyboard()
                )
        else:
            await safe_send_message(
                user_id, context,
                "Error saving your character. Please try again.",
                reply_markup=create_main_menu_keyboard()
            )
        
        for key in ['character_gender', 'character_skin_tone', 'character_body_style', 'character_selfie']:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    
    async def cancel_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        for key in ['character_gender', 'character_skin_tone', 'character_body_style', 'character_selfie']:
            context.user_data.pop(key, None)
        
        keyboard = create_main_menu_keyboard()
        await safe_edit_message(update, "Character creation cancelled.", reply_markup=keyboard)
        return ConversationHandler.END
    
    async def find_opponent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data['user_id']
        
        player = db.get_player(user_id)
        if not player or not player.gender or not player.skin_tone or not player.body_style:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Create Character", callback_data='create_character')],
                [InlineKeyboardButton("Main Menu", callback_data='main_menu')]
            ])
            await safe_edit_message(
                update, 
                "You need to create a character first!",
                reply_markup=keyboard
            )
            return
        
        game_id = db.create_game(user_id)
        
        if game_id:
            await self.start_game(update, context, game_id)
        else:
            await safe_edit_message(
                update,
                "Error creating game. Please try again.",
                reply_markup=create_main_menu_keyboard()
            )
    
    async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: int):
        game = db.get_game(game_id)
        if not game:
            await safe_edit_message(
                update,
                "Game not found. Please try again.",
                reply_markup=create_main_menu_keyboard()
            )
            return
        
        player1 = db.get_player(game.player1_id)
        player2 = db.get_player(game.player2_id) if game.player2_id else None
        
        if not player2:
            player2 = Player(
                user_id=0,
                username="AI Opponent",
                gender=Gender.MALE,
                skin_tone=SkinTone.MEDIUM,
                body_style=BodyStyle.MIDDLEWEIGHT
            )
        
        try:
            game_image = ImageGenerator.generate_game_image(game, player1, player2)
        except ImageGeneratorError as e:
            logger.error(f"Error generating game image: {e}")
            await safe_edit_message(
                update,
                "Error starting game. Please try again.",
                reply_markup=create_main_menu_keyboard()
            )
            return
        
        keyboard = create_game_keyboard(game, game.player1_id)
        caption = f"Round {game.round_number} - Your HP: {game.player1_hp}"
        
        if update.callback_query and update.callback_query.message.photo:
            await update.callback_query.edit_message_media(
                media=InputMediaPhoto(game_image, caption=caption),
                reply_markup=keyboard
            )
        else:
            await update.callback_query.message.reply_photo(
                photo=game_image,
                caption=caption,
                reply_markup=keyboard
            )
    
    async def handle_slap(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data['user_id']
        data_parts = query.data.split('_')
        slap_count = int(data_parts[1])
        game_id = int(data_parts[2])
        
        game = db.get_game(game_id)
        if not game:
            await safe_edit_message(update, "Game not found.", reply_markup=create_main_menu_keyboard())
            return
        
        is_valid, error_msg = GameLogic.is_valid_move(game, user_id, ActionType.SLAP, slap_count)
        if not is_valid:
            await query.answer(error_msg, show_alert=True)
            return
        
        game = GameLogic.process_slap(game, user_id, slap_count)
        if not db.update_game(game):
            await query.answer("Error processing move. Please try again.", show_alert=True)
            return
        
        if not game.player2_id and game.current_turn == 0:
            await asyncio.sleep(2)
            game = GameLogic.make_ai_move(game)
            db.update_game(game)
        
        await self.update_game_interface(update, context, game)
    
    async def handle_guess(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data['user_id']
        data_parts = query.data.split('_')
        guess_count = int(data_parts[1])
        game_id = int(data_parts[2])
        
        game = db.get_game(game_id)
        if not game:
            await safe_edit_message(update, "Game not found.", reply_markup=create_main_menu_keyboard())
            return
        
        is_valid, error_msg = GameLogic.is_valid_move(game, user_id, ActionType.GUESS, guess_count)
        if not is_valid:
            await query.answer(error_msg, show_alert=True)
            return
        
        game = GameLogic.process_guess(game, user_id, guess_count)
        if not db.update_game(game):
            await query.answer("Error processing move. Please try again.", show_alert=True)
            return
        
        if game.state == GameState.GAME_END:
            await self.end_game(update, context, game)
            return
        
        if not game.player2_id and game.current_turn == 0:
            await asyncio.sleep(2)
            game = GameLogic.make_ai_move(game)
            db.update_game(game)
            
            if game.state == GameState.GAME_END:
                await self.end_game(update, context, game)
                return
        
        await self.update_game_interface(update, context, game)
    
    async def handle_club(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data['user_id']
        game_id = int(query.data.split('_')[1])
        
        game = db.get_game(game_id)
        if not game:
            await safe_edit_message(update, "Game not found.", reply_markup=create_main_menu_keyboard())
            return
        
        is_valid, error_msg = GameLogic.is_valid_move(game, user_id, ActionType.CLUB)
        if not is_valid:
            await query.answer(error_msg, show_alert=True)
            return
        
        game = GameLogic.process_club(game, user_id)
        if not db.update_game(game):
            await query.answer("Error processing move. Please try again.", show_alert=True)
            return
        
        if game.state == GameState.GAME_END:
            await self.end_game(update, context, game)
            return
        
        if not game.player2_id and game.current_turn == 0:
            await asyncio.sleep(2)
            game = GameLogic.make_ai_move(game)
            db.update_game(game)
            
            if game.state == GameState.GAME_END:
                await self.end_game(update, context, game)
                return
        
        await self.update_game_interface(update, context, game)
    
    async def handle_flinch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data['user_id']
        game_id = int(query.data.split('_')[1])
        
        game = db.get_game(game_id)
        if not game:
            await safe_edit_message(update, "Game not found.", reply_markup=create_main_menu_keyboard())
            return
        
        is_valid, error_msg = GameLogic.is_valid_move(game, user_id, ActionType.FLINCH)
        if not is_valid:
            await query.answer(error_msg, show_alert=True)
            return
        
        game = GameLogic.process_flinch(game, user_id)
        if not db.update_game(game):
            await query.answer("Error processing move. Please try again.", show_alert=True)
            return
        
        if game.state == GameState.GAME_END:
            await self.end_game(update, context, game)
            return
        
        if not game.player2_id and game.current_turn == 0:
            await asyncio.sleep(2)
            game = GameLogic.make_ai_move(game)
            db.update_game(game)
            
            if game.state == GameState.GAME_END:
                await self.end_game(update, context, game)
                return
        
        await self.update_game_interface(update, context, game)
    
    async def update_game_interface(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        user_id = context.user_data['user_id']
        
        player1 = db.get_player(game.player1_id)
        player2 = db.get_player(game.player2_id) if game.player2_id else None
        
        if not player2:
            player2 = Player(
                user_id=0,
                username="AI Opponent",
                gender=Gender.MALE,
                skin_tone=SkinTone.MEDIUM,
                body_style=BodyStyle.MIDDLEWEIGHT
            )
        
        try:
            game_image = ImageGenerator.generate_game_image(game, player1, player2)
        except ImageGeneratorError as e:
            logger.error(f"Error generating game image: {e}")
            await safe_edit_message(
                update,
                "Error updating game. Please try again.",
                reply_markup=create_main_menu_keyboard()
            )
            return
        
        keyboard = create_game_keyboard(game, user_id)
        player_hp = game.player1_hp if user_id == game.player1_id else game.player2_hp
        caption = f"Round {game.round_number} - Your HP: {player_hp}"
        
        if update.callback_query and update.callback_query.message.photo:
            await update.callback_query.edit_message_media(
                media=InputMediaPhoto(game_image, caption=caption),
                reply_markup=keyboard
            )
        else:
            await update.callback_query.message.reply_photo(
                photo=game_image,
                caption=caption,
                reply_markup=keyboard
            )
    
    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        winner_id, result_message = GameLogic.determine_winner(game)
        
        player1 = db.get_player(game.player1_id)
        player2 = db.get_player(game.player2_id) if game.player2_id else None
        
        if winner_id == game.player1_id:
            player1.wins += 1
            if player2:
                player2.losses += 1
        elif winner_id == game.player2_id:
            if player2:
                player2.wins += 1
            player1.losses += 1
        else:
            player1.losses += 0.5
            if player2:
                player2.losses += 0.5
        
        db.update_player(player1)
        if player2:
            db.update_player(player2)
        
        keyboard = create_main_menu_keyboard()
        
        player1 = db.get_player(game.player1_id)
        player2 = db.get_player(game.player2_id) if game.player2_id else None
        
        if not player2:
            player2 = Player(
                user_id=0,
                username="AI Opponent",
                gender=Gender.MALE,
                skin_tone=SkinTone.MEDIUM,
                body_style=BodyStyle.MIDDLEWEIGHT
            )
        
        try:
            game_image = ImageGenerator.generate_game_image(game, player1, player2)
        except ImageGeneratorError as e:
            logger.error(f"Error generating game image: {e}")
            await safe_edit_message(
                update,
                f"Game Over!\n{result_message}",
                reply_markup=keyboard
            )
            return
        
        if update.callback_query and update.callback_query.message.photo:
            await update.callback_query.edit_message_media(
                media=InputMediaPhoto(game_image, caption=f"Game Over!\n{result_message}"),
                reply_markup=keyboard
            )
        else:
            await update.callback_query.message.reply_photo(
                photo=game_image,
                caption=f"Game Over!\n{result_message}",
                reply_markup=keyboard
            )
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query:
            await query.answer()
        
        user_id = context.user_data['user_id']
        player = db.get_player(user_id)
        
        if not player:
            await safe_send_message(
                user_id, context,
                "You need to create a character first!",
                reply_markup=create_main_menu_keyboard()
            )
            return
        
        total_games = player.wins + player.losses
        win_rate = (player.wins / total_games * 100) if total_games > 0 else 0
        
        stats_text = (
            f"🏆 Your Stats 🏆\n\n"
            f"Wins: {player.wins}\n"
            f"Losses: {player.losses}\n"
            f"Win Rate: {win_rate:.1f}%\n\n"
            f"Keep slapping to improve your rank!"
        )
        
        keyboard = create_main_menu_keyboard()
        
        if query:
            await safe_edit_message(update, stats_text, reply_markup=keyboard)
        else:
            await safe_send_message(user_id, context, stats_text, reply_markup=keyboard)
    
    async def show_rankings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query:
            await query.answer()
        
        rankings = db.get_global_rankings(limit=10)
        
        if not rankings:
            rankings_text = "No rankings available yet. Be the first to play!"
        else:
            rankings_text = "🏆 Global Rankings 🏆\n\n"
            for i, player in enumerate(rankings, 1):
                total_games = player['wins'] + player['losses']
                win_rate = (player['wins'] / total_games * 100) if total_games > 0 else 0
                rankings_text += f"{i}. {player['username']} - {player['wins']} wins ({win_rate:.1f}%)\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Refresh", callback_data='rankings')],
            [InlineKeyboardButton("Main Menu", callback_data='main_menu')]
        ])
        
        if query:
            await safe_edit_message(update, rankings_text, reply_markup=keyboard)
        else:
            await safe_send_message(context.user_data['user_id'], context, rankings_text, reply_markup=keyboard)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "🤖 *Slap Fight Bot Help*\n\n"
            "/start - Open the main menu\n"
            "/help - Show this help message\n"
            "/about - About this bot\n\n"
            "Use the buttons to create your character, find fights, and check rankings."
        )
        if update.message:
            await update.message.reply_text(help_text, parse_mode="Markdown")
        else:
            await update.callback_query.edit_message_text(help_text, parse_mode="Markdown")
    
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        about_text = (
            "🤖 *Slap Fight Bot*\n"
            "Version: development build\n"
            "Find me at: t.me/Slap_Fight_Bot"
        )
        if update.message:
            await update.message.reply_text(about_text, parse_mode="Markdown")
        else:
            await update.callback_query.edit_message_text(about_text, parse_mode="Markdown")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.exception("Unhandled exception while handling update: %s", update)

def main():
    try:
        config.validate()
        
        token = os.getenv("BOT_TOKEN", "")
        if not token:
            raise RuntimeError("BOT_TOKEN is missing. Set it in .env or environment.")
        
        bot = SlapFightBot(token)
        logger.info("Starting slap fight bot...")
        bot.application.run_polling()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        exit(1)

if __name__ == "__main__":
    main()
