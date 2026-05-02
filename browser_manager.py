"""
ブラウザ管理モジュール - Playwrightを使用したブラウザ操作

Playwrightを使用してブラウザの起動、ページ推移、終了を管理します。
"""
import asyncio
from playwright.async_api import async_playwright, Browser, Page
from config import HEADLESS_MODE, BROWSER_TIMEOUT, NAVIGATION_TIMEOUT


class BrowserManager:
    """Playwrightを使用したブラウザ実装を管理するクラス"""
    
    def __init__(self):
        # 初期化: Playwright、Browser、Pageオブジェクトを保持する変数
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def launch(self):
        """
        ブラウザを起動
        
        1. Playwrightを初期化
        2. Chromiumブラウザを読動
        3. 新しいページを作成
        4. タイムアウトを設定
        """
        self.playwright = await async_playwright().start()
        
        # Chromiumブラウザを起動（headlessモードは設定値で決定）
        self.browser = await self.playwright.chromium.launch(headless=HEADLESS_MODE)
        
        # 新しいページを作成
        self.page = await self.browser.new_page()
        
        # タイムアウトを設定。謟隊承起時間内を矢接後、エラーを発生
        self.page.set_default_timeout(BROWSER_TIMEOUT)
        
        # ナビゲーション待機時間を設定
        self.page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        
        return self.page
    
    async def close(self):
        """
        ブラウザを終了 (逆順で終了)
        
        1. ページを閉じる
        2. ブラウザを閉じる
        3. Playwrightを終了
        """
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def goto(self, url: str):
        """
        指定URLに移動
        
        Args:
            url: 移動先URL
        """
        # 'domcontentloaded': ページの基本的な読み込みが完了した時点で継続
        # これにより、不要なネットワーク待機を回避
        await self.page.goto(url, wait_until='domcontentloaded')
    
    async def get_page(self) -> Page:
        """
        ページオブジェクトを取得
        
        Returns:
            Page: Playwrightページオブジェクト
        """
        return self.page
    
    def get_browser(self) -> Browser:
        """
        ブラウザオブジェクトを取得（独立したコンテキスト作成用）
        
        Returns:
            Browser: Playwrightブラウザオブジェクト
        """
        return self.browser


async def create_browser_manager() -> BrowserManager:
    """
    BrowserManagerインスタンスを起動し作成
    
    Returns:
        BrowserManager: 設定されて起動済みのブラウザ管理オブジェクト
    """
    manager = BrowserManager()
    await manager.launch()
    return manager
