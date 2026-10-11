"""
main のテスト（ブラウザ・スプレッドシートには接続しない）

処理の流れ（接続失敗ならブラウザを起動しない、失敗時は書き込まない、
必ずブラウザを閉じる、「完了」は本当に完了したときだけ記録する）を確認する。
"""
import asyncio
import pytest
import main as main_mod
from logger import get_logger

COMPLETED = '楽天市場お気に入り商品情報取得プログラムが完了しました'


class FakeBrowserManager:
    def __init__(self):
        self.closed = False

    async def get_page(self):
        return object()

    def get_context(self):
        return object()

    async def close(self):
        self.closed = True


@pytest.fixture
def flow(monkeypatch):
    """main が使う関数を差し替える。state を書き換えて状況を作り、呼び出し状況を確認する"""
    state = {
        'service': object(), 'existing': {'a:1'}, 'header': ['ItemCode'],
        'login_ok': True, 'items': [], 'fetch_error': None,
        'browser': None, 'fetch_args': None, 'written': None,
    }

    def connect():
        return state['service'], state['existing'], state['header']

    async def create_browser_manager():
        state['browser'] = FakeBrowserManager()
        return state['browser']

    async def login(page):
        return state['login_ok']

    async def fetch(page, context, max_items, existing_item_codes):
        state['fetch_args'] = {'max_items': max_items, 'existing': existing_item_codes}
        if state['fetch_error']:
            raise state['fetch_error']
        return state['items']

    def write(service, items, header):
        state['written'] = (service, items, header)

    monkeypatch.setattr(main_mod, 'connect_to_sheets_and_get_existing_codes', connect)
    monkeypatch.setattr(main_mod, 'create_browser_manager', create_browser_manager)
    monkeypatch.setattr(main_mod, 'login_to_rakuten', login)
    monkeypatch.setattr(main_mod, 'get_favorite_items_info', fetch)
    monkeypatch.setattr(main_mod, 'write_items_info_to_google_sheet', write)
    return state


def log_lines_since(start):
    return get_logger().log_file.read_text(encoding='utf-8').splitlines()[start:]


def log_length():
    path = get_logger().log_file
    return len(path.read_text(encoding='utf-8').splitlines()) if path.exists() else 0


def test_success_writes_items(flow):
    flow['items'] = [{'ItemCode': 'b:2', 'ItemName': '商品2'}]
    start = log_length()
    asyncio.run(main_mod.main())

    assert flow['fetch_args'] == {'max_items': 200, 'existing': {'a:1'}}  # 登録済みの商品コードを渡す
    assert flow['written'] == (flow['service'], flow['items'], ['ItemCode'])
    assert flow['browser'].closed
    assert any(COMPLETED in line for line in log_lines_since(start))


def test_no_new_items_still_completes(flow):
    flow['items'] = []
    start = log_length()
    asyncio.run(main_mod.main())
    assert flow['written'][1] == []
    assert any(COMPLETED in line for line in log_lines_since(start))


def test_sheet_connection_failure_does_not_start_browser(flow):
    flow['service'] = None
    asyncio.run(main_mod.main())
    assert flow['browser'] is None
    assert flow['written'] is None


def test_login_failure_stops_and_closes_browser(flow):
    flow['login_ok'] = False
    asyncio.run(main_mod.main())
    assert flow['fetch_args'] is None
    assert flow['written'] is None
    assert flow['browser'].closed


def test_fetch_failure_is_not_recorded_as_completed(flow):
    """取得に失敗（None）したら書き込まず、「完了」と記録しない"""
    flow['items'] = None
    start = log_length()
    asyncio.run(main_mod.main())
    lines = log_lines_since(start)
    assert flow['written'] is None
    assert flow['browser'].closed
    assert any('お気に入り商品情報の取得に失敗しました' in line for line in lines)
    assert not any(COMPLETED in line for line in lines)


def test_unexpected_error_closes_browser(flow):
    flow['fetch_error'] = RuntimeError('想定外')
    start = log_length()
    asyncio.run(main_mod.main())
    lines = log_lines_since(start)
    assert flow['written'] is None
    assert flow['browser'].closed
    assert any('[ERROR] 予期しないエラーが発生しました: 想定外' in line for line in lines)
