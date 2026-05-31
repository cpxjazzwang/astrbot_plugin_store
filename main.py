import aiosqlite  # noqa: F401

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.session_waiter import (
    SessionController,
    session_waiter,
)


@register("helloworld", "cpxjazz", "一个简单的 store 插件", "v1.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        import sqlite3

        self.DB_PATH = "../data/astrbot_plugin_store.db"
        # 将 storedb 保存为实例属性，供后续使用
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute("""
                CREATE TABLE IF NOT EXISTS store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    image_name TEXT,
                    image_location TEXT,
                    photo_path TEXT,
                    created_at DATETIME DEFAULT (datetime('now','localtime'))
                )
            """)
        conn.commit()
        conn.close()

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。
        框架在调用时不会传入参数，因此 `storedb` 应为可选。
        """

        # 在插件初始化时进行数据库迁移，确保表存在

    # 注册指令的装饰器。指令名为 存。注册成功后，发送 `/存` 就会触发这个指令，并创建储存记录，第一个参数为物品名称（图片名称），第二个参数为位置`
    @filter.command("存")
    async def write(self, event: AstrMessageEvent, name: str, location: str):
        """这是一个 存 指令，参数1为物品名字，参数2为储存位置"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        user_id = event.get_sender_id()
        # 用户发的纯文本消息字符串

        message_chain = (
            event.get_messages()
        )  # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(
            f"Hello, {user_name}, 请发送记忆图片!如果空，请输入no"
        )  # 发送一条纯文本消息

        @session_waiter(timeout=60, record_history_chains=False)
        async def wait_for_image(
            controller: SessionController, event: AstrMessageEvent
        ):
            idiom = event.message_str
            if idiom == "no":  # 假设用户想主动退出
                await event.send(event.plain_result("已退出存~"))
                controller.stop()  # 停止会话控制器，会立即结束。
                return
            else:
                msgs = event.message_obj.message  # 下载图片并获取本地路径
                local_path = None
                for msg in msgs:
                    if isinstance(msg, Comp.Image):
                        local_path = msg.path

                async with aiosqlite.connect(
                    self.DB_PATH
                ) as db:  # 将图片信息插入数据库
                    cursor = await db.execute(
                        """
                        INSERT INTO store (user_id, image_name, image_location, photo_path) VALUES (?, ?, ?,?)
                    """,
                        (user_id, name, location, local_path),
                    )
                    new_id = cursor.lastrowid
                    await db.commit()

                await event.send(
                    event.plain_result(f"已存储物品：{name}，id：{new_id}")
                )
                controller.stop()  # 存储完成后停止会话控制器
                return

        # noqa: W293

        try:
            await wait_for_image(event)
        except TimeoutError as _:  # 当超时后，会话控制器会抛出 TimeoutError
            yield event.plain_result("你超时了！")
        except Exception as e:
            yield event.plain_result("发生错误，请联系管理员: " + str(e))
        finally:
            event.stop_event()

    # def insert(self, user_id, image_name, image_location, photo_path):
    #     self.cursor.execute(
    #         """
    #         INSERT INTO store (user_id, image_name, image_location, photo_path) VALUES (?, ?, ?,?)
    #     """,
    #         (user_id, image_name, image_location, photo_path),
    #     )
    #     self.conn.commit()

    # def query_by_user_id(self, user_id):
    #     self.cursor.execute(
    #         """
    #         SELECT id, user_id, image_name, photo_path, created_at FROM store WHERE user_id = ?
    #     """,
    #         (user_id,),
    #     )
    #     return self.cursor.fetchall()

    # def query_by_id(self, user_id, image_name):
    #     self.cursor.execute(
    #         """
    #         SELECT id, user_id, image_name, photo_path, created_at FROM store WHERE user_id = ? AND image_name = ?
    #     """,
    #         (user_id, image_name),
    #     )
    #     return self.cursor.fetchone()

    # def delete_photo(self, user_id, image_name):
    #     self.cursor.execute(
    #         """
    #         SELECT id FROM store WHERE user_id = ? AND image_name = ?
    #     """,
    #         (user_id, image_name),
    #     )
    #     if self.cursor.fetchone() is None:
    #         logger.warning(
    #             f"⚠️没有找到记录，无法删除: user_id={user_id}, image_name={image_name}"
    #         )
    #         return "❌没有找到记录，无法删除"
    #     else:
    #         self.cursor.execute(
    #             """
    #             DELETE FROM store WHERE user_id = ? AND image_name = ?
    #         """,
    #             (user_id, image_name),
    #         )
    #         self.conn.commit()
    #         return "✅记录已删除"

    # noqa: W293
    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
