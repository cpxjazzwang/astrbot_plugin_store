import aiosqlite  # noqa: F401

import astrbot.api.message_components as comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.session_waiter import (
    SessionController,
    session_waiter,
)

from .db import Storedb


@register("helloworld", "cpxjazz", "一个简单的 store 插件", "v1.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。
        框架在调用时不会传入参数，因此 `storedb` 应为可选。
        """
        self.storedb = Storedb()
        await self.storedb.init()

        # 在插件初始化时进行数据库迁移，确保表存在

    # 注册指令的装饰器。指令名为 存。注册成功后，发送 `/存` 就会触发这个指令，并创建储存记录，第一个参数为物品名称（图片名称），第二个参数为位置`
    @filter.command("存")
    async def write(self, event: AstrMessageEvent, name: str, location: str):
        """这是一个 存 指令，参数1为物品名字，参数2为储存位置"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        user_id = event.get_sender_id()
        # 用户发的纯文本消息字符串

        message_chain = event.get_messages()  # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 请发送记忆图片!如果空，请输入no")  # 发送一条纯文本消息

        @session_waiter(timeout=60, record_history_chains=False)
        async def wait_for_image(controller: SessionController, event: AstrMessageEvent):
            idiom = event.message_str
            if idiom == "no":  # 假设用户想主动退出
                await event.send(event.plain_result("已退出存~"))
                controller.stop()  # 停止会话控制器，会立即结束。
                return
            else:
                msgs = event.message_obj.message  # 下载图片并获取本地路径
                local_path = None
                for msg in msgs:
                    if isinstance(msg, comp.Image):
                        local_path = msg.path
                await self.storedb.insert(user_id, name, location, local_path)  # 将图片信息插入数据库
                new_id = await self.storedb.query_by_id(user_id, name)  # 获取新插入记录的 ID

                await event.send(event.plain_result(f"已存储物品：{name}，id：{new_id}"))
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

    @filter.command("删除")
    async def delete(self, event: AstrMessageEvent, name: str):
        """这是一个 删 指令，参数为物品名字"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_id = event.get_sender_id()
        result = await self.storedb.delete_photo(user_id, name)
        yield event.plain_result(result)

    @filter.command("查全部")
    async def query_all(self, event: AstrMessageEvent):
        """这是一个 查 指令，没有参数"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_id = event.get_sender_id()
        records = await self.storedb.query_by_user_id(user_id)
        if not records:
            yield event.plain_result("你没有存储任何物品。")
        else:
            response = "你存储的物品有：\n" + "\n".join([f"- {record[0]}" for record in records])
            yield event.plain_result(response)

    @filter.command("查")
    async def query(self, event: AstrMessageEvent, name: str):
        """这是一个 查 指令，参数为物品名字"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_id = event.get_sender_id()
        record = await self.storedb.query_by_id(user_id, name)
        if not record:
            yield event.plain_result("没有找到该物品。")
        else:
            _, _, image_name, photo_path, created_at = record
            response = f"物品名称: {image_name}\n储存时间: {created_at}\n"
            chain = [comp.At(qq=user_id), comp.Plain(response), comp.Image.fromFileSystem(path=photo_path)]
            yield event.chain_result(chain)

    # noqa: W293
    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await self.storedb.close()
