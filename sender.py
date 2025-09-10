# sender.py
from astrbot.api.event import MessageChain
from astrbot.api.message_components import Video
from astrbot.api import logger
import asyncio
import hashlib
import os
import json

class MessageSender:
    """消息发送器 - 支持文本、图片、视频，并记录已发送文件的 MD5 到磁盘"""

    def __init__(self, context, target_groups, temp_dir: str = None):
        self.context = context
        self.target_groups = target_groups
        self.temp_dir = temp_dir or "data/plugins_data/astrbot_plugin_fuckanka/temp/shit"
        os.makedirs(self.temp_dir, exist_ok=True)
        self.md5_file = os.path.join(self.temp_dir, "sent_md5.json")
        self.sent_md5 = self._load_md5()
        logger.info(f"[MessageSender] 初始化完成，目标群组: {target_groups}")

    def _load_md5(self):
        """从文件加载已发送的 MD5"""
        if os.path.exists(self.md5_file):
            try:
                with open(self.md5_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"[MessageSender] 已加载 {len(data)} 条已发送 MD5")
                    return set(data)
            except Exception as e:
                logger.error(f"[MessageSender] 加载 MD5 文件失败: {e}")
        return set()

    def _save_md5(self):
        """将已发送的 MD5 保存到文件"""
        try:
            with open(self.md5_file, "w", encoding="utf-8") as f:
                json.dump(list(self.sent_md5), f, ensure_ascii=False, indent=2)
            logger.info(f"[MessageSender] 已保存 {len(self.sent_md5)} 条 MD5")
        except Exception as e:
            logger.error(f"[MessageSender] 保存 MD5 文件失败: {e}")

    def _get_session_id(self, group_id: int) -> str:
        return f"aiocqhttp:GroupMessage:{group_id}"

    async def _send_message_chain(self, group_id: int, message_chain):
        try:
            session_id = self._get_session_id(group_id)
            await self.context.send_message(session_id, message_chain)
            logger.info(f"[MessageSender] 消息成功发送到群组 {group_id}")
            return True
        except Exception as e:
            logger.error(f"[MessageSender] 发送消息到群组 {group_id} 失败: {e}")
            return False

    def _calc_md5(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _is_duplicate(self, file_path: str) -> bool:
        md5 = self._calc_md5(file_path)
        if not md5:
            return False
        if md5 in self.sent_md5:
            logger.info(f"[MessageSender] 检测到重复文件 (md5={md5})，跳过发送: {file_path}")
            return True
        self.sent_md5.add(md5)
        self._save_md5()  # 每次新增 MD5 都保存
        return False

    async def send_text_message(self, text: str):
        if not text:
            return False
        success = True
        for gid in self.target_groups:
            chain = MessageChain().message(text)
            if not await self._send_message_chain(int(gid), chain):
                success = False
            await asyncio.sleep(0.3)
        return success

    async def send_image_message(self, image_paths: list, text: str = None):
        if not image_paths:
            return False
        success = True
        for gid in self.target_groups:
            chain = MessageChain()
            if text:
                chain = chain.message(text)
            for img_path in image_paths:
                if self._is_duplicate(img_path):
                    continue
                chain = chain.file_image(img_path)
            if not await self._send_message_chain(int(gid), chain):
                success = False
            await asyncio.sleep(0.3)
        return success

    async def send_video_message(self, video_path: str):
        if not video_path:
            return False
        if self._is_duplicate(video_path):
            return True
        success = True
        for gid in self.target_groups:
            try:
                session_id = self._get_session_id(int(gid))
                video = Video.fromFileSystem(path=video_path)
                chain = MessageChain([video])
                await self.context.send_message(session_id, chain)
                logger.info(f"[MessageSender] 视频已发送到群 {gid}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"[MessageSender] 视频消息发送失败: {e}")
                success = False
        return success

    async def send_combined_message(self, text: str = None, image_paths: list = None, video_path: str = None):
        success = True
        if text or image_paths:
            if not await self.send_image_message(image_paths or [], text=text):
                success = False
        if video_path:
            if not await self.send_video_message(video_path):
                success = False
        return success
