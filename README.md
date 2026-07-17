# 天玑300量化研究系统

这是对大学时期“天玑300智能低吸交易系统”Demo 的第一阶段重构。旧版 Tkinter、AI 分析及交易实验代码仍原样保留在项目根目录；新系统位于 `backend/` 与 `frontend/`。

当前版本只提供行情研究、数据展示和策略信号。**不包含、不导入、也不会调用任何实盘下单逻辑。** 页面及接口输出仅供学习研究，不构成投资建议。

## 已实现

- FastAPI REST API 与 WebSocket 行情推送
- 统一 `MarketDataProvider` 接口：`get_quote`、`get_history`、`get_stock_list`、`get_trade_calendar`
- 默认可复现的 `MockProvider`，以及延迟加载的 `AkShareProvider`、`TushareProvider`
- 超时、指数退避重试、内存 TTL 缓存和统一错误响应
- 本地 JSON 自选股存储，服务层可在后续替换为 PostgreSQL
- 历史 K 线、20 周期布林线和低吸观察信号
- 响应式 React 研究看板，断开后端时自动保留 Mock 演示
- Token 仅由后端环境变量读取，前端永不接触数据源密钥

## 目录

```text
backend/
  app/api/          # REST 与 WebSocket 路由
  app/providers/    # 行情数据源适配器
  app/services/     # 缓存、指标、自选股和行情编排
  tests/            # 基础 API 测试
frontend/           # React / vinext 响应式网站
Trader2.py          # 旧版入口，仅保留，不被新系统加载
```

## 本地启动

推荐 Python 3.11+ 与 Node.js 22.13+。

### 1. 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item ..\.env.example .env
uvicorn app.main:app --reload --port 8000
```

默认数据源是 Mock，无需联网和 Token。接口文档位于 `http://localhost:8000/api/docs`。

### 2. 前端

另开终端：

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

打开 `http://localhost:3000`。

## 切换数据源

在 `backend/.env` 或启动进程环境中设置：

```dotenv
MARKET_DATA_PROVIDER=akshare
```

Tushare 需要仅保存在本机的 Token：

```dotenv
MARKET_DATA_PROVIDER=tushare
TUSHARE_TOKEN=your_local_token
```

iFinD 使用容器可用的 HTTP API。将从 iFinD 后台获取的 refresh token 只写入后端环境变量：

```dotenv
MARKET_DATA_PROVIDER=ifind
IFIND_REFRESH_TOKEN=your_local_refresh_token
MARKET_DATA_FALLBACK_PROVIDER=mock
```

后端会在内存中换取短期 access token，绝不会把 refresh token 或 access token 传给前端。若 iFinD 暂时不可用，响应会明确标为 `MockProvider`。

首次切换到 AkShare 或 Tushare 前安装可选行情依赖：

```powershell
pip install -r requirements-marketdata.txt
```

不要使用 `NEXT_PUBLIC_` 前缀保存任何 Token；该前缀的值会进入浏览器包。AkShare/Tushare/iFinD 均为延迟导入，默认 Mock 测试不会发出外部请求。

## API

- `GET /api/health`
- `GET /api/stocks/{code}/quote`
- `GET /api/stocks/{code}/history?start=YYYY-MM-DD&end=YYYY-MM-DD&period=daily`
- `GET /api/stocks?query=茅台&limit=50`
- `GET /api/trade-calendar?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `GET /api/watchlist`
- `POST /api/watchlist`，JSON：`{"code":"600519","name":"贵州茅台"}`
- `DELETE /api/watchlist/{code}`
- `WS /ws/quotes`

## 验证

```powershell
cd backend
pytest

cd ..\frontend
npm run build
```

## 下一阶段建议

引入 PostgreSQL 仓储接口与迁移、补充 Tushare 交易日历同步、增加回测任务与策略参数版本、接入 QMT/xtquant 只读行情适配器。实盘执行应作为独立、需要二次授权和严格风控的新边界设计，而不是迁移旧版自动交易代码。

## 公网部署

根目录的 `render.yaml` 定义了一个默认使用 Mock 行情的 FastAPI Web Service。Render 部署成功后，将网站构建变量 `NEXT_PUBLIC_API_BASE_URL` 设置为服务的 HTTPS 地址即可连接 REST 与 WebSocket。部署配置明确关闭实盘交易，且不包含任何 Token。
