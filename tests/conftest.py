"""
テストの共通設定

- プロジェクト直下のモジュールを import できるようにする
- ログは一時フォルダに出力し、プロジェクトの logs を汚さない
- ログイン情報・スプレッドシートの設定はダミーにする（.envの本物を使わない）
  （config を import する前に環境変数で指定する。load_dotenv は既存の環境変数を上書きしない）
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

os.environ['LOG_DIR'] = tempfile.mkdtemp(prefix='rakuten_favorite_test_logs_')
os.environ['RAKUTEN_USER_ID'] = 'dummy_user'
os.environ['RAKUTEN_PASSWORD'] = 'dummy_pass'
os.environ['SPREADSHEET_ID'] = 'dummy_spreadsheet'
os.environ['SHEET_NAME'] = 'リスト'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_original_sleep = asyncio.sleep


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    """
    すべてのテストで asyncio.sleep の待ち時間を0にして、テストを速く終わらせる
    （ブラウザを使わないため、実際に待つ必要は無い。待ち時間の上限は実時間で判定されるので、上限の判定はそのまま働く）
    """
    async def sleep(_delay, *_args, **_kwargs):
        await _original_sleep(0)
    monkeypatch.setattr(asyncio, 'sleep', sleep)
