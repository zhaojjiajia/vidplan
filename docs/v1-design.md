# VidPlan AI · V1 技术设计

本文基于产品规格 `/Users/dxy/Desktop/v1.md` 编写,目标是在动手编码前把架构、数据模型、API、前端结构、开发节奏对齐清楚。

> 更新日期: 2026-04-29。本文同时作为后续开发执行文档使用,后文的“当前实现基线”和“落地契约”优先级高于早期草案描述。

---

## 1. 设计目标

- **闭环优先**: 用最小代价跑通"选方向 → 填想法 → AI 生成 → 编辑 → AI 优化 → 保存 → 复用"。
- **资产分离**: 视频方案 (易变) 与人物/风格/世界观/栏目资产 (稳定) 分表,系列方案引用资产。
- **AI 提供商可替换**: 后端封装统一接口,模型可在 OpenAI / Claude / Gemini / 国产模型间切换,Prompt 模板与代码解耦。
- **逐步加重**: 单条方案 P0 → 系列方案 P1 → 剪辑建议 / 导出 P1-P2 → 文生视频对接 P3+。

---

## 2. 技术栈

| 层 | 选型 | 备注 |
|---|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Element Plus + Pinia + Vue Router 4 | TS 提早引入,数据结构复杂 |
| 后端 | Python 3.11 + Django 5 + Django REST Framework | DRF ViewSet + Router |
| 数据库 | PostgreSQL 15 | JSONB 字段存储分镜/方案正文 |
| 缓存/队列 | Redis | Celery 异步任务 broker/result backend |
| 鉴权 | `djangorestframework-simplejwt` | JWT access + refresh |
| AI SDK | `openai`, `anthropic`, `google-genai` | 统一封装在 `apps/ai/providers/` |
| 导出 | `markdown` + `weasyprint` (PDF) + `python-docx` | 后端生成 |
| 部署 | Docker Compose (V1 单机) | nginx + gunicorn + postgres + redis |

### 2.1 当前实现基线

| 模块 | 当前状态 | 说明 |
|---|---|---|
| 阶段 0 脚手架 | 已完成 | Django/DRF、Vue/Vite、JWT、受保护路由已跑通 |
| 阶段 1 单条方案 MVP | 已完成 | 向导、编辑器、列表、生成、优化、自动保存可用 |
| 阶段 2 系列 + 资产 | 基本完成 | 后端模型/CRUD、前端基础 CRUD、AI 生成系列、单集生成、一致性检查已接通；剩余体验收尾与更完整测试 |
| 阶段 3 导出 | 基本完成 | 单条方案 Markdown/PDF/Docx 已接通；系列 Markdown/Word 已接通；macOS 本地 PDF 依赖先不处理 |
| 阶段 4 体验增强 | 基本完成 | AITask 模型、查询 API、AI 接口任务记录、Celery/Redis 异步入口、前端 SSE/轮询恢复已完成；真实流式 token 输出后续再做 |
| 用户自带 AI Key | 已完成 | OpenAI/Qwen 兼容配置页已可用 |

当前本地开发可使用 SQLite (`backend/.env` 中 `DATABASE_URL=sqlite:///db.sqlite3`),正式/容器环境按设计使用 PostgreSQL。所有涉及 JSON 查询、索引和正式部署的能力以 PostgreSQL 为准。

---

## 3. 仓库结构

```
vidplan-ai/
├── backend/
│   ├── manage.py
│   ├── vidplan/                  # Django project (settings/urls/wsgi)
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── accounts/             # User + JWT
│   │   ├── plans/                # VideoPlan + SeriesPlan
│   │   ├── assets/               # Character/Style/Worldview/Column
│   │   ├── ai/                   # provider 抽象 + prompt 模板
│   │   │   ├── providers/
│   │   │   ├── prompts/
│   │   │   └── services.py
│   │   ├── exports/              # markdown/pdf/docx
│   │   └── core/                 # 公共 base model / 工具
│   ├── requirements.txt
│   ├── .env.example
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── api/                  # axios + 各资源 client
│   │   ├── components/           # 通用组件 (PlanCard, AssetEditor 等)
│   │   ├── composables/          # useAI / useExport / useAuth
│   │   ├── layouts/              # 默认布局 + 编辑器布局
│   │   ├── router/
│   │   ├── stores/               # Pinia
│   │   ├── views/                # 页面级组件
│   │   ├── types/                # TS 类型 (与 backend 模型对齐)
│   │   ├── App.vue
│   │   └── main.ts
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── docker-compose.yml
├── docs/
│   ├── v1-design.md              ← 本文
│   └── v1.md                     # 建议从 /Users/dxy/Desktop/v1.md 拷贝或软链进来
└── README.md
```

> **决策**: 单仓 monorepo,前后端平级目录,不引入 pnpm workspaces / turbo —— V1 体量不需要。

---

## 4. 后端设计

### 4.1 App 划分

| App | 职责 |
|---|---|
| `accounts` | 用户、JWT、登录注册 |
| `plans` | 单条方案、系列方案 |
| `assets` | 4 类长期资产 |
| `ai` | AI 调用、Prompt 模板、provider 抽象 |
| `exports` | 方案导出 (md/pdf/docx) |
| `core` | `TimestampedModel`、`UUIDModel`、分页、异常处理 |

### 4.2 数据模型

**约定**:
- 所有表 UUID 主键 (继承 `core.UUIDModel`)。
- 所有表带 `created_at` / `updated_at` (继承 `core.TimestampedModel`)。
- V1 用硬删除,不做 soft delete。
- 长文本 / 结构化内容用 PostgreSQL `JSONField`,而非裸 TEXT,方便前端渲染分镜表格。

#### 4.2.1 `accounts.User`

直接继承 `AbstractUser`,扩展:

```python
class User(AbstractUser):
    id = UUIDField(primary_key=True)
    nickname = CharField(max_length=64)
    avatar_url = URLField(blank=True)
```

#### 4.2.2 `plans.VideoPlan` (单条视频方案)

```python
class VideoPlan(UUIDModel, TimestampedModel):
    user = FK(User)
    series = FK(SeriesPlan, null=True, blank=True, related_name="episodes")

    title = CharField(max_length=200)
    direction = CharField(max_length=64)            # vlog / tutorial / ai_drama ...
    category = CharField(choices=["real", "ai_generated"])
    is_ai_generated_video = BooleanField()

    target_platform = CharField(max_length=32)       # douyin/xhs/kuaishou/bilibili
    target_audience = CharField(max_length=200)
    duration_seconds = IntegerField()
    style = CharField(max_length=64, blank=True)

    summary = TextField(blank=True)
    content = JSONField(default=dict)                # 结构化方案正文 (定位/结构/字幕/音乐/发布文案/封面)
    storyboard = JSONField(default=list)             # 分镜列表,每项 {idx, duration, visual, line, editing, ai_prompt}
    editing_advice = JSONField(default=dict)         # 剪辑/剪映建议
    ai_prompts = JSONField(default=dict)             # 文生/图生提示词集合

    status = CharField(choices=["draft","optimizing","confirmed","completed"], default="draft")
```

#### 4.2.3 `plans.SeriesPlan` (系列方案)

```python
class SeriesPlan(UUIDModel, TimestampedModel):
    user = FK(User)
    title = CharField(max_length=200)
    direction = CharField(max_length=64)
    summary = TextField(blank=True)

    target_platform = CharField(max_length=32)
    target_audience = CharField(max_length=200)
    update_frequency = CharField(max_length=64)
    episode_duration_seconds = IntegerField()
    planned_episodes = IntegerField(default=0)

    positioning = JSONField(default=dict)            # 定位/卖点/风格基调
    episode_template = JSONField(default=dict)       # 单集结构模板
    visual_style = JSONField(default=dict)
    title_style = JSONField(default=dict)
    initial_topics = JSONField(default=list)         # 前 N 集选题

    status = CharField(choices=["draft","ongoing","paused","completed"], default="draft")

    # 资产引用 (M2M,因为同一个角色可能复用到不同系列)
    characters = M2M("assets.CharacterAsset", blank=True)
    styles = M2M("assets.StyleAsset", blank=True)
    worldviews = M2M("assets.WorldviewAsset", blank=True)
    columns = M2M("assets.ColumnAsset", blank=True)
```

#### 4.2.4 `assets.*` (4 类长期资产)

每类资产同一套基类:

```python
class AssetBase(UUIDModel, TimestampedModel):
    user = FK(User)
    name = CharField(max_length=120)
    payload = JSONField(default=dict)        # 详细字段全放进去
    fixed_traits = JSONField(default=list)   # 禁止修改的特征 (用于一致性检查)

    class Meta:
        abstract = True

class CharacterAsset(AssetBase): ...   # 人物
class StyleAsset(AssetBase): ...       # 画面/剪辑/音乐风格
class WorldviewAsset(AssetBase): ...   # 世界观
class ColumnAsset(AssetBase): ...      # 栏目结构
```

`payload` 字段按 v1.md §8.3 列出的字段填充,放在 JSON 里避免每加一个字段就改表。

#### 4.2.5 关系图

```
User 1─┬─* VideoPlan ──? SeriesPlan
       └─* SeriesPlan ─┬─* CharacterAsset (M2M)
                       ├─* StyleAsset (M2M)
                       ├─* WorldviewAsset (M2M)
                       └─* ColumnAsset (M2M)
```

### 4.3 REST API

> 路径前缀 `/api/v1/`,均需 JWT (除注册/登录)。

| Method | Path | 说明 |
|---|---|---|
| POST | `/auth/register/` | 注册 |
| POST | `/auth/login/` | 返回 access + refresh |
| POST | `/auth/refresh/` | 刷新 token |
| GET | `/auth/me/` | 当前用户 |
| GET POST | `/plans/` | 列表 / 创建空白草稿 |
| GET PATCH DELETE | `/plans/{id}/` | 详情 / 编辑 / 删除 |
| POST | `/plans/generate/` | **AI 生成初版** (传方向 + 想法,返回完整方案) |
| POST | `/plans/{id}/optimize/` | **AI 优化** (整体/标题/开头/分镜/剪辑/提示词,scope 参数选) |
| POST | `/plans/{id}/check-consistency/` | 系列一致性检查 (人物/风格是否漂移) |
| POST | `/plans/{id}/duplicate/` | 基于此方案再创作 |
| GET | `/plans/{id}/export/?format=md\|pdf\|docx` | 导出 |
| GET POST | `/series/` | 系列列表 / 创建 |
| GET PATCH DELETE | `/series/{id}/` | |
| POST | `/series/generate/` | AI 生成整体系列方案 |
| POST | `/series/{id}/episodes/` | 基于系列创建单集 (会带入资产) |
| GET | `/series/{id}/episodes/` | 该系列下所有单集 |
| GET POST | `/assets/characters/` | 人物 CRUD,其余 styles/worldviews/columns 同形 |

#### 4.3.1 API 约定

- 所有 DRF ViewSet 路径保留尾斜杠,前端请求必须使用尾斜杠。
- 列表统一使用 DRF 分页格式: `{ count, next, previous, results }`。
- 资源权限统一由 queryset `.filter(user=request.user)` 控制,查不到当前用户资源时返回 404,不暴露是否属于其他用户。
- 错误响应优先使用 `{ "detail": "..." }`; 表单校验错误沿用 DRF 字段错误格式。
- 导出接口统一使用 `format` 查询参数,例如 `/plans/{id}/export/?format=md`。
- DRF 已关闭 `URL_FORMAT_OVERRIDE`,避免 `?format=pdf/docx` 被框架当作响应渲染器格式。

#### 4.3.2 阶段 2 新增 API 契约

`POST /series/generate/`

请求:

```json
{
  "direction": "ai_short_drama",
  "idea": "校园悬疑短剧,每集 60 秒",
  "target_platform": "抖音",
  "target_audience": "18-25 岁年轻用户",
  "update_frequency": "日更",
  "episode_duration_seconds": 60,
  "planned_episodes": 20,
  "style": "悬疑、快节奏、强反转",
  "auto_create_assets": true
}
```

响应: `201 SeriesPlan`,并在 `auto_create_assets=true` 时同时创建人物/风格/世界观/栏目资产,返回的系列已关联这些资产。

`POST /series/{id}/episodes/`

请求:

```json
{
  "topic": "第 1 集: 转校生收到匿名纸条",
  "episode_goal": "建立主角和悬念",
  "extra_requirements": "结尾必须反转,留下下一集钩子"
}
```

响应: `201 VideoPlan`,生成的单集必须设置 `series={id}`。

`POST /series/{id}/check-consistency/`

请求:

```json
{
  "plan_id": "可选,只检查某个单集",
  "scope": "all"
}
```

响应:

```json
{
  "score": 86,
  "issues": [
    {
      "level": "warning",
      "asset_type": "characters",
      "asset_id": "uuid",
      "field": "appearance",
      "message": "第 3 集中主角发色与固定特征不一致",
      "suggestion": "改回黑色短发"
    }
  ]
}
```

#### 4.3.3 AI 端点统一响应格式

```json
{
  "task_id": "uuid",         // 同步返回时也会记录任务 ID
  "result": { ... },          // 同步返回的方案/优化结果
  "model": "gpt-4o",
  "usage": { "input_tokens": 1234, "output_tokens": 567 }
}
```

当前默认仍同步调用并在响应中附带 `task_id`。配置 `AI_TASK_EXECUTION=celery` 或请求带 `?async=1` 时返回任务对象,由 Celery worker 后台执行。前端优先用 SSE 任务状态流等待结果,连接失败时自动轮询降级。

### 4.3.4 JSON 数据契约

JSONField 允许扩展字段,但 V1 必须保证以下基础结构稳定。

`VideoPlan.content`

```json
{
  "positioning": {
    "core_hook": "一句话钩子",
    "selling_point": "内容卖点",
    "audience_pain": "用户痛点"
  },
  "structure": [
    { "name": "开头", "goal": "3 秒抓人", "duration": 3 },
    { "name": "主体", "goal": "展开信息", "duration": 24 },
    { "name": "结尾", "goal": "互动/转化", "duration": 3 }
  ],
  "copywriting": {
    "title_options": ["标题 1", "标题 2"],
    "opening_line": "开场白",
    "caption": "发布文案",
    "hashtags": ["#标签"]
  },
  "cover": {
    "text": "封面字",
    "visual": "封面画面"
  }
}
```

`VideoPlan.storyboard`

```json
[
  {
    "idx": 1,
    "duration": 3,
    "visual": "画面/场景",
    "line": "台词/旁白",
    "editing": "剪辑方式",
    "camera": "运镜",
    "ai_prompt": "文生/图生视频提示词"
  }
]
```

`VideoPlan.editing_advice`

```json
{
  "rhythm": "节奏建议",
  "music": "音乐建议",
  "subtitle": "字幕样式",
  "transition": "转场建议",
  "tools": ["剪映功能点"]
}
```

`VideoPlan.ai_prompts`

```json
{
  "text_to_video": ["提示词"],
  "image_to_video": ["提示词"],
  "image_generation": ["提示词"],
  "negative_prompt": "负向提示词"
}
```

`SeriesPlan.positioning`

```json
{
  "core_concept": "系列核心概念",
  "target_user": "目标用户",
  "differentiation": "差异化",
  "promise": "持续观看承诺"
}
```

`SeriesPlan.episode_template`

```json
{
  "sections": [
    { "name": "开头钩子", "duration": 5, "goal": "制造悬念" },
    { "name": "剧情推进", "duration": 45, "goal": "完成本集事件" },
    { "name": "结尾钩子", "duration": 10, "goal": "引导下一集" }
  ],
  "must_have": ["固定口头禅", "固定反转"]
}
```

`Asset.payload`

```json
{
  "description": "资产描述",
  "traits": {},
  "usage_notes": "使用注意",
  "examples": []
}
```

### 4.4 AI 模块设计

```
apps/ai/
├── providers/
│   ├── base.py           # class AIProvider(abstract): chat(messages, **kw) -> Response
│   ├── openai_provider.py
│   ├── claude_provider.py
│   └── gemini_provider.py
├── prompts/
│   ├── direction.py      # §13.1 方向判断
│   ├── single_plan.py    # §13.2 单条方案生成
│   ├── series_plan.py    # §13.3 系列方案生成
│   ├── storyboard.py     # §13.4 分镜优化
│   ├── editing.py        # §13.5 剪映建议
│   └── consistency.py    # 一致性检查
├── services.py           # 高层 service: generate_single_plan(user_input) -> dict
└── registry.py           # provider 工厂,settings.AI_DEFAULT_PROVIDER 切换
```

**Prompt 模板形式**: 用 Python f-string 模板而非外部 YAML,保留类型检查,方便测试。

**输出契约**: 所有 prompt 强制要求模型返回 JSON,后端用 pydantic 校验,失败时重试 1 次再降级到原始字符串保存。

**模型默认**: 当前实现默认 OpenAI 兼容接口 (`gpt-4o`),用户可在 AI 设置页切换到 Qwen 兼容接口。Claude/Gemini provider 保留为后续扩展,不作为当前 V1 必须项。

#### 4.4.1 AI 输出校验策略

- 每个 AI service 都必须定义 Pydantic schema: `SinglePlanOutput`、`SeriesPlanOutput`、`EpisodeOutput`、`ConsistencyReportOutput`。
- Prompt 要求模型只返回 JSON,不得包裹 Markdown 代码块。
- JSON parse 失败时执行一次修复请求: 把原始输出交给同一 provider,要求转换成合法 JSON。
- Pydantic 校验失败时返回 502,错误信息写入后端日志,前端提示“AI 输出格式异常,请重试”。
- 不允许把 `_raw` 字符串直接写入正式业务字段；降级保存只能写入 `content.raw_ai_output`,并将方案状态保持 `draft`。

### 4.5 鉴权

`djangorestframework-simplejwt`:
- access token 1h,refresh token 14 天
- 默认所有 ViewSet 加 `permissions.IsAuthenticated`
- 资源级权限: 自定义 `IsOwner`,所有 queryset 默认 `.filter(user=request.user)`

### 4.6 导出

`apps/exports/services.py` 把方案 dict 渲染成:
- **Markdown**: 套用 v1.md §14.1 / §14.2 模板,字符串拼接。
- **PDF**: markdown → HTML → WeasyPrint。
- **Docx**: `python-docx` 直接构造 (表格友好)。

#### 4.6.1 导出接口契约

| format | Content-Type | 文件名 | 状态 |
|---|---|---|---|
| `md` / `markdown` | `text/markdown; charset=utf-8` | `{title}.md` | 当前已实现 |
| `pdf` | `application/pdf` | `{title}.pdf` | 阶段 3 实现 |
| `docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `{title}.docx` | 阶段 3 实现 |

不支持的格式返回 `400 {"detail": "暂不支持的导出格式: xxx"}`。

PDF 样式要求: A4、中文字体优先、表格可换行、分镜表格不截断。Docx 要求: 基本信息用列表,分镜脚本用表格,JSON 结构用二级标题展开。

---

## 5. 前端设计

### 5.1 路由

| Path | View | 鉴权 |
|---|---|---|
| `/` | `Home.vue` | 公开 |
| `/login` | `Login.vue` | 公开 |
| `/register` | `Register.vue` | 公开 |
| `/app/plan/new` | `PlanWizard.vue` (方向 → 类型 → 表单 → 生成) | 需登录 |
| `/app/plan/:id` | `PlanEditor.vue` | 需登录 |
| `/app/series/new` | `SeriesEditor.vue` | 需登录 |
| `/app/series/:id` | `SeriesEditor.vue`；阶段 2 后续扩展为 `SeriesDetail.vue` | 需登录 |
| `/app/me/plans` | `MyPlans.vue` | 需登录 |
| `/app/me/series` | `MySeries.vue` | 需登录 |
| `/app/me/assets/characters` | `AssetLibrary.vue` | 需登录 |
| `/app/me/assets/styles` | `AssetLibrary.vue` | 需登录 |
| `/app/me/assets/worldviews` | `AssetLibrary.vue` | 需登录 |
| `/app/me/assets/columns` | `AssetLibrary.vue` | 需登录 |
| `/app/settings/ai` | `AISettings.vue` | 需登录 |

### 5.2 Pinia Stores

- `useAuthStore` —— user / token / login / logout
- `usePlanStore` —— plans 列表 + 当前编辑的 plan + dirty flag
- `useSeriesStore` —— series 列表 + 当前 series + 单集列表
- `useAssetStore` —— 4 类资产 (单 store 管 4 类)
- `useUiStore` —— 全局 loading / message

当前实现中,`plans` 已有 Pinia store；`series/assets` 暂由页面直接调用 API。后续如果页面间复用增加,再补 `useSeriesStore` 和 `useAssetStore`,避免过早抽象。

### 5.3 关键组件

| 组件 | 说明 |
|---|---|
| `DirectionPicker` | 一级二级方向选择器,首页与 wizard 共用 |
| `PlanCard` / `SeriesCard` | 个人中心卡片 |
| `StoryboardEditor` | 分镜表格编辑 (拖拽排序、增删行、AI 重生成单行) |
| `PlanEditor` | 整体方案编辑器,左侧分模块 (定位/结构/分镜/剪辑/发布),右侧 AI 操作面板 |
| `AIActionPanel` | "AI 帮我完善"、"只优化标题"等按钮组 |
| `AssetSelector` | 创建单集时选择/新建系列资产 |
| `ConsistencyReport` | 一致性检查结果弹窗 |
| `ExportDialog` | 导出格式选择 |

### 5.4 前后端类型同步

`frontend/src/types/api.ts` 手写,与 Django serializers 对齐。V2 引入 `drf-spectacular` 自动生成 OpenAPI + `openapi-typescript-codegen` 时再切换。

---

## 6. 核心流程

### 6.1 单条方案完整链路

```
PlanWizard.vue
  └ DirectionPicker → 选择方向
  └ TypeChoice → 单条 (本流程) / 系列
  └ SinglePlanForm → 填表 (主题/目标/平台/时长/...)
  └ POST /plans/generate/  ← AI 同步生成
  └ 跳转 /app/plan/:id (status=draft)
PlanEditor.vue
  └ 用户编辑 (本地 dirty flag)
  └ PATCH /plans/:id/ (debounce 自动保存)
  └ AIActionPanel → POST /plans/:id/optimize/ body={scope: full|title|hook|storyboard|editing|ai_prompt}
  └ 用户确认 → PATCH status=confirmed
```

### 6.2 系列 → 单集

```
SeriesEditor → 手动创建系列方案 + 关联资产
SeriesGenerate → AI 创建系列方案 + 自动产出资产 (人物/风格/世界观/栏目)
SeriesDetail → 点击 "创建本集"
  └ POST /series/:id/episodes/ body={topic, episode_goal, ...}
  └ 后端读取系列 + 资产作为上下文,调 AI 生成单集
  └ 返回 VideoPlan,前端跳 /app/plan/:id
```

阶段 2 分两步交付:

1. 基础 CRUD: 系列方案、人物资产、风格资产、世界观资产、栏目资产可手动增删改查。
2. AI 串联: 系列 AI 生成、基于系列生成单集、一致性检查。

### 6.3 编辑-优化循环

每次 AI 优化后,前端把旧版本压入本地 undo 栈 (V1 仅前端 session 保留,V2 上服务端版本表)。

---

## 7. 分阶段开发计划

后续开发按“先补契约缺口,再做新功能”的顺序推进。每个阶段都必须同时完成后端、前端、测试和验收清单。

### 7.1 阶段 0/1 已完成基线

已完成能力:

- 用户注册、登录、JWT 刷新、`/api/v1/auth/me/`。
- 单条方案 CRUD、AI 生成、AI 优化、复制方案、Markdown 导出。
- 前端首页、登录注册、个人方案列表、方案向导、方案编辑器、AI 设置页。
- 用户自带 AI Key: OpenAI/Qwen 兼容接口,支持保存和连通性测试。

阶段 1 收尾修正:

- 导出接口参数统一为 `format`,同时兼容旧参数 `type` 一个版本。
- `/plans/{id}/export/` 404 时需要区分“方案不存在/无权限”和“路由不存在”,前端提示要具体。
- `optimize` 成功后不应长期保持 `optimizing`,应在写入结果后改回 `draft` 或 `confirmed` 由用户确认。
- AI JSON 解析失败不能只写 `_raw`,需要按 §4.4.1 增加修复和校验。

### 7.2 阶段 2A: 系列与资产基础 CRUD

当前后端和前端基础 CRUD 已有,阶段 2A 的目标是把体验补完整。

后端:

- `SeriesPlanViewSet` 增加 `prefetch_related` 优化资产和单集数量查询。
- serializers 明确可写 M2M 字段: `characters`、`styles`、`worldviews`、`columns`。
- 资产列表支持 `search` 和 `ordering=-updated_at`。
- 为 Series/Asset 增加最小测试: 只能访问自己的数据、创建时自动绑定 user、M2M 可写。

前端:

- `SeriesEditor` 支持编辑基本信息、定位、单集模板、视觉风格、标题风格、初始选题。
- `SeriesEditor` 支持关联 4 类资产,可从弹窗快速新建资产。
- `MySeries` 展示状态、计划集数、已生成集数、更新时间。
- `AssetLibrary` 按资产类型切换字段模板,不要只给用户一个裸 JSON 编辑框。

验收:

- 用户可手动创建一个系列,关联人物/风格/世界观/栏目资产,保存后再次打开数据完整。
- 用户可创建、编辑、删除 4 类资产,不同用户之间数据不可见。

### 7.3 阶段 2B: 系列 AI 生成与单集生成

后端:

- 新增 `apps/ai/prompts/series_plan.py`、`episode.py`、`consistency.py`。
- 新增 AI service: `generate_series_plan`、`generate_episode_plan`、`check_series_consistency`。
- `POST /api/v1/series/generate/`: 根据方向和想法生成系列,可选自动创建资产。
- `POST /api/v1/series/{id}/episodes/`: 读取系列和资产上下文生成单集 `VideoPlan`。
- `POST /api/v1/series/{id}/check-consistency/`: 对全部或指定单集做一致性检查。
- 增加 Pydantic 输出校验,不合格返回 502。

前端:

- `SeriesGenerate` 页面或 `SeriesEditor` 的 AI 生成模式。
- `SeriesDetail` 页面: 基本信息、资产、单集列表、生成单集入口、一致性检查入口。
- `ConsistencyReport` 弹窗展示分数、问题级别、建议修正。

验收:

- 输入一个系列想法后,系统能生成系列方案并自动生成至少人物、风格、栏目资产。
- 在系列详情中输入单集主题后,能生成一条已绑定 `series` 的 `VideoPlan`。
- 一致性检查能指出至少人物或风格字段的冲突,并给出可执行建议。

### 7.4 阶段 3: 导出增强

后端:

- `apps/exports/services.py` 统一导出入口: `render_plan(plan, format)`。
- Markdown 保持现有能力,补充系列导出模板。
- PDF 使用 WeasyPrint: 增加中文字体、A4 页面、分镜表格换行。
- Docx 使用 `python-docx`: 基本信息、分镜表格、剪辑建议、AI 提示词分块输出。
- 导出文件名使用安全标题,并处理空标题。

前端:

- `ExportDialog` 支持 `md`、`pdf`、`docx`。
- 下载失败时读取后端 `detail` 并展示。
- 系列详情页支持导出系列总案和单集清单。

验收:

- 同一个方案可以导出 Markdown、PDF、Docx,文件能正常打开,中文不乱码。
- PDF 分镜表格不被截断,Docx 分镜为可编辑表格。

### 7.5 阶段 4: SSE 流式生成与异步任务

后端:

- 已定义 `AITask` 模型记录状态、进度、错误、结果,并提供 `/api/v1/ai-tasks/` 查询接口。
- 当前默认同步执行:单条生成、方案优化、系列生成、生成单集、一致性检查都会创建任务并在响应中返回 `task_id`。
- 已加入 Redis + Celery 配置和 worker task。设置 `AI_TASK_EXECUTION=celery` 或请求带 `?async=1` 时,长任务接口返回 `202` 和任务对象,由 Celery worker 执行。
- SSE 端点: `/api/v1/ai-tasks/{task_id}/events/`,推送 `queued/running/succeeded/failed/canceled` 状态事件。
- Provider 层真实 token 流式输出暂未接入,当前 SSE 推送任务状态,前端保留轮询降级。

前端:

- AI 生成按钮进入任务态,优先用 SSE 展示进度,连接失败时自动轮询降级。
- 用户刷新页面后,同一浏览器可通过 localStorage 恢复未完成任务并继续等待。
- AI 设置页支持 provider/model/base_url 切换,并显示当前使用来源: 用户配置或环境默认。

验收:

- 生成长方案时页面不会卡死,刷新后能继续看到任务状态。
- Provider 切换后,下一次生成明确使用新配置。

---

## 8. V1 验收清单

### 8.1 当前已完成

- [x] 用户可注册/登录。
- [x] 用户可在首页进入方案规划页选择方向。
- [x] 用户填写想法后,AI 同步生成完整单条方案。
- [x] 用户可在编辑器修改方案并自动保存。
- [x] 用户可点击“AI 完善”优化方案。
- [x] 用户保存后,个人中心可见方案卡片。
- [x] 用户可重新打开方案继续编辑。
- [x] 用户可基于已有方案复制再创作。
- [x] 用户可配置自己的 OpenAI/Qwen 兼容 API Key。
- [x] 用户可手动维护系列和 4 类资产的基础 CRUD。
- [x] 用户可通过 AI 生成系列方案。
- [x] 用户可基于系列生成单集方案。
- [x] 用户可对系列做一致性检查。
- [x] AI 输出已有 Pydantic 校验和一次修复重试。
- [x] 系列编辑页支持快速新建并关联资产。
- [x] 单条方案可导出 Markdown、PDF、Docx。
- [x] 系列方案可导出 Markdown、Word。
- [x] 核心 API 后端测试已覆盖账号、方案、系列/资产、导出、AI 设置、AI JSON 修复分支。
- [x] 系列编辑页已有只读概览,集中展示定位、模板、资产、选题和单集。
- [x] 阶段 4 基础任务模型 `AITask` 与 `/api/v1/ai-tasks/` 查询接口已完成。
- [x] 阶段 4 AI 入口已接入同步任务记录,响应包含 `task_id`,成功/失败状态可追踪。
- [x] 阶段 4 Celery/Redis 配置和异步入队入口已完成,本地可继续同步降级。
- [x] 阶段 4 前端已兼容 `AITask` 响应,单条生成、优化、系列生成、单集生成、一致性检查支持轮询和刷新恢复。
- [x] 阶段 4 SSE 任务状态端点已完成,前端优先使用 SSE,失败时自动降级轮询。
- [x] 前端关键路径类型检查和构建通过。

### 8.2 V1 还必须补齐

- [x] V1 手动验收。

### 8.3 暂不进入 V1

- 多人协作。
- 公开模板市场。
- 细粒度版本历史。
- 文生视频平台真实提交任务。
- 付费、额度、账单。

---

## 9. 当前实现差异与修正项

| 编号 | 差异 | 影响 | 处理 |
|---|---|---|---|
| D1 | 设计要求导出参数为 `format`,当前后端读取 `type` | 前端用 `format=md` 时行为不明确,排查困难 | 已处理:后端优先读 `format`,兼容 `type` |
| D2 | AI JSON 解析失败会返回 `_raw` | 正式字段可能缺失,编辑器显示不稳定 | 已处理:增加 Pydantic schema + 修复重试 |
| D3 | `SeriesPlanViewSet` 只有基础 CRUD | 系列 AI 流程还没闭环 | 已处理:系列生成、单集生成、一致性检查已接通 |
| D4 | 资产编辑偏通用 JSON | 非技术用户编辑成本高 | 已处理:前端按资产类型提供结构化表单,系列页支持快速新建并关联资产 |
| D5 | PDF/Docx 依赖未完成 | 导出只支持 Markdown | 已处理:单条方案支持 Markdown/PDF/Docx；macOS 本地 PDF 需安装 WeasyPrint 系统依赖 |
| D6 | README 缺失 | 新环境启动成本高 | 已处理:补充根 README 和 docs/dev-setup.md |
| D7 | Series/Plan 关联字段未限制到当前用户资源 | 用户知道 UUID 时可能绑定他人系列或资产 | 已处理:serializer queryset 限制到当前用户,并补测试 |
| D8 | 系列无法导出总案 | 系列定位、资产、单集清单无法离线交付 | 已处理:系列支持 Markdown/Word 导出 |
| D9 | 长 AI 调用只能同步等待 | 页面等待时间长,刷新后无法恢复任务状态 | 阶段 4 已基本解决:AITask、查询 API、Celery 异步入口、前端 SSE/轮询恢复已落地 |

---

## 10. 本地开发与环境变量

### 10.1 后端环境

`backend/.env` 是当前本地运行配置文件,仍然有用。它不应提交真实密钥,提交仓库的是 `backend/.env.example`。

必须项:

```env
DJANGO_SETTINGS_MODULE=vidplan.settings.dev
DJANGO_SECRET_KEY=change-me-in-prod
DJANGO_DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
CORS_ALLOWED_ORIGINS=http://localhost:5173
AI_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=
```

说明:

- 本地快速开发可以用 SQLite。
- 正式和 Docker 环境使用 PostgreSQL,因为 JSONB、索引和并发能力更稳定。
- 用户在页面配置了自己的 API Key 时,优先使用用户配置；未配置时才使用环境变量。

### 10.2 推荐本地命令

后端:

```bash
cd backend
python manage.py migrate
python manage.py runserver
python manage.py test
```

前端:

```bash
cd frontend
npm install
npm run dev
npm run type-check
npm run build
```

---

## 11. 测试与质量门禁

后端最低测试:

- accounts: 注册、登录、刷新、me。
- plans: CRUD、权限隔离、generate、optimize、duplicate、export。
- series/assets: CRUD、权限隔离、M2M 关联。
- ai: provider 配置解析、JSON 解析失败、Pydantic 校验失败。
- exports: md/pdf/docx 的 Content-Type、文件名、空字段容错。

当前已实现 29 个后端测试,覆盖上述核心路径、跨用户隔离风险、阶段 4 任务查询、异步入队和 SSE 状态流基础能力。后续新增功能时按同等粒度补测试。

前端最低检查:

- `npm run type-check` 必须通过。
- `npm run build` 必须通过。
- 关键页面手动验收: 登录、创建方案、编辑保存、导出、AI 设置、资产 CRUD、系列 CRUD。

不要在 V1 为了测试引入过重的 E2E 套件。等核心流程稳定后再补 Playwright。

---

## 12. 关键决策

| 决策 | 选择 | 理由 |
|---|---|---|
| TS / JS | TS | 数据结构复杂,类型化降低前后端漂移 |
| 自动保存 / 手动保存 | 自动保存 + 明确保存状态 | 编辑器型应用更符合用户预期 |
| storyboard 存 JSON 还是单独表 | JSONField | V1 不做镜头级跨方案查询,JSON 够用 |
| 资产与系列关系 | M2M | 角色、风格、栏目都可能跨系列复用 |
| 同步 / 流式 / 异步 | 默认同步,已具备 Celery 异步入口和前端 SSE/轮询恢复 | 先保证闭环,再优化长任务体验 |
| Prompt 形态 | Python f-string | 当前实现简单,易测试；后续模板复杂再抽文件 |
| 默认 AI provider | OpenAI 兼容接口 | 同时支持 OpenAI 和 Qwen 兼容模式 |
| 数据库 | 本地 SQLite,正式 PostgreSQL 15 | 本地启动快,正式环境需要 JSONB 和稳定并发 |
| UI 语言 | 仅中文 | 当前目标用户明确 |
| 登录方式 | 用户名 + 密码 | V1 不做邮箱验证、短信和第三方登录 |

---

## 13. 下一步开发顺序

1. 做上服务环境联调:后端、worker、Redis、前端任务恢复一起跑通。
2. 根据部署环境补 Celery worker 进程守护、日志和失败告警。
3. 如需更细体验,再接 Provider token 级流式输出。
