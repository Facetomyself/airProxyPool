# airProxyPool 代理池


用于“代理池”场景：把不同来源、不同格式的节点统一成一个稳定的隧道出口（HTTP/SOCKS）。适合爬虫、批量注册、自动化任务等需要大量/稳定出站代理的场景。

1) 通过 subscription_collector（原 aggregator 模块）自动扫描与聚合可用节点
2) 使用 glider 将 SS / VMess 节点统一转换为隧道代理出口（HTTP/SOCKS）
3) FastAPI 负责管理面：采集、评分、轮换策略与统计

- 普通用户：使用“白嫖机场”订阅作为代理池，开箱即用。
- 有追求用户：使用自建订阅或付费机场作为代理池，更干净、更可控。

## 功能特点

- 自动收集与定时更新
- 可用性检测与故障转移
- 支持 SS / VMess
- 统一的隧道访问接口（HTTP/SOCKS）
- 支持自定义订阅（机场）→ glider 节点转换（单次或定时轮询）

## 目录
- [架构概览](#架构概览)
- [快速开始（Docker Compose）](#快速开始docker-compose)
- [隧道代理使用](#隧道代理使用)
- [API 管理接口](#api-管理接口)
- [定时任务与健康评分](#定时任务与健康评分)
- [环境变量清单](#环境变量清单)
- [使用“白嫖机场”订阅作为代理池](#使用白嫖机场订阅作为代理池)
- [使用自建/付费订阅作为代理池](#使用自建付费订阅作为代理池)
- [目录结构](#目录结构)
- [设计原则](#设计原则)
- [常见问题（FAQ）](#常见问题faq)

## 架构概览

- glider（隧道代理）：将 SS/VMess 等节点统一为稳定的 HTTP/SOCKS 出口
- API（FastAPI）：管理面（采集、评分、轮换策略、统计）
- Worker（Celery）：执行采集与健康检查任务
- Beat（Celery Beat）：定时调度任务
- Redis：Celery broker & 计数存储

端口约定：
- 隧道代理（glider）：HTTP/SOCKS → 127.0.0.1:10707、10710
- API：管理接口 → 127.0.0.1:18000

配置流：Worker 拉取/解析 → 写入 glider.conf（共享卷）→ glider 热重载生效

## 快速开始（Docker Compose）

```bash
cp .env.example .env  # 可按需调整变量
docker-compose up -d --build

# 验证
curl http://127.0.0.1:18000/healthz
curl "http://127.0.0.1:18000/api/proxies?min_score=20"

# 使用隧道代理（HTTP）
http_proxy=http://127.0.0.1:10707 curl http://httpbin.org/ip
```

环境变量（关键）：
- 在 `.env` 中配置（`./.env.example` 提供参考默认）：
  - FETCH_INTERVAL（拉取间隔秒，默认 3600）
  - HEALTHCHECK_INTERVAL（健康检查间隔秒，默认 1800）
  - PROXYPOOL_DB（SQLite 路径，默认 /app/data/data.db）
  - API_HOST_PORT（API 暴露端口，默认 18000）
  - GLIDER_HTTP_PORT、GLIDER_ALT_PORT（隧道端口，默认 10707、10710）

## 环境变量清单

- API
  - `API_HOST_PORT` = 18000 — API 对外暴露端口
  - `APP_HOST` = 0.0.0.0 — API 容器内绑定地址
  - `APP_PORT` = 8000 — API 容器内监听端口
  - `WORKERS` = 2 — Uvicorn 进程数
  - `LOG_LEVEL` = info — API 日志级别

- Celery/Redis
  - `CELERY_BROKER_URL` = redis://redis:6379/0 — Celery Broker（Redis）
  - `CELERY_RESULT_BACKEND` = redis://redis:6379/1 — Celery 结果存储
  - `REDIS_URL` = redis://redis:6379/0 — 通用 Redis 连接（轮换计数等）

- 调度与健康检查
  - `FETCH_INTERVAL` = 3600 — 定时采集间隔（秒）
  - `HEALTHCHECK_INTERVAL` = 1800 — 定时健康检查间隔（秒）
  - `HEALTHCHECK_WORKERS` = 10 — 健康检查并发

- 存储
  - `PROXYPOOL_DB` = /app/data/data.db — SQLite DB 路径（容器内）

- glider（隧道代理）
  - `GLIDER_HTTP_PORT` = 10707 — glider 对外端口 1（HTTP/SOCKS）
  - `GLIDER_ALT_PORT` = 10710 — glider 对外端口 2（HTTP/SOCKS）
  - `GLIDER_BIN` = /usr/local/bin/glider — 仅 worker 容器使用（临时 glider 健康探测）
  - 可选 wrapper 变量：
    - `GLIDER_CONFIG` = /config/glider.conf — glider 配置文件（glider 服务容器内）
    - `RELOAD_INTERVAL` = 30 — glider 热重载检测间隔（秒）

---

## 使用“白嫖机场”订阅作为代理池

此方式通过容器内的 Worker 自动聚合免费节点，无需本地安装依赖或子模块初始化。

- 启动后，Worker 会按 `FETCH_INTERVAL` 周期采集 → 解析为 forward= → 写入 glider.conf（共享卷）→ glider 热重载生效。
- 立即采集（可选）：
```bash
docker compose exec worker python -c "from features.proxy_pool.infrastructure.collector_runner import run_collect_and_update_glider; run_collect_and_update_glider()"
```
- 默认隧道端口：127.0.0.1:10707（与 10710）


---

## 使用自建/付费订阅作为代理池

此方式不依赖 subscription_collector。可选：在项目根创建 `subscriptions.txt`（每行一个订阅 URL），使用工具脚本
`features/proxy_pool/infrastructure/subscription_scheduler.py` 运行或集成到你的自动化：
- 定时拉取 → 解析为 forward= → 写入 glider.conf（共享卷）→ glider 热重载生效
- 隧道端口：127.0.0.1:10707（与 10710）




## 目录结构

```
.
├─ app.py                      # FastAPI 入口（管理面）
├─ main.sh                     # 单一入口（api/worker/beat）
├─ docker-compose.yml          # 容器编排（api/worker/beat/redis/glider）
├─ Dockerfile                  # 应用镜像（API/Worker/Beat）
├─ Dockerfile.glider           # glider 官方镜像 wrapper（热重载）
├─ features/
│  └─ proxy_pool/
│     ├─ domain/               # 模型
│     ├─ application/          # 用例/服务（采集、轮换）
│     ├─ infrastructure/       # DB、仓储、解析器、任务、健康检查
│     └─ interface/            # API 路由
├─ scripts/
│  └─ glider_entry.sh          # glider 热重载启动脚本
├─ features/subscription_collector/
│     ├─ subscribe/            # 聚合脚本与采集逻辑
│     ├─ data/                 # 聚合输出（clash.yaml 等）
│     └─ requirements.txt      # 采集所需依赖
├─ glider/                     # 本地运行辅助（可选，容器模式下使用卷）
├─ tests/                      # 测试
└─ docs/                       # 文档/图片
```

## 设计原则

- 职责分离：glider 专注传输与协议转换，FastAPI 专注管理；Worker 专注任务执行
- 演进友好：评分/轮换策略可替换；glider 可切换为其他实现
- 可观测：日志、评分、统计可追踪；故障具备可诊断性

## 常见问题（FAQ）

- 构建镜像很慢或拉取依赖超时怎么办？
  - 优先使用稳定的网络环境；必要时可以在 Dockerfile 的 pip 安装步骤添加国内源（例如阿里/清华镜像）。
  - 也可以在企业私有仓库缓存依赖（推荐生产场景）。

- glider 热重载多久生效？如何调整？
  - 默认 30 秒内检测到 /config/glider.conf 变更并重启 glider。
  - 修改 `.env` 中 `RELOAD_INTERVAL`，然后 `docker compose up -d glider` 使之生效。

- 为什么 requests 不能直接用 vmess/ss？
  - requests 仅支持 HTTP/HTTPS（配合 PySocks 支持 SOCKS），不理解 vmess/ss。需通过 glider 转换后使用 glider 暴露的隧道端口。

- 如何限制 glider 对外暴露？
  - 在 `.env` 中将端口映射改为仅监听本机，例如：`GLIDER_HTTP_PORT=127.0.0.1:10707`（或在 docker-compose.yml 中使用 `127.0.0.1:10707:10707`）。
  - 建议结合防火墙或仅在内网环境使用。

- API 无法访问 18000？
  - 检查端口是否占用，修改 `.env` 的 `API_HOST_PORT`；或查看 `docker compose logs api` 日志是否安装依赖失败。

- 数据如何持久化？
  - SQLite 文件默认在容器内 `/app/data/data.db`，通过命名卷 `data:/app/data` 持久化。需要主机目录时可修改 docker-compose.yml 将卷映射到宿主路径。


## 隧道代理使用

- requests（HTTP 代理）：
```python
import requests
proxies = {"http": "http://127.0.0.1:10707", "https": "http://127.0.0.1:10707"}
print(requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10).text)
```

- requests（SOCKS5，需安装）：
```bash
pip install "requests[socks]"
```
```python
import requests
proxies = {"http": "socks5h://127.0.0.1:10707", "https": "socks5h://127.0.0.1:10707"}
print(requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10).text)
```

## API 管理接口

- GET `/healthz` 健康检查
- GET `/api/proxies?min_score=20` 列表（含评分与延迟）
- GET `/api/proxy/rotate?token=abc&rotate_every=5&min_score=20` 管理面“固定次数轮换”选择一个上游
- POST `/api/proxies/fetch` 立即采集并更新 glider.conf

说明：实际传输的连接轮询由 glider 的 `strategy=rr` 执行；上面轮换接口用于“控制面”的按次策略与审计。

## 定时任务与健康评分

- Beat 定时触发：
  - `fetch_proxies`：默认 3600 秒；调用 features/subscription_collector 聚合 → glider.conf → DB
  - `health_check_all`：默认 1800 秒；逐节点启动临时 glider 探测，计算评分
- 评分公式（简化）：成功率 ×（1 - 延迟惩罚），范围 [0,100]
