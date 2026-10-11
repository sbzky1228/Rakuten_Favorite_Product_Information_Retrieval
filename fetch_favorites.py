"""
お気に入り商品取得モジュール - 楽天市場のお気に入り商品情報を取得
"""
import asyncio
import re
from typing import Dict, List, Optional
from playwright.async_api import BrowserContext, Page, Route
from config import RAKUTEN_FAVORITES_URL
from logger import get_logger
from rakuten_login import complete_login_form, is_login_page

# 商品URL（https://item.rakuten.co.jp/{ShopCode}/{ItemID}/）からショップコードと商品IDを取り出す
ITEM_URL_PATTERN = re.compile(r'item\.rakuten\.co\.jp/([^/?#]+)/([^/?#]+)')

# お気に入り一覧の商品リンクのうち、メインエリアにあるものだけを返す（サイドバーのおすすめ等は除外）
# リンクごとにブラウザとやり取りすると遅いため、1回の呼び出しでまとめて取得する
COLLECT_LINKS_SCRIPT = """
links => links
  .filter(a => !a.closest('.styles__sideBarBlock___M-hla'))
  .filter(a => a.closest('.bookmarkPage__block--centerContent') || a.closest('#bookmark-main'))
  .map(a => a.href)
"""

# お気に入り一覧の「次へ」ボタン
NEXT_BUTTON_SELECTOR = (
    "a.styles__nextPageBtn___3CWcG, a[aria-label='Next'], a[aria-label='次へ'], a:has-text('次へ')"
)

# 商品ページの同時取得数
MAX_PARALLEL_PAGES = 3

# お気に入り一覧のページ送りの上限（ページ構造の変化で終了判定できない場合の無限ループ防止）
MAX_FAVORITE_PAGES = 50

# 商品名の取得に不要なリソース（画像・動画・フォント・CSS）は読み込まず、メモリと通信量を抑える
BLOCKED_RESOURCE_TYPES = {'image', 'media', 'font', 'stylesheet'}


async def get_favorite_items_info(page: Page, context: BrowserContext, max_items: int = 200,
                                  existing_item_codes: Optional[set] = None) -> Optional[List[Dict]]:
    """
    楽天市場のお気に入り商品のうち、スプレッドシートに未登録の商品の情報を取得

    Args:
        page: Playwrightのページオブジェクト（お気に入りページ遷移用）
        context: Playwrightのブラウザコンテキスト（商品ページを開くページの作成用。ログインセッションを共有する）
        max_items: お気に入りから収集する商品URLの最大数（登録済みの商品も含む）
        existing_item_codes: スプレッドシートに登録済みの商品コードのset
                             登録済みの商品は商品ページを開かずにスキップする

    Returns:
        List[Dict]: スプレッドシートに書き込む商品情報のリスト（新規商品が無い場合は空のリスト）
        None: お気に入りページを開けないなど、取得に失敗した場合
    """
    logger = get_logger()
    existing_item_codes = existing_item_codes or set()

    try:
        if not await open_favorites_page(page):
            return None

        item_urls = await collect_favorite_item_urls(page, max_items)
        logger.info(f"お気に入り商品のURLを{len(item_urls)}件取得しました")

        # 登録済みの商品を除き、新規商品だけ商品ページを開く
        new_items = []
        for item_url in item_urls:
            match = ITEM_URL_PATTERN.search(item_url)
            shop_code, item_id = match.group(1), match.group(2)
            item_code = f"{shop_code}:{item_id}"
            if item_code in existing_item_codes:
                continue
            new_items.append({
                'ItemURL': item_url,
                'ShopCode': shop_code,
                'ItemID': item_id,
                'ItemCode': item_code,
                'ItemName': '',
                'PostStatus': '未',
                'CollectionStatus': '未',
            })

        logger.info(f"新規商品: {len(new_items)}件 / スキップ（登録済み）: {len(item_urls) - len(new_items)}件")
        if not new_items:
            return []

        await fill_item_names(context, new_items)

        # 商品名を取得できなかった商品は書き込まない（スプレッドシートに未登録のため、次回の実行で再取得する）
        items = []
        for item in new_items:
            if item['ItemName']:
                items.append(item)
            else:
                logger.warning(f"商品名を取得できなかったため、今回は登録しません: {item['ItemURL']}")
        return items

    except Exception as e:
        logger.error(f"お気に入り商品情報の取得に失敗しました: {e}")
        return None


async def open_favorites_page(page: Page, timeout: int = 30000) -> bool:
    """
    お気に入りページを開く

    お気に入りページの表示時に楽天から再認証（ログイン画面）を求められた場合は、
    認証を完了させてからお気に入りページを開き直します。

    Args:
        page: Playwrightのページオブジェクト
        timeout: お気に入り一覧（またはログイン画面）が表示されるまでの最大待機時間（ミリ秒）

    Returns:
        bool: お気に入りページを開けた場合True
    """
    logger = get_logger()
    favorites_area = page.locator('#bookmark-main, .bookmarkPage__block--centerContent').first

    async def goto_favorites() -> bool:
        """お気に入りページを開き、一覧が表示されればTrue、ログイン画面に移動すればFalse"""
        await page.goto(RAKUTEN_FAVORITES_URL, wait_until='domcontentloaded')
        deadline = asyncio.get_running_loop().time() + (timeout / 1000)
        while asyncio.get_running_loop().time() < deadline:
            if is_login_page(page.url):
                return False
            if await favorites_area.count() > 0:
                return True
            await asyncio.sleep(0.5)
        raise RuntimeError(f"お気に入り一覧が表示されませんでした。現在のURL: {page.url}")

    if await goto_favorites():
        return True

    logger.info("お気に入りページの表示前に再認証を求められたため、ログインします")
    if not await complete_login_form(page):
        logger.error("お気に入りページ表示前の再認証に失敗しました")
        return False

    if await goto_favorites():
        return True

    logger.error(f"再認証後もお気に入りページを表示できませんでした。現在のURL: {page.url}")
    return False


async def collect_favorite_item_urls(page: Page, max_items: int) -> List[str]:
    """
    お気に入り一覧をページ送りしながら、商品URLを重複なく収集する

    Args:
        page: お気に入りページを表示しているページ
        max_items: 収集する商品URLの最大数

    Returns:
        List[str]: 商品URL（https://item.rakuten.co.jp/{ShopCode}/{ItemID}/ の形式）
    """
    item_urls = []
    seen_item_codes = set()

    for page_count in range(1, MAX_FAVORITE_PAGES + 1):
        # 動的ロード対策 (スクロール)
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)

        hrefs = await page.eval_on_selector_all("a[href*='item.rakuten.co.jp']", COLLECT_LINKS_SCRIPT)
        added = 0
        for href in hrefs:
            match = ITEM_URL_PATTERN.search(href)
            if not match:
                continue
            shop_code, item_id = match.group(1), match.group(2)
            item_code = f"{shop_code}:{item_id}"
            if item_code in seen_item_codes:
                continue
            seen_item_codes.add(item_code)
            # クエリ（?scid=...）等を除いた形にそろえる
            item_urls.append(f"https://item.rakuten.co.jp/{shop_code}/{item_id}/")
            added += 1
            if len(item_urls) >= max_items:
                return item_urls

        print(f"[DEBUG] お気に入りページ {page_count}: {added}件追加（累計 {len(item_urls)}件）")

        # 新しい商品が1件も無い = ページが切り替わっていない、または最終ページ
        if added == 0 and page_count > 1:
            break

        next_button = page.locator(NEXT_BUTTON_SELECTOR).first
        if await next_button.count() == 0 or await next_button.get_attribute('aria-disabled') == 'true':
            print("[DEBUG] 次ページがありません。収集を終了します。")
            break

        await next_button.click()
        await wait_for_list_change(page, hrefs)
    else:
        get_logger().warning(f"お気に入り一覧のページ送りが上限（{MAX_FAVORITE_PAGES}ページ）に達したため、収集を終了します")

    return item_urls


async def wait_for_list_change(page: Page, previous_hrefs: List[str], timeout: int = 15000):
    """「次へ」をクリックした後、一覧の商品リンクが切り替わるまで待つ（同一ページ内で書き換わる場合にも対応）"""
    deadline = asyncio.get_running_loop().time() + (timeout / 1000)
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.5)
        try:
            hrefs = await page.eval_on_selector_all("a[href*='item.rakuten.co.jp']", COLLECT_LINKS_SCRIPT)
        except Exception:
            continue  # ページ遷移中は取得できないため、次のループで再取得する
        if hrefs and hrefs != previous_hrefs:
            return


async def block_heavy_resources(route: Route):
    """商品名の取得に不要なリソースの読み込みを中止する"""
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.fallback()


async def fill_item_names(context: BrowserContext, items: List[Dict]):
    """
    商品ページを開いて商品名を取得し、各商品のItemNameに設定する

    【メモリ・速度対策】
    同時にMAX_PARALLEL_PAGES個のページだけを作成し、各ページで商品ページを順番に開き直して使い回す。
    画像・CSS等は読み込まない。ページは処理後に必ず閉じる。

    Args:
        context: ブラウザコンテキスト（ログインセッションを共有する）
        items: 商品情報のリスト（ItemURLを使用し、ItemNameを書き換える）
    """
    queue: asyncio.Queue = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)

    async def worker():
        page = await context.new_page()
        try:
            page.set_default_timeout(30000)
            page.set_default_navigation_timeout(30000)
            await page.route("**/*", block_heavy_resources)
            while not queue.empty():
                item = queue.get_nowait()
                item['ItemName'] = await extract_item_name_from_item_page(page, item['ItemURL'])
        finally:
            await page.close()

    await asyncio.gather(*(worker() for _ in range(min(MAX_PARALLEL_PAGES, len(items)))))


async def extract_item_name_from_item_page(page: Page, item_url: str) -> str:
    """
    商品ページのHTMLから商品名を取得する

    【取得方法】
    domcontentloadedでHTML骨格が読み込まれた時点で、次の順に商品名を探す。
    広告や追跡ツールの通信は待たない。
      ① meta[itemprop="name"]（動的に描画するショップもあるため最大10秒待つ）
      ② meta[property="og:title"]
      ③ ページタイトル
    ②③は「【楽天市場】商品名：ショップ名」の形式のため、商品名の部分だけを取り出す。

    Returns:
        str: 商品名（取得できなかった場合は空文字）
    """
    try:
        await page.goto(item_url, wait_until='domcontentloaded')

        # meta要素は画面に表示されないため、state='attached'（DOMへの追加）で待つ
        try:
            meta_name = await page.wait_for_selector('meta[itemprop="name"]', state='attached', timeout=10000)
            item_name = (await meta_name.get_attribute('content') or '').strip()
            if item_name:
                return item_name
        except Exception:
            pass  # 見つからない場合は次の方法を試す

        og_title = await page.query_selector('meta[property="og:title"]')
        title = (await og_title.get_attribute('content') or '') if og_title else ''
        return clean_page_title(title or await page.title())

    except Exception as e:
        get_logger().error(f"商品ページから商品名を取得できませんでした: {item_url} - {e}")
        return ''


def clean_page_title(title: str) -> str:
    """「【楽天市場】商品名：ショップ名」形式のタイトルから商品名の部分を取り出す"""
    title = title.strip()
    if title.startswith('【楽天市場】'):
        title = title[len('【楽天市場】'):]
        # 末尾の「：ショップ名」を除く（商品名に「：」が含まれる場合を考慮し、最後の1つだけ）
        if '：' in title:
            title = title.rsplit('：', 1)[0]
    return title.strip()
