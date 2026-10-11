"""
fetch_favorites のテスト（ブラウザは起動しない）

ページ操作はフェイクのページに置き換え、URLの収集・ページ送りの終了判定・
登録済み商品のスキップ・商品名の取得と整形・ページの後片付けを確認する。
"""
import asyncio
import pytest
import fetch_favorites as ff

ITEM = 'https://item.rakuten.co.jp'


def run(coro):
    return asyncio.run(coro)


# ============================================================
# 商品名の整形
# ============================================================

@pytest.mark.parametrize('title, expected', [
    ('【楽天市場】商品名：ショップ名', '商品名'),
    ('【楽天市場】商品：説明付き：ショップ名', '商品：説明付き'),  # 最後の「：」だけを区切りとみなす
    ('【楽天市場】商品名だけ', '商品名だけ'),
    ('  普通の名前  ', '普通の名前'),
    ('名前：コロン付き', '名前：コロン付き'),  # 【楽天市場】で始まらなければそのまま
    ('', ''),
])
def test_clean_page_title(title, expected):
    assert ff.clean_page_title(title) == expected


# ============================================================
# お気に入り一覧のURL収集・ページ送り
# ============================================================

class FakeNextButton:
    def __init__(self, page):
        self.page = page

    @property
    def first(self):
        return self

    async def count(self):
        return 1 if self.page.has_next_button else 0

    async def get_attribute(self, name):
        if name == 'aria-disabled' and self.page.disable_on_last and self.page.index == len(self.page.lists) - 1:
            return 'true'
        return None

    async def click(self):
        self.page.clicks += 1
        if self.page.index < len(self.page.lists) - 1:
            self.page.index += 1


class FakeListPage:
    """お気に入り一覧の代わり。lists[i] が iページ目のリンク（href）"""

    def __init__(self, lists, has_next_button=True, disable_on_last=True):
        self.lists = lists
        self.index = 0
        self.clicks = 0
        self.has_next_button = has_next_button
        self.disable_on_last = disable_on_last

    async def evaluate(self, _script):
        pass  # スクロール

    async def eval_on_selector_all(self, _selector, _script):
        return list(self.lists[self.index])

    def locator(self, selector):
        return FakeNextButton(self)


def test_collect_normalizes_and_dedupes_urls():
    page = FakeListPage([[
        f'{ITEM}/shopa/item1/?scid=af_pc',   # クエリは除く
        f'{ITEM}/shopa/item1/',              # 同じ商品は1件にする
        f'{ITEM}/shopa/item2#review',        # 末尾の / が無い・#付き
        'https://www.rakuten.co.jp/',        # 商品ページ以外は無視
    ]])
    urls = run(ff.collect_favorite_item_urls(page, max_items=200))
    assert urls == [f'{ITEM}/shopa/item1/', f'{ITEM}/shopa/item2/']


def test_collect_follows_pages_until_next_is_disabled():
    page = FakeListPage([
        [f'{ITEM}/s/{i}/' for i in range(20)],
        [f'{ITEM}/s/{i}/' for i in range(20, 40)],
        [f'{ITEM}/s/{i}/' for i in range(40, 45)],
    ])
    urls = run(ff.collect_favorite_item_urls(page, max_items=200))
    assert len(urls) == 45
    assert page.clicks == 2


def test_collect_stops_at_max_items():
    page = FakeListPage([
        [f'{ITEM}/s/{i}/' for i in range(20)],
        [f'{ITEM}/s/{i}/' for i in range(20, 40)],
    ])
    urls = run(ff.collect_favorite_item_urls(page, max_items=25))
    assert len(urls) == 25


def test_collect_stops_without_next_button():
    page = FakeListPage([[f'{ITEM}/s/1/']], has_next_button=False)
    assert run(ff.collect_favorite_item_urls(page, max_items=200)) == [f'{ITEM}/s/1/']
    assert page.clicks == 0


def test_collect_stops_when_page_does_not_change(monkeypatch):
    """「次へ」が無効にならず一覧も変わらない場合でも、新しい商品が0件なら終了する（無限ループ防止）"""
    async def no_change_wait(page, previous_hrefs, timeout=15000):
        pass
    monkeypatch.setattr(ff, 'wait_for_list_change', no_change_wait)
    page = FakeListPage([[f'{ITEM}/s/1/'], [f'{ITEM}/s/2/']], disable_on_last=False)
    urls = run(ff.collect_favorite_item_urls(page, max_items=200))
    assert urls == [f'{ITEM}/s/1/', f'{ITEM}/s/2/']
    assert page.clicks == 2  # 2ページ目の「次へ」の後、0件で終了


def test_collect_stops_at_page_limit(monkeypatch):
    """ページが無限に続いても上限ページ数で止まる"""
    class EndlessPage(FakeListPage):
        async def eval_on_selector_all(self, _selector, _script):
            return [f'{ITEM}/s/{self.clicks}/']

    async def no_change_wait(page, previous_hrefs, timeout=15000):
        pass
    monkeypatch.setattr(ff, 'wait_for_list_change', no_change_wait)
    monkeypatch.setattr(ff, 'MAX_FAVORITE_PAGES', 5)
    page = EndlessPage([[]], disable_on_last=False)
    urls = run(ff.collect_favorite_item_urls(page, max_items=200))
    assert len(urls) == 5


# ============================================================
# お気に入りページを開く（再認証を含む）
# ============================================================

class FakeArea:
    def __init__(self, page):
        self.page = page

    @property
    def first(self):
        return self

    async def count(self):
        return 1 if self.page.show_list else 0


class FakeFavoritesPage:
    """goto するたびに redirects の先頭のURLへ移動する"""

    def __init__(self, redirects, show_list=True):
        self.redirects = list(redirects)
        self.url = 'about:blank'
        self.show_list = show_list
        self.gotos = 0

    async def goto(self, url, **kwargs):
        self.gotos += 1
        self.url = self.redirects.pop(0) if self.redirects else url

    def locator(self, selector):
        return FakeArea(self)


LOGIN_URL = 'https://login.account.rakuten.com/session/upgrade'


def test_open_favorites_page_success():
    page = FakeFavoritesPage([])
    assert run(ff.open_favorites_page(page)) is True
    assert page.gotos == 1


def test_open_favorites_page_reauth_then_success(monkeypatch):
    calls = []

    async def complete_login_form(page):
        calls.append(page.url)
        return True
    monkeypatch.setattr(ff, 'complete_login_form', complete_login_form)
    page = FakeFavoritesPage([LOGIN_URL])
    assert run(ff.open_favorites_page(page)) is True
    assert calls == [LOGIN_URL]
    assert page.gotos == 2  # 再認証の後に開き直す


def test_open_favorites_page_reauth_failure(monkeypatch):
    async def complete_login_form(page):
        return False
    monkeypatch.setattr(ff, 'complete_login_form', complete_login_form)
    assert run(ff.open_favorites_page(FakeFavoritesPage([LOGIN_URL]))) is False


def test_open_favorites_page_list_not_shown_raises():
    """一覧が表示されない（ページ構造の変化など）場合はエラーにする"""
    page = FakeFavoritesPage([], show_list=False)
    with pytest.raises(RuntimeError, match='お気に入り一覧が表示されませんでした'):
        run(ff.open_favorites_page(page, timeout=300))


# ============================================================
# 商品名の取得
# ============================================================

class FakeElement:
    def __init__(self, content):
        self.content = content

    async def get_attribute(self, name):
        return self.content


class FakeItemPage:
    def __init__(self, meta=None, og=None, title='', goto_error=None):
        self.meta = meta
        self.og = og
        self._title = title
        self.goto_error = goto_error
        self.wait_states = []

    async def goto(self, url, **kwargs):
        if self.goto_error:
            raise self.goto_error

    async def wait_for_selector(self, selector, state='visible', timeout=None):
        self.wait_states.append(state)
        if self.meta is None:
            raise TimeoutError('meta not found')
        return FakeElement(self.meta)

    async def query_selector(self, selector):
        return FakeElement(self.og) if self.og is not None else None

    async def title(self):
        return self._title


def test_item_name_from_meta_waits_attached():
    page = FakeItemPage(meta=' 商品A ', og='【楽天市場】別の名前：店', title='t')
    assert run(ff.extract_item_name_from_item_page(page, f'{ITEM}/a/1/')) == '商品A'
    # metaは画面に表示されないため、visibleではなくattachedで待つこと
    assert page.wait_states == ['attached']


def test_item_name_falls_back_to_og_title():
    page = FakeItemPage(og='【楽天市場】商品B：ショップ', title='t')
    assert run(ff.extract_item_name_from_item_page(page, f'{ITEM}/a/1/')) == '商品B'


def test_item_name_falls_back_to_page_title():
    page = FakeItemPage(meta='', title='【楽天市場】商品C：ショップ')
    assert run(ff.extract_item_name_from_item_page(page, f'{ITEM}/a/1/')) == '商品C'


def test_item_name_error_returns_empty():
    page = FakeItemPage(goto_error=RuntimeError('net::ERR_FAILED'))
    assert run(ff.extract_item_name_from_item_page(page, f'{ITEM}/a/1/')) == ''


# ============================================================
# 並列取得（ページの使い回し・不要リソースの遮断・後片付け）
# ============================================================

class FakeRoute:
    def __init__(self, resource_type):
        self.request = type('Request', (), {'resource_type': resource_type})()
        self.result = None

    async def abort(self):
        self.result = 'abort'

    async def fallback(self):
        self.result = 'fallback'


@pytest.mark.parametrize('resource_type, expected', [
    ('image', 'abort'), ('media', 'abort'), ('font', 'abort'), ('stylesheet', 'abort'),
    ('document', 'fallback'), ('script', 'fallback'), ('xhr', 'fallback'),
])
def test_block_heavy_resources(resource_type, expected):
    route = FakeRoute(resource_type)
    run(ff.block_heavy_resources(route))
    assert route.result == expected


class FakeWorkerPage:
    def __init__(self):
        self.closed = False
        self.routes = []

    def set_default_timeout(self, timeout):
        pass

    def set_default_navigation_timeout(self, timeout):
        pass

    async def route(self, _pattern, handler):
        self.routes.append(handler)

    async def close(self):
        self.closed = True


class FakeContext:
    def __init__(self):
        self.pages = []

    async def new_page(self):
        page = FakeWorkerPage()
        self.pages.append(page)
        return page


def test_fill_item_names_reuses_limited_pages(monkeypatch):
    opened = {}

    async def extract(page, url):
        opened.setdefault(id(page), []).append(url)
        return f'名前 {url}'
    monkeypatch.setattr(ff, 'extract_item_name_from_item_page', extract)

    items = [{'ItemURL': f'{ITEM}/s/{i}/', 'ItemName': ''} for i in range(10)]
    context = FakeContext()
    run(ff.fill_item_names(context, items))

    assert all(item['ItemName'] == f"名前 {item['ItemURL']}" for item in items)
    assert len(context.pages) == ff.MAX_PARALLEL_PAGES          # 商品ごとにページを作らない
    assert all(page.closed for page in context.pages)           # 必ず閉じる
    assert all(page.routes == [ff.block_heavy_resources] for page in context.pages)
    assert sum(len(urls) for urls in opened.values()) == 10


def test_fill_item_names_few_items_opens_fewer_pages(monkeypatch):
    async def extract(page, url):
        return '名前'
    monkeypatch.setattr(ff, 'extract_item_name_from_item_page', extract)
    context = FakeContext()
    run(ff.fill_item_names(context, [{'ItemURL': f'{ITEM}/s/1/', 'ItemName': ''}]))
    assert len(context.pages) == 1


def test_fill_item_names_closes_pages_on_error(monkeypatch):
    async def extract(page, url):
        raise RuntimeError('想定外')
    monkeypatch.setattr(ff, 'extract_item_name_from_item_page', extract)
    context = FakeContext()
    with pytest.raises(RuntimeError):
        run(ff.fill_item_names(context, [{'ItemURL': f'{ITEM}/s/{i}/', 'ItemName': ''} for i in range(5)]))
    assert context.pages and all(page.closed for page in context.pages)


# ============================================================
# 全体（登録済みのスキップ・商品名が取れない商品の除外・失敗時のNone）
# ============================================================

@pytest.fixture
def favorites(monkeypatch):
    """open / collect / fill を差し替える。state を書き換えて状況を作る"""
    state = {'open': True, 'urls': [], 'names': {}, 'filled': None}

    async def open_page(page):
        return state['open']

    async def collect(page, max_items):
        return list(state['urls'])

    async def fill(context, items):
        state['filled'] = [item['ItemURL'] for item in items]
        for item in items:
            item['ItemName'] = state['names'].get(item['ItemURL'], '')

    monkeypatch.setattr(ff, 'open_favorites_page', open_page)
    monkeypatch.setattr(ff, 'collect_favorite_item_urls', collect)
    monkeypatch.setattr(ff, 'fill_item_names', fill)
    return state


def test_get_items_skips_registered_and_unnamed(favorites):
    favorites['urls'] = [f'{ITEM}/shopa/1/', f'{ITEM}/shopb/old/', f'{ITEM}/shopc/broken/']
    favorites['names'] = {f'{ITEM}/shopa/1/': '商品1'}
    items = run(ff.get_favorite_items_info(object(), object(), existing_item_codes={'shopb:old'}))

    # 登録済みの商品は商品ページを開かない
    assert favorites['filled'] == [f'{ITEM}/shopa/1/', f'{ITEM}/shopc/broken/']
    # 商品名を取れなかった商品は書き込まない（次回再取得）
    assert items == [{
        'ItemURL': f'{ITEM}/shopa/1/', 'ShopCode': 'shopa', 'ItemID': '1', 'ItemCode': 'shopa:1',
        'ItemName': '商品1', 'PostStatus': '未', 'CollectionStatus': '未',
    }]


def test_get_items_all_registered_returns_empty_list(favorites):
    favorites['urls'] = [f'{ITEM}/shopb/old/']
    assert run(ff.get_favorite_items_info(object(), object(), existing_item_codes={'shopb:old'})) == []
    assert favorites['filled'] is None


def test_get_items_open_failure_returns_none(favorites):
    """取得の失敗は None（0件の [] と区別し、「完了」と記録しない）"""
    favorites['open'] = False
    assert run(ff.get_favorite_items_info(object(), object())) is None


def test_get_items_unexpected_error_returns_none(favorites, monkeypatch):
    async def collect(page, max_items):
        raise RuntimeError('ページ構造が変わった')
    monkeypatch.setattr(ff, 'collect_favorite_item_urls', collect)
    assert run(ff.get_favorite_items_info(object(), object())) is None
