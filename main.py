from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.star import Context, Star, register
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import (
    session_waiter,
    SessionController,
)

from .db import Storedb  # noqa: F401


@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self, storedb: Storedb):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        self.storedb = Storedb()
        self.storedb.migrate()  # 确保数据库表存在

    # 注册指令的装饰器。指令名为 存。注册成功后，发送 `/存` 就会触发这个指令，并创建储存记录，第一个参数为物品名称（图片名称），第二个参数为位置`
    @filter.command("存")
    async def write(self, event: AstrMessageEvent, name: str, location: str):
        """这是一个 存 指令，参数1为物品名字，参数2为储存位置"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        user_id = event.get_sender_id()
        message_str = event.message_str  # 用户发的纯文本消息字符串

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
            if type(idiom) is str:  # 假设用户想主动退出
                await event.send(event.plain_result("已退出存~"))
                controller.stop()  # 停止会话控制器，会立即结束。
                return
            else:
                image_path = event.get_messages()  # 下载图片并获取本地路径
                self.storedb.insert(
                    user_id, name, location, image_path
                )  # 将记录插入数据库
                await event.send(event.plain_result(f"已存储 {name} 在 {location}！"))
                controller.stop()  # 停止会话控制器，会立即结束。
                return

        try:
            await wait_for_image(event)
        except TimeoutError as _:  # 当超时后，会话控制器会抛出 TimeoutError
            yield event.plain_result("你超时了！")
        except Exception as e:
            yield event.plain_result("发生错误，请联系管理员: " + str(e))
        finally:
            event.stop_event()

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        self.storedb.close()  # 关闭数据库连接
