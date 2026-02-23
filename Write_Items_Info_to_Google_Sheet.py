import os
from google_sheets_utils import get_google_sheets_service

def write_items_info_to_google_sheet(items, year, month, day, hour, minute):
    """
    商品情報をGoogleスプレッドシートに書き込む関数

    Args:
        items (list): 商品情報のリスト（各要素は辞書形式）
        year (int): 現在の年
        month (int): 現在の月
        day (int): 現在の日
        hour (int): 現在の時
        minute (int): 現在の分
    """
    # Google Sheets APIのサービスを取得
    service = get_google_sheets_service()

    # スプレッドシートのID
    spreadsheet_id = os.getenv('SPREADSHEET_ID')

    # 書き込む範囲
    range_name = os.getenv('SHEET_NAME', 'リスト!A1')  # シート名を適宜変更

    # 既存のデータを読み込んでitemCodeを取得
    existing_item_codes = set()
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])
        if values:
            # ヘッダーをスキップしてD列(ItemCode)を取得
            for row in values[1:]:
                if len(row) > 3:
                    existing_item_codes.add(row[3])  # D列はItemCode
    except Exception as e:
        print(f"既存データの読み込みに失敗しました: {e}")

    # ヘッダー行
    values = [
        ['ItemURL', 'ShopCode', 'ItemID', 'ItemCode', 'ItemName', 'CollectionName', 'CollectionGenre', 'PostStatus', 'PostedDate', 'CollectionStatus', 'CollectedDate']
    ]

    # 商品情報を追加 (重複チェック)
    for item in items:
        item_code = item.get('ItemCode', '')
        if item_code in existing_item_codes:
            continue  # 一致している場合は記載しない

        values.append([
            item.get('ItemURL', ''),  # ItemURL
            item.get('ShopCode', ''),  # ShopCode
            item.get('ItemID', ''),  # ItemID
            item_code,  # ItemCode
            item.get('ItemName', ''),  # ItemName
            '',  # CollectionName (空)
            '',  # CollectionGenre (空)
            item.get('PostStatus', '未'),  # PostStatus
            '',  # PostedDate (空)
            item.get('CollectionStatus', '未'),  # CollectionStatus
            ''  # CollectedDate (空)
        ])

    if len(values) == 1:
        print("新規追加する商品がありません。")
        return

    # 書き込みリクエストのボディ
    body = {
        'values': values
    }

    # スプレッドシートに書き込む
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()

    print(f"{result.get('updatedCells')} セルが更新されました。")