import threading
import time
import asyncio
from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
import os
import requests
import httpx
import logging
import re
from mirai import Image, MessageChain, Plain
from plugins.QChatGPT_Plugin_Dynamic_Bilibili.dynamic import get_information

stop_thread = False
makesure_stop_thread = False
thread = None
makesure_thread = None
text = ''
# 注册插件
@register(name="Dynamic_Bilibili", description="获取b站up的动态和直播推送", version="0.1", author="zzseki")
class B_Live(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        self.logger = logging.getLogger(__name__)

    @handler(PersonNormalMessageReceived)
    async def person_normal_message_received(self, ctx: EventContext, **kwargs):
        global thread, makesure_thread
        global stop_thread
        global makesure_stop_thread
        receive_text = ctx.event.text_message
        pattern = re.compile(r"#开启动态推送")
        match = pattern.search(receive_text)

        if match:
            # await self.main(ctx)
            if thread is None or not thread.is_alive():
                file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "UID.txt")
                with open(file_path, "r", encoding="utf-8") as file:
                    ids = [line.strip() for line in file if line.strip()]
                if not ids:
                    await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("开启失败，关注up数量为0\n请发送'#关注up[UID]'以添加关注")], False)
                else:
                    thread = threading.Thread(target=self.run_in_thread, args=(ctx,), daemon=True)
                    thread.start()
                    makesure_thread = threading.Thread(target=self.makesure_run_in_thread, args=(ctx,), daemon=True)
                    makesure_thread.start()
            else:
                self.ap.logger.info("线程已经在运行中，跳过启动。")
                await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("动态推送已开启，无需重复开启")], False)
            ctx.prevent_default()
        else:
            pattern = re.compile(r"#关闭动态推送")
            match = pattern.search(receive_text)
            if match:
                if thread is not None and thread.is_alive():
                    await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("正在关闭动态推送......")], False)
                    makesure_stop_thread = True
                    makesure_thread.join()  # 等待保险线程结束
                    stop_thread = True
                    thread.join()  # 等待线程结束
                    self.ap.logger.info("动态推送线程关闭")
                    await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("已关闭动态推送")], False)
                    print("动态推送线程已彻底关闭")
                else:
                    await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("未开启动态推送，无需关闭")], False)
                ctx.prevent_default()
            else:
                if "#关注up" in receive_text:
                    # 如果包含，使用正则表达式提取方括号中的数字
                    pattern = re.compile(r'\[(\d+)\]')  # 匹配方括号内的数字
                    matches = pattern.findall(receive_text)
                    if len(matches) == 1:
                        await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("参数个数错误，需要输入up主UID和直播间号ROOM_ID\n‘#关注up[UID][ROOM_ID]’")],False)
                        ctx.prevent_default()
                    if len(matches) >= 2:
                        uid = matches[0]
                        room_id = matches[1]
                        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "UID.txt"), "r", encoding="utf-8") as file:
                            # 读取文件内容并按行分割
                            lines = file.read().splitlines()
                            # 使用列表推导式获取每行按 | 分割后的第一个元素
                            existing_ids = [line.split("|")[0] for line in lines]
                        if uid not in existing_ids:
                            id = f"{uid}|{room_id}"
                            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "UID.txt"), "a", encoding="utf-8") as file:
                                file.write(id + f"\n")
                            await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("关注成功")], False)
                            await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("注意需要关闭并重新开启动态推送功能才会生效")], False)
                        else:
                            await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("此up已在关注列表中，无需重复添加")], False)
                        ctx.prevent_default()
                pattern = re.compile(r"#取消关注up.*\[(\d+)\]")
                match = pattern.search(receive_text)
                if match:
                    id_to_remove = match.group(1)
                    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "UID.txt")

                    # 读取当前UID.txt中的内容
                    with open(file_path, "r", encoding="utf-8") as file:
                        lines = file.readlines()

                    # 过滤掉要删除的 ID
                    updated_lines = [line for line in lines if line.strip().split("|")[0] != id_to_remove]

                    # 只有当内容有变化时才写回文件
                    if updated_lines != lines:
                        with open(file_path, "w", encoding="utf-8") as file:
                            file.writelines(updated_lines)
                        print(f"ID {id_to_remove} 已删除。")
                        await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("取消关注成功")], False)
                        await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("注意需要关闭并重新开启动态推送功能才会生效")], False)
                    else:
                        print(f"ID {id_to_remove} 不存在。")
                        await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("未关注该up无需取关")], False)
                    ctx.prevent_default()

    def run_in_thread(self, ctx):
        try:
            asyncio.run(self.main(ctx))
        except Exception as e:
            print(f"执行异步函数 main 时出现异常: {e}")

    def makesure_run_in_thread(self, ctx):
        try:
            asyncio.run(self.makesure_main(ctx))
        except Exception as e:
            print(f"执行异步函数 makesure_main 时出现异常: {e}")

    async def makesure_main(self, ctx):
        global thread
        while not makesure_stop_thread:
            await asyncio.sleep(60*5)
            if thread is None or not thread.is_alive():
                thread = threading.Thread(target=self.run_in_thread, args=(ctx,), daemon=True)
                thread.start()
                await ctx.event.query.adapter.reply_message(ctx.event.query.message_event,[("动态推送线程意外关闭，正在自动重新开启...")], False)
            else:
                continue

    async def main(self, ctx):
        i = 0
        global stop_thread
        global text
        global processes
        # await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("正在开启动态推送......")], False)
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "UID.txt")
        with open(file_path, "r", encoding="utf-8") as file:
            ids = [line.strip() for line in file if line.strip()]
        if not ids:
            await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("开启失败，关注up数量为0\n请发送'#关注up[UID]'以添加关注")], False)
        else:
            for id in ids:
                uid = id.split("|")[0]
                room_id = id.split("|")[1]
                get_information(uid, room_id)
            await asyncio.sleep(10)
            # 清除历史文本
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "path.txt"), 'w') as file:
                pass
            await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [("成功开启动态推送")], False)
            while not stop_thread:
                i += 1
                if i%100 == 0:
                    self.ap.logger.info("动态推送线程正在运行中...")
                try:
                    for id in ids:
                        await asyncio.sleep(max(60/max(len(ids), 1), 15))
                        uid = id.split("|")[0]
                        room_id = id.split("|")[1]
                        get_information(uid, room_id)
                        if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), "path.txt")):
                            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "path.txt"), "r",
                                      encoding="utf-8") as file:
                                lines = file.readlines()
                                try:
                                    if text != lines[-1].replace("\n", ""):
                                        text = lines[-1].replace("\n", "")
                                        self.ap.logger.info(text)
                                        if re.search('.png', text):
                                            file_path = text
                                            ctx.add_return("reply", [Image(path=file_path)])
                                            await ctx.send_message(target_type='group', target_id=123456789,
                                                                    message=MessageChain([Image(path=file_path)]))
                                        # else:
                                        #     # await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, [(text)],False)
                                        #     await ctx.send_message(target_type='group', target_id=123456789, message=text)
                                except:
                                    continue
                except:
                    continue
                    
    # 插件卸载时触发
    def __del__(self):
        pass
