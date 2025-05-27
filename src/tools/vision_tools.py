from playwright.async_api import Page
from agent.playwright.playwright_manager import PlaywrightManager
import asyncio
import base64
import logging

logger = logging.getLogger(__name__)

class ToolExecutionError(Exception):
    pass

async def browse_url(url: str) -> str:
    """Navigates to a URL and returns a summary of the page content."""
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        logger.info(f"🌐 Navigating to URL: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        logger.info(f"✅ Successfully loaded URL: {url}")

        logger.info("📄 Extracting page title and content...")
        title = await page.title()
        content = await page.content()
        await asyncio.sleep(0.2)
        logger.info(f"✅ Retrieved page title and content from: {url}")

        return f"Successfully navigated to {url}. Page Title: '{title}'. Page content length: {len(content)}. First 500 chars: {content[:500]}..."
    except Exception as e:
        logger.error(f"❌ Error while browsing URL {url}: {e}")
        raise ToolExecutionError(f"Error Browse URL {url}: {e}")

async def take_screenshot_base64() -> str:
    """Takes a viewport-only screenshot and returns it as base64 encoded PNG."""
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        logger.info("📸 Taking screenshot of the viewport...")
        screenshot_bytes = await manager.take_screenshot_and_save(page)
        await asyncio.sleep(0.2)
        logger.info("✅ Screenshot captured successfully.")
        return base64.b64encode(screenshot_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"❌ Error taking screenshot: {e}")
        raise ToolExecutionError(f"Error taking screenshot: {e}")

async def move_mouse(x: int, y: int) -> None:
    """Moves mouse to specified coordinates."""
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        logger.info(f"🖱️ Moving mouse to ({x}, {y})...")
        await page.mouse.move(x, y)
        await asyncio.sleep(0.3)
        logger.info(f"✅ Mouse moved to ({x}, {y})")
    except Exception as e:
        logger.warning(f"⚠️ Warning: Error moving mouse to ({x}, {y}): {e}")

async def click_coordinates(x: int, y: int, button: str = "left") -> str:
    """Clicks at the given screen coordinates."""
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        logger.info(f"🖱️ Clicking at ({x}, {y}) with '{button}' button...")
        await page.mouse.click(x, y, button="left")
        await asyncio.sleep(0.3)
        logger.info(f"✅ Clicked at ({x}, {y}) with '{button}' button.")
        return f"Successfully clicked at coordinates ({x}, {y}) with '{button}' button."
    except Exception as e:
        logger.error(f"❌ Error clicking at ({x}, {y}): {e}")
        raise ToolExecutionError(f"Error clicking at coordinates ({x}, {y}): {e}")

async def type_text_at_coordinates(x: int, y: int, text: str) -> str:
    """Types text at the clicked coordinates using keyboard input."""
    manager = await PlaywrightManager.get_instance()
    page = await manager.get_page()
    try:
        logger.info(f"🖱️ Clicking to focus at ({x}, {y}) before typing...")
        await page.mouse.click(x, y)
        await asyncio.sleep(0.3)
        logger.info(f"⌨️ Typing text: '{text}' at ({x}, {y})...")
        await page.keyboard.type(text, delay=50)
        await asyncio.sleep(0.3)
        logger.info(f"✅ Typed '{text}' at coordinates ({x}, {y})")
        return f"Typed '{text}' at coordinates ({x}, {y})."
    except Exception as e:
        logger.error(f"❌ Error typing text at ({x}, {y}): {e}")
        raise ToolExecutionError(f"Error typing text at coordinates ({x}, {y}): {e}")
