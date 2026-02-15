import os
import json
from PIL import Image, ImageDraw, ImageFilter, ImageFont
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
        text_colors = {int(k): tuple(v) for k, v in CONFIG["tile_name_colors"].items()}
        pointvalue_coords = {int(k): v for k, v in CONFIG["pointvalue_coords"].items()}

        TEXT_BOX_WIDTH = CONFIG["text_box_width"]
        base_font_size = CONFIG["base_font_size"]
        smaller_font_size = CONFIG["smaller_font_size"]
        thumbnail_size = tuple(CONFIG["thumbnail_size"])
        line_spacing = CONFIG["line_spacing"]
        title_stroke_width = 4
        body_stroke_width = 2
        stroke_color = (0, 0, 0)
        thumbnail_outline_color = (0, 0, 0, 0)
        thumbnail_outline_width = 3
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

                slot_x, slot_y = image_coords[i]
                centered_x = slot_x + (thumbnail_size[0] - tile_img.width) // 2
                centered_y = slot_y + (thumbnail_size[1] - tile_img.height) // 2

                tile_rgba = tile_img.convert("RGBA")
                alpha_mask = tile_rgba.getchannel("A")

                effect_padding = thumbnail_outline_width + 2
                alpha_canvas = Image.new(
                    "L",
                    (
                        tile_rgba.width + (effect_padding * 2),
                        tile_rgba.height + (effect_padding * 2),
                    ),
                    0,
                )
                alpha_canvas.paste(alpha_mask, (effect_padding, effect_padding))

                expanded_alpha = alpha_canvas.filter(
                    ImageFilter.MaxFilter((thumbnail_outline_width * 2) + 1)
                )
                outline_layer = Image.new(
                    "RGBA", alpha_canvas.size, thumbnail_outline_color
                )
                outline_layer.putalpha(expanded_alpha)
                base_img.paste(
                    outline_layer,
                    (centered_x - effect_padding, centered_y - effect_padding),
                    outline_layer,
                )

                base_img.paste(
                    tile_rgba,
                    (centered_x, centered_y),
                    tile_rgba,
                )

                draw.text(
                    (tilename_coords[i][0], tilename_coords[i][1]),
                    tile.get("tile_name", "Unknown Tile Name"),
                    font=header_font,
                    fill=(text_colors[i]),
                    stroke_width=title_stroke_width,
                    stroke_fill=stroke_color,
                )

                # pointvalue_coords
                draw.text(
                    (pointvalue_coords[i][0], pointvalue_coords[i][1]),
                    f"+{pointvalue_coords[i][2]}",
                    font=header_font,
                    fill=(text_colors[i]),
                    stroke_width=title_stroke_width,
                    stroke_fill=stroke_color,
                )

                description = tile.get("description", "")

                # Empty description fix for when it's "" empty string
                if not description:
                    description = "No description provided."

                wrapped_lines = wrap_text(
                    description, smaller_font, TEXT_BOX_WIDTH, draw
                )

                y_offset = tilename_coords[i][1] + base_font_size + line_spacing
                for line in wrapped_lines:
                    draw.text(
                        (tilename_coords[i][0], y_offset),
                        line,
                        font=smaller_font,
                        fill=(255, 255, 255),
                        stroke_width=body_stroke_width,
                        stroke_fill=stroke_color,
                    )
                    y_offset += smaller_font_size + line_spacing

            base_img = base_img.convert("RGBA")
            img_io = BytesIO()
            base_img.save(img_io, "PNG")
            img_io.seek(0)
            return img_io
    except Exception as e:
        print(f"Error generating image: line number {e.__traceback__.tb_lineno} {e}")
