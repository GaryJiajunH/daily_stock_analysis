# -*- coding: utf-8 -*-
"""
===================================
日内实时分析流水线（轻量级）
===================================

职责：
1. 获取实时行情快照
2. 执行技术分析（复用 StockTrendAnalyzer）
3. 应用信号过滤器
4. 生成轻量级分析结果

与完整流水线（StockAnalysisPipeline）的区别：
- ❌ 不调用 AI 分析（GeminiAnalyzer / OpenAI）
- ❌ 不进行新闻搜索（SearchService）
- ✅ 仅技术分析 + 实时行情
- ✅ 执行速度 5-10秒/股（vs 30秒）
- ✅ 成本 $0（使用免费 API）

数据源（全部免费）：
- PyTDX（通达信，无限制）
- Tencent Finance（腾讯财经，~1000次/天）
- Sina Finance（新浪财经，~500次/天）
- EFinance（东方财富，~200次/天）
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional
from random import uniform

import pandas as pd

from src.config import get_config
from src.stock_analyzer import StockTrendAnalyzer
from src.storage import get_db
from src.core.signal_filter import SignalFilter, IntradayResult
from data_provider.base import DataFetcherManager

logger = logging.getLogger(__name__)


class IntradayAnalysisPipeline:
    """
    日内实时分析流水线

    设计原则：
    1. 速度优先：跳过 AI 和新闻，仅技术分析
    2. 成本优先：使用 100% 免费 API
    3. 信号质量：通过 SignalFilter 过滤噪音

    使用示例：
        pipeline = IntradayAnalysisPipeline(config, signal_filter)
        results = pipeline.run(['600519', '000001'])
        # results 仅包含触发信号的股票
    """

    def __init__(self, config=None, signal_filter: SignalFilter = None):
        """
        初始化日内分析流水线

        Args:
            config: Config 实例（可选，默认使用全局配置）
            signal_filter: SignalFilter 实例（可选，默认自动创建）
        """
        self.config = config or get_config()
        self.db = get_db()

        # 数据源管理器（自动故障切换，使用默认数据源）
        self.fetcher_manager = DataFetcherManager()

        # 技术分析器（复用现有，不需要 config 参数）
        self.trend_analyzer = StockTrendAnalyzer()

        # 信号过滤器
        self.signal_filter = signal_filter or SignalFilter(self.config)

        # 并发配置
        self.max_workers = getattr(self.config, 'max_workers', 3)

        # 请求间隔（防止 API 限流）
        self.request_delay = (
            getattr(self.config, 'akshare_sleep_min', 2.0),
            getattr(self.config, 'akshare_sleep_max', 3.0)
        )

        logger.info(
            f"日内分析流水线初始化完成 - "
            f"并发数: {self.max_workers}, "
            f"请求间隔: {self.request_delay[0]}-{self.request_delay[1]}秒"
        )

    def analyze_intraday(self, code: str) -> Optional[IntradayResult]:
        """
        分析单只股票（日内轻量级）

        执行步骤：
        1. 获取实时行情（price, volume_ratio, turnover_rate）
        2. 获取历史数据（用于计算 MA/MACD/RSI）
        3. 运行技术分析（StockTrendAnalyzer.analyze）
        4. 构建 IntradayResult

        Args:
            code: 股票代码（如 600519）

        Returns:
            IntradayResult 或 None（失败时）
        """
        try:
            # ========== 步骤 1: 获取实时行情 ==========
            realtime_quote = self.fetcher_manager.get_realtime_quote(code)

            if not realtime_quote:
                logger.warning(f"[{code}] 无法获取实时行情，跳过")
                return None

            # ========== 步骤 2: 获取历史数据 ==========
            context = self.db.get_analysis_context(code)

            if not context or 'raw_data' not in context:
                logger.warning(f"[{code}] 无历史数据，跳过")
                return None

            raw_data = context['raw_data']
            if not raw_data:
                logger.warning(f"[{code}] 历史数据为空，跳过")
                return None

            # 转换为 DataFrame
            df = pd.DataFrame(raw_data)

            if len(df) < 20:
                logger.warning(f"[{code}] 数据不足（{len(df)} 天），跳过")
                return None

            # ========== 步骤 3: 技术分析 ==========
            trend_result = self.trend_analyzer.analyze(df, code)

            # ========== 步骤 4: 构建轻量级结果 ==========
            intraday_result = IntradayResult(
                code=code,
                stock_name=realtime_quote.name,
                timestamp=datetime.now(),
                current_price=realtime_quote.price,
                change_pct=realtime_quote.change_pct,

                # 趋势和信号
                trend_status=trend_result.trend_status,
                buy_signal=trend_result.buy_signal,
                signal_score=trend_result.signal_score,

                # 均线
                ma5=trend_result.ma5,
                ma10=trend_result.ma10,
                ma20=trend_result.ma20,
                bias_ma5=trend_result.bias_ma5,

                # 量能和其他指标
                volume_ratio=realtime_quote.volume_ratio if hasattr(realtime_quote, 'volume_ratio') else None,
                volume_status=trend_result.volume_status.value if trend_result.volume_status else None,
                macd_status=trend_result.macd_status,
                rsi_12=trend_result.rsi_12,

                # 信号理由和风险
                signal_reasons=trend_result.signal_reasons,
                risk_factors=trend_result.risk_factors
            )

            logger.info(
                f"[{code}] {realtime_quote.name} - "
                f"价格: {realtime_quote.price:.2f} ({realtime_quote.change_pct:+.2f}%), "
                f"信号: {trend_result.buy_signal.value} (评分: {trend_result.signal_score})"
            )

            return intraday_result

        except Exception as e:
            logger.exception(f"[{code}] 日内分析失败: {e}")
            return None

    def run(self, stock_codes: List[str]) -> List[IntradayResult]:
        """
        批量日内分析

        执行流程：
        1. 使用线程池并发分析（max_workers=3）
        2. 每只股票分析间隔 2-3 秒（防 API 限流）
        3. 应用信号过滤器
        4. 仅返回触发信号的结果

        Args:
            stock_codes: 股票代码列表

        Returns:
            触发信号的 IntradayResult 列表
        """
        if not stock_codes:
            logger.warning("股票列表为空，跳过日内分析")
            return []

        logger.info(f"开始日内分析 - 共 {len(stock_codes)} 只股票")
        start_time = datetime.now()

        triggered_results = []
        analyzed_count = 0
        failed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_code = {
                executor.submit(self._analyze_with_delay, code): code
                for code in stock_codes
            }

            # 收集结果
            for future in as_completed(future_to_code):
                code = future_to_code[future]

                try:
                    result = future.result()
                    analyzed_count += 1

                    if result is None:
                        failed_count += 1
                        continue

                    # 应用信号过滤器
                    if self.signal_filter.should_notify(result):
                        triggered_results.append(result)
                        logger.info(
                            f"[{code}] ✅ 信号触发: {result.buy_signal.value} "
                            f"(评分: {result.signal_score})"
                        )
                    else:
                        logger.debug(f"[{code}] ⏸️  信号未触发，已过滤")

                except Exception as e:
                    logger.error(f"[{code}] 分析任务异常: {e}")
                    failed_count += 1

        # 统计信息
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"日内分析完成 - "
            f"耗时: {elapsed:.1f}秒, "
            f"成功: {analyzed_count - failed_count}/{len(stock_codes)}, "
            f"触发信号: {len(triggered_results)} 只"
        )

        return triggered_results

    def _analyze_with_delay(self, code: str) -> Optional[IntradayResult]:
        """
        带延迟的分析（防止 API 限流）

        Args:
            code: 股票代码

        Returns:
            IntradayResult 或 None
        """
        # 随机延迟（2-3秒）
        delay = uniform(*self.request_delay)
        time.sleep(delay)

        return self.analyze_intraday(code)


def create_intraday_pipeline(config=None) -> IntradayAnalysisPipeline:
    """
    便捷函数：创建日内分析流水线

    Args:
        config: Config 实例（可选）

    Returns:
        IntradayAnalysisPipeline 实例
    """
    config = config or get_config()
    signal_filter = SignalFilter(config)
    return IntradayAnalysisPipeline(config, signal_filter)


if __name__ == "__main__":
    # 测试日内分析流水线
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )

    print("=" * 60)
    print("日内分析流水线测试")
    print("=" * 60)

    # 测试股票
    test_codes = ['600519', '000001', '300750']

    if len(sys.argv) > 1:
        test_codes = sys.argv[1].split(',')

    print(f"\n测试股票: {', '.join(test_codes)}\n")

    # 创建流水线
    pipeline = create_intraday_pipeline()

    # 执行分析
    results = pipeline.run(test_codes)

    # 显示结果
    print(f"\n{'=' * 60}")
    print(f"触发信号数: {len(results)}")
    print(f"{'=' * 60}\n")

    for result in results:
        print(f"[{result.code}] {result.stock_name}")
        print(f"  当前价: {result.current_price:.2f} ({result.change_pct:+.2f}%)")
        print(f"  信号: {result.buy_signal.value} (评分: {result.signal_score})")
        print(f"  MA5: {result.ma5:.2f} (乖离: {result.bias_ma5:+.2f}%)")

        if result.volume_ratio:
            print(f"  量比: {result.volume_ratio:.2f}x")

        if result.signal_reasons:
            print(f"  理由: {', '.join(result.signal_reasons[:3])}")

        print()
