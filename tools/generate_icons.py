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


def create_direction_icon(filename, size=25):
    """Create a direction toggle icon (Uno reverse style circular arrows)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 4 if size > 20 else 2

    # Bounding box for the main arcs
    bbox = [margin, margin, size - margin - 1, size - margin - 1]

    # Center y coordinate for arrow heads
    cy = (bbox[1] + bbox[3]) / 2

    color = (255, 255, 255, 255)
    width = 2

    # Draw arcs
    # Top arc from ~left (but higher) to right
    draw.arc(bbox, start=200, end=360, fill=color, width=width)

    # Bottom arc from ~right (but lower) to left
    draw.arc(bbox, start=20, end=180, fill=color, width=width)

    # Arrow heads
    # Right side: tip pointing down from the end of the top arc
    head_size = 4 if size > 20 else 2
    right_x = bbox[2]
    # Arc ends exactly at y = cy
    draw.polygon(
        [
            (right_x - head_size, cy),
            (right_x + head_size, cy),
            (right_x, cy + head_size + 1),
        ],
        fill=color,
    )

    # Left side: tip pointing up from the end of the bottom arc
    left_x = bbox[0]
    draw.polygon(
        [
            (left_x - head_size, cy),
            (left_x + head_size, cy),
            (left_x, cy - head_size - 1),
        ],
        fill=color,
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
    create_text_icon("icon_plus_30sec.png", "+30")
    create_text_icon("icon_plus_20sec.png", "+20")
    create_text_icon("icon_plus_5sec.png", "+5", size=15, bg_color=(0, 0, 0, 255))
    create_text_icon("icon_plus_1sec.png", "+1s")

    # ControlModeEditSec minus icons (25x25 unless specified)
    create_text_icon("icon_minus_30sec.png", "-30")
    create_text_icon("icon_minus_20sec.png", "-20")
    create_text_icon("icon_minus_5sec.png", "-5", size=15, bg_color=(0, 0, 0, 255))
    create_text_icon("icon_minus_1sec.png", "-1s")

    # Counting mode icons (25x25)
    create_text_icon("icon_edit.png", "Edt")
    create_bg_icon("icon_bg.png")
    create_dots_icon("icon_details.png")

    # Long press icons (15x15)
    create_text_icon("icon_rep_en.png", "Rep", size=15)
    create_text_icon("icon_reset.png", "Rst", size=15)
    create_x_icon("icon_quit.png", size=15)

    # EditRepeat icons (25x25)
    create_text_icon("icon_plus_20_rep.png", "+20")
    create_text_icon("icon_plus_5_rep.png", "+5")
    create_text_icon("icon_plus_1_rep.png", "+1")
    create_text_icon("icon_rst_cnt.png", "0")

    # EditRepeat minus icons (25x25)
    create_text_icon("icon_minus_20_rep.png", "-20")
    create_text_icon("icon_minus_5_rep.png", "-5")
    create_text_icon("icon_minus_1_rep.png", "-1")

    # Direction toggle icon (15x15)
    create_direction_icon("icon_direction.png", size=15)

    print("\nDone! All icons generated.")


if __name__ == "__main__":
    main()
