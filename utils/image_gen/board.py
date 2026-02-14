import os
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64
from utils.image_gen.wrap_text import wrap_text

FONT_PATH = os.path.join(os.path.dirname(__file__), "Skranji-Regular.ttf")
FONT_PATH = os.path.abspath(FONT_PATH)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "board_config.json")
CONFIG_PATH = os.path.abspath(CONFIG_PATH)


def generate_image(board):
    try:
        # Load config from file each time
        with open(CONFIG_PATH, "r") as f:
            CONFIG = json.load(f)

        # Load config values
        image_coords = {int(k): v for k, v in CONFIG["image_coords"].items()}
        tilename_coords = {int(k): v for k, v in CONFIG["tilename_coords"].items()}
        TEXT_BOX_WIDTH = CONFIG["text_box_width"]
        base_font_size = CONFIG["base_font_size"]
        smaller_font_size = CONFIG["smaller_font_size"]
        thumbnail_size = tuple(CONFIG["thumbnail_size"])
        line_spacing = CONFIG["line_spacing"]
        background_filepath = os.path.join(os.path.dirname(__file__), "sample-bg.png")
        background_filepath = os.path.abspath(background_filepath)
        with Image.open(background_filepath) as base_img:
            draw = ImageDraw.Draw(base_img)
            header_font = ImageFont.truetype(FONT_PATH, size=base_font_size)
            smaller_font = ImageFont.truetype(FONT_PATH, size=smaller_font_size)
            for i, tile in enumerate(board):
                img_base64 = tile["image_data"]
                img_data = base64.b64decode(img_base64)
                tile_img = Image.open(BytesIO(img_data))
                tile_img.thumbnail(thumbnail_size, Image.LANCZOS)
                base_img.paste(
                    tile_img,
                    (image_coords[i][0], image_coords[i][1]),
                    tile_img if tile_img.mode == "RGBA" else None,
                )

                draw.text(
                    (tilename_coords[i][0], tilename_coords[i][1]),
                    tile.get("tile_name", "Unknown Tile Name"),
                    font=header_font,
                    fill=(0, 0, 0),
                )

                description = tile.get("description", "")

                # Empty description fix for when it's "" empty string
                if not description:
                    description = "No description provided."
                
                wrapped_lines = wrap_text(
                    description, smaller_font, TEXT_BOX_WIDTH, draw
                )

                y_offset = tilename_coords[i][1] + base_font_size
                for line in wrapped_lines:
                    draw.text(
                        (tilename_coords[i][0], y_offset),
                        line,
                        font=smaller_font,
                        fill=(50, 50, 50),
                    )
                    y_offset += smaller_font_size + line_spacing

            base_img = base_img.convert("RGBA")
            img_io = BytesIO()
            base_img.save(img_io, "PNG")
            img_io.seek(0)
            print(img_io)
            return img_io
    except Exception as e:
        print(f"Error generating image: line number {e.__traceback__.tb_lineno} {e}")
