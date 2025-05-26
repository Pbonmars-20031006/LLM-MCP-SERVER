# vision_tools.py
from playwright.async_api import Page
from agent.playwright.playwright_manager import PlaywrightManager
import asyncio
import base64
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class ToolExecutionError(Exception):
    pass

async def browse_url(url: str) -> str:
    """Navigates to a URL and returns a summary of the page content. Good for initial page loads."""
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        # Added wait_until for better reliability on page loads
        await page.goto(url, wait_until="domcontentloaded")
        title = await page.title() # Get page title for a more meaningful summary
        content = await page.content()
        return f"Successfully navigated to {url}. Page Title: '{title}'. Page content length: {len(content)}. First 500 chars: {content[:500]}..."
    except Exception as e:
        logger.error(f"Error Browse URL {url}: {e}")
        raise ToolExecutionError(f"Error Browse URL {url}: {e}")

async def take_screenshot_base64() -> str:
    """Takes a full-page screenshot and returns it as a base64 encoded PNG string.
    This image should then be sent to an LLM with vision capabilities (like Gemini)
    for visual analysis and decision-making."""
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        # IMPORTANT: If your playwright_manager still has _inject_element_ids, remove it
        # or comment it out, as it's not needed for this coordinate-only approach.
        screenshot_bytes = await page.screenshot(full_page=True)
        return base64.b64encode(screenshot_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        raise ToolExecutionError(f"Error taking screenshot: {e}")

async def move_mouse(x: int, y: int) -> None:
    """
    Move the mouse to the specified coordinates.
    This action is mainly for visual feedback or to prepare for a click.
    """
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        await page.mouse.move(x, y)
        await asyncio.sleep(0.1) # Small delay for visual effect
        logger.info(f"🖱️ Moved mouse to ({x}, {y}).")
    except Exception as e:
        # Log the error but don't raise, as mouse move is often a precursor
        # and not critical for the overall task success.
        logger.warning(f"Warning: Error moving mouse to ({x}, {y}): {e}")
        pass # Allow the operation to continue even if mouse move fails

async def click_coordinates(x: int, y: int, button: str="left") -> str:
    """
    Clicks at the specified x, y coordinates on the page.
    Args:
        x (int): The x-coordinate (horizontal pixel).
        y (int): The y-coordinate (vertical pixel).
        button (str): The mouse button to click ('left', 'right', 'middle'). Defaults to 'left'.
    """
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        await asyncio.sleep(0.5) # Wait a bit before clicking to ensure page stability
        await page.mouse.click(x, y, button=button)
        await asyncio.sleep(0.1) # Short delay after click
        logger.info(f"✅ Successfully clicked at coordinates ({x}, {y}) with '{button}' button.")
        return f"Successfully clicked at coordinates ({x}, {y}) with '{button}' button."
    except Exception as e:
        logger.error(f"Error clicking at coordinates ({x}, {y}): {e}")
        raise ToolExecutionError(f"Error clicking at coordinates ({x}, {y}): {e}")

async def type_text_at_coordinates(x: int, y: int, text: str) -> str:
    """
    Types text into an element at the specified x, y coordinates on the page.
    It simulates a click to focus before typing.
    Args:
        x (int): The x-coordinate (horizontal pixel) to click for focus.
        y (int): The y-coordinate (vertical pixel) to click for focus.
        text (str): The text to type.
    """
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        await asyncio.sleep(0.5) # Wait a bit before typing to ensure page stability
        # Simulate a click to focus the element first
        await page.mouse.click(x, y)
        await asyncio.sleep(0.1) # Small delay after click to ensure focus

        logger.info(f"⌨️ Typing '{text}' at coordinates ({x}, {y}).")
        # Use fill if possible, otherwise type (fill is generally more robust for inputs)
        # We try to locate an element near the coordinates first to use .fill()
        try:
            # This attempts to find an input/textarea near the coordinates
            # and prefers .fill() which is better for input fields.
            # Adjust the selector or tolerance if needed.
            locator = page.locator(f"input[type='text'], input[type='password'], textarea, input:not([type='submit']):not([type='button'])",
                                   has_text=text[:10] if len(text) > 0 else "") # Simple guess
            
            # Find the closest visible element to the coordinates
            # This part is a bit tricky without direct element_id.
            # For simplicity, we'll revert to direct keyboard type after click if robust locator isn't feasible.
            
            # The most reliable way for coordinate-only is direct keyboard input after click.
            await page.keyboard.type(text, delay=50) # delay=50 makes it more human-like
            await asyncio.sleep(0.1)
            logger.info(f"✅ Successfully typed '{text}' at coordinates ({x}, {y}).")
            return f"Successfully typed '{text}' at coordinates ({x}, {y})."
        except Exception as locator_error:
            # Fallback to direct keyboard type if locator fails
            logger.warning(f"Could not locate specific input for fill at ({x}, {y}). Falling back to keyboard type. Error: {locator_error}")
            await page.keyboard.type(text, delay=50)
            await asyncio.sleep(0.1)
            logger.info(f"✅ Successfully typed '{text}' at coordinates ({x}, {y}) (keyboard fallback).")
            return f"Successfully typed '{text}' at coordinates ({x}, {y}) (keyboard fallback)."
    except Exception as e:
        logger.error(f"Error typing text '{text}' at coordinates ({x}, {y}): {e}")
        raise ToolExecutionError(f"Error typing text '{text}' at coordinates ({x}, {y}): {e}")