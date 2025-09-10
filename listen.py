# listen.py
from astrbot.api import logger

async def parse_message_components(components, level=0):
    """
    解析消息组件
    返回: list 包含所有消息组件的列表
    """
    all_components = []
    indent = "  " * level
    
    for i, comp in enumerate(components):
        comp_type = comp.get("type", "unknown").lower()
        data = comp.get("data", {})
        url = data.get("url", "")

        logger.info(f"{indent}- 组件{i} 原始值: {comp}")

        if comp_type in ["plain", "text"]:
            text = data.get("text")
            logger.info(f"{indent}- 组件{i}: 类型=文本 | 内容={text}")
            all_components.append(comp)
            
        elif comp_type in ["image", "video"]:
            logger.info(f"{indent}- 组件{i}: 类型={comp_type} | URL={url}")
            all_components.append(comp)
            
        else:
            logger.info(f"{indent}- 组件{i}: 类型={comp_type} | 详细数据={comp}")
            # 忽略其他类型消息
    
    return all_components