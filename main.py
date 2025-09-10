# main.py (改进版本)
import asyncio
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from .listen import parse_message_components
from .download import MediaDownloader
from .forward_manager import ForwardManager
from .local_cache import LocalCache
from .sender import MessageSender
from .cleaner import AsyncDailyCleaner

@register(
    "fuckanka",
    "ali",
    "监听消息并转发，可用于防撤回，主要还是搬屎用",
    "0.0.5"
)
class MediaMonitorPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.downloader = MediaDownloader()
        self.config = config or {}
        
        self.monitored_groups = [str(gid) for gid in self.config.get("monitored_groups", [])]
        self.target_groups = [str(gid) for gid in self.config.get("target_groups", [])]

        temp_dir = "data/plugins_data/astrbot_plugin_fuckanka/temp"
        cleaner = AsyncDailyCleaner(temp_dir)
        #启动食雪汉
        asyncio.create_task(cleaner.run_daily_task())

        self.local_cache = LocalCache()
        self.sender = MessageSender(context, self.target_groups)
        self.message_cache = {}
        logger.info(f"[MediaMonitor] 插件已加载, 监听群: {self.monitored_groups}, 目标群: {self.target_groups}")

    async def process_ordinary_message(self, message_data: dict, msg_id: int):
        """处理普通消息（文本+媒体）"""
        if "message" not in message_data:
            return

        components = await parse_message_components(message_data["message"])
        
        self.message_cache[msg_id] = {
            "components": components,
            "text_content": "",
            "media_files": [],
            "processed": False,
            "is_forward": False
        }
        
        text_parts = []
        media_list = []
        for comp in components:
            comp_type = comp.get("type", "").lower()
            data = comp.get("data", {})
            if comp_type == "text":
                txt = data.get("text", "")
                if txt:
                    text_parts.append(txt)
            elif comp_type in ["image", "video", "record"]:
                url = data.get("url", "")
                if url:
                    media_list.append({
                        "type": comp_type,
                        "url": url,
                        "data": data
                    })
        
        self.message_cache[msg_id]["text_content"] = "\n".join(text_parts)
        self.message_cache[msg_id]["media_files"] = media_list
        logger.info(f"[MediaMonitor] 普通消息 {msg_id} 解析完成: {len(text_parts)}文本, {len(media_list)}媒体")

    async def download_and_forward_ordinary_message(self, msg_id: int):
        """下载普通消息的媒体文件并通过sender发送"""
        if msg_id not in self.message_cache:
            return
        
        message_info = self.message_cache[msg_id]
        if message_info.get("is_forward", True):
            return
        
        if message_info["text_content"] or message_info["media_files"]:
            logger.info(f"[MediaMonitor] 转发普通消息 {msg_id}")
            
            image_paths = []
            video_path = None
            
            for media_info in message_info["media_files"]:
                logger.info(f"[MediaMonitor] 开始下载媒体: {media_info['type']}")
                result = await self.downloader.download_media(media_info)
                if result:
                    if media_info["type"] == "image":
                        image_paths.append(result)
                        logger.info(f"[MediaMonitor] 图片下载成功: {result}")
                    elif media_info["type"] == "video" and video_path is None:
                        video_path = result
                        logger.info(f"[MediaMonitor] 视频下载成功: {result}")
                    elif media_info["type"] == "record":
                        logger.info(f"[MediaMonitor] 语音消息下载成功: {result}")
            
            # ✅ 调用 sender 发送
            if video_path:
                await self.sender.send_combined_message(
                    text=message_info["text_content"],
                    image_paths=image_paths,
                    video_path=video_path
                )
            elif image_paths:
                await self.sender.send_combined_message(
                    text=message_info["text_content"],
                    image_paths=image_paths
                )
            else:
                await self.sender.send_text_message(message_info["text_content"])
        
        message_info["processed"] = True

    async def process_forward_message(self, event: AstrMessageEvent, message_data: dict, msg_id: int):
        """处理转发消息 - 直接通过forward_manager转发"""
        # 检查是否为重复转发
        if self.local_cache.is_duplicate_forward(message_data):
            logger.info(f"[MediaMonitor] 检测到重复转发消息, ID: {msg_id}，跳过处理")
            return
        
        logger.info(f"[MediaMonitor] 检测到转发消息, ID: {msg_id}")
        
        # 缓存转发消息信息（用于去重）
        await self.local_cache.add_cache(msg_id, message_data)
        
        # 直接通过forward_manager转发到目标群组
        if self.target_groups:
            forward_manager = ForwardManager(event)
            for target_group in self.target_groups:
                try:
                    await forward_manager.send_forward_msg_raw(msg_id, int(target_group))
                    logger.info(f"[MediaMonitor] 转发消息 {msg_id} 到群组 {target_group}")
                    await asyncio.sleep(1)  # 避免发送过快
                except Exception as e:
                    logger.error(f"[MediaMonitor] 转发消息失败: {e}")

    def is_forward_message(self, message_data: dict) -> bool:
        """检查是否为转发消息"""
        if "message" not in message_data:
            return False
        
        for comp in message_data["message"]:
            if comp.get("type") == "forward":
                return True
        return False

    @filter.event_message_type(filter.EventMessageType.ALL)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def on_message(self, event: AstrMessageEvent):
        """消息事件处理 - 分离转发消息和普通消息的处理逻辑"""
        if not isinstance(event, AiocqhttpMessageEvent):
            return

        group_id = event.get_group_id()
        if group_id is None:
            return

        group_id_str = str(group_id)
        if self.monitored_groups and group_id_str not in self.monitored_groups:
            return

        client = event.bot
        msg_id = event.message_obj.message_id
        sender_id = str(event.get_sender_id())
        sender_name = event.get_sender_name()

        logger.info(f"[MediaMonitor] 收到消息 - 群: {group_id_str}, 用户: {sender_name}({sender_id}), 消息ID: {msg_id}")

        try:
            # 获取完整消息详情
            ret = await client.api.call_action("get_msg", message_id=msg_id)

            # 分离处理逻辑
            if self.is_forward_message(ret):
                # 转发消息：直接通过forward_manager处理
                await self.process_forward_message(event, ret, msg_id)
            else:
                # 普通消息：通过sender处理
                await self.process_ordinary_message(ret, msg_id)
                # 异步下载和转发
                asyncio.create_task(self.download_and_forward_ordinary_message(msg_id))

        except Exception as e:
            try:
                # 尝试读取异常属性
                msg_text = getattr(e, "message", str(e))
                if msg_text == "消息不存在" :
                    logger.warning(f"[MediaMonitor] 无意义消息 {msg_id}, message='消息不存在', 已忽略")
                    return  
            except Exception:
                pass

            # 其他异常继续打印 traceback
            import traceback
            logger.error(f"[MediaMonitor] 处理消息失败: {e}")
            logger.error(f"[MediaMonitor] 错误详情: {traceback.format_exc()}")
