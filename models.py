# models.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import sqlite3
import time
from datetime import datetime

class GameState(Enum):
    WAITING = "waiting"
    PLAYER1_CHOOSE_SLAP = "player1_choose_slap"
    PLAYER2_GUESS = "player2_guess"
    PLAYER2_CHOOSE_SLAP = "player2_choose_slap"
    PLAYER1_GUESS = "player1_guess"
    ROUND_END = "round_end"
    GAME_END = "game_end"
    TIMED_OUT = "timed_out"

class Gender(Enum):
    MALE = "male"
    FEMALE = "female"

class SkinTone(Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    DARK = "dark"

class BodyStyle(Enum):
    LIGHTWEIGHT = "lightweight"
    MIDDLEWEIGHT = "middleweight"
    SUPER_HEAVYWEIGHT = "super_heavyweight"

@dataclass
class Player:
    user_id: int
    username: str
    gender: Optional[Gender] = None
    skin_tone: Optional[SkinTone] = None
    body_style: Optional[BodyStyle] = None
    selfie_image: Optional[bytes] = None
    wins: int = 0
    losses: int = 0
    created_at: float = time.time()
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "gender": self.gender.value if self.gender else None,
            "skin_tone": self.skin_tone.value if self.skin_tone else None,
            "body_style": self.body_style.value if self.body_style else None,
            "selfie_image": self.selfie_image,
            "wins": self.wins,
            "losses": self.losses,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            gender=Gender(data["gender"]) if data["gender"] else None,
            skin_tone=SkinTone(data["skin_tone"]) if data["skin_tone"] else None,
            body_style=BodyStyle(data["body_style"]) if data["body_style"] else None,
            selfie_image=data["selfie_image"],
            wins=data["wins"],
            losses=data["losses"],
            created_at=data["created_at"]
        )

@dataclass
class Game:
    game_id: int
    player1_id: int
    player2_id: Optional[int]
    player1_hp: int
    player2_hp: int
    player1_clubs: int
    player2_clubs: int
    player1_flinches: int
    player2_flinches: int
    current_turn: Optional[int]
    round_number: int
    state: GameState
    player1_slap: Optional[int] = None
    player2_slap: Optional[int] = None
    created_at: float = time.time()
    updated_at: float = time.time()
    
    def to_dict(self):
        return {
            "game_id": self.game_id,
            "player1_id": self.player1_id,
            "player2_id": self.player2_id,
            "player1_hp": self.player1_hp,
            "player2_hp": self.player2_hp,
            "player1_clubs": self.player1_clubs,
            "player2_clubs": self.player2_clubs,
            "player1_flinches": self.player1_flinches,
            "player2_flinches": self.player2_flinches,
            "current_turn": self.current_turn,
            "round_number": self.round_number,
            "state": self.state.value,
            "player1_slap": self.player1_slap,
            "player2_slap": self.player2_slap,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            game_id=data["game_id"],
            player1_id=data["player1_id"],
            player2_id=data["player2_id"],
            player1_hp=data["player1_hp"],
            player2_hp=data["player2_hp"],
            player1_clubs=data["player1_clubs"],
            player2_clubs=data["player2_clubs"],
            player1_flinches=data["player1_flinches"],
            player2_flinches=data["player2_flinches"],
            current_turn=data["current_turn"],
            round_number=data["round_number"],
            state=GameState(data["state"]),
            player1_slap=data["player1_slap"],
            player2_slap=data["player2_slap"],
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )
