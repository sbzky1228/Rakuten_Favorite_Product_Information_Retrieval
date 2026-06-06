"""
Google Sheets 書き込みモジュール - 商品情報をスプレッドシートに書き込む
 
楽天で取得した商品情報をGoogle Sheetsに記録します。
重複チェック機能により、既に登録されている商品は上書きしません。
 
【設計方針】
このファイルは書き込み処理のみに専念します。
接続・認証処理は google_sheets_utils.py が担当します。
 
【書き込み方針】
既存データは一切上書きしません。
新規商品のみスプレッドシートの一番下の行に追加します。
楽天市場のお気に入りから削除された商品もスプレッドシートには残ります。
"""
from config import SPREADSHEET_ID, SHEET_NAME

def write_items_info_to_google_sheet(service, existing_item_codes, items, has_header):
    """
    商品情報をGoogleスプレッドシートの一番下に追加する関数
 
    以下の処理を実行します:
    1. 新規商品のみを抽出（既存商品は重複チェックでスキップ）
    2. スプレッドシートの一番下の行に追加（既存データは上書きしない）
    3. 更新結果をログ出力
 
    Args:
        service: Google Sheets APIのサービスオブジェクト
                 （google_sheets_utils.pyで取得済みのものを引き渡す）
        existing_item_codes (set): 既存の商品コードのset
                                   （google_sheets_utils.pyで取得済みのものを引き渡す）
        items (list): 商品情報のリスト（各要素は辞書形式で以下を含む）
                    - ItemURL: 商品URL
                    - ShopCode: ショップコード
                    - ItemID: 商品ID
                    - ItemCode: 商品コード
                    - ItemName: 商品名
                    - PostStatus: 投稿ステータス
                    - CollectionStatus: コレクションステータス
    """
    # 書き込む範囲（シート名はconfig.pyから取得）
    range_name = f"{SHEET_NAME}!A1"

    # 新規商品のみを抽出
    values = []
    for item in items:
        item_code = item.get('ItemCode', '')

        # 既に登録されている商品コードの場合はスキップ
        if item_code in existing_item_codes:
            continue

        # 商品情報を行として追加
        values.append([
            item.get('ItemURL', ''),            # A列: 商品URL
            item.get('ShopCode', ''),           # B列: ショップコード
            item.get('ItemID', ''),             # C列: 商品ID
            item_code,                          # D列: 商品コード
            item.get('ItemName', ''),           # E列: 商品名
            '',                                 # F列: コレクション名（初期値：空）
            '',                                 # G列: コレクションジャンル（初期値：空）
            item.get('PostStatus', '未'),       # H列: 投稿ステータス
            '',                                 # I列: 投稿日時（初期値：空）
            item.get('CollectionStatus', '未'), # J列: コレクションステータス
            ''                                  # K列: コレクション日時（初期値：空）
        ])

    # 新規商品がない場合は処理をスキップ
    if not values:
        print("新規追加する商品がありません。")
        return

    # スプレッドシートが空の場合（初回実行時）はヘッダーを先頭に追加する
    # existing_item_codesが空 = スプレッドシートにデータが存在しない
    if not has_header:
        values.insert(0, [
            'ItemURL', 'ShopCode', 'ItemID', 'ItemCode', 'ItemName',
            'CollectionName', 'CollectionGenre', 'PostStatus', 'PostedDate',
            'CollectionStatus', 'CollectedDate'
        ])
        print("[DEBUG] 初回実行のためヘッダーを追加します。")

    # スプレッドシートの一番下の行に追加（既存データは上書きしない）
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',  # 既存データの下に新規行として追加
        body={'values': values}
    ).execute()

    # 更新結果をログ出力
    updated_cells = result.get('updates', {}).get('updatedCells', 0)
    print(f"✓ {len(values)}件の新規商品を追加しました（{updated_cells}セル更新）")