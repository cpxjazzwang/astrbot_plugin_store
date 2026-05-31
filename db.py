import sqlite3

from astrbot.api import logger

DB_PATH = "../astrbot_plugin_store.db"


class Storedb:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()

    def migrate(self):

        self.cursor.execute(
            'SELECT name FROM sqlite_master WHERE type="table" AND name="store"'
        )
        table_exists = self.cursor.fetchone() is not None
        if table_exists:
            logger.info("✅表已经存在，跳过建表")

        # Create the plugins table if it doesn't exist
        else:
            logger.info("🆕 表不存在，正在创建表")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    image_name TEXT,
                    image_location TEXT,
                    photo_path TEXT,
                    created_at DATETIME DEFAULT (datetime('now','localtime'))
                )
            """)

        self.conn.commit()

    def insert(self, user_id, image_name, image_location, photo_path):
        self.cursor.execute(
            """
            INSERT INTO store (user_id, image_name, image_location, photo_path) VALUES (?, ?, ?,?)
        """,
            (user_id, image_name, image_location, photo_path),
        )
        self.conn.commit()

    def query_by_user_id(self, user_id):
        self.cursor.execute(
            """
            SELECT id, user_id, image_name, photo_path, created_at FROM store WHERE user_id = ?
        """,
            (user_id,),
        )
        return self.cursor.fetchall()

    def query_by_id(self, user_id, image_name):
        self.cursor.execute(
            """
            SELECT id, user_id, image_name, photo_path, created_at FROM store WHERE user_id = ? AND image_name = ?
        """,
            (user_id, image_name),
        )
        return self.cursor.fetchone()

    def delete_photo(self, user_id, image_name):
        self.cursor.execute(
            """
            SELECT id FROM store WHERE user_id = ? AND image_name = ?
        """,
            (user_id, image_name),
        )
        if self.cursor.fetchone() is None:
            logger.warning(
                f"⚠️没有找到记录，无法删除: user_id={user_id}, image_name={image_name}"
            )
            return "❌没有找到记录，无法删除"
        else:
            self.cursor.execute(
                """
                DELETE FROM store WHERE user_id = ? AND image_name = ?
            """,
                (user_id, image_name),
            )
            self.conn.commit()
            return "✅记录已删除"

    def close(self):
        self.conn.close()
