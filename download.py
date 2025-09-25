# download.py
import asyncio
import os
import traceback
import uuid
import requests
from astrbot.api import logger

class MediaDownloader:
    """媒体下载器 - 带详细调试日志"""

    def __init__(self, temp_dir: str = None):
        self.temp_dir = temp_dir or "data/plugins_data/astrbot_plugin_fuckanka/temp"
        # 确保目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info(f"[MediaDownloader] 临时目录: {self.temp_dir}")

    def _is_tencent_multimedia_url(self, url: str) -> bool:
        """检查是否是腾讯多媒体链接"""
        is_tencent = url and ("multimedia.nt.qq.com.cn" in url or "multimedia.nt.qq.com" in url)
        logger.debug(f"[MediaDownloader] URL检测: {url} -> 腾讯链接: {is_tencent}")
        return is_tencent

    async def download_file(self, url: str, file_type: str) -> str:
        """通用文件下载方法"""
        logger.info(f"[MediaDownloader] 开始下载: {url}")
        
        if not url:
            logger.warning("[MediaDownloader] URL为空，无法下载")
            return ""

        # 生成文件名和路径
        filename = f"{uuid.uuid4()}.{file_type}"
        filepath = os.path.join(self.temp_dir, filename)
        
        logger.debug(f"[MediaDownloader] 目标文件路径: {filepath}")

        try:
            def _download():
                logger.debug(f"[MediaDownloader] 开始HTTP请求: {url}")
                
                # 设置请求头
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://qq.com",
                    "Accept": "*/*",
                    "Connection": "keep-alive"
                }
                
                response = requests.get(url, stream=True, timeout=30, headers=headers, verify=True)
                
                logger.debug(f"[MediaDownloader] 响应状态码: {response.status_code}")
                logger.debug(f"[MediaDownloader] 内容类型: {response.headers.get('Content-Type', '未知')}")
                
                response.raise_for_status()
                
                # 写入文件
                total_size = 0
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total_size += len(chunk)
                
                logger.info(f"[MediaDownloader] 下载完成，大小: {total_size} bytes")
                return total_size

            downloaded_size = await asyncio.to_thread(_download)

            # 验证文件
            if os.path.exists(filepath):
                actual_size = os.path.getsize(filepath)
                logger.debug(f"[MediaDownloader] 文件检查: 路径={filepath}, 大小={actual_size} bytes")
                
                if actual_size > 0:
                    if actual_size == downloaded_size:
                        logger.info(f"[MediaDownloader] 下载验证成功: {filepath}")
                        return filepath
                    else:
                        logger.warning(f"[MediaDownloader] 文件大小不匹配: 预期={downloaded_size}, 实际={actual_size}")
                        # 仍然返回文件路径，让sender尝试发送
                        return filepath
                else:
                    logger.warning(f"[MediaDownloader] 文件大小为0")
                    try:
                        os.remove(filepath)
                    except:
                        pass
                        logger.warning(f"[MediaDownloader] 文件大小为0,remove失败")
                    return ""
            else:
                logger.warning(f"[MediaDownloader] 文件不存在: {filepath}")
                return ""

        except requests.exceptions.RequestException as e:
            logger.error(f"[MediaDownloader] 网络请求失败: {e}")
        except Exception as e:
            logger.error(f"[MediaDownloader] 下载异常: {e}")
            logger.error(traceback.format_exc())
        
        return ""

    async def download_image(self, url: str) -> str:
        """下载图片"""
        logger.info(f"[MediaDownloader] 开始下载图片: {url}")
        file_type = "jpg"
        if "." in url.split("/")[-1]:
            ext = url.split(".")[-1].split("?")[0].lower()  # 去除URL参数
            if ext in ["jpg", "jpeg", "png", "gif", "webp", "bmp"]:
                file_type = ext
        logger.debug(f"[MediaDownloader] 图片文件类型推断: {file_type}")
        return await self.download_file(url, file_type)

    async def download_video(self, url: str) -> str:
        """下载视频"""
        logger.info(f"[MediaDownloader] 开始下载视频: {url}")
        file_type = "mp4"
        if "." in url.split("/")[-1]:
            ext = url.split(".")[-1].split("?")[0].lower()  # 去除URL参数
            if ext in ["mp4", "mov", "webm", "mkv", "flv", "avi"]:
                file_type = ext
        logger.debug(f"[MediaDownloader] 视频文件类型推断: {file_type}")
        return await self.download_file(url, file_type)

    async def download_audio(self, url: str) -> str:
        """下载音频"""
        logger.info(f"[MediaDownloader] 开始下载音频: {url}")
        return await self.download_file(url, "mp3")

    async def download_media(self, media_info: dict) -> str:
        """根据媒体信息下载文件"""
        media_type = media_info.get("type", "")
        url = media_info.get("url", "")

        logger.info(f"[MediaDownloader] 处理媒体: 类型={media_type}, URL={url}")

        if not url:
            logger.warning("[MediaDownloader] 媒体URL为空")
            return ""

        try:
            if media_type == "image":
                return await self.download_image(url)
            elif media_type == "video":
                return await self.download_video(url)
            elif media_type == "record":
                return await self.download_audio(url)
            else:
                logger.warning(f"[MediaDownloader] 未知媒体类型: {media_type}")
                return ""
        except Exception as e:
            logger.error(f"[MediaDownloader] 媒体下载异常: {e}")
            return ""
