"""
設定ファイル - 環境変数や定数を管理
"""
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv('.env')

# 楽天ログイン情報
RAKUTEN_USER_ID = os.getenv('RAKUTEN_USER_ID', '')
RAKUTEN_PASSWORD = os.getenv('RAKUTEN_PASSWORD', '')

# Google Sheets情報
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '')
SHEET_NAME = os.getenv('SHEET_NAME', 'Sheet1')

# API情報
RAKUTEN_APP_ID = os.getenv('RAKUTEN_APP_ID', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Playwrightの設定
HEADLESS_MODE = True  # ヘッドレスモード
BROWSER_TIMEOUT = 30000  # タイムアウト（ミリ秒）
PAGE_LOAD_TIMEOUT = 10000  # ページロード待機時間
NAVIGATION_TIMEOUT = 10000  # ナビゲーション待機時間

# Google Sheets APIスコープ
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# スプレッドシート列定義
COLUMN_MAP = {
    'ItemURL': 'A',
    'ShopCode': 'B',
    'ItemID': 'C',
    'ItemCode': 'D',
    'ItemName': 'E',
    'Collection': 'F',
    'PostStatus': 'G',
    'PostedDate': 'H',
    'CollectionStatus': 'I',
    'CollectedDate': 'J'
}

# Rakuten Room URLs
RAKUTEN_FAVORITES_URL = "https://my.bookmark.rakuten.co.jp/"
RAKUTEN_ROOM_BASE_URL = "https://room.rakuten.co.jp"
RAKUTEN_ITEM_BASE_URL = "https://item.rakuten.co.jp"
