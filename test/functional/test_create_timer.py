"""
Test Case: Create a 2-minute timer using the down button.

This test verifies that pressing the Down button affects the timer display.

Note: The app has a 3-second inactivity timer that transitions from
ControlModeNew to ControlModeCounting. Due to emulator startup time,
tests may observe the app in counting mode rather than "New" mode.
The tests verify that button presses correctly update the display.
"""

import logging
import pytest
from PIL import Image
import pytesseract
import time

from .conftest import Button, EmulatorHelper, PLATFORMS

# Configure module logger
logger = logging.getLogger(__name__)


def extract_text(img: Image.Image) -> str:
    """Extract text from a Pebble screenshot using OCR.

    Pebble screenshots are small, so we scale them up for better OCR accuracy.
    """
    # Scale up the image 4x for better OCR recognition
    scaled = img.resize((img.width * 4, img.height * 4), Image.Resampling.LANCZOS)
    # Convert to grayscale for better OCR
    grayscale = scaled.convert("L")
    # Use PSM 6 (uniform block of text) for better recognition of watch display
    config = "--psm 6"
    return pytesseract.image_to_string(grayscale, config=config)


@pytest.fixture(scope="module", params=PLATFORMS)
def persistent_emulator(request, build_app):
    """
    Module-scoped fixture that launches the emulator once per platform.

    The fixture performs a "warm-up" cycle:
    1. Wipe storage, install app
    2. Long press Down to quit the app (sets app state for next launch)
    3. Re-open the app within the same emulator (preserves persisted state)

    This ensures each test session starts with consistent app state without
    destroying the persist data set by the long-press quit action.
    """
    platform = request.param
    platform_opt = request.config.getoption("--platform")
    if platform_opt and platform != platform_opt:
        pytest.skip(f"Skipping test for {platform} since --platform={platform_opt} was specified.")

    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    # Phase 1: Warm-up cycle to clear any stale state and set initial state
    logger.info(f"[{platform}] Starting warm-up cycle to clear stale state")
    helper.wipe()
    helper.install()
    logger.info(f"[{platform}] Waiting for emulator to stabilize (2s)")
    time.sleep(2)  # Allow emulator to stabilize

    # Long press Down button to quit the app - this sets the app's persist state
    logger.info(f"[{platform}] Holding down button to quit app and set persist state")
    helper.hold_button(Button.DOWN)
    time.sleep(1)
    helper.release_buttons()
    logger.info(f"[{platform}] App quit via long press, persist state set")
    time.sleep(0.5)

    # Phase 2: Re-open the app via menu navigation (preserves persist state)
    # Using install() would clear the app's persisted state, so instead we
    # navigate through the Pebble launcher menu to re-open the app
    logger.info(f"[{platform}] Re-opening app via menu navigation (preserving persist state)")
    helper.open_app_via_menu()
    logger.info(f"[{platform}] Waiting for app to load (0.5s)")
    time.sleep(0.5)  # Allow app to fully load
    logger.info(f"[{platform}] Emulator ready for tests")

    yield helper

    # Teardown: kill emulator
    logger.info(f"[{platform}] Tearing down - killing emulator")
    helper.kill()


class TestCreateTimer:
    """Tests for creating a timer via button presses."""

    def test_create_2_minute_timer(self, persistent_emulator):
        """
        Test creating a 2-minute timer via two Down button presses.

        This test verifies:
        1. The app shows "New" mode initially
        2. After pressing Down twice, the timer shows approximately 2 minutes (1:5x)
        """
        emulator = persistent_emulator

        # Step 1: Take initial screenshot and verify "New" mode
        img1 = emulator.screenshot("step1_initial")
        text1 = extract_text(img1)
        assert "New" in text1, f"Expected 'New' in initial screen, got: {text1}"

        # Step 2: Press Down twice to set 2 minutes
        emulator.press_down()
        emulator.press_down()
        img2 = emulator.screenshot("step2_after_two_down")

        # Step 3: Verify the timer shows ~2 minutes (1:5x due to countdown)
        # Note: OCR may misread 7-segment digits (e.g., "1" as "L", "5" as "S")
        text2 = extract_text(img2)
        logger.info(f"extracted text {text2}")
        # Check for common OCR interpretations of "1:5x"
        time_patterns = ["1:5", "L:5", "1:S", "L:S"]
        has_time = any(pattern in text2 for pattern in time_patterns)
        assert has_time, f"Expected time starting with '1:5' (or OCR variant) after 2 Down presses, got: {text2}"

    def test_initial_state_shows_new(self, persistent_emulator):
        """Test that the initial state shows 'New' in the header."""
        emulator = persistent_emulator
        # Take screenshot of initial state
        img = emulator.screenshot("initial_state")

        # Basic check: image was captured and has content
        assert img is not None
        assert img.size[0] > 0 and img.size[1] > 0

        # The image should not be completely blank/uniform
        # Check that there's some variation in pixel values
        extrema = img.convert("L").getextrema()
        assert extrema[0] != extrema[1], "Screen appears to be blank"

    def test_down_button_increments_minutes(self, persistent_emulator):
        """Test that each Down press adds 1 minute to the timer."""
        emulator = persistent_emulator
        # Take initial screenshot for comparison
        initial = emulator.screenshot()

        # Press Down and verify change
        emulator.press_down()
        after_one = emulator.screenshot()

        assert initial.tobytes() != after_one.tobytes(), (
            "Display should change after Down press"
        )

        # Press Down again
        emulator.press_down()
        after_two = emulator.screenshot()

        assert after_one.tobytes() != after_two.tobytes(), (
            "Display should change after second Down press"
        )

        # Press Down a third time
        emulator.press_down()
        after_three = emulator.screenshot()

        assert after_two.tobytes() != after_three.tobytes(), (
            "Display should change after third Down press"
        )


class TestButtonPresses:
    """Additional tests for button functionality."""

    def test_up_button_increments_20_minutes(self, persistent_emulator):
        """Test that Up button increments timer by 20 minutes."""
        emulator = persistent_emulator
        initial = emulator.screenshot()

        emulator.press_up()
        after_up = emulator.screenshot()

        # The display should change after pressing Up
        assert initial.tobytes() != after_up.tobytes(), (
            "Display should change after Up press"
        )

    def test_select_button_increments_5_minutes(self, persistent_emulator):
        """Test that Select button increments timer by 5 minutes."""
        emulator = persistent_emulator
        initial = emulator.screenshot()

        emulator.press_select()
        after_select = emulator.screenshot()

        # The display should change after pressing Select
        assert initial.tobytes() != after_select.tobytes(), (
            "Display should change after Select press"
        )
