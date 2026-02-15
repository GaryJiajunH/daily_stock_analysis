# 🚀 Docker 快速启动指南

## 📋 5分钟快速部署

### 步骤1：配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件（必填项）
nano .env
```

**最小配置**（仅启动基础功能）：
```bash
# 股票列表
STOCK_LIST=600519,000001,300750

# 通知渠道（至少配置一个）
FEISHU_WEBHOOK_URL=your_feishu_webhook_url
# 或
WECHAT_WEBHOOK_URL=your_wechat_webhook_url
```

**启用日内分析**（推荐）：
```bash
# 日内实时分析
INTRADAY_ENABLED=true
INTRADAY_TIME_POINTS=09:30,13:00,14:45
INTRADAY_MODE=lightweight

# 信号过滤
INTRADAY_NOTIFY_THRESHOLD=60
INTRADAY_SIGNAL_TYPES=STRONG_BUY,BUY,STRONG_SELL
INTRADAY_VOLUME_ALERT=3.0
```

**可选AI增强**（启用AI分析和新闻搜索）：
```bash
# AI 分析（可选）
GEMINI_API_KEY=your_gemini_api_key

# 新闻搜索（可选）
TAVILY_API_KEYS=your_tavily_api_key
```

---

### 步骤2：构建镜像

```bash
# 构建 Docker 镜像（首次需要，约5-10分钟）
docker-compose -f docker-compose-full.yml build
```

**预期输出**：
```
Building webui
Step 1/20 : FROM node:20-slim AS web-builder
...
Successfully built abc123def456
Successfully tagged daily_stock_analysis:latest
```

---

### 步骤3：启动服务

**方案1：仅 WebUI**（最简单）
```bash
docker-compose -f docker-compose-full.yml up -d webui
```
访问：http://localhost:8000

**方案2：WebUI + 盘后分析**（每天18:00自动分析）
```bash
docker-compose -f docker-compose-full.yml up -d webui daily
```

**方案3：完整部署**（推荐 - WebUI + 盘后 + 日内）
```bash
docker-compose -f docker-compose-full.yml up -d
```

---

### 步骤4：验证部署

**查看服务状态**：
```bash
docker-compose -f docker-compose-full.yml ps
```

**预期输出**：
```
NAME                      STATUS              PORTS
stock-webui               Up (healthy)        0.0.0.0:8000->8000/tcp
stock-daily-analyzer      Up
stock-intraday-analyzer   Up
```

**检查 WebUI**：
```bash
curl http://localhost:8000/health
```

**查看日志**：
```bash
# 查看所有服务日志
docker-compose -f docker-compose-full.yml logs -f

# 查看特定服务
docker-compose -f docker-compose-full.yml logs -f intraday
```

**预期日志**（日内分析器）：
```
stock-intraday-analyzer  | ============================================================
stock-intraday-analyzer  | 日内实时分析调度器启动
stock-intraday-analyzer  | 交易时间点: 09:30, 13:00, 14:45
stock-intraday-analyzer  | 节假日检测: simple
stock-intraday-analyzer  | 下次执行: 2025-02-17 09:30:00
stock-intraday-analyzer  | ============================================================
stock-intraday-analyzer  | ✅ 今日为交易日
```

---

## 🎯 访问服务

启动后，打开浏览器访问：

- **WebUI 主页**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## 🔧 常用命令

### 服务管理
```bash
# 启动所有服务
docker-compose -f docker-compose-full.yml up -d

# 停止所有服务
docker-compose -f docker-compose-full.yml down

# 重启服务
docker-compose -f docker-compose-full.yml restart

# 重启特定服务
docker-compose -f docker-compose-full.yml restart intraday
```

### 日志查看
```bash
# 实时查看所有日志
docker-compose -f docker-compose-full.yml logs -f

# 查看最近100行
docker-compose -f docker-compose-full.yml logs --tail=100

# 查看特定服务
docker-compose -f docker-compose-full.yml logs -f webui
docker-compose -f docker-compose-full.yml logs -f daily
docker-compose -f docker-compose-full.yml logs -f intraday
```

### 状态检查
```bash
# 查看服务状态
docker-compose -f docker-compose-full.yml ps

# 查看资源使用
docker stats stock-webui stock-daily-analyzer stock-intraday-analyzer

# 进入容器（调试用）
docker exec -it stock-webui bash
```

---

## ⚙️ 配置修改

### 修改日内分析时间点

编辑 `.env` 文件：
```bash
# 改为开盘和尾盘（仅2个时间点）
INTRADAY_TIME_POINTS=09:30,14:45
```

重启服务：
```bash
docker-compose -f docker-compose-full.yml restart intraday
```

### 修改盘后分析时间

编辑 `.env` 文件：
```bash
# 改为17:00执行
SCHEDULE_TIME=17:00
```

重启服务：
```bash
docker-compose -f docker-compose-full.yml restart daily
```

### 修改WebUI端口

编辑 `.env` 文件：
```bash
# 改为8080端口
WEBUI_PORT=8080
```

重启服务：
```bash
docker-compose -f docker-compose-full.yml restart webui
```

访问：http://localhost:8080

---

## 🐛 故障排查

### 问题1：容器无法启动

**检查日志**：
```bash
docker-compose -f docker-compose-full.yml logs webui
```

**常见原因**：
1. 端口被占用 → 修改 `WEBUI_PORT` 或停止占用进程
2. .env 配置错误 → 检查必填项是否配置

### 问题2：日内分析不运行

**检查配置**：
```bash
docker exec stock-intraday-analyzer env | grep INTRADAY
```

**检查时区**：
```bash
docker exec stock-intraday-analyzer date
# 应显示：Mon Feb 17 09:30:00 CST 2025
```

**查看调度日志**：
```bash
docker logs -f stock-intraday-analyzer | grep -E "日内|交易日|下次执行"
```

### 问题3：无法访问 WebUI

**测试连接**：
```bash
# 从容器内测试
docker exec stock-webui curl -f http://localhost:8000/health

# 从宿主机测试
curl http://localhost:8000/health
```

**检查端口映射**：
```bash
docker port stock-webui
# 应输出：8000/tcp -> 0.0.0.0:8000
```

---

## 📊 服务说明

### WebUI 服务
- **端口**：8000
- **功能**：Web管理界面、RESTful API、机器人交互
- **资源**：CPU 0.5核、内存 512MB
- **启动**：立即启动，无定时任务

### Daily 分析服务
- **功能**：盘后完整分析（AI + 新闻 + 技术分析）
- **执行时间**：每天 18:00（可配置 `SCHEDULE_TIME`）
- **资源**：CPU 1核、内存 512MB
- **执行时长**：约5-10分钟（取决于股票数量）

### Intraday 分析服务
- **功能**：日内实时分析（仅技术分析，快速轻量）
- **执行时间**：9:30、13:00、14:45（可配置 `INTRADAY_TIME_POINTS`）
- **资源**：CPU 0.5核、内存 256MB
- **执行时长**：约1-2分钟（取决于股票数量）
- **成本**：$0/月（使用免费API）

---

## 💰 成本说明

### 免费使用（默认配置）
```bash
# 不配置AI和新闻API密钥
# GEMINI_API_KEY=  # 留空
# TAVILY_API_KEYS= # 留空
```

**功能**：
- ✅ WebUI 管理界面
- ✅ 技术分析（MA、MACD、RSI）
- ✅ 日内实时分析（3次/天）
- ✅ 盘后分析（1次/天）
- ❌ AI智能分析（需要Gemini API）
- ❌ 新闻搜索（需要Tavily API）

**成本**：$0/月

### 完整功能（配置API密钥）
```bash
# 配置AI和新闻API
GEMINI_API_KEY=your_key
TAVILY_API_KEYS=your_key
```

**成本**：
- Gemini API：~$1-2/月（每日分析 $0.02-0.05/次）
- Tavily API：$0/月（免费额度 1000次/月）
- **总计**：~$1-2/月

---

## 📚 更多文档

- [日内分析详细指南](docs/INTRADAY_ANALYSIS.md)
- [WebUI 使用指南](docs/WEBUI_GUIDE.md)
- [Docker 部署详解](docs/DOCKER_DEPLOYMENT.md)
- [项目主文档](README.md)

---

## ✅ 快速检查清单

- [ ] 已配置 `.env` 文件
- [ ] 已配置股票列表 `STOCK_LIST`
- [ ] 已配置至少一个通知渠道（飞书/企业微信等）
- [ ] 已构建 Docker 镜像
- [ ] 已启动服务 `docker-compose up -d`
- [ ] WebUI 可访问 http://localhost:8000
- [ ] 查看日志确认服务正常运行

---

## 🎉 完成！

现在你的股票分析系统已经运行起来了！

- **日内分析**会在 9:30、13:00、14:45 自动执行
- **盘后分析**会在 18:00 自动执行
- **触发信号时**会自动推送通知到飞书/企业微信

祝投资顺利！📈
