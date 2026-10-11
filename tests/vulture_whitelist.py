"""
vulture（使っていないコードのチェック）に「使っている」と伝えるための一覧

pytest の fixture は関数名を文字列（usefixtures）や引数名で参照するため、
vulture からは使われていないように見える。ここで名前を参照して誤検出を防ぐ。
"""
from conftest import no_wait

no_wait  # conftest.py の autouse の fixture（すべてのテストで自動的に使われる）
