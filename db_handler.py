import sqlite3
from datetime import datetime
import pandas as pd
import bcrypt  # ★追加

class DBHandler:
    def __init__(self, db_path="route_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """データベースとテーブルの初期化"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 1. ユーザー管理テーブル（新規作成）
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL
            )
        ''')

        # 2. ルート履歴テーブル（user_idを追加）
        c.execute('''
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                start_place TEXT,
                end_place TEXT,
                distance_km REAL,
                search_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
        conn.close()

    # --- ユーザー認証機能 ---
    def register_user(self, username, password):
        """ユーザー登録（成功ならTrue, 重複ならFalseを返す）"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # パスワードのハッシュ化（暗号化）
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

        try:
            c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hashed))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # ユーザー名が既に存在する
        finally:
            conn.close()

    def login_user(self, username, password):
        """ログイン認証（成功ならuser_id, 失敗ならNoneを返す）"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user:
            user_id, stored_hash = user
            # パスワード照合
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                return user_id
        return None

    # --- 履歴管理機能（ユーザーIDでフィルタリング） ---
    def add_route(self, user_id, start_place, end_place, distance_km):
        """履歴保存（ユーザーID紐付け）"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        c.execute('''
            INSERT INTO routes (user_id, start_place, end_place, distance_km, search_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, start_place, end_place, distance_km, now))
        
        conn.commit()
        conn.close()

    def get_history(self, user_id):
        """ログインユーザーの履歴のみ取得"""
        conn = sqlite3.connect(self.db_path)
        # user_id が一致するものだけを取得
        df = pd.read_sql_query(
            "SELECT id, start_place, end_place, distance_km FROM routes WHERE user_id = ? ORDER BY id DESC", 
            conn,
            params=(user_id,)
        )
        conn.close()
        return df