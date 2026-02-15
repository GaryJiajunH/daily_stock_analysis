# Docker 部署指南

## 🚀 快速开始

### 准备工作

1. **安装 Docker 和 Docker Compose**

```bash
# 检查是否已安装
docker --version
docker-compose --version
```

如未安装，请访问：
- Docker Desktop: https://www.docker.com/products/docker-desktop
- Docker Engine (Linux): https://docs.docker.com/engine/install/

2. **配置环境变量**

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置（必填项）
nano .env  # 或使用其他编辑器
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

**完整配置**（启用所有功能）：
```bash
# AI 分析
GEMINI_API_KEY=your_gemini_api_key

# 新闻搜索
TAVILY_API_KEYS=your_tavily_api_key

# 日内分析
INTRADAY_ENABLED=true
```

---

## 📦 部署方案

### 方案1：仅 WebUI（最简单）

适合：只想使用 Web 界面查看和管理

```bash
docker-compose -f docker-compose-full.yml up -d webui
```

访问：http://localhost:8000

### 方案2：WebUI + 盘后分析

适合：每天 18:00 自动分析 + Web 管理

```bash
docker-compose -f docker-compose-full.yml up -d webui daily
```

### 方案3：完整部署（推荐）

适合：WebUI + 盘后分析(18:00) + 日内分析(9:30/13:00/14:45)

```bash
docker-compose -f docker-compose-full.yml up -d
```

---

## 🎯 详细步骤

### 步骤1：构建镜像

```bash
# 进入项目目录
cd /Users/huangjiajun/Desktop/daily_stock_analysis

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

### 步骤2：启动服务

**启动所有服务**：
```bash
docker-compose -f docker-compose-full.yml up -d
```

**查看启动状态**：
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

### 步骤3：验证部署

**检查 WebUI**：
```bash
curl http://localhost:8000/health
```

**查看日志**：
```bash
# 查看所有服务日志
docker-compose -f docker-compose-full.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose-full.yml logs -f webui
docker-compose -f docker-compose-full.yml logs -f daily
docker-compose -f docker-compose-full.yml logs -f intraday
```

**预期日志**（日内分析）：
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

## ⚙️ 配置说明

### 端口配置

默认端口：`8000`

**修改端口**：

方式1：修改 `.env`
```bash
WEBUI_PORT=8080
```

方式2：启动时指定
```bash
WEBUI_PORT=8080 docker-compose -f docker-compose-full.yml up -d
```

访问：http://localhost:8080

### 日内分析配置

编辑 `.env` 文件：

```bash
# 启用日内分析
INTRADAY_ENABLED=true

# 分析时间点（默认：开盘、午盘、尾盘）
INTRADAY_TIME_POINTS=09:30,13:00,14:45

# 分析模式（推荐 lightweight，零成本）
INTRADAY_MODE=lightweight

# 信号过滤
INTRADAY_NOTIFY_THRESHOLD=60
INTRADAY_SIGNAL_TYPES=STRONG_BUY,BUY,STRONG_SELL
INTRADAY_VOLUME_ALERT=3.0
```

修改配置后重启：
```bash
docker-compose -f docker-compose-full.yml restart intraday
```

### 盘后分析配置

```bash
# 启用定时任务
SCHEDULE_ENABLED=true

# 每日执行时间
SCHEDULE_TIME=18:00

# 启动时是否立即执行
SCHEDULE_RUN_IMMEDIATELY=true

# 是否启用大盘复盘
MARKET_REVIEW_ENABLED=true
```

---

## 🔧 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose -f docker-compose-full.yml up -d

# 启动特定服务
docker-compose -f docker-compose-full.yml up -d webui

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

# 查看最近100行日志
docker-compose -f docker-compose-full.yml logs --tail=100

# 查看特定服务日志
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

# 进入容器
docker exec -it stock-webui bash
```

### 数据管理

```bash
# 备份数据
tar -czf backup-$(date +%Y%m%d).tar.gz data/ logs/ reports/

# 清理旧日志
find logs/ -name "*.log" -mtime +30 -delete

# 查看数据库
docker exec -it stock-webui sqlite3 /app/data/stock_analysis.db
```

---

## 🐛 故障排查

### 问题1：容器无法启动

**检查日志**：
```bash
docker-compose -f docker-compose-full.yml logs webui
```

**常见原因**：
1. 端口被占用
```bash
# 检查端口
lsof -i :8000
# 解决：修改 WEBUI_PORT 或停止占用端口的进程
```

2. 配置文件错误
```bash
# 验证 .env 文件
cat .env | grep -v "^#" | grep -v "^$"
```

### 问题2：日内分析不运行

**检查时区**：
```bash
docker exec stock-intraday-analyzer date
# 应显示：Mon Feb 17 09:30:00 CST 2025
```

**检查配置**：
```bash
docker exec stock-intraday-analyzer env | grep INTRADAY
```

**查看调度日志**：
```bash
docker logs -f stock-intraday-analyzer | grep -E "日内|交易日|下次执行"
```

### 问题3：无法访问 WebUI

**检查容器状态**：
```bash
docker-compose -f docker-compose-full.yml ps
# webui 应该是 Up (healthy)
```

**测试连接**：
```bash
# 从容器内测试
docker exec stock-webui curl -f http://localhost:8000/health

# 从宿主机测试
curl http://localhost:8000/health
```

**检查防火墙**：
```bash
# Mac
sudo pfctl -s rules | grep 8000

# Linux
sudo ufw status | grep 8000
```

### 问题4：数据不持久化

**检查挂载**：
```bash
docker inspect stock-webui | grep -A 10 Mounts
```

**验证数据目录**：
```bash
ls -la data/ logs/ reports/
```

---

## 🚀 性能优化

### 调整资源限制

编辑 `docker-compose-full.yml`：

```yaml
services:
  webui:
    deploy:
      resources:
        limits:
          cpus: '2'      # 增加到2核
          memory: 1G      # 增加到1GB
        reservations:
          cpus: '0.5'
          memory: 512M
```

重启服务：
```bash
docker-compose -f docker-compose-full.yml up -d
```

### 使用外部数据库

**PostgreSQL 示例**：

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=stock_analysis
      - POSTGRES_USER=stock
      - POSTGRES_PASSWORD=your_password
    volumes:
      - postgres-data:/var/lib/postgresql/data

  webui:
    environment:
      - DATABASE_URL=postgresql://stock:your_password@db:5432/stock_analysis

volumes:
  postgres-data:
```

---

## 🔒 安全建议

### 1. 使用私有仓库

```bash
# 构建镜像
docker build -t your-registry/stock-analysis:latest -f docker/Dockerfile .

# 推送到私有仓库
docker push your-registry/stock-analysis:latest
```

### 2. 配置 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 限制网络访问

```yaml
services:
  webui:
    ports:
      - "127.0.0.1:8000:8000"  # 只允许本地访问
```

### 4. 使用 secrets

```yaml
services:
  webui:
    secrets:
      - gemini_api_key

secrets:
  gemini_api_key:
    file: ./secrets/gemini_api_key.txt
```

---

## 📊 监控与告警

### Prometheus 监控

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
```

### Grafana 可视化

```yaml
services:
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

### 健康检查告警

```bash
# 创建监控脚本
cat > monitor.sh << 'EOF'
#!/bin/bash
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "WebUI 服务异常" | mail -s "Alert" admin@example.com
fi
EOF

# 添加到 crontab
*/5 * * * * /path/to/monitor.sh
```

---

## 🎯 生产环境部署

### 完整配置示例

```yaml
version: '3.8'

services:
  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - webui

  # WebUI
  webui:
    image: your-registry/stock-analysis:latest
    command: ["python", "webui.py"]
    environment:
      - WEBUI_HOST=0.0.0.0
      - TZ=Asia/Shanghai
    volumes:
      - stock-data:/app/data
      - stock-logs:/app/logs
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

  # 盘后分析
  daily:
    image: your-registry/stock-analysis:latest
    command: ["python", "main.py", "--schedule"]
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - stock-data:/app/data
      - stock-logs:/app/logs

  # 日内分析
  intraday:
    image: your-registry/stock-analysis:latest
    command: ["python", "main.py", "--intraday-schedule"]
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - stock-data:/app/data
      - stock-logs:/app/logs

volumes:
  stock-data:
  stock-logs:
```

---

## 📝 总结

### 推荐配置

**开发环境**：
```bash
docker-compose -f docker-compose-full.yml up -d webui
```

**生产环境**：
```bash
docker-compose -f docker-compose-full.yml up -d
```

### 资源需求

| 服务 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| webui | 0.5核 | 512MB | 100MB |
| daily | 1核 | 512MB | 500MB |
| intraday | 0.5核 | 256MB | 100MB |
| **总计** | **2核** | **1.3GB** | **1GB** |

### 下一步

1. ✅ 配置 `.env` 文件
2. ✅ 构建 Docker 镜像
3. ✅ 启动服务
4. ✅ 访问 WebUI: http://localhost:8000
5. ✅ 查看日志验证运行状态

更多信息请参考：
- [日内分析指南](INTRADAY_ANALYSIS.md)
- [WebUI 使用指南](WEBUI_GUIDE.md)
- [项目 README](../README.md)
