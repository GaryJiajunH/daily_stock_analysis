# WebUI 启动指南

## 概述

本项目提供了基于 FastAPI 的 Web 后端服务和管理界面，支持：
- 📊 RESTful API 接口
- 🤖 机器人交互（飞书、钉钉、Telegram、Discord等）
- 📈 实时任务状态查询
- ⚙️ 系统配置管理
- 📝 API 文档（Swagger UI）

---

## 快速启动

### 方式1：使用 webui.py（推荐）

**最简单的启动方式**：

```bash
# 使用默认配置（127.0.0.1:8000）
python webui.py
```

**自定义监听地址和端口**：

```bash
# 方式1：环境变量
WEBUI_HOST=0.0.0.0 WEBUI_PORT=8080 python webui.py

# 方式2：.env 配置文件
# 编辑 .env
WEBUI_ENABLED=true
WEBUI_HOST=0.0.0.0
WEBUI_PORT=8000

# 启动
python webui.py
```

### 方式2：使用 main.py

**仅启动 WebUI（不执行分析）**：

```bash
# 方式1：使用 --webui-only
python main.py --webui-only

# 方式2：使用 --serve-only
python main.py --serve-only

# 自定义端口
python main.py --serve-only --host 0.0.0.0 --port 8080
```

**启动 WebUI + 执行分析**：

```bash
# 方式1：使用 --webui
python main.py --webui

# 方式2：使用 --serve
python main.py --serve

# 结合定时任务
python main.py --serve --schedule
```

### 方式3：使用 uvicorn 直接启动

**开发模式（自动重载）**：

```bash
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

**生产模式**：

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 配置说明

### .env 配置

在 `.env` 文件中添加：

```bash
# ===================================
# WebUI 配置（可选）
# ===================================
# 是否默认启动 WebUI（true/false，默认 false）
WEBUI_ENABLED=false

# WebUI 监听地址
# - 127.0.0.1: 仅本机访问（默认，安全）
# - 0.0.0.0: 允许外部访问（Docker/远程部署需要）
WEBUI_HOST=127.0.0.1

# WebUI 监听端口（默认 8000）
WEBUI_PORT=8000
```

### 监听地址选择

| 地址 | 适用场景 | 安全性 | 说明 |
|------|---------|--------|------|
| `127.0.0.1` | 本地开发 | ✅ 高 | 只能本机访问，推荐 |
| `0.0.0.0` | Docker/远程 | ⚠️ 中 | 允许外部访问，需配置防火墙 |
| `192.168.x.x` | 局域网 | ⚠️ 中 | 仅局域网可访问 |

**安全建议**：
- 本地开发：使用 `127.0.0.1`
- Docker 部署：使用 `0.0.0.0` + 端口映射
- 生产环境：使用 `0.0.0.0` + Nginx 反向代理 + HTTPS

---

## Docker 部署

### docker-compose.yml 配置

**方式1：WebUI Only（仅API服务）**

```yaml
version: '3.8'

services:
  webui:
    image: stock-analysis:latest
    container_name: stock-analysis-webui
    command: python webui.py
    ports:
      - "8000:8000"  # 主机端口:容器端口
    environment:
      - WEBUI_HOST=0.0.0.0  # Docker 内必须使用 0.0.0.0
      - WEBUI_PORT=8000
      - TZ=Asia/Shanghai
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

**方式2：WebUI + 定时分析**

```yaml
version: '3.8'

services:
  analyzer:
    image: stock-analysis:latest
    container_name: stock-analysis-analyzer
    command: python main.py --serve --schedule
    ports:
      - "8000:8000"
    environment:
      - WEBUI_HOST=0.0.0.0
      - WEBUI_PORT=8000
      - SCHEDULE_ENABLED=true
      - SCHEDULE_TIME=18:00
      - TZ=Asia/Shanghai
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./reports:/app/reports
    restart: unless-stopped
```

**方式3：完整部署（WebUI + 盘后分析 + 日内分析）**

```yaml
version: '3.8'

services:
  # WebUI 服务
  webui:
    image: stock-analysis:latest
    container_name: stock-webui
    command: python main.py --serve-only
    ports:
      - "8000:8000"
    environment:
      - WEBUI_HOST=0.0.0.0
      - WEBUI_PORT=8000
      - TZ=Asia/Shanghai
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  # 盘后完整分析（18:00）
  daily-analyzer:
    image: stock-analysis:latest
    container_name: stock-daily-analyzer
    command: python main.py --schedule
    environment:
      - SCHEDULE_TIME=18:00
      - TZ=Asia/Shanghai
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./reports:/app/reports
    restart: unless-stopped

  # 日内实时分析（9:30, 13:00, 14:45）
  intraday-analyzer:
    image: stock-analysis:latest
    container_name: stock-intraday-analyzer
    command: python main.py --intraday-schedule
    environment:
      - INTRADAY_ENABLED=true
      - INTRADAY_TIME_POINTS=09:30,13:00,14:45
      - INTRADAY_MODE=lightweight
      - TZ=Asia/Shanghai
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

启动服务：

```bash
docker-compose up -d
```

查看日志：

```bash
docker-compose logs -f webui
```

---

## 访问 WebUI

### 本地访问

启动后，打开浏览器访问：

- **主页**: http://127.0.0.1:8000
- **API 文档**: http://127.0.0.1:8000/docs
- **健康检查**: http://127.0.0.1:8000/health

### Docker 访问

如果使用 Docker 部署：

- **主页**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

### 远程访问

如果部署在服务器上：

- **主页**: http://服务器IP:8000
- **API 文档**: http://服务器IP:8000/docs

⚠️ **安全警告**：远程访问建议配置 Nginx 反向代理和 HTTPS。

---

## API 端点

### 核心接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 主页 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API 文档 |
| `/api/v1/...` | * | 业务 API（具体查看 /docs） |

### 示例：健康检查

```bash
curl http://localhost:8000/health
```

**响应**：
```json
{
  "status": "healthy",
  "timestamp": "2025-02-15T10:30:00",
  "version": "2.0.0"
}
```

### 查看完整 API 文档

访问 http://localhost:8000/docs 查看交互式 API 文档（Swagger UI）。

---

## 常见问题

### Q1: 启动后无法访问？

**A**: 检查以下几点：

1. **端口是否被占用**：
```bash
# Linux/Mac
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

2. **防火墙是否放行**：
```bash
# 临时放行端口（Linux）
sudo ufw allow 8000

# 永久放行
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

3. **监听地址是否正确**：
   - 本地访问：使用 `127.0.0.1`
   - Docker/远程：使用 `0.0.0.0`

### Q2: Docker 容器内无法访问？

**A**: 确保使用 `0.0.0.0` 监听地址：

```yaml
environment:
  - WEBUI_HOST=0.0.0.0  # 不要使用 127.0.0.1
```

**原理**：
- `127.0.0.1`：只能容器内访问
- `0.0.0.0`：允许宿主机通过端口映射访问

### Q3: 如何修改端口？

**A**: 三种方式：

**方式1：环境变量**
```bash
WEBUI_PORT=8080 python webui.py
```

**方式2：.env 配置**
```bash
WEBUI_PORT=8080
```

**方式3：命令行参数**
```bash
python main.py --serve-only --port 8080
```

### Q4: 如何同时运行 WebUI 和日内分析？

**A**: 推荐使用 Docker Compose 部署多个容器（见上文配置示例）。

或者使用 `screen`/`tmux` 多终端：

```bash
# 终端1：WebUI
screen -S webui
python main.py --serve-only

# 终端2：日内分析
screen -S intraday
python main.py --intraday-schedule

# 终端3：盘后分析
screen -S daily
python main.py --schedule
```

### Q5: 生产环境如何部署？

**A**: 推荐配置：

**1. 使用 Nginx 反向代理**：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**2. 配置 HTTPS**：

```bash
# 使用 Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

**3. 使用 Supervisor 管理进程**：

```ini
[program:stock-analysis-webui]
command=python /path/to/webui.py
directory=/path/to/project
user=stock
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/stock-analysis/webui.log
```

**4. 配置防火墙**：

```bash
# 只允许特定 IP 访问
sudo ufw allow from YOUR_IP to any port 8000
```

---

## 性能优化

### 生产环境配置

**使用多进程部署**：

```bash
# 使用 Gunicorn + Uvicorn Workers
gunicorn server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

**资源限制**（Docker）：

```yaml
services:
  webui:
    # ... 其他配置 ...
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

---

## 监控与日志

### 查看日志

**本地部署**：
```bash
tail -f logs/api_server.log
```

**Docker 部署**：
```bash
docker logs -f stock-analysis-webui
```

### 健康检查

**设置定时健康检查**：

```bash
# crontab
*/5 * * * * curl -s http://localhost:8000/health || echo "WebUI 服务异常" | mail -s "Alert" admin@example.com
```

**Docker Compose 健康检查**：

```yaml
services:
  webui:
    # ... 其他配置 ...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## 总结

### 启动方式对比

| 方式 | 命令 | 适用场景 |
|------|------|----------|
| webui.py | `python webui.py` | 仅需 WebUI（推荐） |
| main.py --serve-only | `python main.py --serve-only` | 同上 |
| main.py --serve | `python main.py --serve` | WebUI + 分析任务 |
| Docker Compose | `docker-compose up -d` | 生产环境（推荐） |
| uvicorn | `uvicorn server:app` | 开发调试 |

### 推荐配置

**开发环境**：
```bash
python webui.py
# 或
python main.py --serve-only --host 127.0.0.1 --port 8000
```

**生产环境（单服务）**：
```bash
python main.py --serve --schedule
```

**生产环境（多服务，推荐）**：
```bash
docker-compose up -d
# 包含：WebUI + 盘后分析 + 日内分析
```

---

## 下一步

1. ✅ 启动 WebUI
2. 📖 访问 API 文档：http://localhost:8000/docs
3. 🤖 配置机器人（飞书、钉钉等）
4. 📊 查看实时分析状态
5. ⚙️ 自定义配置参数

更多信息请参考：
- [日内分析指南](INTRADAY_ANALYSIS.md)
- [项目 README](../README.md)
- API 文档：http://localhost:8000/docs
