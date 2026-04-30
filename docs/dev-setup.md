# 开发与部署说明

本文说明 VidPlan AI 的本地开发、容器启动、环境变量、验证命令和部署注意事项。

## 目录结构

```text
vidplan-ai/
├── backend/              # Django 后端
├── frontend/             # Vue/Vite 前端
├── docs/                 # 项目文档
├── docker-compose.yml    # 本地容器编排
└── README.md
```

## 后端本地开发

推荐使用 Python 3.11。

```bash
cd backend
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

后端默认地址:

```text
http://localhost:8000
```

API 前缀:

```text
http://localhost:8000/api/v1/
```

### 本地数据库

本地快速开发可以用 SQLite:

```env
DATABASE_URL=sqlite:///db.sqlite3
```

容器和正式部署建议使用 PostgreSQL:

```env
DATABASE_URL=postgres://vidplan:vidplan@localhost:5432/vidplan
```

## 前端本地开发

推荐使用 Node.js 20。

```bash
cd frontend
npm install
npm run dev
```

前端默认地址:

```text
http://localhost:5173
```

Vite 会把 `/api` 代理到后端 `http://localhost:8000`。

前端默认不强制异步请求,会自动兼容后端同步结果和 `202 AITask` 结果。如果需要前端主动用异步入口,可设置:

```env
VITE_AI_TASK_MODE=async
```

## Docker 启动

项目根目录执行:

```bash
docker compose up --build
```

容器会启动:

- `postgres`: PostgreSQL 15。
- `redis`: Celery broker/result backend。
- `backend`: Django 开发服务器。
- `worker`: Celery worker。
- `frontend`: Vite 开发服务器。

访问:

```text
http://localhost:5173
```

## 环境变量

后端环境文件:

```text
backend/.env
```

可从示例复制:

```bash
cp backend/.env.example backend/.env
```

核心变量:

```env
DJANGO_SETTINGS_MODULE=vidplan.settings.dev
DJANGO_SECRET_KEY=change-me-in-prod
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
CORS_ALLOWED_ORIGINS=http://localhost:5173
AI_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=
REDIS_URL=redis://localhost:6379/0
AI_TASK_EXECUTION=sync
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

说明:

- 用户在前端“AI 设置”页保存了 API Key 时,优先使用用户配置。
- 用户未配置 API Key 时,后端才使用环境变量中的 `OPENAI_API_KEY`。
- `AI_TASK_EXECUTION=sync` 时 AI 接口同步执行并记录任务状态。
- `AI_TASK_EXECUTION=celery` 或请求 URL 带 `?async=1` 时,AI 接口返回 `202` 和任务对象,实际生成由 Celery worker 执行。
- 前端会优先读取 `/api/v1/ai-tasks/{id}/events/` SSE 状态流,连接失败时轮询 `/api/v1/ai-tasks/{id}/`,并用 localStorage 恢复当前浏览器未完成的任务。
- 不要把真实 `.env` 提交到仓库。

## AI 设置

前端入口:

```text
/app/settings/ai
```

当前支持:

- OpenAI 兼容接口。
- Qwen DashScope OpenAI 兼容接口。
- 自定义模型名和 Base URL。
- 连接测试。

## 导出能力

单条方案支持:

- Markdown: `format=md`
- PDF: `format=pdf`
- Word: `format=docx`

系列方案支持:

- Markdown: `format=md`
- Word: `format=docx`

### PDF 依赖

PDF 使用 WeasyPrint。Docker 镜像里会安装 Linux 依赖和中文字体。macOS 本地如果没有安装 `pango/gobject/cairo` 等系统库,PDF 导出会返回明确错误,不影响 Markdown 和 Word 导出。

如果需要在 macOS 本地启用 PDF:

```bash
brew install pango cairo gdk-pixbuf libffi
```

正式服务器如果不使用 Docker,需要在系统层安装:

```bash
apt-get update
apt-get install -y --no-install-recommends \
  libcairo2 \
  libpango-1.0-0 \
  libpangocairo-1.0-0 \
  libpangoft2-1.0-0 \
  libgdk-pixbuf-2.0-0 \
  libglib2.0-0 \
  fonts-noto-cjk
```

## 常用验证

后端:

```bash
cd backend
.venv/bin/python manage.py check
.venv/bin/python manage.py test --verbosity 1
```

前端:

```bash
cd frontend
npm run type-check
npm run build
```

当前前端构建可能出现 Vite 主 chunk 超过 500k 的提示,这是体积优化提醒,不代表构建失败。

## 部署检查项

上线前至少确认:

- `DJANGO_SECRET_KEY` 已替换为正式密钥。
- `DJANGO_DEBUG=False`。
- `DJANGO_ALLOWED_HOSTS` 配置了真实域名。
- `CORS_ALLOWED_ORIGINS` 配置了真实前端地址。
- 数据库使用 PostgreSQL。
- 真实 API Key 不写入代码和仓库。
- Docker 镜像或服务器系统包含 PDF 依赖和中文字体。
- 如果经过 Nginx 等反向代理,SSE 路径需要关闭响应缓冲,避免任务状态延迟推送。
- 后端测试和前端构建通过。

## 当前后续工作

- 做上服务环境联调:后端、worker、Redis、前端任务恢复一起跑通。
- 根据服务器部署方式确认 Celery worker 进程守护和日志采集。
