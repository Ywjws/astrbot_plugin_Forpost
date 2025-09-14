# async_daily_cleaner.py
import os
import asyncio
from datetime import datetime, timezone, timedelta

class AsyncDailyCleaner:
    """食雪汉"""

    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.forward_config = os.path.join(temp_dir, "shit", "forward_config.json")
        self.sent_md5 = os.path.join(temp_dir, "shit", "sent_md5.json")

    @staticmethod
    def is_even_day_tail() -> bool:
        """判断今天日期尾号是否为偶数"""
        now_utc = datetime.now(timezone.utc)
        now_utc8 = now_utc + timedelta(hours=8)
        day_tail = now_utc8.day % 10
        return day_tail % 2 == 0

    async def clear_temp_files(self):
        """删除 temp 目录下文件，但保留文件夹和指定文件"""
        if not os.path.exists(self.temp_dir):
            return

        # 需要保留的特定文件（完整路径）
        preserve_files = {self.forward_config, self.sent_md5}
        
        for root, _, files in os.walk(self.temp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 检查是否是需要保留的特定文件
                if full_path in preserve_files:
                    # 清空内容但保留文件
                    try:
                        await asyncio.to_thread(lambda p: open(p, "w", encoding="utf-8").close(), full_path)
                        print(f"已清空: {full_path}")
                    except Exception as e:
                        print(f"清空文件 {full_path} 时出错: {e}")
                else:
                    # 删除普通文件
                    try:
                        await asyncio.to_thread(os.remove, full_path)
                        print(f"已删除: {full_path}")
                    except Exception as e:
                        print(f"删除文件 {full_path} 时出错: {e}")
        
        print(f"已完成清理 {self.temp_dir} 目录")


    async def run_daily_task(self):
        """主循环，每天 UTC+8 1 点执行一次清理"""
        while True:
            # 当前 UTC 时间
            now_utc = datetime.now(timezone.utc)
            now_utc8 = now_utc + timedelta(hours=8)
            # 今天 UTC+8 的 1 点
            next_run = now_utc8.replace(hour=1, minute=0, second=0, microsecond=0)
            if now_utc8 >= next_run:
                # 已过今天 1 点，则计划明天 1 点
                next_run += timedelta(days=1)
            # 计算秒数
            sleep_seconds = (next_run - now_utc8).total_seconds()
            await asyncio.sleep(sleep_seconds)

            # 判断日期尾号是否为偶数
            if self.is_even_day_tail():
                print("[AsyncDailyCleaner] 偶数尾号日期，执行清理 temp 文件夹...")
                await self.clear_temp_files()
            else:
                print("[AsyncDailyCleaner] 非偶数尾号日期，跳过清理")
