# 📁 TOT ML Enterprise - 项目结构说明

## 整体结构

```
tot-ml-enterprise/
├── 📦 tot/                      # 原有 TOT 算法核心
│   ├── agent.py                 # AI Agent 实现
│   ├── journal.py               # 实验记录
│   ├── interpreter.py           # 代码执行器
│   ├── backend/                 # LLM 后端接口
│   └── utils/                   # 工具函数
│
├── 🚀 backend/                   # FastAPI 后端服务
│   ├── api/                     # API 路由
│   │   ├── __init__.py         
│   │   └── experiments.py       # 实验管理端点
│   │
│   ├── core/                    # 核心配置
│   │   ├── __init__.py
│   │   └── config.py            # 应用配置
│   │
│   ├── database/                # 数据库层
│   │   ├── __init__.py
│   │   └── base.py              # 数据库连接和会话
│   │
│   ├── models/                  # SQLAlchemy 模型
│   │   └── experiment.py        # 实验和节点模型
│   │
│   ├── schemas/                 # Pydantic 模式
│   │   ├── __init__.py
│   │   └── experiment.py        # 请求/响应模式
│   │
│   ├── services/                # 业务逻辑层
│   │   └── experiment_service.py # 实验服务
│   │
│   ├── main.py                  # FastAPI 应用入口
│   └── requirements.txt         # Python 依赖
│
├── 🎨 frontend/                  # React 前端应用
│   ├── src/
│   │   ├── components/          # 可复用组件
│   │   │   └── ui/             # 基础 UI 组件
│   │   │       ├── Button.tsx
│   │   │       └── Card.tsx
│   │   │
│   │   ├── pages/              # 页面组件
│   │   │   ├── Dashboard.tsx    # 仪表盘页面
│   │   │   ├── NewExperiment.tsx # 创建实验页面
│   │   │   └── ExperimentDetail.tsx # 实验详情页面
│   │   │
│   │   ├── services/           # API 客户端
│   │   │   ├── api.ts          # REST API 调用
│   │   │   └── websocket.ts    # WebSocket 客户端
│   │   │
│   │   ├── types/              # TypeScript 类型定义
│   │   │   └── index.ts
│   │   │
│   │   ├── utils/              # 工具函数
│   │   │   └── cn.ts           # 样式合并工具
│   │   │
│   │   ├── App.tsx             # 应用主组件
│   │   ├── main.tsx            # 入口文件
│   │   └── index.css           # 全局样式
│   │
│   ├── package.json            # Node 依赖配置
│   ├── vite.config.ts          # Vite 构建配置
│   ├── tsconfig.json           # TypeScript 配置
│   ├── tailwind.config.js      # Tailwind CSS 配置
│   ├── Dockerfile              # 前端 Docker 镜像
│   └── nginx.conf              # Nginx 配置
│
├── 🐳 部署配置
│   ├── docker-compose.yml       # Docker Compose 编排
│   ├── Dockerfile.backend       # 后端 Docker 镜像
│   └── .env.example            # 环境变量模板
│
├── 📜 脚本
│   ├── scripts/
│   │   ├── setup.sh            # 自动化设置脚本
│   │   └── start.sh            # 启动脚本
│   └── Makefile.new            # Make 命令集合
│
├── 📚 文档
│   ├── README.md               # README
│   ├── QUICK_START.md          # 快速启动指南
│   ├── DEPLOYMENT.md           # 部署指南
│   └── PROJECT_STRUCTURE.md    # 本文档
│
└── 📊 数据目录（运行时创建）
    ├── data/                   # 数据库文件
    ├── logs/                   # 日志文件
    ├── uploads/                # 上传的文件
    └── workspaces/             # 实验工作空间
```

## 核心模块详解

### 1. Backend（后端）

#### API 层 (`backend/api/`)
- **职责**: 处理 HTTP 请求，定义 RESTful 端点
- **主要文件**:
  - `experiments.py`: 实验 CRUD 操作、文件上传、WebSocket 连接

#### Core 层 (`backend/core/`)
- **职责**: 应用配置和全局设置
- **主要文件**:
  - `config.py`: 环境变量、API 密钥、数据库配置

#### Database 层 (`backend/database/`)
- **职责**: 数据库连接和会话管理
- **主要文件**:
  - `base.py`: AsyncSession、依赖注入、数据库初始化

#### Models 层 (`backend/models/`)
- **职责**: SQLAlchemy ORM 模型定义
- **主要文件**:
  - `experiment.py`: Experiment 和 ExperimentNode 表结构

#### Schemas 层 (`backend/schemas/`)
- **职责**: Pydantic 数据验证和序列化
- **主要文件**:
  - `experiment.py`: 请求/响应数据结构、类型验证

#### Services 层 (`backend/services/`)
- **职责**: 业务逻辑实现
- **主要文件**:
  - `experiment_service.py`: 实验管理、TOT 集成、异步任务

### 2. Frontend（前端）

#### Components (`frontend/src/components/`)
- **职责**: 可复用的 UI 组件
- **ui/**: 基础组件（Button, Card, Dialog 等）

#### Pages (`frontend/src/pages/`)
- **职责**: 页面级组件，对应路由
- **Dashboard**: 实验列表和概览
- **NewExperiment**: 创建新实验的表单
- **ExperimentDetail**: 实验详情、代码、指标、日志

#### Services (`frontend/src/services/`)
- **职责**: 外部服务交互
- **api.ts**: REST API 调用封装
- **websocket.ts**: WebSocket 连接管理

#### Types (`frontend/src/types/`)
- **职责**: TypeScript 类型定义
- 确保类型安全，提供智能提示

### 3. TOT Core（算法核心）

保留原有的 TOT 算法实现：
- **Agent**: 树搜索策略
- **Journal**: 实验节点管理
- **Interpreter**: 代码执行
- **Backend**: LLM 接口适配器

## 数据流

### 创建实验流程

```
用户 → Frontend → Backend API → Service → Database → TOT Core
                                                        ↓
用户 ← Frontend ← WebSocket ← Service ← TOT Core (执行)
```

### 详细步骤

1. **用户操作**: 在 Dashboard 点击 "New Experiment"
2. **Frontend**: NewExperiment 页面收集表单数据
3. **API 调用**: `experimentAPI.create()` 发送 POST 请求
4. **Backend 接收**: `POST /api/v1/experiments/` 端点
5. **Service 处理**: ExperimentService 创建数据库记录
6. **Database 存储**: SQLAlchemy 保存到数据库
7. **运行实验**: 后台任务调用 TOT Core
8. **实时更新**: WebSocket 推送进度到前端
9. **完成**: 更新数据库，通知前端

## 技术栈映射

### Backend
```
FastAPI          → Web 框架
SQLAlchemy       → ORM
Pydantic         → 数据验证
Uvicorn          → ASGI 服务器
WebSocket        → 实时通信
AsyncIO          → 异步处理
```

### Frontend
```
React            → UI 框架
TypeScript       → 类型安全
Vite             → 构建工具
TanStack Query   → 数据获取
Tailwind CSS     → 样式框架
Recharts         → 图表库
```

### DevOps
```
Docker           → 容器化
Docker Compose   → 服务编排
Nginx            → 反向代理
Make             → 任务自动化
```

## 配置文件说明

### Backend 配置

- **`.env`**: 环境变量（API 密钥、数据库 URL）
- **`requirements.txt`**: Python 依赖

### Frontend 配置

- **`package.json`**: Node 依赖和脚本
- **`vite.config.ts`**: Vite 构建配置
- **`tsconfig.json`**: TypeScript 编译选项
- **`tailwind.config.js`**: Tailwind CSS 定制

### Docker 配置

- **`docker-compose.yml`**: 服务编排
- **`Dockerfile.backend`**: 后端镜像构建
- **`frontend/Dockerfile`**: 前端镜像构建
- **`frontend/nginx.conf`**: Nginx 配置

## 开发工作流

### 添加新功能

1. **定义数据模型** (`backend/models/`)
2. **创建 Pydantic Schema** (`backend/schemas/`)
3. **实现业务逻辑** (`backend/services/`)
4. **添加 API 端点** (`backend/api/`)
5. **创建前端类型** (`frontend/src/types/`)
6. **实现 API 客户端** (`frontend/src/services/`)
7. **构建 UI 组件** (`frontend/src/components/`)
8. **创建页面** (`frontend/src/pages/`)

### 调试技巧

#### Backend
```bash
# 查看日志
docker-compose logs -f backend

# 进入容器
docker-compose exec backend bash

# 测试 API
curl http://localhost:8000/health
```

#### Frontend
```bash
# 浏览器开发工具
# Network 标签: 查看 API 调用
# Console 标签: 查看错误信息

# 查看构建输出
npm run build
```

## 扩展指南

### 添加新的 LLM 模型

1. 在 `tot/backend/` 添加新的后端适配器
2. 更新 `backend/core/config.py` 添加配置
3. 在前端 `NewExperiment.tsx` 添加选项

### 添加用户认证

1. 创建 `backend/models/user.py`
2. 实现 `backend/services/auth_service.py`
3. 添加 `backend/api/auth.py` 端点
4. 在前端添加登录页面和 token 管理

### 切换到 PostgreSQL

1. 修改 `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:pass@host/db
   ```
2. 安装驱动:
   ```bash
   pip install asyncpg
   ```
3. 重新初始化数据库

## 性能优化建议

### Backend
- 使用连接池
- 添加缓存层（Redis）
- 实现任务队列（Celery）
- 数据库索引优化

### Frontend
- 代码分割
- 图片懒加载
- 虚拟滚动
- 服务端渲染（SSR）

## 安全检查清单

- [ ] 环境变量不提交到版本控制
- [ ] 使用 HTTPS
- [ ] 实现 CSRF 保护
- [ ] API 速率限制
- [ ] 输入验证
- [ ] SQL 注入防护（ORM）
- [ ] XSS 防护
- [ ] 依赖安全更新

---

**提示**: 这只是一个起点！随着项目发展，你可以根据需要调整和扩展这个结构。
