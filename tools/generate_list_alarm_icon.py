#!/usr/bin/env python3
"""Generate the Timer List alarm icon (a bold bell).

The Timer List draws this icon at the left of a row whose alarm is held
(src/timer_list.c, IMAGE_ICON_LIST_ALARM). The image is pure black on a
transparent background with hard edges, so it loads as a 1-bit palettized
bitmap on every platform and can be tinted to the row's text color.

Usage:
    python tools/generate_list_alarm_icon.py
"""

import os

from PIL import Image, ImageDraw

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "images")

SIZE = 28
SCALE = 8  # draw large, then reduce and threshold for clean hard edges


def create_bell_icon():
    big = SIZE * SCALE
    img = Image.new("L", (big, big), 0)
    draw = ImageDraw.Draw(img)

    def s(value):
        return int(round(value * SCALE))

    # Knob on top
    draw.ellipse([s(11.5), s(0.5), s(16.5), s(5.5)], fill=255)
    # Dome and body: a round top that widens to the rim
    draw.pieslice([s(5.5), s(3.0), s(22.5), s(20.0)], 180, 360, fill=255)
    draw.polygon([(s(5.5), s(11.5)), (s(22.5), s(11.5)), (s(24.5), s(20.5)),
                  (s(3.5), s(20.5))], fill=255)
    # Rim
    draw.rounded_rectangle([s(1.0), s(19.0), s(27.0), s(23.5)], radius=s(2.0), fill=255)
    # Clapper
    draw.ellipse([s(10.5), s(22.0), s(17.5), s(27.5)], fill=255)

    small = img.resize((SIZE, SIZE), Image.LANCZOS)
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for y in range(SIZE):
        for x in range(SIZE):
            # Mirror left and right so the reduced image is symmetric
            if max(small.getpixel((x, y)), small.getpixel((SIZE - 1 - x, y))) >= 128:
                out.putpixel((x, y), (0, 0, 0, 255))
    return out


def main():
    icon = create_bell_icon()
    for suffix in ("~bw", "~color"):
        path = os.path.join(RESOURCES_DIR, "icon_list_alarm{}.png".format(suffix))
        icon.save(path)
        print("  Created {} ({}x{})".format(path, SIZE, SIZE))


if __name__ == "__main__":
    main()
