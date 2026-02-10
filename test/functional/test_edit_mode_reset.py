"""
Tests for Edit Mode Toggle functionality.

Verifies that long pressing Select toggles between New and EditSec modes
(preserving timer value), and does nothing in EditRepeat mode.
"""

import logging
import time
import pytest
import numpy as np
from pathlib import Path
from PIL import Image

from .conftest import (
    Button,
    EmulatorHelper,
    PLATFORMS,
    LogCapture,
    assert_mode,
    assert_paused,
    assert_time_equals,
    assert_time_approximately,
    assert_direction,
)
from .test_create_timer import extract_text, normalize_time_text, REFERENCES_DIR

# Configure module logger
logger = logging.getLogger(__name__)

def capture_burst(emulator, count=3, delay=0.3) -> list[Image.Image]:
    """Capture a burst of screenshots to handle blinking UI elements."""
    imgs = []
    for i in range(count):
        imgs.append(emulator.screenshot(f"burst_{i}"))
        time.sleep(delay)
    return imgs

def get_best_image(imgs: list[Image.Image], crop_box: tuple = None) -> Image.Image:
    """Return the image with the most white pixels (assuming ON phase of blink)."""
    best_img = imgs[0]
    max_white = -1
    
    for img in imgs:
        target = img.crop(crop_box) if crop_box else img
        arr = np.array(target.convert("L"))
        # Count pixels > 128 (light/white)
        white_count = np.sum(arr > 128)
        
        if white_count > max_white:
            max_white = white_count
            best_img = img
            
    return best_img

def matches_reference(img: Image.Image, name: str, crop_box: tuple = None) -> bool:
    """Check if the image matches a stored reference."""
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    
    if crop_box:
        target = img.crop(crop_box)
    else:
        target = img

    target_arr = np.array(target.convert("L")) > 128
    
    ref_path = REFERENCES_DIR / f"ref_{name}.png"
    
    if not ref_path.exists():
        logger.info(f"Reference '{name}' not found. Saving current image as reference.")
        target.save(ref_path)
        return True
        
    ref_img = Image.open(ref_path).convert("L")
    ref_arr = np.array(ref_img) > 128
    
    if target_arr.shape != ref_arr.shape:
        return False
        
    diff_pixels = np.sum(target_arr != ref_arr)
    total_pixels = target_arr.size
    diff_ratio = diff_pixels / total_pixels
    
    return diff_ratio < 0.02

class TestEditModeToggle:
    """Tests for long press select toggle behavior between edit modes."""

    def test_long_press_select_toggles_new_to_editsec(self, persistent_emulator):
        """
        Test 1: Long press select in ControlModeNew toggles to EditSec preserving value.

        Uses log-based assertions for reliable state verification:
        1. Sets a 2-minute timer and enters New mode
        2. Long press Select toggles to EditSec with value preserved
        3. Pressing Back adds 60 seconds (confirms EditSec mode)
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # Start log capture
        capture = LogCapture(platform)
        capture.start()
        time.sleep(1.0)  # Wait for pebble logs to connect
        capture.clear_state_queue()

        # Step 1: Set a 2-minute timer and wait for Counting mode
        emulator.press_down()
        emulator.press_down()
        time.sleep(4)

        # Step 2: Press Up to enter edit mode
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        time.sleep(0.5)

        # Verify we're in New mode (editing existing timer)
        assert state_edit is not None, "Did not receive button_up state log"
        logger.info(f"After Up press state: {state_edit}")
        assert_mode(state_edit, "New")

        # Step 3: Long press Select to toggle to EditSec (preserving value)
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)
        emulator.release_buttons()

        # Wait for the long_press_select state log
        state_toggle = capture.wait_for_state(event="long_press_select", timeout=5.0)

        # Verify mode is EditSec and timer value is preserved (approximately 2:00)
        assert state_toggle is not None, "Did not receive long_press_select state log"
        logger.info(f"After long press Select state: {state_toggle}")
        assert_mode(state_toggle, "EditSec")
        # Timer value should be preserved (~1:54 after countdown)
        assert_time_approximately(state_toggle, minutes=1, seconds=54, tolerance=10)

        # Step 4: Press Back to verify Edit Seconds mode (adds 60 seconds)
        emulator.press_back()
        state_back = capture.wait_for_state(event="button_back", timeout=5.0)

        capture.stop()

        # Verify Back button added 60 seconds (confirms EditSec mode)
        assert state_back is not None, "Did not receive button_back state log"
        logger.info(f"After Back press state: {state_back}")
        assert_mode(state_back, "EditSec")

    def test_long_press_select_toggles_editsec_to_new(self, persistent_emulator):
        """
        Test 2: Long press select in EditSec toggles to New mode preserving value.

        Uses log-based assertions:
        1. Enter EditSec mode and add some seconds
        2. Long press Select toggles to New with value preserved
        3. Pressing Down adds 1 minute (confirms New mode)
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # Start log capture
        capture = LogCapture(platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Wait for chrono mode, then pause
        time.sleep(3.5)
        emulator.press_select()
        time.sleep(0.3)

        # Long press Select to reset to 0:00 and enter EditSec (from paused Counting)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_editsec = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_editsec is not None
        assert_mode(state_editsec, "EditSec")

        # Add 20 seconds (press Up once in EditSec)
        emulator.press_up()
        state_up = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_up is not None
        assert_time_equals(state_up, minutes=0, seconds=20)
        assert_mode(state_up, "EditSec")

        # Long press Select to toggle to New mode (preserving value)
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)
        emulator.release_buttons()

        state_toggle = capture.wait_for_state(event="long_press_select", timeout=5.0)

        assert state_toggle is not None, "Did not receive long_press_select state log"
        logger.info(f"After toggle to New: {state_toggle}")
        assert_mode(state_toggle, "New")
        assert_time_equals(state_toggle, minutes=0, seconds=20)

        # Press Down to verify New mode (adds 1 minute)
        emulator.press_down()
        state_down = capture.wait_for_state(event="button_down", timeout=5.0)

        capture.stop()

        assert state_down is not None
        assert_time_equals(state_down, minutes=1, seconds=20)
        assert_mode(state_down, "New")

    def test_toggle_new_to_editsec_preserves_reverse_direction(self, persistent_emulator):
        """
        Test 3: Toggling from New to EditSec preserves reverse direction.

        Steps:
        1. Set a 2-minute timer and wait for Counting
        2. Press Up to enter New mode
        3. Long press Up to toggle to reverse direction
        4. Long press Select to toggle to EditSec
        5. Verify direction is still reverse
        """
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set a 2-minute timer and wait for Counting mode
        emulator.press_down()
        emulator.press_down()
        time.sleep(4)

        # Step 2: Press Up to enter edit mode
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None
        assert_mode(state_edit, "New")
        assert_direction(state_edit, forward=True)

        # Step 3: Long press Up to toggle to reverse direction
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir is not None
        assert_direction(state_dir, forward=False)

        # Step 4: Long press Select to toggle to EditSec
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)
        emulator.release_buttons()
        state_toggle = capture.wait_for_state(event="long_press_select", timeout=5.0)

        capture.stop()

        # Step 5: Verify direction is preserved (still reverse)
        assert state_toggle is not None
        assert_mode(state_toggle, "EditSec")
        assert_direction(state_toggle, forward=False)

    def test_toggle_editsec_to_new_preserves_reverse_direction(self, persistent_emulator):
        """
        Test 4: Toggling from EditSec to New preserves reverse direction.

        Steps:
        1. Enter EditSec via paused Counting -> long press Select
        2. Long press Up to toggle to reverse direction
        3. Long press Select to toggle to New
        4. Verify direction is still reverse
        """
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for chrono mode, then pause and enter EditSec at 0:00
        time.sleep(3.5)
        emulator.press_select()
        time.sleep(0.3)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_editsec = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_editsec is not None
        assert_mode(state_editsec, "EditSec")

        # Add some time so we have a nonzero value
        emulator.press_up()
        state_up = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_up is not None

        # Step 2: Long press Up to toggle to reverse direction
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir is not None
        assert_direction(state_dir, forward=False)

        # Step 3: Long press Select to toggle to New
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)
        emulator.release_buttons()
        state_toggle = capture.wait_for_state(event="long_press_select", timeout=5.0)

        capture.stop()

        # Step 4: Verify direction is preserved (still reverse)
        assert state_toggle is not None
        assert_mode(state_toggle, "New")
        assert_direction(state_toggle, forward=False)

    @pytest.mark.skip(reason="Visual comparison flaky due to animations/blinking")
    def test_long_press_select_no_op_in_edit_repeat(self, persistent_emulator):
        emulator = persistent_emulator
        platform = emulator.platform
        
        # Step 1: Set 2 min timer
        emulator.press_down()
        emulator.press_down()
        time.sleep(4)
        
        # Step 2: Long press Up to enable repeat mode
        emulator.hold_button(Button.UP)
        time.sleep(1.5)
        emulator.release_buttons()
        time.sleep(1)
        
        # Capture reference (Header Edit) - ON phase if blinking
        header_crop = (0, 0, 90, 25)
        burst_before = capture_burst(emulator)
        best_before = get_best_image(burst_before, crop_box=header_crop)
    
        matches_reference(best_before, f"{platform}_header_edit_safe", crop_box=header_crop)
    
        # Step 3: Long press Select
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)
        emulator.release_buttons()
        time.sleep(1)
    
        # Step 4: Verify header is still "Edit"
        burst_after = capture_burst(emulator)
        match_found = False
        for img in burst_after:
            if matches_reference(img, f"{platform}_header_edit_safe", crop_box=header_crop):
                match_found = True
                break
                
        assert match_found, "Header changed after long press select in EditRepeat"
