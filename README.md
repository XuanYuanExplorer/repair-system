# 学生宿舍服务平台（Dorm Service）

基于 **FastAPI + Vue 3** 的学生宿舍全栈服务系统，覆盖**报修、缴费、寝室、值日、公告、消息、个人中心、反馈、帮助**九大业务域。
前后端同仓分离、单端口部署，移动端 H5 优先，严格遵循配套的《后端开发文档》《前端开发文档》《测试文档》与 UI 设计稿（黑白瑞士风格）。

> 默认免依赖开箱即跑：后端使用 SQLite（aiosqlite）+ 进程内缓存，**无需安装 MySQL / Redis 即可运行**；
> 通过环境变量一键切换到 MySQL + Redis + ARQ 生产配置。

---

## 1. 快速开始

### 1.1 环境要求

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | ≥ 3.11 | 后端（**必需**） |
| Node.js | ≥ 18（推荐 20+） | 仅二次开发前端时需要；发布包已内置 `frontend/dist`，直接运行不需要 |
| pnpm | ≥ 8 | 同上（`npm i -g pnpm`） |
| MySQL / Redis | 可选 | 不配置则使用 SQLite / 进程内缓存 |

### 1.2 一键启动（推荐）

发布包内 `frontend/dist` 已构建完成，**解压后无需 Node.js、无需 pnpm**，只要 Python 即可跑起完整网站：

```bash
# Linux / macOS
cd dorm-service
./start.sh                 # 自动建虚拟环境 → 装依赖 → 启动（默认 8000 端口）
PORT=9000 ./start.sh       # 换端口
```

```powershell
# Windows（推荐：双击 start.bat，或在 cmd 里执行）
cd dorm-service
start.bat                  # 默认 8000 端口
start.bat 9000             # 换端口
```

`start.bat` 会复用已装好的依赖；若检测不到，则自动创建 `.venv` 并安装，失败时自动切清华镜像重试。

> Windows 若提示「无法加载文件，因为在此系统上禁止运行脚本」，那是 PowerShell 的执行策略限制，
> 请改用 **cmd**（开始菜单搜索 cmd）运行 `start.bat`，或执行 `powershell -ExecutionPolicy Bypass -File start.bat`。

打开 **http://127.0.0.1:8000** 即可使用。首次启动自动建表 + 写入演示数据（`app/seed_data.py`），
SQLite 库落在 `backend/data/dorm.db`；删除该文件重启即可恢复到初始演示状态。

### 1.2.1 手动分步启动

```bash
# ① 后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 首次启动自动建表 + 写入演示数据（app/seed_data.py）

# ② 前端（仅在需要改前端时构建；发布包已内置 dist，可跳过）
cd frontend
pnpm install
pnpm build
```

### 1.2.2 手机 / 局域网访问

`start.sh` 与 `start.bat` 均监听 `0.0.0.0`，同一 WiFi 下手机可直接打开：

1. 查电脑内网 IP：Windows `ipconfig`（看「IPv4 地址」），macOS/Linux `ip addr` 或 `ifconfig | grep inet`
2. 手机浏览器访问 `http://192.168.x.x:8000`（换成上一步的 IP，端口与启动时一致）
3. 打不开先排查：电脑防火墙是否放行该端口（Windows 首次启动会弹「允许访问」→ 勾选**专用网络**）；手机与电脑是否同一网段

只在本机用，直接访问 `http://127.0.0.1:8000` 即可。

### 1.3 前后端分离开发模式

```bash
cd backend   && python -m uvicorn app.main:app --port 8000   # 终端 1
cd frontend  && pnpm dev                                      # 终端 2 → http://localhost:5173
```

Vite 已配置 `/api` 与 `/uploads` 代理到 8000 端口，前端改动热更新。

### 1.4 生产配置（MySQL + Redis）

```bash
cp backend/.env.example backend/.env   # 按需修改
```

```dotenv
DATABASE_URL=mysql+asyncmy://user:pass@127.0.0.1:3306/dorm_service
REDIS_URL=redis://127.0.0.1:6379/0     # 设置后缓存/限流/网关模拟自动切换
JWT_SECRET=请更换为至少 32 位的随机串
AUTO_INIT=false                        # 生产关闭自动建表，用 scripts/init_db.py
ENABLE_SCHEDULER=true                  # 定时任务（防掉单轮询 / 逾期计费 / 排班提醒）
```

### 1.5 演示账号（种子数据）

| 账号 | 密码 | 角色 | 用途 |
|---|---|---|---|
| `20223601` | `Abc123456` | 学生 林晓阳（3号楼412 · 床3） | 主演示账号 |
| `20223602` | `Abc123456` | 寝室长 王一诺（3号楼412 · 床1） | 公约 / 排班管理 |
| `20223701` | `Abc123456` | 学生 赵一鸣（5号楼201） | 跨寝室越权校验演示 |
| `20223702` | `Abc123456` | 学生 周予安（6号楼305） | 逾期账单 / 滞纳金演示 |
| `20229999` | `Abc123456` | 学生 未分配寝室 | 空态 / 未绑定宿舍演示 |
| `13800000000` | `Abc123456` | 维修工 张建国 | 接单侧数据 |
| `admin` | `Admin@123` | 宿管中心管理员 | 派单 / 公告 / 反馈回复 |

种子数据包含：26 个覆盖 6 种状态的工单、18 笔已缴 + 3 笔待缴账单（含逾期与滞纳金）、
4 条公告、5 条 FAQ、消息 / 值日 / 卫生检查 / 反馈等完整演示数据。

### 1.6 常用命令

```bash
# 后端测试（48 个用例：认证 / 报修 / 支付 / 越权与并发）
cd backend && python -m pytest -q

# 手动重置数据库
cd backend && rm -f data/dorm.db && python scripts/seed.py

# 前端类型检查 + 构建
cd frontend && pnpm typecheck && pnpm build
```

---

## 2. 网站介绍

### 2.1 功能总览（21 个页面）

| 模块 | 页面 | 亮点 |
|---|---|---|
| 认证 | 登录 / 注册认证 / 重置密码 | JWT 双令牌轮换、防枚举校验、5 次锁定、短信验证码（开发环境回显）、密码强度前后端同规则 |
| 首页 | 服务大厅 | 一次聚合请求（问候、待缴、工单、公告、CTA），60s 缓存 |
| 报修 | 提交 / 列表 / 详情 / 确认评价 / 维修档案 | 时段防超卖（条件 UPDATE）、幂等提交、乐观锁状态机、催单 5 分钟冷却、聊天增量轮询、返修轮次 |
| 缴费 | 缴费中心 / 账单详情 / 支付结果 / 记录票据 | 多选合并支付（整数分累加）、罚金不可合并、15 分钟支付时效、服务端主动查单防掉单、CSV 导出、PDF 电子票据 |
| 寝室 | 我的寝室 / 成员 | 设施故障一键带入报修、公约编辑（寝室长）、物品借还、入住/退宿/调宿申请 |
| 值日 | 值日与卫生 | 周视图轮换、今日高亮、卫生扣分与整改照片回传 |
| 内容 | 公告与公约 | 置顶卡、已读回执统计、过期过滤 |
| 消息 | 消息中心 | 按业务分组、单条/全部已读、按 biz_type 深链跳转、推送偏好开关失败回滚 |
| 其他 | 个人中心 / 编辑资料 / 意见反馈 / 帮助中心 | 认证字段只读（前后端双重校验）、设备管理、反馈满意度评价、FAQ 搜索 + 一键拨号 |

### 2.2 界面预览

UI 严格按《报修系统.html》设计稿实现：零圆角零阴影、1.5px 结构线、
衬线数字（金额/评分/单号）、唯一强调色 `#D93B3B`、内联 SVG 图标（24 个 symbol）。
布局为**网页化自适应**：无模拟手机顶栏，内容栏最大宽 640px（移动端全宽）、随文档流自然滚动，
列表滚动到底自动加载下一页（IntersectionObserver 分页），底部导航固定于视口底部。

| | |
|---|---|
| ![登录](docs/screenshots/01-login.png) | ![首页](docs/screenshots/04-home.png) |
| ![报修提交](docs/screenshots/05-repair-submit.png) | ![我的报修](docs/screenshots/06-repair-list.png) |
| ![工单跟踪](docs/screenshots/07-repair-detail.png) | ![缴费中心](docs/screenshots/10-payment-center.png) |
| ![账单详情](docs/screenshots/11-bill-detail.png) | ![支付结果](docs/screenshots/12-pay-result.png) |
| ![值日卫生](docs/screenshots/16-dorm-duty.png) | ![个人中心](docs/screenshots/19-profile.png) |

完整 18 张截图见 [`docs/screenshots/`](docs/screenshots/)。

### 2.3 架构与目录

```
dorm-service/
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # 应用装配：中间件 / 异常 / 路由 / SPA 托管
│   │   ├── config.py            # pydantic-settings 集中配置
│   │   ├── db.py                # async engine（SQLite/MySQL 双适配）
│   │   ├── core/                # response / errors / security / cache / tracing / ratelimit
│   │   ├── models/              # SQLAlchemy 2.0 ORM（33 张表）
│   │   ├── schemas/             # 请求模型（pydantic v2）
│   │   ├── routers/             # 11 个路由域
│   │   ├── services/            # 业务逻辑（与路由解耦，可独立测试）
│   │   ├── tasks/               # 事务性发件箱 + 进程内调度器
│   │   ├── seed_data.py         # 演示数据（对齐测试文档 2.2）
│   │   └── tests/               # pytest 48 用例
│   ├── scripts/                 # init_db.py / seed.py
│   └── data/                    # SQLite 与上传文件（运行时生成）
└── frontend/                    # Vue 3.5 + Vite 5 + Pinia
    └── src/
        ├── api/                 # axios 实例（401 单飞刷新）+ 11 个领域模块
        ├── stores/              # auth / badge / ui
        ├── router/              # 路由表 + 登录守卫 + 静默续期
        ├── composables/         # useAsyncData / usePolling / useCountdown / useUploader…
        ├── components/          # layout / base / data / form / feedback（19 个自研组件）
        ├── views/               # 21 个页面
        └── styles/              # 设计令牌 tokens.css + global.css
```

**分层原则**：`router（参数校验）→ service（业务/事务）→ model（ORM）`，
service 之间只允许向下依赖，跨域事件通过 `OutboxEvent` 异步投递（工单完成 → 材料费账单 / 消息 / 回执）。

### 2.4 安全设计

- **认证**：JWT HS256，access 2h + refresh 7d 轮换；refresh 复用检测即吊销全部；登出 access 进黑名单；
  bcrypt（sha256 预哈希规避 72 字节截断，rounds=12）；登录防枚举（不存在账号也执行哈希）。
- **授权**：所有接口显式角色依赖（`StudentUser / WorkerUser / AdminUser`），寝室数据按 `room_id` 隔离（跨寝 403）。
- **输入**：pydantic 严格 schema + 手机号/学号正则；上传文件 magic bytes 白名单 + 大小限制 + 随机文件名 + SHA256 去重。
- **支付**：金额一律服务端计算（前端不回传）；`Idempotency-Key` + 库内唯一键双重幂等；回调验签且只信服务端查单；
  账单置已付使用条件 UPDATE（rowcount 校验）防并发重复扣款。
- **限流与审计**：全局 API 限流（120 次/分，可配）、登录/短信/催单/消息多级冷却；`AuditLog` 全量留痕，响应头 `X-Trace-Id`。
- **隐私**：手机号/姓名出口统一脱敏；认证字段（学号/宿舍）前后端双重只读。

### 2.5 可用性与可迭代性

- 三态 UI 强制：所有异步区块必有 骨架屏 / 空态 / 错误重试，禁止白屏。
- 前后端契约以 OpenAPI 为唯一真源，`pnpm typecheck` 为 CI 卡口；types.ts 与后端 serializer 字段一一对应。
- 测试：`pytest 48 用例` 覆盖认证、报修状态机、并发超卖、支付幂等、越权访问；前端 `vue-tsc` 全量类型检查。
- 切换生产组件零代码改动：`DATABASE_URL` / `REDIS_URL` 环境变量即可。

---

## 3. 接口速查

- Swagger 文档：`http://127.0.0.1:8000/api/v1/docs`
- OpenAPI JSON：`http://127.0.0.1:8000/api/v1/openapi.json`
- 健康探针：`/api/v1/healthz`、`/api/v1/readyz`

统一响应包：

```json
{ "code": 0, "message": "ok", "data": { }, "trace_id": "c0a8…" }
```

主要端点：`/auth/*`（11 个）、`/repair/*`（15 个）、`/bills|/payment/*`（10 个）、
`/dorm/*`、`/duty/*`、`/notices/*`、`/messages/*`、`/profile|/help/*`、`/feedbacks/*`、`/files`、`/admin/*`。
错误码表见《01-后端开发文档.md》§错误码（1001 未登录 / 2005 密码错误 / 3001 状态冲突 / 4001 已支付 …）。

---

## 4. 常见问题

| 现象 | 处理 |
|---|---|
| 访问 `/` 出现 JSON 提示“前端尚未构建” | 先执行 `cd frontend && pnpm build` |
| 登录提示“账号已锁定” | 种子环境连续 5 次失败触发，15 分钟自动解锁，或重置数据库 |
| 短信验证码 | 开发模式直接在响应与 toast 中回显 `debug_code` |
| 支付一直“处理中” | 点击「刷新状态」即可（Mock 网关已标记成功，服务端主动查单兜底） |
| 首次启动很慢 | 首次建表 + 种子数据写入，属正常现象 |
| 端口占用 | 修改 uvicorn `--port` 后同步修改 `frontend/vite.config.ts` 代理目标 |

---

## 5. 交付清单

- [x] 后端：FastAPI + SQLAlchemy 2.0 async，33 表，11 路由域 70+ 接口，48 测试用例全部通过
- [x] 前端：Vue 3.5 + Vite 5 + Pinia，21 页面 + 19 自研组件，`vue-tsc` 类型检查通过
- [x] 单端口部署：后端托管前端产物，SPA fallback
- [x] 种子数据与测试文档账号矩阵一致
- [x] 界面还原设计稿（黑白瑞士风 / 移动端 H5）
- [x] 本 README（网站介绍 + 运行说明）

### 5.1 发布包说明

| 路径 | 说明 |
|---|---|
| `start.sh` | 一键启动（建虚拟环境 → 装依赖 → 起服务），Windows 见 §1.2 |
| `backend/` | 全部后端源码；`data/dorm.db` 首次启动自动生成 |
| `frontend/src/` | 全部前端源码（`node_modules` 未打包，`pnpm install` 后即可开发） |
| `frontend/dist/` | **已构建好的前端产物**，运行时由后端直接托管，无需 Node |
| `docs/screenshots/` | 18 张真机尺寸界面截图 |
| `README.md` | 本文档 |

> 分包体积约 4.5 MB：已剔除 `node_modules`（70 MB）、运行时数据库与用户上传文件。
> 重新打包：`zip -r dorm-service.zip dorm-service -x '*/node_modules/*' -x '*.db'`
