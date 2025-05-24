import asyncio
import os
import time
from typing import Optional, Any
from playwright.async_api import async_playwright, Browser, Page, Playwright

class PlaywrightManager:
    _instance: Optional['PlaywrightManager'] = None # Stores the singleton instance
    _playwright_context: Optional[Playwright] = None # The Playwright object itself
    _browser: Optional[Browser] = None # The launched browser instance
    _page: Optional[Page] = None # The single, persistent page
    _headless: bool = True
    _save_screenshots_locally: bool = False
    _screenshots_dir: str = "screenshots"
    _screenshot_counter: int = 0 # To ensure unique screenshot filenames

    def __init__(self):
        # Prevent direct instantiation, enforce singleton
        if PlaywrightManager._instance is not None:
            raise Exception("This class is a singleton! Use PlaywrightManager.get_instance()")

    @classmethod
    async def get_instance(cls):
        """Returns the singleton instance of PlaywrightManager."""
        if cls._instance is None:
            cls._instance = PlaywrightManager()
            # The actual browser launch will happen via set_config and launch_browser
            # called from main.py's startup event.
        return cls._instance

    def set_config(self, headless: bool, save_screenshots_locally: bool, screenshots_dir: str):
        """Sets the configuration for Playwright browser and screenshots."""
        self._headless = headless
        self._save_screenshots_locally = save_screenshots_locally
        self._screenshots_dir = screenshots_dir
        if self._save_screenshots_locally and not os.path.exists(self._screenshots_dir):
            os.makedirs(self._screenshots_dir)
        print(f"PlaywrightManager configured: Headless={self._headless}, Save Screenshots={self._save_screenshots_locally}, Dir='{self._screenshots_dir}'")


    async def launch_browser(self):
        """Launches the Playwright browser and creates a single persistent page."""
        if self._browser is None:
            self._playwright_context = await async_playwright().start()
            self._browser = await self._playwright_context.chromium.launch(headless=self._headless)
            # Create ONE persistent page for all interactions with viewport size 800x600
            self._page = await self._browser.new_page(viewport={"width": 800, "height": 600})
            self._screenshot_counter = 0 # Reset counter for a new browser session
            print("Playwright browser launched and persistent page created with viewport 800x600.")
        else:
            print("Playwright browser already launched.")

    async def get_page(self) -> Page:
        """Returns the single persistent Playwright page."""
        if self._page is None or self._page.is_closed():
            # If the page was somehow closed, re-create it within the existing browser
            if self._browser is None or self._browser.is_closed():
                await self.launch_browser() # Re-launch browser if necessary
            else:
                self._page = await self._browser.new_page(viewport={"width": 800, "height": 600}) # Create new page if only page was closed
                print("Recreated Playwright page with viewport 800x600.")
        return self._page

    async def close_browser(self):
        """Closes the Playwright browser and context."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None # Clear the page reference too
            print("Playwright browser closed.")
        if self._playwright_context:
            await self._playwright_context.stop()
            self._playwright_context = None
            print("Playwright context stopped.")
        # Reset the singleton instance on full shutdown
        PlaywrightManager._instance = None

    async def take_screenshot_and_save(self, page: Page) -> bytes:
        """Takes a screenshot and optionally saves it locally based on manager's config."""
        screenshot_bytes = await page.screenshot(full_page=True)
        if self._save_screenshots_locally:
            self._screenshot_counter += 1
            timestamp = int(time.time())
            filename = os.path.join(self._screenshots_dir, f"screenshot_{timestamp}_{self._screenshot_counter}.png")
            with open(filename, "wb") as f:
                f.write(screenshot_bytes)
            print(f"Screenshot saved to {filename}")
        return screenshot_bytes

# The __aenter__ and __aexit__ are removed as they are not used with get_instance() pattern
# The example usage (main) at the bottom is also removed as it's not needed for the server.