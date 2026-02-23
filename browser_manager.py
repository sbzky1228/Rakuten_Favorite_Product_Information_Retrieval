"""
ブラウザ管理モジュール - Playwrightを使用したブラウザ操作
"""
import asyncio
from playwright.async_api import async_playwright, Browser, Page
from config import HEADLESS_MODE, BROWSER_TIMEOUT, NAVIGATION_TIMEOUT


class BrowserManager:
    """Playwrightブラウザの管理クラス"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def launch(self):
        """ブラウザを起動"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=HEADLESS_MODE)
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(BROWSER_TIMEOUT)
        self.page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        return self.page
    
    async def close(self):
        """ブラウザを閉じる"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def goto(self, url: str):
        """指定URLに移動"""
        await self.page.goto(url, wait_until='networkidle')
    
    async def get_page(self) -> Page:
        """ページオブジェクトを取得"""
        return self.page


async def create_browser_manager() -> BrowserManager:
    """BrowserManagerインスタンスを生成"""
    manager = BrowserManager()
    await manager.launch()
    return manager
