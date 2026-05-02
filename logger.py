"""
ロギングモジュール - プログラム実行時のログ出力機能

以下の処理を提供します:
- 標準出力（コンソール）への出力
- ログファイルへの書き込み
INFO, WARNING, ERROR の3つのレベルをサポート
"""
import datetime
import os


class Logger:
    """
    ログ出力を管理するクラス
    
    コンソールとログファイルの両方へこたいメッセージを
    タイムスタンプ付きで出力します。
    """
    
    def __init__(self, log_dir: str = 'logs'):
        """
        Logger を初期化
        
        Args:
            log_dir: ログファイルを保存するディレクトリ (推奨設定: 'logs')
        """
        self.log_dir = log_dir
        
        # ディレクトリが存在しない場合、作成したい
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # ログファイル名を生成
        # 例: rakuten_room_20250301_143022.log
        now = datetime.datetime.now()
        self.log_file = os.path.join(
            log_dir,
            f"rakuten_room_{now.strftime('%Y%m%d_%H%M%S')}.log"
        )
    
    def log(self, message: str, level: str = 'INFO'):
        """
        ログを出力
        
        標準出力とログファイルの両方へ出力します。
        
        Args:
            message: ログメッセージ
            level: ログレベル (INFO, WARNING, ERROR)
        """
        # タイムスタンプを追加
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # ログメッセージを組み立てる
        log_message = f"[{timestamp}] [{level}] {message}"
        
        # 標準出力へ出力
        print(log_message)
        
        # ファイルへも書き込む
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def info(self, message: str):
        """INFO レベルでログ出力（通常の処理情報）"""
        self.log(message, 'INFO')
    
    def warning(self, message: str):
        """WARNING レベルでログ出力（警告情報）"""
        self.log(message, 'WARNING')
    
    def error(self, message: str):
        """ERROR レベルでログ出力（エラー情報）"""
        self.log(message, 'ERROR')
    
    def get_log_file(self) -> str:
        """
        現在使用中のログファイルのパスを取得
        
        Returns:
            str: ログファイルのパス
        """
        return self.log_file
