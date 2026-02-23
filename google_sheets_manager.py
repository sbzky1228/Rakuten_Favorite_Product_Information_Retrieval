"""
Google Sheetsマネージャー - Google Sheetsへのデータ読み書き
"""
import os
import pickle
from typing import List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import SCOPES, SPREADSHEET_ID, SHEET_NAME


class GoogleSheetsManager:
    """Google Sheets APIを操作するクラス"""
    
    def __init__(self):
        self.service = self._get_service()
        self.spreadsheet_id = SPREADSHEET_ID
        self.sheet_name = SHEET_NAME
    
    def _get_service(self):
        """Google Sheets APIのサービスを取得"""
        creds = None
        
        # 既存のトークンを読み込む
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # トークンが有効でない場合は再認証
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # クライアントシークレットからフローを作成
                secret_file = 'client_secret_760100385433-1sk74s5lmguisme6baovdn73gi2ie8ks.apps.googleusercontent.com.json'
                flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # トークンを保存
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('sheets', 'v4', credentials=creds)
    
    def append_items(self, items: List[Dict]):
        """商品情報を追加"""
        try:
            values = []
            for item in items:
                values.append([
                    item.get('ItemURL', ''),
                    item.get('ShopCode', ''),
                    item.get('ItemID', ''),
                    item.get('ItemCode', ''),
                    item.get('ItemName', ''),
                    item.get('Collection', ''),
                    item.get('PostStatus', ''),
                    item.get('PostedDate', ''),
                    item.get('CollectionStatus', ''),
                    item.get('CollectedDate', '')
                ])
            
            range_name = f"{self.sheet_name}!A2"
            body = {'values': values}
            
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✓ {len(items)}件の商品情報をスプレッドシートに追加しました")
        
        except Exception as e:
            print(f"✗ スプレッドシートへの追加に失敗しました: {e}")
    
    def get_unposted_items(self) -> List[Dict]:
        """未投稿の商品情報を取得"""
        try:
            range_name = f"{self.sheet_name}!A:J"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            items = []
            
            # ヘッダー行をスキップして処理
            for row in values[1:] if len(values) > 1 else []:
                if len(row) >= 10:
                    post_status = row[6] if len(row) > 6 else ''
                    if post_status != '済':  # 未投稿の場合
                        items.append({
                            'ItemURL': row[0] if len(row) > 0 else '',
                            'ShopCode': row[1] if len(row) > 1 else '',
                            'ItemID': row[2] if len(row) > 2 else '',
                            'ItemCode': row[3] if len(row) > 3 else '',
                            'ItemName': row[4] if len(row) > 4 else '',
                            'Collection': row[5] if len(row) > 5 else '',
                            'PostStatus': row[6] if len(row) > 6 else '',
                            'PostedDate': row[7] if len(row) > 7 else '',
                            'CollectionStatus': row[8] if len(row) > 8 else '',
                            'CollectedDate': row[9] if len(row) > 9 else ''
                        })
            
            print(f"✓ 未投稿の商品数: {len(items)}")
            return items
        
        except Exception as e:
            print(f"✗ スプレッドシートからのデータ取得に失敗しました: {e}")
            return []
    
    def update_post_status(self, item_code: str, posted_date: str):
        """投稿ステータスを更新"""
        try:
            range_name = f"{self.sheet_name}!A:J"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            for i, row in enumerate(values[1:], start=2):
                if len(row) > 3 and row[3] == item_code:
                    # G列（PostStatus）とH列（PostedDate）を更新
                    update_range = f"{self.sheet_name}!G{i}:H{i}"
                    update_body = {'values': [['済', posted_date]]}
                    
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=update_range,
                        valueInputOption='RAW',
                        body=update_body
                    ).execute()
                    
                    print(f"✓ 商品 {item_code} の投稿ステータスを更新しました")
                    return True
            
            print(f"✗ 商品コード {item_code} が見つかりません")
            return False
        
        except Exception as e:
            print(f"✗ ステータス更新に失敗しました: {e}")
            return False
    
    def update_collection_status(self, item_code: str, collected_date: str):
        """コレクション登録ステータスを更新"""
        try:
            range_name = f"{self.sheet_name}!A:J"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            for i, row in enumerate(values[1:], start=2):
                if len(row) > 3 and row[3] == item_code:
                    # I列（CollectionStatus）とJ列（CollectedDate）を更新
                    update_range = f"{self.sheet_NAME}!I{i}:J{i}"
                    update_body = {'values': [['済', collected_date]]}
                    
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=update_range,
                        valueInputOption='RAW',
                        body=update_body
                    ).execute()
                    
                    print(f"✓ 商品 {item_code} のコレクション登録ステータスを更新しました")
                    return True
            
            print(f"✗ 商品コード {item_code} が見つかりません")
            return False
        
        except Exception as e:
            print(f"✗ コレクション登録ステータス更新に失敗しました: {e}")
            return False
