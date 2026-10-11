"""
config・logger のテスト

ログの保存先（LOG_DIR）とcp932のコンソールでの出力は、import 時の環境で決まるため、
別のPythonプロセスを起動して確認する（テスト本体の設定に影響させない）。
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def run_python(code, cwd, **env):
    """
    プロジェクトのモジュールを使う短いPythonを、指定した作業フォルダ・環境変数で実行する
    出力は既定でUTF-8（フォルダ名の日本語を読み取るため）。PYTHONIOENCODING で変更できる
    """
    full_env = {**os.environ, 'PYTHONPATH': str(PROJECT_DIR), 'PYTHONIOENCODING': 'utf-8'}
    full_env.pop('PYTHONUTF8', None)
    full_env.update(env)
    return subprocess.run([sys.executable, '-c', code], cwd=cwd, env=full_env,
                          capture_output=True)


def test_log_dir_default_is_program_folder(tmp_path):
    """LOG_DIR が未指定なら、作業フォルダではなくプログラムのフォルダの logs"""
    result = run_python('import config; print(config.LOG_DIR)', cwd=tmp_path, LOG_DIR='')
    assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
    assert Path(result.stdout.decode().strip()) == PROJECT_DIR / 'logs'


def test_log_dir_absolute(tmp_path):
    target = tmp_path / 'my_logs'
    result = run_python('import config; print(config.LOG_DIR)', cwd=tmp_path, LOG_DIR=str(target))
    assert Path(result.stdout.decode().strip()) == target


def test_log_dir_relative_is_based_on_program_folder(tmp_path):
    result = run_python('import config; print(config.LOG_DIR)', cwd=tmp_path, LOG_DIR='sub/logs')
    assert Path(result.stdout.decode().strip()) == (PROJECT_DIR / 'sub' / 'logs').resolve()


def test_logger_writes_file_and_survives_cp932_console(tmp_path):
    """cp932の出力先でも「✓」等でエラーにならず、ログファイルには正しく書き込まれる"""
    log_dir = tmp_path / 'logs'
    code = "from logger import get_logger; get_logger().info('✓ テスト'); get_logger().error('失敗')"
    result = run_python(code, cwd=tmp_path, LOG_DIR=str(log_dir), PYTHONIOENCODING='cp932')
    assert result.returncode == 0, result.stderr.decode('cp932', 'replace')

    log_files = list(log_dir.glob('rakuten_favorite_*.log'))
    assert len(log_files) == 1
    text = log_files[0].read_text(encoding='utf-8')
    assert '[INFO] ✓ テスト' in text
    assert '[ERROR] 失敗' in text
