# -*- coding: utf-8 -*-
"""
===================================
智能信号过滤器
===================================

职责：
1. 过滤掉噪音信号，只保留有价值的通知
2. 防止通知疲劳（notification fatigue）
3. 智能去重和时间间隔控制

通知触发条件（满足任一即通知）：
- 强烈买入/卖出信号（STRONG_BUY, STRONG_SELL）
- 异常放量（volume_ratio > threshold）
- MACD 金叉/死叉
- RSI 超买/超卖（< 30 或 > 70）
- 信号评分显著变化（>= 15 points）
- 信号类型翻转（BUY ↔ SELL）

不通知条件：
- HOLD/WAIT 信号且评分变化 < 阈值
- 横盘整理（CONSOLIDATION）
- 连续相同信号（30分钟内）
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field

from src.stock_analyzer import BuySignal, MACDStatus, TrendStatus

logger = logging.getLogger(__name__)


@dataclass
class IntradayResult:
    """
    日内分析结果（轻量级数据模型）

    与完整的 TrendAnalysisResult 的区别：
    - 无 AI 分析内容
    - 无新闻情报
    - 仅包含技术指标和信号
    """
    code: str
    stock_name: str
    timestamp: datetime
    current_price: float
    change_pct: float

    # 技术指标
    trend_status: TrendStatus
    buy_signal: BuySignal
    signal_score: int
    ma5: float
    ma10: float
    ma20: float
    bias_ma5: float
    volume_ratio: Optional[float] = None
    volume_status: Optional[str] = None
    macd_status: Optional[MACDStatus] = None
    rsi_12: Optional[float] = None

    # 信号详情
    signal_reasons: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


class SignalFilter:
    """
    智能信号过滤器

    核心逻辑：
    1. 只通知有价值的信号（强信号、异常情况、趋势变化）
    2. 避免重复通知（30分钟内相同信号去重）
    3. 可配置的阈值参数

    使用示例：
        filter = SignalFilter(config)
        if filter.should_notify(result):
            send_notification(result)
    """

    def __init__(self, config):
        """
        初始化信号过滤器

        Args:
            config: Config 实例，包含过滤参数
        """
        self.config = config

        # 上次通知记录 {code: (timestamp, signal_type, signal_score)}
        self._last_notifications: Dict[str, tuple] = {}

        # 从配置读取参数
        self.notify_threshold = getattr(config, 'intraday_notify_threshold', 60)
        self.volume_alert = getattr(config, 'intraday_volume_alert', 3.0)
        self.min_notify_interval = getattr(config, 'intraday_min_notify_interval', 1800)  # 30分钟

        # 允许通知的信号类型
        signal_types_str = getattr(config, 'intraday_signal_types', ['STRONG_BUY', 'BUY', 'STRONG_SELL'])
        self.allowed_signal_types = set(signal_types_str)

        logger.info(
            f"信号过滤器初始化完成 - "
            f"评分阈值: {self.notify_threshold}, "
            f"放量阈值: {self.volume_alert}, "
            f"通知间隔: {self.min_notify_interval}秒"
        )

    def should_notify(self, result: IntradayResult) -> bool:
        """
        判断是否应该发送通知

        Args:
            result: 日内分析结果

        Returns:
            True: 发送通知, False: 静默
        """
        code = result.code
        signal = result.buy_signal
        score = result.signal_score

        # ========== 规则 1: 强烈买入/卖出信号 - 必须通知 ==========
        if signal == BuySignal.STRONG_BUY:
            logger.info(f"[{code}] ✅ 触发强烈买入信号")
            self._record_notification(code, signal, score)
            return True

        if signal == BuySignal.STRONG_SELL:
            logger.info(f"[{code}] ✅ 触发强烈卖出信号")
            self._record_notification(code, signal, score)
            return True

        # ========== 规则 2: 异常放量 - 必须通知 ==========
        if result.volume_ratio and result.volume_ratio > self.volume_alert:
            logger.info(f"[{code}] ✅ 异常放量: {result.volume_ratio:.2f}x")
            self._record_notification(code, signal, score)
            return True

        # ========== 规则 3: MACD 金叉/死叉 - 必须通知 ==========
        if result.macd_status in [
            MACDStatus.GOLDEN_CROSS_ZERO,
            MACDStatus.GOLDEN_CROSS,
            MACDStatus.DEATH_CROSS
        ]:
            logger.info(f"[{code}] ✅ MACD 信号: {result.macd_status.value}")
            self._record_notification(code, signal, score)
            return True

        # ========== 规则 4: RSI 超买/超卖 - 必须通知 ==========
        if result.rsi_12 is not None:
            if result.rsi_12 < 30:
                logger.info(f"[{code}] ✅ RSI 超卖: {result.rsi_12:.1f}")
                self._record_notification(code, signal, score)
                return True

            if result.rsi_12 > 70:
                logger.info(f"[{code}] ✅ RSI 超买: {result.rsi_12:.1f}")
                self._record_notification(code, signal, score)
                return True

        # ========== 规则 5: 检查重复通知（去重逻辑）==========
        if code in self._last_notifications:
            last_time, last_signal, last_score = self._last_notifications[code]
            time_diff = (datetime.now() - last_time).total_seconds()

            # 如果在最小通知间隔内
            if time_diff < self.min_notify_interval:
                score_change = abs(score - last_score)

                # 信号类型未变化且评分变化小 - 跳过
                if signal == last_signal and score_change < 15:
                    logger.debug(
                        f"[{code}] ⏸️  重复信号跳过 "
                        f"(间隔 {time_diff:.0f}秒, 评分变化 {score_change})"
                    )
                    return False

        # ========== 规则 6: 信号评分阈值检查 ==========
        if score < self.notify_threshold:
            logger.debug(f"[{code}] ⏸️  评分不足: {score} < {self.notify_threshold}")
            return False

        # ========== 规则 7: 信号类型白名单检查 ==========
        if signal.name not in self.allowed_signal_types:
            logger.debug(f"[{code}] ⏸️  信号类型不在白名单: {signal.name}")
            return False

        # ========== 规则 8: HOLD/WAIT 信号特殊处理 ==========
        if signal in [BuySignal.HOLD, BuySignal.WAIT]:
            # 检查与上次的评分变化
            if code in self._last_notifications:
                _, _, last_score = self._last_notifications[code]
                score_change = abs(score - last_score)

                if score_change < 15:
                    logger.debug(
                        f"[{code}] ⏸️  HOLD/WAIT 信号且评分变化小: {score_change}"
                    )
                    return False

        # ========== 规则 9: 横盘整理 - 通常不通知 ==========
        if result.trend_status == TrendStatus.CONSOLIDATION:
            logger.debug(f"[{code}] ⏸️  横盘整理，暂不通知")
            return False

        # ========== 规则 10: 检测信号翻转（BUY ↔ SELL）==========
        if code in self._last_notifications:
            _, last_signal, _ = self._last_notifications[code]

            if self._is_signal_reversal(last_signal, signal):
                logger.info(f"[{code}] ✅ 信号反转: {last_signal.name} → {signal.name}")
                self._record_notification(code, signal, score)
                return True

        # ========== 默认: 通过所有检查 - 通知 ==========
        logger.info(f"[{code}] ✅ 信号触发: {signal.name} (评分: {score})")
        self._record_notification(code, signal, score)
        return True

    def _is_signal_reversal(self, old_signal: BuySignal, new_signal: BuySignal) -> bool:
        """
        检测信号是否反转（买入 ↔ 卖出）

        Args:
            old_signal: 上次信号
            new_signal: 当前信号

        Returns:
            True: 信号反转, False: 未反转
        """
        buy_signals = {BuySignal.STRONG_BUY, BuySignal.BUY}
        sell_signals = {BuySignal.STRONG_SELL, BuySignal.SELL}

        old_is_buy = old_signal in buy_signals
        new_is_buy = new_signal in buy_signals
        old_is_sell = old_signal in sell_signals
        new_is_sell = new_signal in sell_signals

        # 买 → 卖 或 卖 → 买
        return (old_is_buy and new_is_sell) or (old_is_sell and new_is_buy)

    def _record_notification(self, code: str, signal: BuySignal, score: int):
        """
        记录通知时间和信号

        Args:
            code: 股票代码
            signal: 信号类型
            score: 信号评分
        """
        self._last_notifications[code] = (datetime.now(), signal, score)

    def clear_cache(self):
        """清空缓存（每日开盘时调用）"""
        self._last_notifications.clear()
        logger.info("信号过滤器缓存已清空")

    def get_stats(self) -> dict:
        """
        获取过滤器统计信息

        Returns:
            统计字典
        """
        return {
            "cached_stocks": len(self._last_notifications),
            "threshold": self.notify_threshold,
            "volume_alert": self.volume_alert,
            "min_interval": self.min_notify_interval,
            "allowed_signals": list(self.allowed_signal_types)
        }


if __name__ == "__main__":
    # 测试信号过滤器
    from dataclasses import dataclass

    @dataclass
    class MockConfig:
        intraday_notify_threshold: int = 60
        intraday_volume_alert: float = 3.0
        intraday_min_notify_interval: int = 1800
        intraday_signal_types: list = None

        def __post_init__(self):
            if self.intraday_signal_types is None:
                self.intraday_signal_types = ['STRONG_BUY', 'BUY', 'STRONG_SELL']

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )

    config = MockConfig()
    filter = SignalFilter(config)

    print("\n测试 1: 强烈买入信号")
    result1 = IntradayResult(
        code="600519",
        stock_name="贵州茅台",
        timestamp=datetime.now(),
        current_price=1850.0,
        change_pct=2.5,
        trend_status=TrendStatus.BULL,
        buy_signal=BuySignal.STRONG_BUY,
        signal_score=85,
        ma5=1820.0,
        ma10=1800.0,
        ma20=1780.0,
        bias_ma5=1.6
    )
    print(f"应该通知: {filter.should_notify(result1)}\n")

    print("测试 2: HOLD 信号（评分低）")
    result2 = IntradayResult(
        code="000001",
        stock_name="平安银行",
        timestamp=datetime.now(),
        current_price=12.5,
        change_pct=-0.5,
        trend_status=TrendStatus.CONSOLIDATION,
        buy_signal=BuySignal.HOLD,
        signal_score=50,
        ma5=12.6,
        ma10=12.7,
        ma20=12.8,
        bias_ma5=-0.8
    )
    print(f"应该通知: {filter.should_notify(result2)}\n")

    print("测试 3: 异常放量")
    result3 = IntradayResult(
        code="300750",
        stock_name="宁德时代",
        timestamp=datetime.now(),
        current_price=180.0,
        change_pct=1.2,
        trend_status=TrendStatus.BULL,
        buy_signal=BuySignal.HOLD,
        signal_score=55,
        ma5=178.0,
        ma10=176.0,
        ma20=174.0,
        bias_ma5=1.1,
        volume_ratio=4.5  # 异常放量
    )
    print(f"应该通知: {filter.should_notify(result3)}\n")

    print("过滤器统计:")
    print(filter.get_stats())
