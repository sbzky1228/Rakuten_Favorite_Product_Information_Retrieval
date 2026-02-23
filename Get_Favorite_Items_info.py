import os
import requests
from typing import List, Dict

def get_favorite_items_info(driver=None, max_items: int = 200) -> List[Dict]:
    """
    楽天APIを使用して商品情報を取得する関数（お気に入りリストはAPIで直接取得できないため、
    SeleniumでURLを取得し、APIで詳細情報を補完）

    戻り値: 商品情報の辞書リスト（例: {'title','url','image','price'}）
    """
    # 楽天APIキー
    rakuten_app_id = os.getenv('RAKUTEN_APP_ID')

    items = []

    # Seleniumで楽天ルームのお気に入りから商品URLを取得（APIで置き換え不可）
    if driver:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        # お気に入りページに移動
        driver.get("https://my.bookmark.rakuten.co.jp/")
        time.sleep(2)

        # 商品リンクを取得
        anchors = driver.find_elements(By.TAG_NAME, "a")
        urls = []
        for a in anchors:
            href = a.get_attribute('href')
            if href and 'item.rakuten.co.jp' in href:
                urls.append(href)
                if len(urls) >= max_items:
                    break

        # APIキーがあればAPIで詳細を取得、なければSeleniumで基本情報を取得
        if rakuten_app_id:
            for url in urls:
                item_code = extract_item_code_from_url(url)
                if item_code:
                    item_info = get_item_info_from_api(item_code, rakuten_app_id)
                    if item_info:
                        items.append(item_info)
        else:
            # APIキーなし: Seleniumで基本情報を取得
            for url in urls:
                item_info = {
                    'item_code': extract_item_code_from_url(url) or '',
                    'shop_id': '',
                    'item_number': '',
                    'name': 'Unknown',  # Seleniumでタイトルを取得する場合は追加実装
                    'url': url,
                    'room_post_url': '',
                    'collection': '',
                    'status': '',
                    'last_posted_date': '',
                    'collection_status': '',
                    'note': '',
                    'description': ''
                }
                items.append(item_info)
    else:
        # driverなし: APIキーがあれば検索
        if rakuten_app_id:
            sample_keywords = ['人気商品', 'おすすめ']
            for keyword in sample_keywords:
                api_items = search_items_by_api(keyword, rakuten_app_id, max_items // len(sample_keywords))
                items.extend(api_items)

    return items

def extract_item_code_from_url(url: str) -> str:
    """
    URLから商品コードを抽出
    """
    # 例: https://item.rakuten.co.jp/xxx/yyy/ から yyy を抽出
    parts = url.rstrip('/').split('/')
    if len(parts) >= 5:
        return parts[-1]
    return None

def get_item_info_from_api(item_code: str, app_id: str) -> Dict:
    """
    楽天APIで商品詳細を取得
    """
    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
    params = {
        'applicationId': app_id,
        'itemCode': item_code,
        'format': 'json'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'Items' in data and data['Items']:
            item = data['Items'][0]['Item']
            return {
                'item_code': item.get('itemCode', ''),
                'shop_id': item.get('shopCode', ''),
                'item_number': '',  # APIにない場合
                'name': item.get('itemName', ''),
                'url': item.get('itemUrl', ''),
                'room_post_url': '',
                'collection': '',
                'status': '',
                'last_posted_date': '',
                'collection_status': '',
                'note': '',
                'description': item.get('itemCaption', '')  # 説明文
            }
    return None

def search_items_by_api(keyword: str, app_id: str, max_items: int) -> List[Dict]:
    """
    楽天APIでキーワード検索
    """
    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
    params = {
        'applicationId': app_id,
        'keyword': keyword,
        'hits': max_items,
        'format': 'json'
    }
    response = requests.get(url, params=params)
    items = []
    if response.status_code == 200:
        data = response.json()
        for item_data in data.get('Items', []):
            item = item_data['Item']
            items.append({
                'item_code': item.get('itemCode', ''),
                'shop_id': item.get('shopCode', ''),
                'item_number': '',
                'name': item.get('itemName', ''),
                'url': item.get('itemUrl', ''),
                'room_post_url': '',
                'collection': '',
                'status': '',
                'last_posted_date': '',
                'collection_status': '',
                'note': '',
                'description': item.get('itemCaption', '')
            })
    return items