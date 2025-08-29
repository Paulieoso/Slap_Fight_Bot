# game_logic.py
import logging
import random
from typing import Optional, Tuple, Dict, Any
from enum import Enum

from models import Game, GameState, Player
from config import config
from database import db

logger = logging.getLogger(__name__)

class ActionType(Enum):
    SLAP = "slap"
    GUESS = "guess"
    CLUB = "club"
    FLINCH = "flinch"

class GameLogic:
    @staticmethod
    def calculate_damage(slap_count: int, guess_count: int) -> Tuple[int, int]:
        """Calculate damage based on slap and guess counts"""
        difference = abs(slap_count - guess_count)
        
        if difference == 0:
            return 1, 1  # Both take 1 damage (taunt)
        elif difference == 1:
            return 2, 0  # Slappee takes 2 damage
        else:  # difference == 2
            return 3, 0  # Slappee takes 3 damage
    
    @staticmethod
    def is_valid_move(game: Game, player_id: int, action: ActionType, value: Optional[int] = None) -> Tuple[bool, str]:
        """Validate if a move is allowed in the current game state"""
        # Check if it's the player's turn
        if game.current_turn != player_id:
            return False, "It's not your turn!"
        
        # Check if player is in this game
        if player_id not in [game.player1_id, game.player2_id]:
            return False, "You're not in this game!"
        
        # State-specific validations
        if action == ActionType.CLUB:
            # Check if player can use club
            clubs_used = game.player1_clubs if player_id == game.player1_id else game.player2_clubs
            if clubs_used >= config.MAX_CLUBS:
                return False, "You've used all your clubs for this game!"
            
            # Can only use club when it's your turn to slap
            if game.state not in [GameState.PLAYER1_CHOOSE_SLAP, GameState.PLAYER2_CHOOSE_SLAP]:
                return False, "You can only use club when it's your turn to slap!"
        
        elif action == ActionType.FLINCH:
            # Check if player can use flinch
            flinches_used = game.player1_flinches if player_id == game.player1_id else game.player2_flinches
            if flinches_used >= config.MAX_FLINCHES:
                return False, "You've used all your flinches for this game!"
            
            # Can only use flinch when it's your turn to guess
            if game.state not in [GameState.PLAYER1_GUESS, GameState.PLAYER2_GUESS]:
                return False, "You can only use flinch when it's your turn to guess!"
        
        elif action == ActionType.SLAP:
            # Validate slap value
            if value not in [1, 2, 3]:
                return False, "Slap count must be 1, 2, or 3!"
            
            # Check if it's the right state for slapping
            if (player_id == game.player1_id and game.state != GameState.PLAYER1_CHOOSE_SLAP) or \
               (player_id == game.player2_id and game.state != GameState.PLAYER2_CHOOSE_SLAP):
                return False, "It's not your turn to slap!"
        
        elif action == ActionType.GUESS:
            # Validate guess value
            if value not in [1, 2, 3]:
                return False, "Guess must be 1, 2, or 3!"
            
            # Check if it's the right state for guessing
            if (player_id == game.player1_id and game.state != GameState.PLAYER1_GUESS) or \
               (player_id == game.player2_id and game.state != GameState.PLAYER2_GUESS):
                return False, "It's not your turn to guess!"
        
        return True, "Valid move"
    
    @staticmethod
    def process_slap(game: Game, player_id: int, slap_count: int) -> Game:
        """Process a slap action"""
        # Record the slap
        if player_id == game.player1_id:
            game.player1_slap = slap_count
            game.state = GameState.PLAYER2_GUESS
            game.current_turn = game.player2_id
        else:
            game.player2_slap = slap_count
            game.state = GameState.PLAYER1_GUESS
            game.current_turn = game.player1_id
        
        # Log the action
        db.add_game_action(game.game_id, game.round_number, player_id, 
                          ActionType.SLAP.value, slap_count=slap_count)
        
        return game
    
    @staticmethod
    def process_guess(game: Game, player_id: int, guess_count: int) -> Game:
        """Process a guess action and calculate damage"""
        # Determine who slapped and who guessed
        if player_id == game.player1_id:  # Player1 is guessing Player2's slap
            slap_count = game.player2_slap
            damage, counter_damage = GameLogic.calculate_damage(slap_count, guess_count)
            
            # Apply damage
            game.player1_hp -= counter_damage  # Counter damage from taunt
            game.player2_hp -= damage
        else:  # Player2 is guessing Player1's slap
            slap_count = game.player1_slap
            damage, counter_damage = GameLogic.calculate_damage(slap_count, guess_count)
            
            # Apply damage
            game.player2_hp -= counter_damage  # Counter damage from taunt
            game.player1_hp -= damage
        
        # Log the action
        db.add_game_action(game.game_id, game.round_number, player_id, 
                          ActionType.GUESS.value, guess_count=guess_count, damage=damage)
        
        if counter_damage > 0:
            # Also log the counter damage
            slapper_id = game.player2_id if player_id == game.player1_id else game.player1_id
            db.add_game_action(game.game_id, game.round_number, slapper_id, 
                              "counter_damage", damage=counter_damage)
        
        # Check if game is over
        if game.player1_hp <= 0 or game.player2_hp <= 0 or game.round_number >= config.TOTAL_ROUNDS:
            game.state = GameState.GAME_END
        else:
            # Move to next round
            game.round_number += 1
            game.player1_slap = None
            game.player2_slap = None
            
            # Alternate who starts the round
            if game.round_number % 2 == 1:  # Odd rounds: player1 starts
                game.state = GameState.PLAYER1_CHOOSE_SLAP
                game.current_turn = game.player1_id
            else:  # Even rounds: player2 starts
                game.state = GameState.PLAYER2_CHOOSE_SLAP
                game.current_turn = game.player2_id
        
        return game
    
    @staticmethod
    def process_club(game: Game, player_id: int) -> Game:
        """Process a club action"""
        damage = config.CLUB_DAMAGE
        
        if player_id == game.player1_id:
            game.player1_clubs += 1
            game.player2_hp -= damage
            game.current_turn = game.player2_id
            game.state = GameState.PLAYER2_CHOOSE_SLAP
        else:
            game.player2_clubs += 1
            game.player1_hp -= damage
            game.current_turn = game.player1_id
            game.state = GameState.PLAYER1_CHOOSE_SLAP
        
        # Log the action
        db.add_game_action(game.game_id, game.round_number, player_id, 
                          ActionType.CLUB.value, damage=damage)
        
        # Check if game is over
        if game.player1_hp <= 0 or game.player2_hp <= 0:
            game.state = GameState.GAME_END
        
        return game
    
    @staticmethod
    def process_flinch(game: Game, player_id: int) -> Game:
        """Process a flinch action"""
        damage = config.FLINCH_DAMAGE
        
        if player_id == game.player1_id:
            game.player1_flinches += 1
            game.player2_hp -= damage
            game.current_turn = game.player2_id
            game.state = GameState.PLAYER2_CHOOSE_SLAP
        else:
            game.player2_flinches += 1
            game.player1_hp -= damage
            game.current_turn = game.player1_id
            game.state = GameState.PLAYER1_CHOOSE_SLAP
        
        # Log the action
        db.add_game_action(game.game_id, game.round_number, player_id, 
                          ActionType.FLINCH.value, damage=damage)
        
        # Check if game is over
        if game.player1_hp <= 0 or game.player2_hp <= 0:
            game.state = GameState.GAME_END
        
        return game
    
    @staticmethod
    def determine_winner(game: Game) -> Tuple[Optional[int], str]:
        """Determine the winner of a completed game"""
        if game.state != GameState.GAME_END:
            return None, "Game is not over yet"
        
        if game.player1_hp <= 0 and game.player2_hp <= 0:
            return None, "It's a draw!"
        elif game.player1_hp <= 0:
            return game.player2_id, f"Player {game.player2_id} wins!"
        elif game.player2_hp <= 0:
            return game.player1_id, f"Player {game.player1_id} wins!"
        else:  # Round limit reached
            if game.player1_hp > game.player2_hp:
                return game.player1_id, f"Player {game.player1_id} wins by HP!"
            elif game.player2_hp > game.player1_hp:
                return game.player2_id, f"Player {game.player2_id} wins by HP!"
            else:
                return None, "It's a draw!"
    
    @staticmethod
    def make_ai_move(game: Game) -> Game:
        """Make a move for an AI opponent"""
        if not game.player2_id:  # Only AI games have no player2_id
            return game
        
        # Simple AI strategy
        if game.state == GameState.PLAYER2_CHOOSE_SLAP:
            # Decide whether to use club or slap
            if game.player2_clubs < config.MAX_CLUBS and random.random() < 0.2:
                game = GameLogic.process_club(game, game.player2_id)
            else:
                slap_count = random.randint(1, 3)
                game = GameLogic.process_slap(game, game.player2_id, slap_count)
        
        elif game.state == GameState.PLAYER2_GUESS:
            # Decide whether to use flinch or guess
            if game.player2_flinches < config.MAX_FLINCHES and random.random() < 0.2:
                game = GameLogic.process_flinch(game, game.player2_id)
            else:
                guess_count = random.randint(1, 3)
                game = GameLogic.process_guess(game, game.player2_id, guess_count)
        
        return game
    
    @staticmethod
    def check_game_timeout(game: Game) -> bool:
        """Check if a game has timed out due to inactivity"""
        current_time = time.time()
        return (current_time - game.updated_at) > config.GAME_TIMEOUT
