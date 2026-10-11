"""
メインプログラム - 楽天市場お気に入り商品情報取得

以下の処理フローを実行します:
1. スプレッドシート接続確認・既存データ取得（失敗したら即終了）
2. ブラウザを起動（user_dataに保存されたログインセッションを読み込む）
3. 楽天にログイン（ログイン済みの場合はスキップ）
4. お気に入り商品のうち、未登録の商品の情報（商品名など）を取得
5. Google Sheetsに書き込み
6. ブラウザを終了

【設計方針】
main.pyは各モジュールの関数を呼び出すだけのシンプルな構成にしています。
  - スプレッドシートの接続・既存データ取得 → google_sheets_utils.py
  - お気に入りURL収集・商品名取得         → fetch_favorites.py
  - スプレッドシートへの書き込み          → Write_Items_Info_to_Google_Sheet.py
"""
import asyncio
import traceback
from browser_manager import create_browser_manager
from rakuten_login import login_to_rakuten
from fetch_favorites import get_favorite_items_info
from google_sheets_utils import connect_to_sheets_and_get_existing_codes
from Write_Items_Info_to_Google_Sheet import write_items_info_to_google_sheet
from logger import get_logger


async def main():
    """メイン処理"""
    logger = get_logger()
    browser_manager = None

    try:
        logger.info("=" * 80)
        logger.info("楽天市場お気に入り商品情報取得プログラムを開始します")
        logger.info("=" * 80)

        # ステップ1: スプレッドシート接続確認・既存データ取得
        # ここで失敗した場合、ブラウザ起動前に即終了する
        logger.info("スプレッドシートへの接続を確認しています...")
        service, existing_item_codes, header = connect_to_sheets_and_get_existing_codes()
        if service is None:
            logger.error("スプレッドシートへの接続に失敗しました。処理を終了します。")
            return
        logger.info(f"接続成功（既存商品数: {len(existing_item_codes)}件）")

        # ステップ2: ブラウザを起動
        logger.info("ブラウザを起動しています...")
        browser_manager = await create_browser_manager()
        page = await browser_manager.get_page()

        # ステップ3: 楽天にログイン
        logger.info("楽天にログインしています...")
        if not await login_to_rakuten(page):
            logger.error("楽天へのログインに失敗しました。処理を終了します。")
            return

        # ステップ4: お気に入り商品のうち、未登録の商品の情報を取得
        logger.info("お気に入り商品の情報を取得しています...")
        items = await get_favorite_items_info(
            page, browser_manager.get_context(), max_items=200, existing_item_codes=existing_item_codes
        )
        if items is None:
            logger.error("お気に入り商品情報の取得に失敗しました。処理を終了します。")
            return

        # ステップ5: Google Sheetsに書き込み（serviceとheaderはステップ1で取得済みのものを渡す）
        write_items_info_to_google_sheet(service, items, header)

        logger.info("=" * 80)
        logger.info("楽天市場お気に入り商品情報取得プログラムが完了しました")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        logger.error(traceback.format_exc())

    finally:
        if browser_manager:
            logger.info("ブラウザを閉じています...")
            await browser_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
