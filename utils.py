import logging
import asyncio
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from models import Game, Player, GameState
from database import db
from game_logic import GameLogic
from image_generator import ImageGenerator

logger = logging.getLogger(__name__)

async def safe_send_message(chat_id: int, context, text: str, 
                           reply_markup: Optional[InlineKeyboardMarkup] = None, 
                           parse_mode: Optional[str] = None) -> bool:
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except TelegramError as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return False

async def safe_edit_message(update: Update, text: str, 
                           reply_markup: Optional[InlineKeyboardMarkup] = None, 
                           parse_mode: Optional[str] = None) -> bool:
    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except TelegramError as e:
        logger.error(f"Failed to edit message: {e}")
        return False

async def safe_send_photo(chat_id: int, context, photo: io.BytesIO, 
                         caption: Optional[str] = None,
                         reply_markup: Optional[InlineKeyboardMarkup] = None) -> bool:
    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            reply_markup=reply_markup
        )
        return True
    except TelegramError as e:
        logger.error(f"Failed to send photo to {chat_id}: {e}")
        return False

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🥊 Find Fight", callback_data='fight')],
        [InlineKeyboardButton("🧍 Create Character", callback_data='create_character')],
        [InlineKeyboardButton("🏆 Rankings", callback_data='rankings')],
        [InlineKeyboardButton("📊 My Stats", callback_data='stats')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_character_gender_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Male", callback_data='gender_male')],
        [InlineKeyboardButton("Female", callback_data='gender_female')],
        [InlineKeyboardButton("Back", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_skin_tone_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Light", callback_data='skin_light')],
        [InlineKeyboardButton("Medium", callback_data='skin_medium')],
        [InlineKeyboardButton("Dark", callback_data='skin_dark')],
        [InlineKeyboardButton("Back", callback_data='create_character')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_body_style_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Lightweight", callback_data='body_lightweight')],
        [InlineKeyboardButton("Middleweight", callback_data='body_middleweight')],
        [InlineKeyboardButton("Super Heavyweight", callback_data='body_super_heavyweight')],
        [InlineKeyboardButton("Back", callback_data='create_character')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_game_keyboard(game: Game, player_id: int) -> Optional[InlineKeyboardMarkup]:
    if game.state == GameState.GAME_END or game.state == GameState.TIMED_OUT:
        return None
    
    keyboard = []
    
    if game.current_turn == player_id:
        if game.state in [GameState.PLAYER1_CHOOSE_SLAP, GameState.PLAYER2_CHOOSE_SLAP]:
            keyboard.append([
                InlineKeyboardButton("Slap on 1", callback_data=f'slap_1_{game.game_id}'),
                InlineKeyboardButton("Slap on 2", callback_data=f'slap_2_{game.game_id}'),
                InlineKeyboardButton("Slap on 3", callback_data=f'slap_3_{game.game_id}')
            ])
            
            clubs_used = game.player1_clubs if player_id == game.player1_id else game.player2_clubs
            if clubs_used < 2:
                keyboard.append([InlineKeyboardButton("Use Club 🏒", callback_data=f'club_{game.game_id}')])
        
        elif game.state in [GameState.PLAYER1_GUESS, GameState.PLAYER2_GUESS]:
            keyboard.append([
                InlineKeyboardButton("Guess 1", callback_data=f'guess_1_{game.game_id}'),
                InlineKeyboardButton("Guess 2", callback_data=f'guess_2_{game.game_id}'),
                InlineKeyboardButton("Guess 3", callback_data=f'guess_3_{game.game_id}')
            ])
            
            flinches_used = game.player1_flinches if player_id == game.player1_id else game.player2_flinches
            if flinches_used < 2:
                keyboard.append([InlineKeyboardButton("Use Flinch 😬", callback_data=f'flinch_{game.game_id}')])
    
    keyboard.append([InlineKeyboardButton("Main Menu", callback_data='main_menu')])
    
    return InlineKeyboardMarkup(keyboard)

async def cleanup_timed_out_games(context):
    try:
        all_games = []
        for user_id in []:
            user_games = db.get_player_games(user_id, active_only=True)
            all_games.extend(user_games)
        
        for game in all_games:
            if GameLogic.check_game_timeout(game):
                game.state = GameState.TIMED_OUT
                db.update_game(game)
                
                player1 = db.get_player(game.player1_id)
                if player1:
                    await safe_send_message(
                        game.player1_id, context,
                        "Your game has timed out due to inactivity."
                    )
                
                if game.player2_id:
                    player2 = db.get_player(game.player2_id)
                    if player2:
                        await safe_send_message(
                            game.player2_id, context,
                            "Your game has timed out due to inactivity."
                        )
    
    except Exception as e:
        logger.error(f"Error in cleanup_timed_out_games: {e}")

async def notify_opponent(game: Game, context, message: str):
    if not game.player2_id:
        return
    
    opponent_id = game.player2_id if context.user_data['user_id'] == game.player1_id else game.player1_id
    opponent = db.get_player(opponent_id)
    
    if opponent:
        await safe_send_message(opponent_id, context, message)
        
        if game.current_turn == opponent_id:
            player = db.get_player(opponent_id)
            game_image = ImageGenerator.generate_game_image(game, 
                                                          db.get_player(game.player1_id), 
                                                          db.get_player(game.player2_id))
            keyboard = create_game_keyboard(game, opponent_id)
            
            await safe_send_photo(
                opponent_id, context, game_image,
                caption=f"Round {game.round_number} - Your HP: {game.player2_hp if opponent_id == game.player2_id else game.player1_hp}",
                reply_markup=keyboard
            )
