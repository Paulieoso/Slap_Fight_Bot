import logging
import io
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps

from models import Player, Game
from config import config

logger = logging.getLogger(__name__)

class ImageGeneratorError(Exception):
    pass

class ImageGenerator:
    SKIN_TONE_COLORS = {
        "light": (255, 220, 177),
        "medium": (210, 170, 130),
        "dark": (140, 100, 70)
    }
    
    BODY_SIZES = {
        "lightweight": (0.8, 0.8),
        "middleweight": (1.0, 1.0),
        "super_heavyweight": (1.3, 1.2)
    }
    
    @staticmethod
    def generate_character_image(player: Player) -> Optional[io.BytesIO]:
        try:
            gender_prefix = "m" if player.gender and player.gender.value == "male" else "f"
            body_style = player.body_style.value if player.body_style else "middleweight"
            
            try:
                body_path = f"assets/bodies/{gender_prefix}_{body_style}.png"
                body_img = Image.open(body_path).convert("RGBA")
            except Exception:
                body_img = Image.new("RGBA", (200, 400), (240, 240, 240, 255))
                draw = ImageDraw.Draw(body_img)
                draw.text((10, 10), f"{gender_prefix} {body_style}", fill=(0, 0, 0, 255))
            
            if player.skin_tone:
                skin_color = ImageGenerator.SKIN_TONE_COLORS.get(player.skin_tone.value, (255, 220, 177))
                body_img = ImageGenerator.recolor_image(body_img, (255, 255, 255), skin_color)
            
            size_factor = ImageGenerator.BODY_SIZES.get(body_style, (1.0, 1.0))
            new_size = (int(body_img.width * size_factor[0]), int(body_img.height * size_factor[1]))
            body_img = body_img.resize(new_size, Image.Resampling.LANCZOS)
            
            if player.selfie_image:
                try:
                    selfie_img = Image.open(io.BytesIO(player.selfie_image)).convert("RGBA")
                    selfie_img = selfie_img.resize((80, 80), Image.Resampling.LANCZOS)
                    
                    face_x, face_y = 50, 30
                    if body_style == "lightweight":
                        face_x, face_y = 45, 25
                    elif body_style == "super_heavyweight":
                        face_x, face_y = 55, 35
                    
                    body_img.paste(selfie_img, (face_x, face_y), selfie_img)
                except Exception as e:
                    logger.warning(f"Failed to add selfie to character: {e}")
            
            img_byte_arr = io.BytesIO()
            body_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            return img_byte_arr
        
        except Exception as e:
            logger.error(f"Error generating character image: {e}")
            raise ImageGeneratorError(f"Failed to generate character image: {e}")
    
    @staticmethod
    def generate_game_image(game: Game, player1: Player, player2: Player) -> Optional[io.BytesIO]:
        try:
            try:
                bg_img = Image.open("assets/backgrounds/arena.png").convert("RGBA")
            except Exception:
                bg_img = Image.new("RGBA", (800, 400), (100, 100, 255, 255))
                draw = ImageDraw.Draw(bg_img)
                draw.text((350, 180), "ARENA", fill=(255, 255, 255, 255))
            
            player1_img = Image.open(ImageGenerator.generate_character_image(player1))
            player2_img = Image.open(ImageGenerator.generate_character_image(player2))
            
            player2_img = ImageOps.mirror(player2_img)
            
            player1_x, player1_y = 100, 200
            player2_x, player2_y = 500, 200
            
            if player1.body_style and player1.body_style.value == "super_heavyweight":
                player1_y -= 20
            if player2.body_style and player2.body_style.value == "super_heavyweight":
                player2_y -= 20
            
            bg_img.paste(player1_img, (player1_x, player1_y), player1_img)
            bg_img.paste(player2_img, (player2_x, player2_y), player2_img)
            
            draw = ImageDraw.Draw(bg_img)
            
            hp_width = 200
            hp_height = 20
            hp_x1, hp_y1 = 50, 150
            hp_x2, hp_y2 = hp_x1 + hp_width, hp_y1 + hp_height
            
            draw.rectangle([hp_x1, hp_y1, hp_x2, hp_y2], fill=(100, 100, 100))
            
            hp_percent = max(0, game.player1_hp) / config.MAX_HP
            current_width = int(hp_width * hp_percent)
            draw.rectangle([hp_x1, hp_y1, hp_x1 + current_width, hp_y2], fill="green")
            
            draw.rectangle([hp_x1, hp_y1, hp_x2, hp_y2], outline=(0, 0, 0), width=2)
            
            hp2_x1, hp2_y1 = bg_img.width - 50 - hp_width, 150
            hp2_x2, hp2_y2 = hp2_x1 + hp_width, hp2_y1 + hp_height
            
            draw.rectangle([hp2_x1, hp2_y1, hp2_x2, hp2_y2], fill=(100, 100, 100))
            
            hp_percent = max(0, game.player2_hp) / config.MAX_HP
            current_width = int(hp_width * hp_percent)
            draw.rectangle([hp2_x2 - current_width, hp2_y1, hp2_x2, hp2_y2], fill="green")
            
            draw.rectangle([hp2_x1, hp2_y1, hp2_x2, hp2_y2], outline=(0, 0, 0), width=2)
            
            try:
                font = ImageFont.truetype("assets/fonts/ComicNeue-Bold.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            draw.text((bg_img.width // 2 - 30, 50), f"Round {game.round_number}", 
                     fill=(0, 0, 0), font=font)
            
            p1_name = player1.username[:15] + "..." if len(player1.username) > 15 else player1.username
            p2_name = player2.username[:15] + "..." if len(player2.username) > 15 else player2.username
            
            draw.text((hp_x1, hp_y1 - 25), p1_name, fill=(0, 0, 0), font=font)
            name_width = draw.textlength(p2_name, font=font)
            draw.text((hp2_x2 - name_width, hp2_y1 - 25), p2_name, fill=(0, 0, 0), font=font)
            
            img_byte_arr = io.BytesIO()
            bg_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            return img_byte_arr
        
        except Exception as e:
            logger.error(f"Error generating game image: {e}")
            raise ImageGeneratorError(f"Failed to generate game image: {e}")
    
    @staticmethod
    def recolor_image(image: Image.Image, target_color: Tuple[int, int, int], 
                     replacement_color: Tuple[int, int, int]) -> Image.Image:
        data = image.getdata()
        new_data = []
        
        for item in data:
            if all(abs(item[i] - target_color[i]) < 30 for i in range(3)):
                new_data.append(replacement_color + (item[3],))
            else:
                new_data.append(item)
        
        image.putdata(new_data)
        return image
