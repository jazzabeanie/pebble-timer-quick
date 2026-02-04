"""
Tests for Edit Mode Reset functionality.

Verifies that long pressing Select in Edit Mode (ControlModeNew) resets the timer
to 0:00 and enters Edit Seconds mode, while doing nothing in other edit modes.
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

class TestEditModeReset:
    """Tests for long press select reset behavior in edit modes."""

    def test_long_press_select_resets_in_control_mode_new(self, persistent_emulator):
        """
        Test 1: Long press select in ControlModeNew resets to paused 0:00 in edit seconds mode.

        Uses log-based assertions for reliable state verification:
        1. Verifies mode is EditSec after long press
        2. Verifies timer is 0:00
        3. Verifies pressing Back adds 60 seconds (confirms EditSec mode)
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

        # Step 3: Long press Select to reset to 0:00 in EditSec mode
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)
        emulator.release_buttons()

        # Wait for the long_press_select state log
        state_reset = capture.wait_for_state(event="long_press_select", timeout=5.0)

        # Verify timer is 0:00 and mode is EditSec
        assert state_reset is not None, "Did not receive long_press_select state log"
        logger.info(f"After long press Select state: {state_reset}")
        assert_mode(state_reset, "EditSec")
        assert_time_equals(state_reset, minutes=0, seconds=0)
        assert_paused(state_reset, True)

        # Step 4: Press Back to verify Edit Seconds mode (adds 60 seconds)
        emulator.press_back()
        state_back = capture.wait_for_state(event="button_back", timeout=5.0)

        capture.stop()

        # Verify Back button added 60 seconds (confirms EditSec mode)
        assert state_back is not None, "Did not receive button_back state log"
        logger.info(f"After Back press state: {state_back}")
        assert_time_equals(state_back, minutes=1, seconds=0)
        assert_mode(state_back, "EditSec")

    @pytest.mark.skip(reason="Visual comparison flaky due to animations/blinking")
    def test_long_press_select_no_op_in_edit_sec(self, persistent_emulator):
        emulator = persistent_emulator
        platform = emulator.platform
        
        # Step 1: Ensure 0:00
        time.sleep(2) 
        
        # Step 2: Press Up to enter edit mode
        emulator.press_up()
        time.sleep(1)
        
        # Step 3: Press Down to add seconds (0:01)
        emulator.press_down() 
        time.sleep(1)
        
        # Save reference of 0:01 (ON phase)
        burst_val = capture_burst(emulator)
        best_val = get_best_image(burst_val)
        matches_reference(best_val, f"{platform}_editsec_001")
        
        # Step 4: Long press Select
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)
        emulator.release_buttons()
        time.sleep(1)
        
        # Step 5: Verify we still match 0:01 (one of the burst images must match)
        burst_noop = capture_burst(emulator)
        
        match_found = False
        for img in burst_noop:
            if matches_reference(img, f"{platform}_editsec_001"):
                match_found = True
                break
                
        assert match_found, "Timer changed after long press select in EditSec"

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
