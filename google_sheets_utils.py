"""
Google Sheets ユーティリティモジュール - Google Sheetsサービス初期化関数
 
Google Sheets APIへの接続・認証とサービスオブジェクトの取得を担当します。
 
【認証方式について】
サービスアカウント方式を使用しています。
OAuth2方式と異なりトークンの期限切れが発生しないため、
認証情報の更新処理は不要です。
サービスアカウントのJSONファイルのパスは .env の SERVICE_ACCOUNT_PATH に記載してください。
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SCOPES, SERVICE_ACCOUNT_PATH, SPREADSHEET_ID, SHEET_NAME
from logger import get_logger
 
 
def connect_to_sheets_and_get_existing_codes():
    """
    スプレッドシートに接続し、既存の商品コード一覧を取得する
 
    【この関数をmain()の最初に実行する理由】
    - 接続失敗を早期に検知し、無駄なブラウザ起動・楽天処理を防ぐ
    - 取得したserviceを後続の書き込み処理に引き渡すことで
      書き込み時に再度認証する必要がなくなる
    - 重複チェック用の既存商品コードも同時に取得しておくことで
      書き込み時のAPI呼び出しを1回に抑える
 
    Returns:
        tuple: (service, existing_item_codes, header)
            - service: Google Sheets APIのサービスオブジェクト（失敗時はNone）
            - existing_item_codes: 既存の商品コードのset（失敗時は空のset）
            - header: 1行目の見出しのリスト（シートが空の場合・失敗時は空のリスト）
    """
    try:
        # サービスアカウントで認証（トークン期限切れ・更新処理は不要）
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_PATH,
            scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
 
        # 既存の商品コードを取得（重複チェック用）
        # シート全体の値を取得する（単一セルA1のみだとデータが取れないため）
        range_name = f"{SHEET_NAME}!A1:K"
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
 
        existing_item_codes = set()
        existing_values = result.get('values', [])
        header = existing_values[0] if existing_values else []
        if existing_values:
            # ヘッダー行からItemCodeの列を探し、2行目以降の商品コードを取得
            if 'ItemCode' not in header:
                get_logger().error("スプレッドシートの1行目に必須列 'ItemCode' が見つかりません")
                return None, set(), []
            item_code_col = header.index('ItemCode')
            for row in existing_values[1:]:
                if len(row) > item_code_col and row[item_code_col]:
                    existing_item_codes.add(row[item_code_col])
 
        return service, existing_item_codes, header
 
    except Exception as e:
        get_logger().error(f"スプレッドシートへの接続に失敗しました: {e}")
        return None, set(), []