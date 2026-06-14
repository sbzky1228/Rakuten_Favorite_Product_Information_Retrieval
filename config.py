"""
設定ファイル - 環境変数や定数を管理

このモジュールでは以下を定義します：
- 楽天ログイン情報（ユーザーID、パスワード）
- Google Sheets連携情報（spreadsheet ID、sheet name）
- API情報（楽天AppID、OpenAI API Key）
- Playwrightとタイムアウト設定
- Google Sheets APIスコープ
- スプレッドシート列定義
- 楽天ルームURL定義
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def _resolve_env_path() -> Path | None:
    candidates = []
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys._MEIPASS) / '.env')
        candidates.append(Path(sys.executable).resolve().parent / '.env')
    candidates.append(Path.cwd() / '.env')
    candidates.append(Path(__file__).resolve().parent / '.env')
    for path in candidates:
        if path.exists():
            return path.resolve()
    return None


def _resolve_path_from_env(value: str, base_dir: Path) -> str:
    if not value:
        return ''
    path = Path(value)
    if path.is_absolute():
        return str(path)

    candidate = base_dir / path
    if candidate.exists():
        return str(candidate.resolve())

    candidate = Path.cwd() / path
    if candidate.exists():
        return str(candidate.resolve())

    candidate = Path(__file__).resolve().parent / path
    return str(candidate.resolve())


# .envファイルを読み込む（機密な情報を環境変数から取得）
ENV_PATH = _resolve_env_path()
if ENV_PATH:
    load_dotenv(str(ENV_PATH))
    ENV_DIR = ENV_PATH.parent
else:
    load_dotenv('.env')
    ENV_DIR = Path.cwd()

# ============================================================
# 楽天ログイン情報
# ============================================================
RAKUTEN_USER_ID = os.getenv('RAKUTEN_USER_ID', '')  # 楽天会員ID
RAKUTEN_PASSWORD = os.getenv('RAKUTEN_PASSWORD', '')  # 楽天パスワード

# ============================================================
# Google Sheets連携情報
# ============================================================
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '')  # Googleスプレッドシートの一意のID
SHEET_NAME = os.getenv('SHEET_NAME', 'Sheet1')  # シート名
SERVICE_ACCOUNT_PATH = _resolve_path_from_env(os.getenv('SERVICE_ACCOUNT_PATH', ''), ENV_DIR)

# ============================================================
# Playwright設定
# （ブラウザ自動化ツールの設定）
# ============================================================
PLAYWRIGHT_BROWSERS_PATH = _resolve_path_from_env(os.getenv('PLAYWRIGHT_BROWSERS_PATH', ''), ENV_DIR)
CHROMIUM_EXECUTABLE_PATH = _resolve_path_from_env(os.getenv('CHROMIUM_EXECUTABLE_PATH', ''), ENV_DIR)

if not PLAYWRIGHT_BROWSERS_PATH and getattr(sys, 'frozen', False):
    default_playwright = Path(os.path.expanduser('~')) / 'AppData' / 'Local' / 'ms-playwright'
    if default_playwright.exists():
        PLAYWRIGHT_BROWSERS_PATH = str(default_playwright)

if PLAYWRIGHT_BROWSERS_PATH:
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_BROWSERS_PATH

HEADLESS_MODE = False   # ヘッドレスモード（UIを表示しない）
BROWSER_TIMEOUT = 60000  # ブラウザタイムアウト時間（ミリ秒）
PAGE_LOAD_TIMEOUT = 30000  # ページ読み込み待機時間（ミリ秒）
NAVIGATION_TIMEOUT = 30000  # ナビゲーション待機時間（ミリ秒）

# ============================================================
# APIスコープ
# ============================================================
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# ============================================================
# スプレッドシート列定義
# （各列がどの情報を保持するかを指定）
# ============================================================
COLUMN_MAP = {
    'ItemURL': 'A',           # A列: 商品URL
    'ShopCode': 'B',          # B列: ショップコード
    'ItemID': 'C',            # C列: 商品ID
    'ItemCode': 'D',          # D列: 商品コード
    'ItemName': 'E',          # E列: 商品名
    'CollectionName': 'F',    # F列: コレクション名
    'CollectionGenre': 'G',   # G列: コレクションジャンル
    'PostStatus': 'H',        # H列: 投稿ステータス (未/済)
    'PostedDate': 'I',        # I列: 投稿日時
    'CollectionStatus': 'J',  # J列: コレクションステータス (未/済)
    'CollectedDate': 'K'      # K列: コレクション日時
}

# ============================================================
# 楽天市場URL定義
# ============================================================
RAKUTEN_FAVORITES_URL = "https://my.bookmark.rakuten.co.jp/"  # 楽天お気に入りページ
RAKUTEN_FAVORITES_ALT_URL = "https://my.bookmark.rakuten.co.jp/?l-id=pc_header_func_bookmark"  # 代替URL（マイページ）
RAKUTEN_ICHIBA_BASE_URL = "https://www.rakuten.co.jp/"  # 楽天市場ベースURL
RAKUTEN_ITEM_BASE_URL = "https://item.rakuten.co.jp"  # 楽天商品ページベースURL
