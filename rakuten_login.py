"""
楽天ログインモジュール - Playwrightを使用した楽天へのログイン処理

以下の処理を実行します:
1. 楽天ルームのログインページからログインボタンを找戮
2. ユーザーーIDとパススワードを入力
3. ログインを実行
4. ログイン成功メを確認
"""
import asyncio
import time
from playwright.async_api import Page
from config import RAKUTEN_USER_ID, RAKUTEN_PASSWORD, RAKUTEN_ICHIBA_BASE_URL, NAVIGATION_TIMEOUT


async def login_to_rakuten(page: Page) -> bool:
    """
    楽天へのログイン処理
    
    楽天の市場ぺージにナビゲートし、認証情報を使用してログインします。
    
    Args:
        page: Playwrightのページオブジェクト
    
    Returns:
        bool: ログイン成功True、失敗False
    """
    async def wait_for_selector_safe(selector: str, timeout: int = 5000):
        try:
            return await page.wait_for_selector(selector, timeout=timeout)
        except Exception:
            return None

    try:
        # 楽天市場のベースページへ移動
        # 初回アクセス時はタイムアウトを長めに設定
        await page.goto(RAKUTEN_ICHIBA_BASE_URL, wait_until='domcontentloaded', timeout=NAVIGATION_TIMEOUT)
        
        # ページが少し読み込まれるまで待機
        await asyncio.sleep(1)
        
        # ログインボタンをクリック
        # 異なるセレクタが存在する可能性に対応
        login_button = await wait_for_selector_safe("[aria-label='ログイン'], a:has-text('ログイン'), button:has-text('ログイン')")
        if login_button:
            await login_button.click()
            await page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(1)
        
        # ユーザーIDを入力
        user_id_input = await wait_for_selector_safe("input[id='user_id']")
        if user_id_input:
            await user_id_input.fill(RAKUTEN_USER_ID)
            # ユーザーID入力後に「次へ」ボタンをクリック
            next_button = await wait_for_selector_safe("div[id='cta001']")
            if next_button:
                await next_button.click()
                await page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(1)
        
        # パスワードを入力
        password_input = await wait_for_selector_safe("input[id='password_current']")
        if password_input:
            await password_input.fill(RAKUTEN_PASSWORD)
            # パスワード入力後にログインボタンをクリックまたはEnterキーを押す
            login_button = await wait_for_selector_safe("div[id='cta011']")
            if login_button:
                await login_button.click()
                await page.wait_for_load_state('domcontentloaded')
            else:
                # ログインボタンが見つからない場合はEnterキーを押す
                await password_input.press('Enter')
                await page.wait_for_load_state('domcontentloaded')
        
        # ログイン成功を確認
        await asyncio.sleep(10)
        current_url = page.url
        
        # ログイン成功URLを判定
        if RAKUTEN_ICHIBA_BASE_URL in current_url or 'my.rakuten' in current_url:
            print("楽天へのログインに成功しました")
            return True
        else:
            print("楽天へのログインに失敗しました")
            return False
        
    except Exception as e:
        print(f"楽天へのログイン処理中にエラーが発生しました: {e}")
        return False