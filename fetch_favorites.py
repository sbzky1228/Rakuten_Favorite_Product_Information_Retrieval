"""
お気に入り商品取得モジュール - 楽天市場のお気に入り商品情報を取得
"""
import asyncio
import re
from typing import List, Dict
from playwright.async_api import Page
import requests
from config import RAKUTEN_FAVORITES_URL, RAKUTEN_APP_ID, RAKUTEN_ITEM_BASE_URL


async def get_favorite_items_info(page: Page, max_items: int = 200) -> List[Dict]:
    """
    楽天市場のお気に入り商品情報を取得
    
    Args:
        page: Playwrightのページオブジェクト
        max_items: 取得する最大商品数
    
    Returns:
        List[Dict]: 商品情報のリスト
    """
    try:
        # お気に入りページに遷移
        await page.goto(RAKUTEN_FAVORITES_URL)
        await page.wait_for_load_state('networkidle')
        
        # すべてのお気に入り商品のURLを取得
        items_data = []
        
        # ページ内のすべてのリンクを取得
        links = await page.query_selector_all("a[href*='item.rakuten.co.jp']")
        
        urls = set()
        for link in links:
            href = await link.get_attribute('href')
            if href and 'item.rakuten.co.jp' in href:
                # クエリパラメータを削除したURLを保存
                clean_url = href.split('?')[0]
                urls.add(clean_url)
                
                if len(urls) >= max_items:
                    break
        
        print(f"取得したお気に入り商品数: {len(urls)}")
        
        # 各URLから商品情報を抽出
        for url in list(urls)[:max_items]:
            item_info = await extract_item_info_from_url(url)
            if item_info:
                items_data.append(item_info)
        
        return items_data
    
    except Exception as e:
        print(f"お気に入り商品情報の取得に失敗しました: {e}")
        return []


async def extract_item_info_from_url(url: str) -> Dict:
    """
    URLから商品情報を抽出
    
    Args:
        url: 商品URL
    
    Returns:
        Dict: 商品情報（itemCode, shopCode, itemId等）
    """
    try:
        # URLパターン: https://item.rakuten.co.jp/{shopCode}/{itemCode}/
        # または: https://item.rakuten.co.jp/{shopCode}/{itemCode}
        pattern = r'item\.rakuten\.co\.jp/([^/]+)/([^/]+)'
        match = re.search(pattern, url)
        
        if not match:
            return None
        
        shop_code = match.group(1)
        item_code = match.group(2)
        
        # 楽天APIから商品情報を取得
        item_name = ""
        item_id = ""
        
        return {
            'ItemURL': url,
            'ShopCode': shop_code,
            'ItemID': item_id,
            'ItemCode': item_code,
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


def get_item_info_from_api(item_code: str, app_id: str) -> Dict:
    """
    楽天APIから商品情報を取得
    
    Args:
        item_code: 商品コード
        app_id: 楽天AppID
    
    Returns:
        Dict: 商品情報
    """
    try:
        url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
        params = {
            'applicationId': app_id,
            'itemCode': item_code,
            'format': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'Items' in data and len(data['Items']) > 0:
                item = data['Items'][0]['Item']
                return {
                    'name': item.get('itemName', ''),
                    'item_id': item.get('itemNumber', ''),
                    'price': item.get('itemPrice', ''),
                    'image_url': item.get('smallImageUrl', '')
                }
    
    except Exception as e:
        print(f"APIエラー (itemCode: {item_code}): {e}")
    
    return None


async def scroll_to_load_all_items(page: Page) -> List[str]:
    """
    ページをスクロールして全アイテムを読み込む
    
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
