"""
Asset checks for the app's launcher menu icon.

`appinfo.json` declares images/timer_icon.png as IMAGE_ICON with "menuIcon": true.
The launcher draws menu icons as-is - it does not recolour them - so artwork made
entirely of white pixels disappears against the launcher's light unselected rows
and is only visible on the highlighted row. That is exactly the bug these checks
guard against.

These are pure file inspections: no emulator, no `platform` fixture (taking one
would parametrize them across every platform for no benefit).
"""

import os

import pytest
from PIL import Image

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ICONS = {
    "color": os.path.join(REPO_ROOT, "resources", "images", "timer_icon~color.png"),
    "bw": os.path.join(REPO_ROOT, "resources", "images", "timer_icon~bw.png"),
}

# A pixel counts as part of the artwork if it is at least half opaque, and as
# "dark" if its luminance is at or below mid-grey.
ALPHA_THRESHOLD = 128
LUMINANCE_THRESHOLD = 128
# The glyph is a line drawing, so only a minority of the opaque pixels are ink.
# 25% is well above what antialiasing alone contributes and far below the ~34%
# the corrected artwork actually reaches.
MIN_DARK_SHARE = 0.25


def _pixels(path):
    with Image.open(path) as img:
        return list(img.convert("RGBA").getdata())


def _luminance(pixel):
    r, g, b, _a = pixel
    return 0.299 * r + 0.587 * g + 0.114 * b


@pytest.mark.parametrize("variant", sorted(ICONS))
def test_menu_icon_artwork_is_not_uniformly_light(variant):
    """Opaque artwork must not be all near-white, or it vanishes on light rows."""
    pixels = _pixels(ICONS[variant])
    opaque = [p for p in pixels if p[3] >= ALPHA_THRESHOLD]
    assert opaque, f"{variant} icon has no opaque pixels at all"

    dark = [p for p in opaque if _luminance(p) <= LUMINANCE_THRESHOLD]
    share = len(dark) / len(opaque)
    assert share >= MIN_DARK_SHARE, (
        f"{variant} menu icon is {share:.0%} dark ({len(dark)}/{len(opaque)} opaque "
        f"pixels); below {MIN_DARK_SHARE:.0%} it reads as invisible against the "
        f"launcher's light unselected rows"
    )


@pytest.mark.parametrize("variant", sorted(ICONS))
def test_menu_icon_has_transparent_background(variant):
    """A fully opaque icon paints a solid rectangle over the launcher row."""
    pixels = _pixels(ICONS[variant])
    transparent = [p for p in pixels if p[3] < ALPHA_THRESHOLD]
    assert transparent, (
        f"{variant} menu icon has no transparent pixels; it will paint a solid "
        f"background block onto the launcher row instead of compositing"
    )


@pytest.mark.parametrize("variant", sorted(ICONS))
def test_menu_icon_is_25x25(variant):
    """Pebble menu icons are 25x25; regenerating the artwork must preserve that."""
    with Image.open(ICONS[variant]) as img:
        assert img.size == (25, 25), f"{variant} menu icon is {img.size}, expected (25, 25)"
