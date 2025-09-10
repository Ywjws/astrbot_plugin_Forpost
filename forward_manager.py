# forward_manager.py
from astrbot.api.event import AstrMessageEvent
from typing import List, Dict, Union
from astrbot.api import logger

class ForwardManager:
    def __init__(self, event: AstrMessageEvent):
        self.event = event
    
    async def get_forward_msg(self, message_id: int = None):
        """获取转发消息"""
        client = self.event.bot
        payloads = {
            "message_id": message_id or self.event.message_obj.message_id
        }
        response = await client.api.call_action("get_forward_msg", **payloads)
        return response
    
    async def send_forward_msg_raw(self, message_id: int, group_id: int):
        """发送转发消息"""
        client = self.event.bot
        payloads = {
            "group_id": group_id,
            "message_id": message_id
        }
        await client.api.call_action("forward_group_single_msg", **payloads)
    
    async def build_base_node(self, msg_data: Dict) -> Dict:
        """构建基础节点"""
        return {
            "type": "node",
            "data": {
                "uin": str(msg_data["user_id"]),
                "content": msg_data["raw_message"],
                "time": msg_data["time"],
                "nick": msg_data["sender"]["nickname"]
            }
        }
        
    async def build_nested_nodes(self, msg_data: Dict, depth: int = 0) -> Union[Dict, List]:
        """构建嵌套节点"""
        if depth >= 3:
            return {"type": "text", "data": {"text": "[嵌套层数过多]"}}

        if msg_data["messages"][0]["type"] == "forward":
            forward_id = msg_data["messages"][0]["data"]["id"]
            res = await self.get_forward_msg(forward_id)
            
            child_nodes = []
            for child_msg in res["messages"]:
                child_node = await self.build_nested_nodes(child_msg, depth + 1)
                child_nodes.append(child_node)
            
            return {
                "type": "forward",
                "data": {
                    "nodes": child_nodes,
                    "title": f"嵌套转发层数: {depth + 1}"
                }
            }
        else:
            return await self.build_base_node(msg_data)