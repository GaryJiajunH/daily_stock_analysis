# -*- coding: utf-8 -*-
"""
===================================
日内实时分析调度器
===================================

职责：
1. 支持每日多个时间点执行日内分析（开盘、午盘、尾盘）
2. 智能跳过非交易日（周末、节假日）
3. 优雅处理信号，确保可靠退出

特性：
- 多时间点调度：9:30, 13:00, 14:45
- 交易日检测：周一至周五，可选中国节假日检测
- 复用现有 schedule 库和 GracefulShutdown 模式
"""

import logging
import time
from datetime import datetime
from typing import Callable, List, Optional

from src.scheduler import GracefulShutdown

logger = logging.getLogger(__name__)


class IntradayScheduler:
    """
    日内实时分析调度器

    与 Scheduler 的区别：
    - 支持多个时间点（而非单一时间）
    - 自动跳过非交易日
    - 可选中国节假日检测

    使用示例：
        scheduler = IntradayScheduler(
            time_points=["09:30", "13:00", "14:45"],
            config=config
        )
        scheduler.set_intraday_tasks(analysis_task)
        scheduler.run()
    """

    def __init__(
        self,
        time_points: List[str],
        holiday_detection: str = "simple"
    ):
        """
        初始化日内调度器

        Args:
            time_points: 每日执行时间点列表，格式 ["HH:MM", ...]
            holiday_detection: 节假日检测模式
                - "simple": 仅检测周末（默认）
                - "advanced": 使用 chinese_calendar 检测中国节假日
        """
        try:
            import schedule
            self.schedule = schedule
        except ImportError:
            logger.error("schedule 库未安装，请执行: pip install schedule")
            raise ImportError("请安装 schedule 库: pip install schedule")

        self.time_points = time_points
        self.holiday_detection = holiday_detection
        self.shutdown_handler = GracefulShutdown()
        self._task_callback: Optional[Callable] = None
        self._running = False

        # 尝试加载 chinese_calendar（可选）
        self._chinese_calendar = None
        if holiday_detection == "advanced":
            try:
                import chinese_calendar
                self._chinese_calendar = chinese_calendar
                logger.info("已启用中国节假日检测（chinese_calendar）")
            except ImportError:
                logger.warning(
                    "chinese_calendar 未安装，回退到简单周末检测。"
                    "如需节假日检测，请执行: pip install chinese-calendar>=1.8.0"
                )
                self.holiday_detection = "simple"

    def is_trading_day(self, date: Optional[datetime] = None) -> bool:
        """
        判断是否为交易日

        Args:
            date: 要检测的日期，默认为今天

        Returns:
            True: 交易日, False: 非交易日
        """
        if date is None:
            date = datetime.now()

        # 简单模式：仅检测周末
        if self.holiday_detection == "simple":
            # Monday=0, Friday=4, Saturday=5, Sunday=6
            is_weekday = date.weekday() < 5
            if not is_weekday:
                logger.debug(f"{date.strftime('%Y-%m-%d')} 是周末，跳过")
            return is_weekday

        # 高级模式：使用 chinese_calendar
        if self._chinese_calendar:
            try:
                is_workday = self._chinese_calendar.is_workday(date.date())
                if not is_workday:
                    logger.debug(f"{date.strftime('%Y-%m-%d')} 是节假日，跳过")
                return is_workday
            except Exception as e:
                logger.warning(f"节假日检测失败，回退到周末检测: {e}")
                return date.weekday() < 5

        # 默认回退
        return date.weekday() < 5

    def set_intraday_tasks(self, task: Callable):
        """
        设置日内分析任务

        Args:
            task: 要执行的任务函数（无参数）
        """
        self._task_callback = task

        # 为每个时间点注册任务
        for time_point in self.time_points:
            self.schedule.every().day.at(time_point).do(self._safe_run_task)
            logger.info(f"已注册日内任务: {time_point}")

        logger.info(f"日内调度器配置完成，共 {len(self.time_points)} 个时间点")

    def _safe_run_task(self):
        """安全执行任务（带交易日检测和异常捕获）"""
        if self._task_callback is None:
            return

        # 检查是否为交易日
        if not self.is_trading_day():
            logger.info("今日非交易日，跳过日内分析")
            return

        try:
            now = datetime.now()
            logger.info("=" * 60)
            logger.info(f"[日内分析] 任务开始 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            self._task_callback()

            elapsed = (datetime.now() - now).total_seconds()
            logger.info(f"[日内分析] 任务完成 - 耗时 {elapsed:.1f} 秒")

        except Exception as e:
            logger.exception(f"[日内分析] 任务执行失败: {e}")

    def run(self):
        """
        运行调度器主循环

        阻塞运行，直到收到退出信号
        """
        self._running = True
        logger.info("=" * 60)
        logger.info("日内实时分析调度器启动")
        logger.info(f"交易时间点: {', '.join(self.time_points)}")
        logger.info(f"节假日检测: {self.holiday_detection}")
        logger.info(f"下次执行: {self._get_next_run_time()}")
        logger.info("=" * 60)

        # 检查今天是否为交易日
        if self.is_trading_day():
            logger.info("✅ 今日为交易日")
        else:
            logger.info("⏸️  今日非交易日，调度器将等待至下一个交易日")

        last_heartbeat_minute = -1

        while self._running and not self.shutdown_handler.should_shutdown:
            # 运行待执行的任务
            self.schedule.run_pending()

            # 每小时打印心跳（仅打印一次）
            current_minute = datetime.now().minute
            if current_minute == 0 and current_minute != last_heartbeat_minute:
                logger.info(f"💓 调度器运行中... 下次执行: {self._get_next_run_time()}")
                last_heartbeat_minute = current_minute

            # 每30秒检查一次
            time.sleep(30)

        logger.info("日内调度器已停止")

    def _get_next_run_time(self) -> str:
        """获取下次执行时间"""
        jobs = self.schedule.get_jobs()
        if not jobs:
            return "未设置"

        next_run = min(job.next_run for job in jobs)
        return next_run.strftime('%Y-%m-%d %H:%M:%S')

    def stop(self):
        """停止调度器"""
        self._running = False


def run_with_intraday_schedule(
    task: Callable,
    time_points: List[str] = None,
    holiday_detection: str = "simple"
):
    """
    便捷函数：使用日内调度运行任务

    Args:
        task: 要执行的任务函数
        time_points: 每日执行时间点列表
        holiday_detection: 节假日检测模式
    """
    if time_points is None:
        time_points = ["09:30", "13:00", "14:45"]

    scheduler = IntradayScheduler(
        time_points=time_points,
        holiday_detection=holiday_detection
    )
    scheduler.set_intraday_tasks(task)
    scheduler.run()


if __name__ == "__main__":
    # 测试日内调度器
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )

    def test_task():
        print(f"[测试] 日内分析任务执行 - {datetime.now().strftime('%H:%M:%S')}")
        time.sleep(1)
        print("[测试] 任务完成!")

    print("启动日内调度器测试（按 Ctrl+C 退出）")
    print("测试模式：将在当前时间+1分钟执行")

    # 计算1分钟后的时间
    next_minute = (datetime.now().minute + 1) % 60
    next_hour = datetime.now().hour
    if next_minute == 0:
        next_hour = (next_hour + 1) % 24

    test_time = f"{next_hour:02d}:{next_minute:02d}"

    run_with_intraday_schedule(
        task=test_task,
        time_points=[test_time],
        holiday_detection="simple"
    )
