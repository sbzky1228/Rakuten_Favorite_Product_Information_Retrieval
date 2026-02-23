import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Google Sheets APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_sheets_service():
    """
    Google Sheets APIのサービスオブジェクトを取得する関数

    Returns:
        service: Google Sheets APIのサービスオブジェクト
    """
    creds = None
    # トークンファイルが存在する場合、読み込む
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # クレデンシャルが無効または存在しない場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # クライアントシークレットファイルからフローを作成
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret_760100385433-1sk74s5lmguisme6baovdn73gi2ie8ks.apps.googleusercontent.com.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # 次回のためにトークンを保存
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Google Sheets APIのサービスを構築
    service = build('sheets', 'v4', credentials=creds)
    return service