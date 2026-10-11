"""
スプレッドシートの読み書きのテスト（Google には接続しない）

google_sheets_utils（接続・登録済み商品コードの取得）と
Write_Items_Info_to_Google_Sheet（追記）を、フェイクの service で確認する。
"""
import pytest
import google_sheets_utils as gsu
import Write_Items_Info_to_Google_Sheet as writer

HEADER = list(writer.DEFAULT_HEADER)


class FakeService:
    """Google Sheets API の service の代わり。get の戻り値を values で指定し、append の内容を記録する"""

    def __init__(self, values=None):
        self.values_data = values or []
        self.appended = []

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def get(self, **kwargs):
        self.request = ('get', kwargs)
        return self

    def append(self, **kwargs):
        self.request = ('append', kwargs)
        self.appended.append(kwargs)
        return self

    def execute(self):
        if self.request[0] == 'get':
            return {'values': self.values_data} if self.values_data else {}
        return {}


@pytest.fixture
def connect(monkeypatch):
    """サービスアカウントの読み込みと build を差し替え、指定した values を返す service を使わせる"""
    def setup(values):
        service = FakeService(values)
        monkeypatch.setattr(gsu.service_account.Credentials, 'from_service_account_file',
                            lambda *_args, **_kwargs: object())
        monkeypatch.setattr(gsu, 'build', lambda *_args, **_kwargs: service)
        return gsu.connect_to_sheets_and_get_existing_codes()
    return setup


# ============================================================
# 接続・登録済み商品コードの取得
# ============================================================

def test_existing_codes_found_by_header_name(connect):
    """ItemCode の列は見出し名で探す（列の順番に依存しない）"""
    values = [
        ['ItemURL', 'ItemName', 'ItemCode'],
        ['u1', '商品1', 'a:1'],
        ['u2', '商品2', 'b:2'],
        ['u3'],                 # ItemCode が無い行
        ['u4', '商品4', ''],    # 空の ItemCode
    ]
    service, codes, header = connect(values)
    assert service is not None
    assert codes == {'a:1', 'b:2'}
    assert header == ['ItemURL', 'ItemName', 'ItemCode']


def test_empty_sheet(connect):
    service, codes, header = connect([])
    assert service is not None
    assert codes == set()
    assert header == []


def test_missing_itemcode_header_fails(connect):
    service, codes, header = connect([['ItemURL', 'ItemName'], ['u1', '商品1']])
    assert service is None


def test_connection_error_fails(monkeypatch):
    def raise_error(*_args, **_kwargs):
        raise FileNotFoundError('service_account.json が無い')
    monkeypatch.setattr(gsu.service_account.Credentials, 'from_service_account_file', raise_error)
    assert gsu.connect_to_sheets_and_get_existing_codes() == (None, set(), [])


# ============================================================
# 追記
# ============================================================

def item(code, name):
    shop, item_id = code.split(':')
    return {
        'ItemURL': f'https://item.rakuten.co.jp/{shop}/{item_id}/', 'ShopCode': shop, 'ItemID': item_id,
        'ItemCode': code, 'ItemName': name, 'PostStatus': '未', 'CollectionStatus': '未',
    }


def test_append_follows_header_order():
    """見出しの並び順で行を作り、見出しに無い項目は空にする"""
    service = FakeService()
    header = ['ItemName', 'ItemCode', 'PostedDate', 'PostStatus', 'ItemURL']
    writer.write_items_info_to_google_sheet(service, [item('a:1', '商品1')], header)

    request = service.appended[0]
    assert request['body']['values'] == [['商品1', 'a:1', '', '未', 'https://item.rakuten.co.jp/a/1/']]
    assert request['insertDataOption'] == 'INSERT_ROWS'   # 既存の行を上書きしない
    assert request['range'] == 'リスト!A1'


def test_append_to_empty_sheet_adds_header():
    service = FakeService()
    writer.write_items_info_to_google_sheet(service, [item('a:1', '商品1')], [])
    values = service.appended[0]['body']['values']
    assert values[0] == HEADER
    assert values[1] == ['https://item.rakuten.co.jp/a/1/', 'a', '1', 'a:1', '商品1', '', '', '未', '', '未', '']


def test_no_items_does_not_call_api():
    service = FakeService()
    writer.write_items_info_to_google_sheet(service, [], HEADER)
    assert service.appended == []


def test_added_items_are_logged():
    """追加した商品はログファイルに1件ずつ残す"""
    from logger import get_logger
    service = FakeService()
    writer.write_items_info_to_google_sheet(service, [item('a:1', '商品1'), item('b:2', '商品2')], HEADER)
    log = get_logger().log_file.read_text(encoding='utf-8')
    assert '2件の新規商品をスプレッドシートに追加しました' in log
    assert '追加した商品: a:1 / 商品1' in log
    assert '追加した商品: b:2 / 商品2' in log
