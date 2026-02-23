"""
メインプログラム - 楽天市場お気に入り商品情報取得
"""
import asyncio
import os
from browser_manager import create_browser_manager
from rakuten_login import login_to_rakuten
from fetch_favorites import get_favorite_items_info
from Get_Favorite_Items_info import get_item_info_from_api
from Write_Items_Info_to_Google_Sheet import write_items_info_to_google_sheet
from logger import Logger
import datetime


async def main():
    """メイン処理"""
    logger = Logger()
    browser_manager = None

    try:
        logger.info("=" * 80)
        logger.info("楽天市場お気に入り商品情報取得プログラムを開始します")
        logger.info("=" * 80)

        # ブラウザを起動
        logger.info("ブラウザを起動しています...")
        browser_manager = await create_browser_manager()
        page = await browser_manager.get_page()

        # 楽天にログイン
        logger.info("楽天にログインしています...")
        if not await login_to_rakuten(page):
            logger.error("楽天へのログインに失敗しました")
            return

        # お気に入り商品のURLを取得
        logger.info("お気に入り商品のURLを取得しています...")
        favorite_items = await get_favorite_items_info(page, max_items=200)

        if not favorite_items:
            logger.warning("お気に入り商品が見つかりません")
            return

        logger.info(f"{len(favorite_items)}件のお気に入り商品を取得しました")

        # 楽天APIでItemNameを取得し、データを準備
        items_to_write = []
        for item in favorite_items:
            item_code = item.get('item_code', '')
            if not item_code:
                continue

            # APIでItemNameを取得
            api_info = get_item_info_from_api(item_code, os.getenv('RAKUTEN_APP_ID'))
            item_name = api_info.get('name', '') if api_info else ''
            item_id = api_info.get('item_id', '') if api_info else ''

            # データを準備
            item_data = {
                'ItemURL': item.get('ItemURL', ''),
                'ShopCode': item.get('ShopCode', ''),
                'ItemID': item_id,
                'ItemCode': item_code,
                'ItemName': item_name,
                'PostStatus': '未',
                'CollectionStatus': '未'
            }
            items_to_write.append(item_data)

        # Google Sheetsに書き込み
        if items_to_write:
            logger.info("Google Sheetsに商品情報を書き込んでいます...")
            now = datetime.datetime.now()
            write_items_info_to_google_sheet(items_to_write, now.year, now.month, now.day, now.hour, now.minute)

        logger.info("=" * 80)
        logger.info("楽天市場お気に入り商品情報取得プログラムが完了しました")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())

    finally:
        # ブラウザを閉じる
        if browser_manager:
            logger.info("ブラウザを閉じています...")
            await browser_manager.close()


if __name__ == "__main__":
    asyncio.run(main())