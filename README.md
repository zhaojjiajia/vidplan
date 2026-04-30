# VidPlan AI

VidPlan AI 是一个视频方案规划工具,用于完成“选方向、填想法、AI 生成、编辑优化、沉淀资产、系列化复用、导出交付”的闭环。

当前实现包含:

- 用户注册、登录、JWT 鉴权。
- 单条视频方案生成、编辑、自动保存、AI 优化、复制、导出。
- 系列方案、人物/风格/世界观/栏目资产管理。
- 系列 AI 生成、基于系列生成单集、一致性检查。
- 单条方案 Markdown/PDF/Word 导出,系列方案 Markdown/Word 导出。
- OpenAI/Qwen 兼容模型配置页。

## 技术栈

- 后端: Python 3.11、Django 5、Django REST Framework、Simple JWT。
- 前端: Vue 3、Vite、TypeScript、Element Plus、Pinia、Vue Router。
- 数据库: 本地可用 SQLite,容器和部署推荐 PostgreSQL 15。
- 异步任务: Redis + Celery,本地默认同步降级。
- AI: OpenAI 兼容接口,当前支持 OpenAI 和 Qwen 配置。
- 长任务体验: AI 入口支持 SSE 状态流、轮询降级和刷新恢复。

## 快速启动

详细说明见 [docs/dev-setup.md](docs/dev-setup.md)。

本地后端:

```bash
cd backend
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

本地前端:

```bash
cd frontend
npm install
npm run dev
```

访问:

- 前端: `http://localhost:5173`
- 后端 API: `http://localhost:8000/api/v1/`

容器启动:

```bash
docker compose up --build
```

## 常用验证

```bash
cd backend
.venv/bin/python manage.py test --verbosity 1
```

```bash
cd frontend
npm run build
```

## 关键文档

- [V1 技术设计](docs/v1-design.md)
- [开发与部署说明](docs/dev-setup.md)
