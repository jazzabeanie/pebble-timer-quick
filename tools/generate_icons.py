#!/usr/bin/env python3
"""Generate placeholder button icon assets for the Pebble timer app.

Creates simple white text/symbol icons on transparent backgrounds.
Standard icons are 25x25, small icons are 15x15.

Usage:
    python tools/generate_icons.py
"""

from PIL import Image, ImageDraw, ImageFont
import os

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "images")


def create_text_icon(filename, text, size=25, bg_color=(0, 0, 0, 0)):
    """Create an icon with white text on specified background."""
    img = Image.new("RGBA", (size, size), bg_color)
    draw = ImageDraw.Draw(img)

    # Use a simple built-in font. Pebble icons are tiny so we use small text.
    try:
        if size <= 15:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9
            )
        else:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11
            )
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]

    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    filepath = os.path.join(RESOURCES_DIR, filename)
    img.save(filepath)
    print(f"  Created {filepath} ({size}x{size})")


def create_x_icon(filename, size=25):
    """Create an X (quit) icon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 5 if size == 25 else 3
    draw.line(
        [(margin, margin), (size - margin - 1, size - margin - 1)],
        fill=(255, 255, 255, 255),
        width=2,
    )
    draw.line(
        [(size - margin - 1, margin), (margin, size - margin - 1)],
        fill=(255, 255, 255, 255),
        width=2,
    )
    filepath = os.path.join(RESOURCES_DIR, filename)
    img.save(filepath)
    print(f"  Created {filepath} ({size}x{size})")


def create_dots_icon(filename, size=25):
    """Create a details/ellipsis icon (...)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    mid_y = size // 2
    dot_r = 2
    for x_off in [-6, 0, 6]:
        cx = size // 2 + x_off
        draw.ellipse(
            [(cx - dot_r, mid_y - dot_r), (cx + dot_r, mid_y + dot_r)],
            fill=(255, 255, 255, 255),
        )
    filepath = os.path.join(RESOURCES_DIR, filename)
    img.save(filepath)
    print(f"  Created {filepath} ({size}x{size})")


def create_bg_icon(filename, size=25):
    """Create a background/exit icon (BG text with arrow)."""
    create_text_icon(filename, "BG", size)


def create_ms_icon(filename, bold_char, size=25):
    """Create an m/s mode-indicator icon.

    The active character (bold_char = 'm' or 's') is drawn in white; the
    inactive character and slash are drawn in a dim grey so both are readable
    but one reads as selected.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = 9
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
        )
    except (OSError, IOError):
        font = ImageFont.load_default()

    active_color = (255, 255, 255, 255)
    inactive_color = (160, 160, 160, 255)

    m_color = active_color if bold_char == "m" else inactive_color
    s_color = active_color if bold_char == "s" else inactive_color
    slash_color = inactive_color

    # Measure each character to lay them out side-by-side
    def char_w(ch):
        bb = draw.textbbox((0, 0), ch, font=font)
        return bb[2] - bb[0], bb[0]

    m_w, m_ox = char_w("m")
    sl_w, sl_ox = char_w("/")
    s_w, s_ox = char_w("s")
    total_w = m_w + sl_w + s_w

    # Vertical centre using 'm' as reference height
    bb = draw.textbbox((0, 0), "m", font=font)
    text_h = bb[3] - bb[1]
    y = (size - text_h) // 2 - bb[1]

    x = (size - total_w) // 2
    draw.text((x - m_ox, y), "m", fill=m_color, font=font)
    x += m_w
    draw.text((x - sl_ox, y), "/", fill=slash_color, font=font)
    x += sl_w
    draw.text((x - s_ox, y), "s", fill=s_color, font=font)

    filepath = os.path.join(RESOURCES_DIR, filename)
    img.save(filepath)
    print(f"  Created {filepath} ({size}x{size})")


def main():
    os.makedirs(RESOURCES_DIR, exist_ok=True)

    print("Generating button icon assets...")

    # ControlModeNew icons (25x25)
    create_text_icon("icon_plus_1hr.png", "+1h")
    create_text_icon("icon_plus_20min.png", "+20")
    # Small icons need black background to be visible on white center circle
    create_text_icon("icon_plus_5min.png", "+5", size=15, bg_color=(0, 0, 0, 255))
    create_text_icon("icon_plus_1min.png", "+1m")

    # ControlModeNew minus icons (25x25 unless specified)
    create_text_icon("icon_minus_1hr.png", "-1h")
    create_text_icon("icon_minus_20min.png", "-20")
    create_text_icon("icon_minus_5min.png", "-5", size=15, bg_color=(0, 0, 0, 255))
    create_text_icon("icon_minus_1min.png", "-1m")

    # ControlModeEditSec icons (25x25)
    create_text_icon("icon_plus_60sec.png", "+60")
    create_text_icon("icon_plus_30sec.png", "+30")
    create_text_icon("icon_plus_20sec.png", "+20")
    create_text_icon("icon_plus_5sec.png", "+5", size=15, bg_color=(0, 0, 0, 255))
    create_text_icon("icon_plus_1sec.png", "+1s")

    # ControlModeEditSec minus icons (25x25 unless specified)
    create_text_icon("icon_minus_60sec.png", "-60")
    create_text_icon("icon_minus_30sec.png", "-30")
    create_text_icon("icon_minus_20sec.png", "-20")
    create_text_icon("icon_minus_5sec.png", "-5", size=15, bg_color=(0, 0, 0, 255))
    create_text_icon("icon_minus_1sec.png", "-1s")

    # Counting mode icons (25x25)
    # create_text_icon("icon_edit.png", "e")  #TODO: this could be used, but would need font size increase

    # Long press icons (15x15)
    # create_text_icon("icon_rep_en.png", "Rep", size=15)
    # create_text_icon("icon_reset.png", "Rst", size=15)

    # EditRepeat icons (25x25)
    create_text_icon("icon_plus_20_rep.png", "+20")
    create_text_icon("icon_plus_5_rep.png", "+5", size=15, bg_color=(0, 0, 0, 255))
    create_text_icon("icon_plus_1_rep.png", "+1")
    create_text_icon("icon_rst_cnt.png", "0")

    # EditRepeat minus icons (25x25)
    create_text_icon("icon_minus_20_rep.png", "-20")
    create_text_icon("icon_minus_5_rep.png", "-5")
    create_text_icon("icon_minus_1_rep.png", "-1")

    # Mode-indicator icons for swap-back-select feature
    create_ms_icon("icon_edit_min.png", "m")
    create_ms_icon("icon_edit_sec.png", "s")

    print("\nDone! All icons generated.")


if __name__ == "__main__":
    main()
