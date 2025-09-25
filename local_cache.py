# local_cache.py
import os
import json
import re
import aiofiles
from astrbot.api import logger

class LocalCache:
    def __init__(self, cache_dir="data/plugins_data/astrbot_plugin_fuckanka/temp/shit"):
        self.cache_dir = cache_dir
        self.config_path = os.path.join(cache_dir, "forward_config.json")
        os.makedirs(cache_dir, exist_ok=True)
        
        # 初始化配置
        self.forward_config = self._load_config()
    
    def _load_config(self):
        """加载转发配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"[LocalCache] 加载配置失败: {e}")
        return {}
    
    def _save_config(self):
        """保存转发配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.forward_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"[LocalCache] 保存配置失败: {e}")
            return False
    
    def _get_cache_path(self, msg_id):
        return os.path.join(self.cache_dir, f"{msg_id}.json")
    
    def _is_pure_number(self, text):
        """检查是否为纯数字"""
        if not text or not isinstance(text, str):
            return False
        return text.isdigit()
    
    def _compare_values(self, value1, value2):
        """比较两个值，如果是数字则进行数值比较，否则进行字符串比较"""
        if not value1 or not value2:
            return False
            
        if self._is_pure_number(value1) and self._is_pure_number(value2):
            # 数值比较
            num1 = int(value1)
            num2 = int(value2)
            return num1 == num2
        else:
            # 字符串比较
            return value1 == value2
    
    def _extract_content_info(self, message_data):
        """提取消息的首尾内容"""
        title = ""
        button = ""
        
        if "message" in message_data and isinstance(message_data["message"], list):
            # 查找转发消息
            for comp in message_data["message"]:
                if isinstance(comp, dict) and comp.get("type") == "forward":
                    # 提取转发消息的content参数
                    forward_data = comp.get("data", {})
                    content = forward_data.get("content", "")
                    
                    if isinstance(content, str):
                        # 字符串形式的content，提取数字部分并拼接"草"
                        numbers = self._extract_numbers_from_content(content)
                        title = f"草{numbers}" if numbers else "草"
                    elif isinstance(content, list) and content:
                        # 列表形式的content，提取第一条和最后一条消息
                        first_msg = content[0]
                        last_msg = content[-1]
                        
                        # 提取第一条消息的内容作为title
                        title = self._extract_message_text(first_msg, is_title=True)
                        
                        # 提取最后一条消息的内容作为button
                        button = self._extract_message_text(last_msg, is_title=False)
                    break
        
        return title, button
    
    def _extract_numbers_from_content(self, content):
        """从content字符串中提取数字部分"""
        if not content:
            return ""
        
        # 提取所有数字
        numbers = re.findall(r'\d+', content)
        if numbers:
            # 返回所有数字连接起来的字符串
            return ''.join(numbers)
        return ""
    
    def _extract_message_text(self, message, is_title=False):
        """从单条消息中提取文本内容"""
        if not isinstance(message, dict):
            return ""
        
        # 优先使用raw_message
        raw_message = message.get("raw_message", "")
        if raw_message:
            extracted = self._extract_raw_message_content(raw_message, is_title)
            return extracted
        
        # 如果没有raw_message，尝试从message字段提取
        message_content = message.get("message", "")
        if isinstance(message_content, list):
            # 从消息组件中提取文本
            text_parts = []
            for comp in message_content:
                if isinstance(comp, dict) and comp.get("type") == "text":
                    text_parts.append(comp.get("data", {}).get("text", ""))
            result = "".join(text_parts)
            return result
        elif isinstance(message_content, str):
            return message_content
        
        return ""
    
    def _extract_raw_message_content(self, raw_message, is_title=False):
        """从raw_message中提取内容"""
        if not raw_message or not isinstance(raw_message, str):
            return ""
        
        # 处理CQ码
        if raw_message.startswith("[CQ:"):
            # 提取CQ码类型和参数
            end_bracket = raw_message.find("]")
            if end_bracket == -1:
                return raw_message
                
            cq_content = raw_message[4:end_bracket]
            comma_pos = cq_content.find(",")
            
            if comma_pos == -1:
                cq_type = cq_content
                params_str = ""
            else:
                cq_type = cq_content[:comma_pos]
                params_str = cq_content[comma_pos + 1:]
            
            # 解析参数
            params = {}
            for param in params_str.split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value
            
            if cq_type == "forward":
                # 转发消息，提取content参数中的数字部分并拼接"草"
                content = params.get("content", "")
                numbers = self._extract_numbers_from_content(content)
                return f"草{numbers}" if numbers else "草"
            elif cq_type in ["image", "video"]:
                # 图片或视频，提取file参数（文件名）
                return params.get("file", "")
            elif cq_type == "reply":  # <--- 新增处理 reply 类型
                # 回复消息：忽略CQ码本身，返回后面的正文内容
                rest_text = raw_message[end_bracket + 1:]
                return rest_text.strip()
            else:
                # 其他CQ码，返回原始消息
                return raw_message
        else:
            # 文本消息，直接返回
            return raw_message
    
    async def add_cache(self, msg_id, message_data=None):
        """缓存消息到本地，并记录首尾内容"""
        cache_path = self._get_cache_path(msg_id)
        try:
            async with aiofiles.open(cache_path, 'w', encoding='utf-8') as f:
                if message_data:
                    await f.write(json.dumps(message_data, ensure_ascii=False, indent=2))
                else:
                    await f.write('')
            logger.info(f"[LocalCache] 消息 {msg_id} 已缓存")
            
            # 记录首尾内容到配置
            if message_data:
                title, button = self._extract_content_info(message_data)
                # 先检查是否重复，再添加到配置
                if not self._is_duplicate_in_config(title, button):
                    self.forward_config[str(msg_id)] = {
                        "title": title,  # 不限制长度
                        "button": button  # 不限制长度
                    }
                    self._save_config()
                    logger.info(f"[LocalCache] 消息 {msg_id} 内容已记录: title='{title}', button='{button}'")
                else:
                    logger.info(f"[LocalCache] 消息 {msg_id} 内容重复，不记录到配置")
            
            return True
        except Exception as e:
            logger.error(f"[LocalCache] 缓存消息失败: {e}")
            return False
    
    def _is_duplicate_in_config(self, title, button):
        """检查配置中是否已存在相同的title和button"""
        if not title or not button:
            return False
        
        for config in self.forward_config.values():
            config_title = config.get("title", "")
            config_button = config.get("button", "")
            
            # 使用智能比较（数字比较或字符串比较）
            title_match = self._compare_values(config_title, title)
            button_match = self._compare_values(config_button, button)
            
            if title_match and button_match:
                logger.info(f"[LocalCache] 发现重复内容: title='{title}'='{config_title}', button='{button}'='{config_button}'")
                return True
        
        return False
    
    def is_duplicate_forward(self, message_data):
        """检查是否为重复的转发消息"""
        try:
            title, button = self._extract_content_info(message_data)
            logger.info(f"[LocalCache] 检查重复: title='{title}', button='{button}'")
            
            # 如果title或button为空，不认为是重复
            if not title or not button:
                logger.info(f"[LocalCache] title或button为空，不进行重复检查")
                return False
            
            # 检查配置中是否已存在
            is_duplicate = self._is_duplicate_in_config(title, button)
            if is_duplicate:
                logger.info(f"[LocalCache] 发现重复转发消息")
            else:
                logger.info(f"[LocalCache] 未发现重复消息")
            
            return is_duplicate
        except Exception as e:
            logger.error(f"[LocalCache] 检查重复转发失败: {e}")
            return False
    
    async def get_waiting_messages(self):
        """获取所有等待转发的消息ID"""
        try:
            if not os.path.exists(self.cache_dir):
                return []
            
            messages = []
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json') and filename != "forward_config.json":
                    try:
                        msg_id = int(filename.split('.')[0])
                        messages.append(msg_id)
                    except ValueError:
                        continue
            return messages
        except Exception as e:
            logger.error(f"[LocalCache] 获取等待消息失败: {e}")
            return []
    
    async def get_message_data(self, msg_id):
        """获取缓存的消息数据"""
        cache_path = self._get_cache_path(msg_id)
        try:
            if os.path.exists(cache_path):
                async with aiofiles.open(cache_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if content.strip():
                        return json.loads(content)
            return None
        except Exception as e:
            logger.error(f"[LocalCache] 获取消息数据失败: {e}")
            return None
    
    async def remove_cache(self, msg_id):
        """移除缓存的消息"""
        cache_path = self._get_cache_path(msg_id)
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
                # 从配置中移除
                if str(msg_id) in self.forward_config:
                    del self.forward_config[str(msg_id)]
                    self._save_config()
                logger.info(f"[LocalCache] 消息 {msg_id} 已移除")
                return True
            return False
        except Exception as e:
            logger.error(f"[LocalCache] 移除消息失败: {e}")
            return False
