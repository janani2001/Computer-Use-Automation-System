"""
Browser control module - Handles Playwright automation.

Provides abstraction over Playwright for:
- Launching browsers
- Taking screenshots
- Clicking elements
- Typing text
- Waiting for elements
- Reading page content
"""

import base64
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser lifecycle and operations."""
    
    def __init__(self):
        """Initialize browser manager."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
    
    async def connect(self, target_url: str, headless: bool = False) -> None:
        """
        Connect to browser and navigate to target.
        
        Args:
            target_url: URL to navigate to (e.g., "http://127.0.0.1:5000")
            headless: Whether to run headless (no UI window)
        """
        try:
            logger.info(f"Starting browser (headless={headless})...")
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            
            logger.info(f"Navigating to {target_url}...")
            await self.page.goto(target_url, wait_until="load")
            logger.info("✅ Browser connected and loaded")
        
        except Exception as e:
            logger.error(f"❌ Failed to connect browser: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close browser and cleanup."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("✅ Browser disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting browser: {e}")
    
    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """
        Take screenshot of current page and return as base64.
        
        Args:
            filename: Optional filename to save screenshot to
        
        Returns:
            Base64-encoded PNG image
        """
        if not self.page:
            raise RuntimeError("Browser not connected. Call connect() first.")
        
        try:
            # Take screenshot
            screenshot_bytes = await self.page.screenshot(full_page=False)
            
            # Optionally save to file
            if filename:
                Path(filename).write_bytes(screenshot_bytes)
                logger.info(f"Screenshot saved to {filename}")
            
            # Encode to base64
            screenshot_b64 = base64.standard_b64encode(screenshot_bytes).decode()
            logger.info(f"Screenshot captured ({len(screenshot_bytes)} bytes)")
            return screenshot_b64
        
        except Exception as e:
            logger.error(f"❌ Failed to take screenshot: {e}")
            raise
    
    async def click(self, selector: str) -> None:
        """
        Click element by CSS selector.
        
        Args:
            selector: CSS selector (e.g., "#member_search_btn")
        
        Raises:
            Exception if element not found or click fails
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        
        try:
            logger.info(f"Clicking: {selector}")
            await self.page.click(selector)
            logger.info(f"✅ Clicked: {selector}")
        
        except Exception as e:
            logger.error(f"❌ Failed to click {selector}: {e}")
            raise
    
    async def type_text(self, selector: str, text: str) -> None:
        """
        Type text into input field.
        
        Args:
            selector: CSS selector for input element
            text: Text to type
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        
        try:
            logger.info(f"Typing '{text}' into: {selector}")
            await self.page.fill(selector, text)
            logger.info(f"✅ Typed text into: {selector}")
        
        except Exception as e:
            logger.error(f"❌ Failed to type into {selector}: {e}")
            raise
    
    async def wait_for_element(self, selector: str, timeout_ms: int = 5000) -> None:
        """
        Wait for element to be present on page.
        
        Args:
            selector: CSS selector to wait for
            timeout_ms: Timeout in milliseconds
        
        Raises:
            Exception if element not found within timeout
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        
        try:
            logger.info(f"Waiting for element: {selector} (timeout={timeout_ms}ms)")
            await self.page.wait_for_selector(selector, timeout=timeout_ms)
            logger.info(f"✅ Element found: {selector}")
        
        except Exception as e:
            logger.error(f"❌ Timeout waiting for {selector}: {e}")
            raise
    
    async def read_element_text(self, selector: str) -> str:
        """
        Read text content of element.
        
        Args:
            selector: CSS selector for element
        
        Returns:
            Text content
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        
        try:
            text = await self.page.inner_text(selector)
            logger.info(f"Read text from {selector}: '{text}'")
            return text
        
        except Exception as e:
            logger.error(f"❌ Failed to read text from {selector}: {e}")
            raise
    
    async def get_page_content(self) -> str:
        """
        Get full HTML content of current page.
        
        Returns:
            HTML content
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        
        try:
            content = await self.page.content()
            logger.info(f"Retrieved page content ({len(content)} bytes)")
            return content
        
        except Exception as e:
            logger.error(f"❌ Failed to get page content: {e}")
            raise
    
    async def get_current_url(self) -> str:
        """Get current page URL."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        return self.page.url
    
    async def navigate(self, url: str) -> None:
        """
        Navigate the current page to a new URL.
        
        Args:
            url: URL to navigate to
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        
        try:
            logger.info(f"Navigating to: {url}")
            await self.page.goto(url, wait_until="load")
            logger.info(f"✅ Navigated to: {url}")
        
        except Exception as e:
            logger.error(f"❌ Failed to navigate to {url}: {e}")
            raise
    
    async def submit_form(self, selector: str) -> None:
        """
        Submit form by clicking submit button.
        
        Args:
            selector: CSS selector for submit button
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        
        try:
            logger.info(f"Submitting form: {selector}")
            await self.page.click(selector)
            # Wait a moment for navigation
            await self.page.wait_for_load_state("load")
            logger.info(f"✅ Form submitted: {selector}")
        
        except Exception as e:
            logger.error(f"❌ Failed to submit form {selector}: {e}")
            raise
