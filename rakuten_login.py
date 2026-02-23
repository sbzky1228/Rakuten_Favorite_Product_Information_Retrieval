"""
楽天ログインモジュール - Playwrightを使用した楽天へのログイン処理
"""
import asyncio
import time
from playwright.async_api import Page
from config import RAKUTEN_USER_ID, RAKUTEN_PASSWORD, RAKUTEN_ROOM_BASE_URL


async def login_to_rakuten(page: Page) -> bool:
    """
    楽天にログイン
    
    Args:
        page: Playwrightのページオブジェクト
    
    Returns:
        bool: ログイン成功時True、失敗時False
    """
    try:
        # 楽天ROOMのログインページに遷移
        await page.goto(RAKUTEN_ROOM_BASE_URL)
        
        # ページが完全に読み込まれるまで待機
        await page.wait_for_load_state('networkidle')
        
        # ログインボタンをクリック
        login_button = await page.query_selector("a.signUp-loginBtn, button[data-test='login-button']")
        if login_button:
            await login_button.click()
            await page.wait_for_load_state('networkidle')
        
        # ユーザーIDを入力
        user_id_input = await page.query_selector("input[id='loginUserInner_rakutenId'], input[placeholder='ユーザーID']")
        if user_id_input:
            await user_id_input.fill(RAKUTEN_USER_ID)
        
        # パスワードを入力
        password_input = await page.query_selector("input[id='loginUserInner_password'], input[type='password']")
        if password_input:
            await password_input.fill(RAKUTEN_PASSWORD)
        
        # ログインボタンをクリック
        submit_button = await page.query_selector("button[type='submit'], button.login-button")
        if submit_button:
            await submit_button.click()
            await page.wait_for_load_state('networkidle')
        
        # ログイン成功確認
        await asyncio.sleep(2)
        current_url = page.url
        
        if RAKUTEN_ROOM_BASE_URL in current_url or 'my.rakuten' in current_url:
            print("楽天へのログインに成功しました")
            return True
        else:
            print("楽天へのログインに失敗しました")
            return False
    
    except Exception as e:
        print(f"ログイン処理でエラーが発生しました: {e}")
        return False
