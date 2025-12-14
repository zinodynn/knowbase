# KnowBase - 知识库管理系统

基于 RAG (Retrieval-Augmented Generation) 的企业级知识库管理系统。

## 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy 2.0
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7+
- **向量数据库**: Qdrant
- **对象存储**: MinIO
- **任务队列**: Celery (Phase 2)

## 快速开始

### 1. 环境准备

确保已安装：
- Python 3.11+
- Docker & Docker Compose

### 2. 启动基础服务

```bash
# 启动 PostgreSQL, Redis, MinIO, Qdrant
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 3. 配置后端

> 如果你在 `pip install -r requirements.txt` 时看到类似 “dependency conflicts / resolver does not currently take into account all the packages that are installed” 的提示，通常是因为你在一个已经装了很多其它包（例如 Spyder、pyppeteer、旧版 aiohttp/pyOpenSSL 等）的 Python 环境里安装。
> 
> **推荐做法**：使用全新的虚拟环境（`.venv`）安装本项目依赖，这样这些冲突不会影响本项目。

```bash
cd backend

# 创建虚拟环境,用venv
python -m venv .venv
# 使用uv
uv venv --python 3.12

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# （可选）如果仍然报全局包冲突：确认你已激活 .venv，或直接新建一个干净的 .venv 重装
```

如果你必须在“同一个（非虚拟环境）Python 环境”里安装，并且想消除这些提示，需要自行协调全局包版本（可能影响其它项目）。常见处理方式：

```bash
# 示例：升级 pyOpenSSL 以兼容较新的 cryptography
pip install -U pyOpenSSL

# 示例：如果某些旧包强制要求 websockets<11 或 async-timeout<5，可考虑卸载/升级那些旧包
# pip uninstall pyppeteer
# pip install -U aiohttp
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head

# 创建初始管理员用户和默认配置
python scripts/init_db.py
```

### 5. 启动服务

```bash
# 开发模式（支持热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 验证安装

```bash
# 运行 Phase 1 检查脚本
python scripts/check_phase1.py
```

## 访问服务

- **API 文档 (Swagger)**: http://localhost:8000/docs
- **API 文档 (ReDoc)**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **MinIO 控制台**: http://localhost:9001 (admin/minioadmin)
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |

> ⚠️ 首次登录后请立即修改密码！

## VS Code 开发

项目已配置 VS Code 调试和任务：

### 调试配置 (F5)

- `FastAPI: Backend` - 启动后端服务（支持热重载）
- `Python: Init Database` - 初始化数据库
- `Pytest: All Tests` - 运行所有测试

### 任务 (Ctrl+Shift+P → Tasks: Run Task)

- `docker-compose-up` - 启动 Docker 服务
- `docker-compose-down` - 停止 Docker 服务
- `alembic-upgrade` - 运行数据库迁移
- `init-database` - 初始化数据库
- `Full Setup` - 完整环境配置

### API 测试

安装 REST Client 扩展后，可使用 `tests/api_test.http` 测试 API。

## 项目结构

```
KnowBase/
├── .vscode/                 # VS Code 配置
│   ├── launch.json          # 调试配置
│   ├── tasks.json           # 任务配置
│   └── settings.json        # 工作区设置
├── backend/
│   ├── alembic/             # 数据库迁移
│   │   └── versions/        # 迁移版本
│   ├── app/
│   │   ├── api/             # API 路由
│   │   │   └── v1/          # v1 版本 API
│   │   ├── core/            # 核心模块
│   │   ├── models/          # SQLAlchemy 模型
│   │   └── schemas/         # Pydantic Schema
│   ├── scripts/             # 脚本工具
│   ├── tests/               # 测试文件
│   ├── .env                 # 环境配置（不提交）
│   ├── .env.example         # 环境配置模板
│   └── requirements.txt     # Python 依赖
├── docker-compose.yml       # Docker 服务编排
└── README.md
```

## API 概览

### 认证
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新令牌
- `GET /api/v1/auth/me` - 获取当前用户

### 用户管理
- `GET /api/v1/users` - 用户列表
- `POST /api/v1/users` - 创建用户
- `GET /api/v1/users/{id}` - 用户详情
- `PUT /api/v1/users/{id}` - 更新用户
- `DELETE /api/v1/users/{id}` - 删除用户

### 知识库
- `GET /api/v1/knowledge-bases` - 知识库列表
- `POST /api/v1/knowledge-bases` - 创建知识库
- `GET /api/v1/knowledge-bases/{id}` - 知识库详情
- `PUT /api/v1/knowledge-bases/{id}` - 更新知识库
- `DELETE /api/v1/knowledge-bases/{id}` - 删除知识库

### API Key
- `GET /api/v1/api-keys` - API Key 列表
- `POST /api/v1/api-keys` - 创建 API Key
- `DELETE /api/v1/api-keys/{id}` - 删除 API Key

### 权限管理
- `GET /api/v1/knowledge-bases/{id}/permissions` - 权限列表
- `POST /api/v1/knowledge-bases/{id}/permissions` - 添加权限
- `DELETE /api/v1/knowledge-bases/{id}/permissions/{user_id}` - 删除权限

### 模型配置
- `GET /api/v1/model-configs` - 配置列表
- `POST /api/v1/model-configs` - 创建配置
- `POST /api/v1/model-configs/{id}/test` - 测试配置

## 开发计划

- [x] **Phase 1**: 核心基础架构（用户、认证、知识库、权限）
- [ ] **Phase 2**: 文档处理系统（上传、解析、向量化）
- [ ] **Phase 3**: 高级检索与运营（混合检索、监控、管理后台）
- [ ] **Phase 4**: 模型迁移与版本控制
- [ ] **Phase 5**: 用户体验优化

## License

MIT
