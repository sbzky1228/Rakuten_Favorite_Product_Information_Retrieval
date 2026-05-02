"""
メインプログラム - 楽天市場お気に入り商品情報取得
 
以下の処理フローを実行します:
1. スプレッドシート接続確認・既存データ取得（失敗したら即終了）
2. ブラウザを起動
3. 楽天にログイン
4. お気に入り商品情報を取得
5. 商品ページのHTMLから商品名を取得し書き込み用データに整形
6. Google Sheetsに書き込み
7. ブラウザを終了
 
【設計方針】
main.pyは各モジュールの関数を呼び出すだけのシンプルな構成にしています。
複雑な処理は各モジュールに任せています。
  - スプレッドシートの接続・既存データ取得 → google_sheets_utils.py
  - お気に入りURL収集・API取得・整形      → fetch_favorites.py
  - スプレッドシートへの書き込み          → Write_Items_Info_to_Google_Sheet.py
"""
import asyncio
from browser_manager import create_browser_manager
from rakuten_login import login_to_rakuten
from fetch_favorites import get_favorite_items_info, build_items_to_write
from google_sheets_utils import connect_to_sheets_and_get_existing_codes
from Write_Items_Info_to_Google_Sheet import write_items_info_to_google_sheet
from logger import Logger
 
 
async def main():
    """
    メイン処理
    """
    logger = Logger()
    browser_manager = None
 
    try:
        logger.info("=" * 80)
        logger.info("楽天市場お気に入り商品情報取得プログラムを開始します")
        logger.info("=" * 80)
 
        # ============================================================
        # ステップ1: スプレッドシート接続確認・既存データ取得
        # ここで失敗した場合、ブラウザ起動前に即終了する
        # ============================================================
        logger.info("スプレッドシートへの接続を確認しています...")
        service, existing_item_codes = connect_to_sheets_and_get_existing_codes()
 
        if service is None:
            logger.error("スプレッドシートへの接続に失敗しました。処理を終了します。")
            return
 
        logger.info(f"接続成功（既存商品数: {len(existing_item_codes)}件）")
 
        # ============================================================
        # ステップ2: ブラウザを起動
        # ============================================================
        logger.info("ブラウザを起動しています...")
        browser_manager = await create_browser_manager()
        page = await browser_manager.get_page()
 
        # ============================================================
        # ステップ3: 楽天にログイン
        # ============================================================
        logger.info("楽天にログインしています...")
        if not await login_to_rakuten(page):
            logger.error("楽天へのログインに失敗しました。処理を終了します。")
            return
 
        # ============================================================
        # ステップ4: お気に入り商品のURLを取得
        # ============================================================
        logger.info("お気に入り商品のURLを取得しています...")
        favorite_items = await get_favorite_items_info(page, browser_manager.get_browser(), max_items=200)
 
        if not favorite_items:
            logger.warning("お気に入り商品が見つかりません。処理を終了します。")
            return
 
        logger.info(f"{len(favorite_items)}件のお気に入り商品を取得しました")
 
        # ============================================================
        # ステップ5: 商品ページのHTMLから商品名を取得し書き込み用データに整形
        # ============================================================
        logger.info("商品ページのHTMLから商品名を取得しています...")
        items_to_write = build_items_to_write(favorite_items)
 
        if not items_to_write:
            logger.warning("書き込む商品がありません。処理を終了します。")
            return
 
        # ============================================================
        # ステップ6: Google Sheetsに書き込み
        # serviceとexisting_item_codesはステップ1で取得済みのものを渡す
        # ============================================================
        logger.info("Google Sheetsに商品情報を書き込んでいます...")
        write_items_info_to_google_sheet(service, existing_item_codes, items_to_write)
 
        logger.info("=" * 80)
        logger.info("楽天市場お気に入り商品情報取得プログラムが完了しました")
        logger.info("=" * 80)
 
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
 
    finally:
        if browser_manager:
            logger.info("ブラウザを閉じています...")
            await browser_manager.close()
 
 
if __name__ == "__main__":
    asyncio.run(main())