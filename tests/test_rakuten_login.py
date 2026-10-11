"""
rakuten_login のテスト（ブラウザは起動しない）

楽天のログイン画面をフェイクのページで再現し、画面の状態に応じた操作の順番と、
アカウントロック防止のため ID・パスワードを1回しか送信しないことを確認する。
"""
import asyncio
import pytest
import rakuten_login as rl

LOGIN_URL = 'https://login.account.rakuten.com/sso/authorize#/sign_in'
AFTER_LOGIN_URL = 'https://my.rakuten.co.jp/'


def run(coro):
    return asyncio.run(coro)


class FakeLoginElement:
    """ログイン画面の要素。name が今の画面（page.screen）と一致するときだけ表示されている"""

    def __init__(self, page, name):
        self.page = page
        self.name = name

    @property
    def first(self):
        return self

    def or_(self, _other):
        return self

    def nth(self, index):
        return self

    async def count(self):
        return 1 if await self.is_visible() else 0

    async def is_visible(self):
        if self.name == 'next':
            return self.page.screen in ('user_id', 'password', 'confirm')
        return self.page.screen == self.name

    async def fill(self, value):
        self.page.filled.append((self.name, value))

    async def press(self, _key):
        await self.page.next()

    async def click(self):
        if self.name == 'next':
            await self.page.next()
        elif self.name == 'use_password':
            self.page.screen = 'password'

    async def wait_for(self, state='visible', timeout=None):
        pass


class FakeLoginPage:
    """
    楽天のログイン画面の代わり
      user_id →（次へ）→ パスキー（キャンセル済み）の「パスワードを使用する」→ password →（次へ）→ ログイン後
      confirm（再認証の「〇〇として続けますか？」）→（次へ）→「パスワードを使用する」
    password_ok=False の場合、パスワードを送信してもパスワード画面のまま
    """

    def __init__(self, screen='user_id', password_ok=True, user_id_ok=True):
        self.url = LOGIN_URL
        self.screen = screen
        self.password_ok = password_ok
        self.user_id_ok = user_id_ok
        self.filled = []

    async def next(self):
        if self.screen == 'user_id' and self.user_id_ok:
            self.screen = 'use_password'
        elif self.screen == 'confirm':
            self.screen = 'use_password'
        elif self.screen == 'password' and self.password_ok:
            self.screen = 'done'
            self.url = AFTER_LOGIN_URL

    def locator(self, selector):
        if 'user_id' in selector:
            return FakeLoginElement(self, 'user_id')
        if 'password' in selector:
            return FakeLoginElement(self, 'password')
        return FakeLoginElement(self, 'next')  # input[value='次へ']

    def get_by_text(self, text, **kwargs):
        names = {'次へ': 'next', 'パスワードを使用する': 'use_password', 'として続けますか': 'confirm'}
        return FakeLoginElement(self, names[text])


@pytest.mark.parametrize('url, expected', [
    ('https://login.account.rakuten.com/session/upgrade', True),
    ('https://my.rakuten.co.jp/', False),
    ('https://my.bookmark.rakuten.co.jp/', False),
])
def test_is_login_page(url, expected):
    assert rl.is_login_page(url) is expected


def test_login_form_full_flow():
    page = FakeLoginPage()
    assert run(rl.complete_login_form(page)) is True
    assert page.filled == [('user_id', 'dummy_user'), ('password', 'dummy_pass')]


def test_login_form_reauth_confirm_screen():
    """再認証（/session/upgrade）は確認画面 →「次へ」→ パスワードの順で進む"""
    page = FakeLoginPage(screen='confirm')
    assert run(rl.complete_login_form(page)) is True
    assert page.filled == [('password', 'dummy_pass')]


def test_wrong_password_is_sent_only_once():
    """パスワードが違っても再送信しない（アカウントロック防止）"""
    page = FakeLoginPage(password_ok=False)
    assert run(rl.complete_login_form(page, timeout=2000)) is False
    assert page.filled.count(('password', 'dummy_pass')) == 1


def test_wrong_user_id_is_sent_only_once():
    page = FakeLoginPage(user_id_ok=False)
    assert run(rl.complete_login_form(page, timeout=2000)) is False
    assert page.filled == [('user_id', 'dummy_user')]


def test_login_form_without_credentials(monkeypatch):
    monkeypatch.setattr(rl, 'RAKUTEN_PASSWORD', '')
    page = FakeLoginPage()
    assert run(rl.complete_login_form(page)) is False
    assert page.filled == []


def test_login_form_timeout_when_screen_unknown():
    """どの画面とも判定できないままなら、時間切れで失敗する"""
    page = FakeLoginPage(screen='unknown')
    assert run(rl.complete_login_form(page, timeout=300)) is False
