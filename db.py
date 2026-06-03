from pathlib import Path

import aiosqlite

from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path

DB_PATH = str(Path(get_astrbot_plugin_data_path()) / "plugin_data" / "astrbot_plugin_store.db")


class Storedb:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.db_path = DB_PATH

    async def init(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.db_path)

        # Create the plugins table if it doesn't exist

        logger.info("🆕，正在创建表")

        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                image_name TEXT,
                image_location TEXT,
                photo_path TEXT,
                created_at DATETIME DEFAULT (datetime('now','localtime'))
            )
        """)

        await self.conn.commit()

    async def insert(self, user_id, image_name, image_location, photo_path):
        await self.conn.execute(
            """
            INSERT INTO store (user_id, image_name, image_location, photo_path) VALUES (?, ?, ?,?)
        """,
            (user_id, image_name, image_location, photo_path),
        )
        await self.conn.commit()

    async def query_by_user_id(self, user_id):
        async with self.conn.execute(
            """
            SELECT  image_name  FROM store WHERE user_id = ?
        """,
            (user_id,),
        ) as cursor:
            return await cursor.fetchall()

    async def query_by_id(self, user_id, image_name):
        async with self.conn.execute(
            """
            SELECT id, user_id, image_name, photo_path, created_at FROM store WHERE user_id = ? AND image_name = ?
        """,
            (user_id, image_name),
        ) as cursor:
            return await cursor.fetchone()

    async def delete_photo(self, user_id, image_name):
        async with self.conn.execute(
            """
            SELECT id FROM store WHERE user_id = ? AND image_name = ?
        """,
            (user_id, image_name),
        ) as cursor:
            if await cursor.fetchone() is None:
                logger.warning(f"⚠️没有找到记录，无法删除: user_id={user_id}, image_name={image_name}")
                return "❌没有找到记录，无法删除"
            else:
                await cursor.execute(
                    """
                    DELETE FROM store WHERE user_id = ? AND image_name = ?
                """,
                    (user_id, image_name),
                )
                return "✅记录已删除"

    async def close(self):
        await self.conn.close()
