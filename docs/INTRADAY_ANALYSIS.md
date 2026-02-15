# 日内实时分析功能使用指南

## 概述

日内实时分析功能允许您在交易时段的关键时间点（开盘、午盘、尾盘）自动分析股票，及时捕捉盘中机会。

### 核心特性

✅ **零成本运行** - 使用100%免费API（PyTDX、腾讯财经、新浪财经）
✅ **快速分析** - 5-10秒/股（vs 完整分析30秒）
✅ **智能过滤** - 只通知有价值的信号，避免通知疲劳
✅ **灵活配置** - 自定义时间点、信号类型、阈值
✅ **独立运行** - 与盘后分析互不干扰，可同时部署

---

## 快速开始

### 1. 配置环境变量

编辑 `.env` 文件，添加以下配置：

```bash
# 启用日内分析
INTRADAY_ENABLED=true

# 分析时间点（默认：开盘、午盘、尾盘）
INTRADAY_TIME_POINTS=09:30,13:00,14:45

# 分析模式（推荐 lightweight）
INTRADAY_MODE=lightweight

# 信号过滤配置
INTRADAY_NOTIFY_THRESHOLD=60
INTRADAY_SIGNAL_TYPES=STRONG_BUY,BUY,STRONG_SELL
INTRADAY_VOLUME_ALERT=3.0
INTRADAY_MIN_NOTIFY_INTERVAL=1800

# 节假日检测（simple 或 advanced）
INTRADAY_HOLIDAY_DETECTION=simple
```

### 2. 启动日内分析

**方式1: 命令行启动**
```bash
# 基础启动
python main.py --intraday-schedule

# 指定模式
python main.py --intraday-schedule --intraday-mode lightweight

# 测试模式（不发送通知）
python main.py --intraday-schedule --no-notify
```

**方式2: Docker 部署（推荐）**

在 `docker-compose.yml` 中添加服务：

```yaml
services:
  # 盘后完整分析（18:00）
  daily-analyzer:
    image: stock-analysis:latest
    command: python main.py --schedule
    environment:
      - SCHEDULE_TIME=18:00
      - TZ=Asia/Shanghai
    restart: unless-stopped

  # 日内实时分析（9:30, 13:00, 14:45）
  intraday-analyzer:
    image: stock-analysis:latest
    command: python main.py --intraday-schedule
    environment:
      - INTRADAY_ENABLED=true
      - INTRADAY_TIME_POINTS=09:30,13:00,14:45
      - INTRADAY_MODE=lightweight
      - TZ=Asia/Shanghai  # 必须设置为中国时区
    restart: unless-stopped
```

启动容器：
```bash
docker-compose up -d intraday-analyzer
```

---

## 配置详解

### 分析模式对比

| 模式 | 分析内容 | 速度 | 成本 | 适用场景 |
|------|---------|------|------|----------|
| **lightweight** | 技术指标 + 实时行情 | 5-10秒 | $0 | 日内交易（推荐） |
| **hybrid** | 开盘/尾盘轻量 + 午盘完整 | 混合 | ~$0.50/月 | 平衡模式 |
| **full** | AI + 新闻 + 技术 | 30秒 | ~$5/月 | 完整分析 |

**推荐配置**: `lightweight` 模式

- 使用免费 API（PyTDX, Tencent, Sina）
- 跳过 AI 分析（无 Gemini/OpenAI 成本）
- 跳过新闻搜索（无 Tavily/SerpAPI 成本）
- **总成本: $0/月** ✅

### 时间点配置

**默认时间点**:
- `09:30` - 开盘（观察开盘走势）
- `13:00` - 午盘（下午开盘）
- `14:45` - 尾盘（收盘前15分钟）

**自定义示例**:
```bash
# 更频繁的分析（每小时一次）
INTRADAY_TIME_POINTS=09:30,10:30,11:00,13:00,14:00,14:45

# 仅关注开盘和尾盘
INTRADAY_TIME_POINTS=09:30,14:45

# 激进日内交易（每30分钟）
INTRADAY_TIME_POINTS=09:30,10:00,10:30,11:00,13:00,13:30,14:00,14:30,14:45
```

⚠️ **注意**: 时间点越多，API 调用越频繁，但使用免费 API 仍无成本顾虑。

### 信号过滤配置

**评分阈值** (`INTRADAY_NOTIFY_THRESHOLD`)
- 范围: 0-100
- 默认: 60
- 说明: 只有评分 >= 此值才通知
- 建议:
  - 激进: 50（更多信号）
  - 稳健: 60（推荐）
  - 保守: 70（只要强信号）

**信号类型白名单** (`INTRADAY_SIGNAL_TYPES`)
- 可选值: `STRONG_BUY`, `BUY`, `HOLD`, `WAIT`, `SELL`, `STRONG_SELL`
- 默认: `STRONG_BUY,BUY,STRONG_SELL`
- 说明: 只通知列表中的信号类型
- 建议:
  - 买入关注: `STRONG_BUY,BUY`
  - 全面监控: `STRONG_BUY,BUY,STRONG_SELL,SELL`
  - 仅强信号: `STRONG_BUY,STRONG_SELL`

**异常放量阈值** (`INTRADAY_VOLUME_ALERT`)
- 默认: 3.0
- 说明: 量比 > 此值时，无论什么信号都通知
- 建议:
  - 激进: 2.0（更敏感）
  - 稳健: 3.0（推荐）
  - 保守: 5.0（只要极端放量）

**通知间隔** (`INTRADAY_MIN_NOTIFY_INTERVAL`)
- 单位: 秒
- 默认: 1800（30分钟）
- 说明: 同一股票在此时间内不重复通知相同信号
- 建议:
  - 激进日内: 900（15分钟）
  - 一般: 1800（30分钟，推荐）
  - 保守: 3600（1小时）

### 节假日检测

**Simple 模式** (默认)
```bash
INTRADAY_HOLIDAY_DETECTION=simple
```
- 仅跳过周末（周六、周日）
- 无需额外依赖
- 可能在法定节假日仍运行（但市场关闭，API 无数据，会自动跳过）

**Advanced 模式** (可选)
```bash
INTRADAY_HOLIDAY_DETECTION=advanced
```
- 检测中国所有法定节假日（春节、国庆等）
- 需要安装依赖: `pip install chinese-calendar>=1.8.0`
- 更精确，避免无效运行

---

## 通知示例

### 日内实时信号报告格式

```
# 🔔 日内实时信号 [13:00]

> 2025-02-17 | 触发信号数: **2** 只

---

## ⭐ [600519] 贵州茅台

**操作建议**: 强烈买入 | **评分**: 85/100

### 💹 当前行情

📈 **当前价**: 1850.00 元 (+2.50%)

### 📊 技术指标

- **趋势**: 多头排列
- **MA5**: 1820.00 (乖离 +1.65%)
- **MA10**: 1800.00
- **MA20**: 1780.00
- 🔥 **量比**: 2.30x
- ✅ **MACD**: 金叉
- 🟡 **RSI(12)**: 65.0

### 💡 信号理由

✅ 多头排列完整，趋势向上
✅ MACD金叉，动能增强
✅ 缩量回调至MA5附近，买点出现

---

*🤖 日内实时分析 | 仅供参考，不构成投资建议*
```

---

## 常见问题

### Q1: 日内分析和盘后分析可以同时运行吗？

**A**: 可以！两个模式完全独立，互不干扰。

推荐配置：
- **Docker 部署**: 运行两个独立容器
  - `daily-analyzer`: 18:00 盘后完整分析（AI + 新闻）
  - `intraday-analyzer`: 9:30/13:00/14:45 轻量级分析

- **单机部署**: 使用 `screen` 或 `tmux` 开两个终端
  ```bash
  # 终端1: 盘后分析
  python main.py --schedule

  # 终端2: 日内分析
  python main.py --intraday-schedule
  ```

### Q2: 为什么推荐 lightweight 模式？

**A**:
1. **零成本**: 使用免费 API，无需 Gemini/Tavily 等付费服务
2. **速度快**: 5-10秒/股 vs 30秒（完整分析）
3. **足够用**: 技术指标已能捕捉90%的交易机会
4. **高频友好**: 适合一天3次的频繁分析

如需 AI 洞察，可在18:00盘后使用完整分析。

### Q3: 如何避免通知疲劳？

**A**: 系统内置智能过滤器，只通知有价值的信号：

**自动过滤**:
- ❌ HOLD/WAIT 信号（除非评分显著变化）
- ❌ 横盘整理（CONSOLIDATION）
- ❌ 重复信号（30分钟内相同信号去重）

**只通知**:
- ✅ 强烈买入/卖出（STRONG_BUY/STRONG_SELL）
- ✅ 异常放量（volume_ratio > 3.0）
- ✅ MACD 金叉/死叉
- ✅ RSI 超买/超卖（<30 或 >70）
- ✅ 信号翻转（BUY ↔ SELL）

**调整建议**:
- 提高 `INTRADAY_NOTIFY_THRESHOLD` (如 70)
- 缩小 `INTRADAY_SIGNAL_TYPES` (仅 `STRONG_BUY,STRONG_SELL`)
- 增加 `INTRADAY_MIN_NOTIFY_INTERVAL` (如 3600秒)

### Q4: 节假日会运行吗？

**A**:
- **Simple 模式**: 周末自动跳过，法定节假日可能运行但无数据
- **Advanced 模式**: 所有节假日自动跳过（需安装 `chinese-calendar`）

无论哪种模式，市场关闭时 API 无数据，系统会自动跳过分析。

### Q5: 如何测试日内分析？

**A**: 使用 `--no-notify` 测试模式：

```bash
# 测试调度器和分析流程（不发送通知）
python main.py --intraday-schedule --no-notify

# 查看日志
tail -f logs/daily_stock_analysis.log
```

**预期输出**:
```
[INFO] 日内实时分析调度器启动
[INFO] 交易时间点: 09:30, 13:00, 14:45
[INFO] ✅ 今日为交易日
[INFO] [日内] 开始分析 10 只股票...
[INFO] [600519] 贵州茅台 - 价格: 1850.00 (+2.50%), 信号: 强烈买入 (评分: 85)
[INFO] [日内] 触发 2 个信号
[INFO] [日内] 通知已禁用（--no-notify）
```

### Q6: 成本到底是多少？

**A**:

| 场景 | 日内分析 | 盘后分析 | 总计/月 |
|------|---------|---------|---------|
| **仅日内（lightweight）** | $0 | - | **$0** ✅ |
| **仅盘后（full）** | - | ~$1.50 | ~$1.50 |
| **日内 + 盘后** | $0 | ~$1.50 | **~$1.50** ✅ |

**结论**: 添加日内分析不增加任何成本！

---

## 进阶配置

### 混合模式 (Hybrid)

在不同时间点使用不同分析深度：

```bash
INTRADAY_MODE=hybrid
```

**策略**:
- **9:30 开盘**: lightweight（快速扫描）
- **13:00 午盘**: full（深度分析，含 AI+新闻）
- **14:45 尾盘**: lightweight（快速决策）

**实现** (需修改代码):
```python
def intraday_task():
    current_time = datetime.now().strftime('%H:%M')

    if current_time == '13:00':
        # 午盘使用完整分析
        run_full_analysis(config, args, stock_codes)
    else:
        # 其他时间使用轻量级分析
        results = pipeline.run(stock_codes)
        # ...
```

### 自定义信号逻辑

修改 `src/core/signal_filter.py` 中的 `should_notify()` 方法：

```python
# 示例：添加自定义规则
def should_notify(self, result: IntradayResult) -> bool:
    # ... 现有逻辑 ...

    # 自定义规则：只通知 MA5 乖离率 < 3% 的买入信号
    if result.buy_signal == BuySignal.BUY:
        if abs(result.bias_ma5) < 3.0:
            logger.info(f"[{result.code}] ✅ 符合低乖离买点")
            return True

    # ... 其他逻辑 ...
```

---

## 故障排查

### 问题1: 调度器不运行

**症状**: 启动后没有任何分析执行

**排查**:
1. 检查时区设置: `echo $TZ` 应为 `Asia/Shanghai`
2. 检查当前时间: `date` 确认时间正确
3. 检查是否为交易日: 周末会自动跳过
4. 查看日志: `tail -f logs/daily_stock_analysis.log`

**解决**:
```bash
# Docker 设置时区
environment:
  - TZ=Asia/Shanghai

# 系统设置时区
export TZ=Asia/Shanghai
```

### 问题2: 无法获取实时行情

**症状**: 日志显示 "无法获取实时行情"

**原因**:
- API 限流
- 网络问题
- 数据源暂时不可用

**解决**:
1. 检查网络连接
2. 调整数据源优先级:
   ```bash
   REALTIME_SOURCE_PRIORITY=pytdx,tencent,akshare_sina,efinance
   ```
3. 增加请求间隔:
   ```bash
   akshare_sleep_min=3
   akshare_sleep_max=6
   ```

### 问题3: 通知未发送

**症状**: 分析完成但没有收到通知

**排查**:
1. 检查 `--no-notify` 是否开启
2. 检查是否有信号触发: 日志中搜索 "触发信号"
3. 检查通知渠道配置: 确认 Webhook URL 等已配置

**解决**:
```bash
# 测试通知渠道
python -c "
from src.notification import NotificationService
service = NotificationService()
print('可用渠道:', service.get_available_channels())
service.send('测试消息')
"
```

---

## 最佳实践

### 1. 推荐配置模板

**稳健型投资者**:
```bash
INTRADAY_ENABLED=true
INTRADAY_TIME_POINTS=09:30,14:45  # 只看开盘和尾盘
INTRADAY_MODE=lightweight
INTRADAY_NOTIFY_THRESHOLD=70  # 高阈值
INTRADAY_SIGNAL_TYPES=STRONG_BUY,STRONG_SELL  # 只要强信号
```

**激进型交易者**:
```bash
INTRADAY_ENABLED=true
INTRADAY_TIME_POINTS=09:30,10:30,11:00,13:00,14:00,14:45  # 更频繁
INTRADAY_MODE=lightweight
INTRADAY_NOTIFY_THRESHOLD=50  # 低阈值
INTRADAY_SIGNAL_TYPES=STRONG_BUY,BUY,SELL,STRONG_SELL  # 买卖都要
INTRADAY_MIN_NOTIFY_INTERVAL=900  # 15分钟间隔
```

**平衡型投资者**:
```bash
INTRADAY_ENABLED=true
INTRADAY_TIME_POINTS=09:30,13:00,14:45  # 标准3次
INTRADAY_MODE=lightweight
INTRADAY_NOTIFY_THRESHOLD=60  # 中等阈值
INTRADAY_SIGNAL_TYPES=STRONG_BUY,BUY,STRONG_SELL  # 默认配置
```

### 2. 资源优化

**降低 API 调用频率**:
```bash
# 增加缓存时间
REALTIME_CACHE_TTL=900  # 15分钟（默认10分钟）

# 减少并发数
MAX_WORKERS=2  # 降低到2（默认3）

# 增加请求间隔
akshare_sleep_min=3
akshare_sleep_max=6
```

### 3. 监控与告警

**系统监控**:
```bash
# 检查日内调度器状态
docker logs -f intraday-analyzer

# 监控资源使用
docker stats intraday-analyzer
```

**预期资源**:
- CPU: <10%
- 内存: ~100MB
- 网络: 极低（免费 API）

---

## 总结

日内实时分析功能为您提供了：

✅ **零成本** - 使用100%免费API
✅ **实时性** - 3个关键时间点捕捉机会
✅ **智能化** - 自动过滤噪音，只推送有价值信号
✅ **灵活性** - 高度可配置，适应不同交易风格
✅ **可靠性** - 完善的错误处理和降级策略

**开始使用**:
1. 复制 `.env.example` 到 `.env`
2. 设置 `INTRADAY_ENABLED=true`
3. 运行 `python main.py --intraday-schedule`
4. 享受日内实时分析带来的便利！

如有问题，请参考[项目 README](../README.md) 或提交 Issue。
