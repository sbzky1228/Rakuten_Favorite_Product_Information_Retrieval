"""
Google Sheets 書き込みモジュール - 商品情報をスプレッドシートに書き込む
 
楽天で取得した商品情報をGoogle Sheetsに記録します。
登録済みの商品は、お気に入りの取得時（fetch_favorites.py）に除外済みです。
 
【設計方針】
このファイルは書き込み処理のみに専念します。
接続・認証処理は google_sheets_utils.py が担当します。
 
【書き込み方針】
既存データは一切上書きしません。
新規商品のみスプレッドシートの一番下の行に追加します。
楽天市場のお気に入りから削除された商品もスプレッドシートには残ります。
"""
from config import SPREADSHEET_ID, SHEET_NAME
from logger import get_logger

# 初回実行時（シートが空の場合）に書き込む見出し
DEFAULT_HEADER = [
    'ItemURL', 'ShopCode', 'ItemID', 'ItemCode', 'ItemName',
    'CollectionName', 'CollectionGenre', 'PostStatus', 'PostedDate',
    'CollectionStatus', 'CollectedDate'
]


def write_items_info_to_google_sheet(service, items, header):
    """
    商品情報をGoogleスプレッドシートの一番下に追加する関数

    以下の処理を実行します:
    1. 1行目の見出しの並び順に合わせて行を作成（見出しに無い項目は空にする）
    2. スプレッドシートの一番下の行に追加（既存データは上書きしない）
    3. 追加結果をログ出力

    Args:
        service: Google Sheets APIのサービスオブジェクト
                 （google_sheets_utils.pyで取得済みのものを引き渡す）
        items (list): 新規商品の情報のリスト（登録済みの商品はfetch_favorites.pyで除外済み）
                    各要素は ItemURL, ShopCode, ItemID, ItemCode, ItemName, PostStatus, CollectionStatus を含む辞書
        header (list): スプレッドシート1行目の見出し（シートが空の場合は空のリスト）
    """
    logger = get_logger()
    if not items:
        logger.info("新規追加する商品がありません。")
        return

    # シートが空の場合（初回実行時）は既定の見出しを使い、先頭に見出し行を追加する
    columns = header or DEFAULT_HEADER
    values = [[item.get(column, '') for column in columns] for item in items]
    if not header:
        values.insert(0, list(DEFAULT_HEADER))
        logger.info("シートが空のため、1行目に見出しを追加します。")

    # スプレッドシートの一番下の行に追加（既存データは上書きしない）
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',  # 既存データの下に新規行として追加
        body={'values': values}
    ).execute()

    logger.info(f"✓ {len(items)}件の新規商品をスプレッドシートに追加しました")
    for item in items:
        logger.info(f"追加した商品: {item.get('ItemCode', '')} / {item.get('ItemName', '')}")
