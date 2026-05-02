"""
お気に入り商品取得モジュール - 楽天市場のお気に入り商品情報を取得
"""
import asyncio
import re
from typing import List, Dict, Optional
from playwright.async_api import Page, Browser
from config import RAKUTEN_FAVORITES_URL, RAKUTEN_FAVORITES_ALT_URL
 
 
async def get_favorite_items_info(page: Page, browser: Browser, max_items: int = 200) -> List[Dict]:
    """
    楽天市場のお気に入り商品情報を取得
    
    Args:
        page: Playwrightのページオブジェクト（お気に入りページ遷移用）
        browser: Playwrightのブラウザオブジェクト（各タスク用の独立コンテキスト作成用）
        max_items: 取得する最大商品数
    
    Returns:
        List[Dict]: 商品情報のリスト
    """
    try:
        print(f"[DEBUG] 現在のページからお気に入りリンクを探す: {page.url}")
 
        # お気に入りページへ移動
        bookmark_link = await page.query_selector("a[href*=\"https://my.bookmark.rakuten.co.jp/?l-id=pc_header_func_bookmark\"]")
        if bookmark_link:
            print("[DEBUG] お気に入りリンクを発見、クリックします")
            await bookmark_link.click()
        else:
            print(f"[DEBUG] お気に入りリンクが見つからないため直接アクセス: {RAKUTEN_FAVORITES_URL}")
            try:
                await page.goto(RAKUTEN_FAVORITES_URL, wait_until='domcontentloaded', timeout=30000)
            except Exception as e:
                print(f"[DEBUG] メインURL失敗、代替URLを試行: {e}")
                await page.goto(RAKUTEN_FAVORITES_ALT_URL, wait_until='domcontentloaded', timeout=30000)
 
        await page.wait_for_load_state('domcontentloaded')
        await asyncio.sleep(2)
        print(f"[DEBUG] 最終URL: {page.url}")
 
        urls = []
        visited_urls = set()
        page_count = 0
 
        while len(urls) < max_items:
            page_count += 1
            print(f"[DEBUG] お気に入りページ収集: ページ {page_count}, 現在のURL数: {len(urls)}")
 
            # 動的ロード対策 (スクロール)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
 
            # リンクを取得（指定エリア配下のみ）
            links = await page.query_selector_all("a[href*='item.rakuten.co.jp']")
            for link in links:
                href = await link.get_attribute('href')
                if not href or 'item.rakuten.co.jp' not in href:
                    continue
 
                # sideBarBlock配下は除外
                is_in_sidebar = await link.evaluate("node => !!node.closest('.styles__sideBarBlock___M-hla')")
                if is_in_sidebar:
                    continue
 
                # 中心エリア or bookmark-main 配下にあるリンクのみ許可
                is_in_center = await link.evaluate("node => !!node.closest('.bookmarkPage__block--centerContent')")
                is_in_main = await link.evaluate("node => !!node.closest('#bookmark-main')")
                if not (is_in_center or is_in_main):
                    continue
 
                clean_url = href.split('?')[0]
                if clean_url not in visited_urls:
                    visited_urls.add(clean_url)
                    urls.append(clean_url)
 
                if len(urls) >= max_items:
                    break
 
            if len(urls) >= max_items:
                break
 
            # 次ページリンクを探す
            # UIが React/CSS module でクラス指定の場合に対応
            next_button = await page.query_selector("a.styles__nextPageBtn___3CWcG")
            if not next_button:
                next_button = await page.query_selector("a:has-text(\"次へ\")")
            if not next_button:
                next_button = await page.query_selector("a[aria-label='Next'], a[aria-label='次へ']")
 
            if not next_button:
                print("[DEBUG] 次ページが見つかりません。ページ遷移は終了します。")
                break
 
            is_disabled = await next_button.get_attribute('aria-disabled')
            if is_disabled == 'true':
                print("[DEBUG] 次ページボタンが無効化されています。終了します。")
                break
 
            print("[DEBUG] 次ページへ遷移します")
            await next_button.click()
            await page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(2)
 
        # 収集URL数
        print(f"取得したお気に入り商品URL数: {len(urls)}")
 
        # 並列度制限を設定（同時に3コンテキストまで開く）
        semaphore = asyncio.Semaphore(3)
        
        if not urls:
            print("[DEBUG] お気に入り商品のURLが1件も収集できませんでした。")
            return []

        # 並列処理で商品情報を取得
        tasks = [
            extract_item_info_with_semaphore(url, browser, semaphore) 
            for url in urls[:max_items]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果をフィルタリング（例外を除外）
        items_data = [item for item in results if isinstance(item, dict)]
        print(f"[DEBUG] 取得した商品情報件数: {len(items_data)}")
        return items_data
    except Exception as e:
        print(f"お気に入り商品情報の取得に失敗しました: {e}")
        return []


async def extract_item_info_with_semaphore(url: str, browser: Browser, semaphore: asyncio.Semaphore) -> Optional[Dict]:
    """
    並列度制限付きで商品情報を抽出
    
    【セッション管理方針】
    各タスクで独立したコンテキストを作成することで、セッションの有効性を保証します。
    これにより、ページの収集エラーを防ぎ、メモリリークを最小化します。
    
    Args:
        url: 商品URL
        browser: ブラウザオブジェクト（新しいコンテキストを作成するのに使用）
        semaphore: 並列制御用セマフォ
    
    Returns:
        Dict: 商品情報またはNone
    """
    async with semaphore:
        context = None
        temp_page = None
        try:
            # 各タスクで独立したコンテキストを作成
            # 【重要】page.context を使わず、新しいコンテキストを作成することで、
            # セッション有効性を確保し、メモリ管理を最適化します
            context = await browser.new_context()
            
            # そのコンテキスト内で新しいページを作成
            temp_page = await context.new_page()
            temp_page.set_default_timeout(30000)
            temp_page.set_default_navigation_timeout(30000)
            
            # URLパターン解析
            pattern = r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)'
            match = re.search(pattern, url)
            
            if not match:
                return None
            
            shop_code = match.group(1)
            item_id = match.group(2)
            item_code_combined = f"{shop_code}:{item_id}"
            
            # 商品名取得
            item_name = await extract_item_name_from_item_page(temp_page, url)
            
            return {
                'ItemURL': url,
                'ShopCode': shop_code,
                'ItemID': item_id,
                'ItemCode': item_code_combined,
                'ItemName': item_name,
                'Collection': '',
                'PostStatus': '',
                'PostedDate': '',
                'CollectionStatus': '',
                'CollectedDate': ''
            }
        
        except Exception as e:
            print(f"URL解析エラー ({url}): {e}")
            return None
        finally:
            # リソースを必ず解放（ページ→コンテキスト）
            if temp_page:
                try:
                    await temp_page.close()
                except Exception as e:
                    print(f"一時ページのクローズに失敗しました: {e}")
            if context:
                try:
                    await context.close()
                except Exception as e:
                    print(f"独立コンテキストのクローズに失敗しました: {e}")


async def extract_item_info_from_url(url: str, page: Page) -> Optional[Dict]:
    """
    URLから商品情報を抽出
    
    Args:
        url: 商品URL
        page: Playwrightのページオブジェクト
    
    Returns:
        Dict: 商品情報（itemCode, shopCode, itemId, ItemName等）
    """
    try:
        # URLパターン: https://item.rakuten.co.jp/{shopCode}/{itemCode}/
        # または: https://item.rakuten.co.jp/{shopCode}/{itemCode}
        pattern = r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)'
        match = re.search(pattern, url)
        
        if not match:
            return None
        
        shop_code = match.group(1)
        item_id = match.group(2)
        item_code_combined = f"{shop_code}:{item_id}"
        item_name = await extract_item_name_from_item_page(page, url)
 
        return {
            'ItemURL': url,
            'ShopCode': shop_code,
            'ItemID': item_id,
            'ItemCode': item_code_combined,
            'ItemName': item_name,
            'Collection': '',
            'PostStatus': '',
            'PostedDate': '',
            'CollectionStatus': '',
            'CollectedDate': ''
        }
    
    except Exception as e:
        print(f"URL解析エラー ({url}): {e}")
        return None
 
 
async def extract_item_name_from_item_page(page: Page, item_url: str) -> str:
    """
    商品ページのHTMLから商品名を取得します。

    【取得方法】
    domcontentloadedでHTML骨格が読み込まれた後、
    各要素が表示されるまで個別に待機します。
    これにより広告や追跡ツールの通信を待たずに済み、
    タイムアウトを防ぎながら確実に商品名を取得できます。
    """
    try:
        # HTML骨格が読み込まれた時点で処理を開始
        await page.goto(item_url, wait_until='domcontentloaded', timeout=30000)

        # ① meta[itemprop="name"]が表示されるまで最大10秒待つ
        # 静的なショップはすぐ取得できる、動的なショップも10秒以内に描画される
        try:
            await page.wait_for_selector('meta[itemprop="name"]', timeout=10000)
            meta_name = await page.query_selector('meta[itemprop="name"]')
            if meta_name:
                item_name = await meta_name.get_attribute('content') or ''
                if item_name:
                    return item_name.strip()
        except Exception:
            pass  # タイムアウトした場合は次の要素を試す

        # ② og:titleが表示されるまで最大5秒待つ
        try:
            await page.wait_for_selector('meta[property="og:title"]', timeout=5000)
            meta_og = await page.query_selector('meta[property="og:title"]')
            if meta_og:
                item_name = await meta_og.get_attribute('content') or ''
                if item_name:
                    return item_name.strip()
        except Exception:
            pass  # タイムアウトした場合は次の要素を試す

        # ③ 最終手段: ページタイトル（domcontentloaded時点で取得可能）
        return (await page.title() or '').strip()

    except Exception as e:
        print(f"商品ページからItemNameを取得できませんでした: {item_url} - {e}")
        return ''
 
 
def build_items_to_write(favorite_items: List[Dict]) -> List[Dict]:
    """
    お気に入り商品リストをスプレッドシート書き込み用データに整形する
 
    get_favorite_items_info()で取得した商品リストに対して、
    ページから抽出したItemNameを含めて書き込み用の形式に変換します。
 
    Args:
        favorite_items: get_favorite_items_info()で取得した商品リスト
 
    Returns:
        List[Dict]: スプレッドシート書き込み用の商品情報リスト
    """
    items_to_write = []
    for item in favorite_items:
        item_code = item.get('ItemCode', '')
        if not item_code:
            continue
 
        items_to_write.append({
            'ItemURL': item.get('ItemURL', ''),
            'ShopCode': item.get('ShopCode', ''),
            'ItemID': item.get('ItemID', ''),
            'ItemCode': item_code,
            'ItemName': item.get('ItemName', ''),
            'PostStatus': '未',
            'CollectionStatus': '未'
        })
    return items_to_write
 
 
async def scroll_to_load_all_items(page: Page) -> List[str]:
    """
    ページをスクロールして全アイテムを読み込む
    
    ページの最下部までスクロールして、動的に読み込まれるアイテムを
    すべて取得します。
    
    Args:
        page: Playwrightのページオブジェクト
    
    Returns:
        List[str]: 商品URLのリスト
    """
    urls = []
    
    try:
        previous_height = await page.evaluate('document.body.scrollHeight')
        
        while True:
            # ページの最下部までスクロール
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
            
            # 新しい高さを取得
            new_height = await page.evaluate('document.body.scrollHeight')
            
            if new_height == previous_height:
                break
            
            previous_height = new_height
        
        # すべてのリンクを取得
        links = await page.query_selector_all("a[href*='item.rakuten.co.jp']")
        for link in links:
            href = await link.get_attribute('href')
            if href and 'item.rakuten.co.jp' in href:
                clean_url = href.split('?')[0]
                urls.append(clean_url)
    
    except Exception as e:
        print(f"スクロール処理でエラーが発生しました: {e}")
    
    return list(set(urls))