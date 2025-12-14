# KnowBase - 企业级知识库管理平台

## 📖 项目概述

KnowBase 是一个功能完整的知识库管理平台，支持：
- ✅ 多源数据接入（上传、Git/SVN 同步、API 推送）
- ✅ 智能向量化检索（语义搜索、混合检索、重排序）
- ✅ 团队协作（多用户、权限管理）
- ✅ 模型配置管理（Embedding、Rerank 模型可配置）
- ✅ 向量库迁移/embed模型更换和同步（支持 Milvus/Qdrant/Weaviate）
- ✅ 召回测试与优化
- ✅ 完善的监控与日志系统
- ✅ 友好的 Web 管理界面

---

## 📚 文档导航

### 核心文档
| 文档 | 说明 | 优先级 |
|------|------|--------|
| [implementation_guide.md](./implementation_guide.md) | 项目总指南、架构设计、技术选型 | ⭐⭐⭐ 必读 |
| [deployment_guide.md](./deployment_guide.md) | Docker Compose、Nginx、部署配置 | ⭐⭐⭐ 部署必读 |

### 分阶段实施文档
| 阶段 | 文档 | 内容 | 时间 | 状态 |
|------|------|------|------|------|
| 阶段一 | [phase1_core_foundation.md](./phase1_core_foundation.md) | 用户系统、知识库 CRUD、权限管理、模型配置 | 3-5天 | 📝 未开始 |
| 阶段二 | [phase2_document_processing.md](./phase2_document_processing.md) | 文档解析、向量化、Git/SVN 同步、基础检索 | 5-7天 | 📝 未开始 |
| 阶段三 | [phase3_advanced_features.md](./phase3_advanced_features.md) | 混合检索、召回测试、监控、Web 管理后台 | 6-8天 | 📝 未开始 |
| 阶段四 | [phase4_migration_and_model_change.md](./phase4_migration_and_model_change.md) | 向量库迁移、模型更换、批量操作 | 3-4天 | 📝 未开始 |
| 阶段五 | [phase5_ux_optimization.md](./phase5_ux_optimization.md) | 操作引导、文档预览、帮助系统、性能优化 | 2-3天 | 📝 未开始 |

### 辅助文档
| 文档 | 说明 |
|------|------|
| [TASK_CHECKLIST.md](./TASK_CHECKLIST.md) | 开发任务总览检查清单 |
| [complete_feature_checklist.md](./complete_feature_checklist.md) | 完整功能检查清单 |
| [qa.md](./qa.md) | 常见问题解答 |

**总计**: 19-27天（约 3-4 周）

---

## 🎯 开发计划概览

### MVP 版本（阶段一至三）
**目标**: 14-20天内完成可用的知识库管理系统

**核心功能**:
- ✅ 用户登录注册、权限管理
- ✅ 知识库增删改查
- ✅ 文档上传、解析、向量化
- ✅ 语义搜索和混合检索
- ✅ 基础的 Web 管理界面
- ✅ 召回测试功能
- ✅ 基础监控

### 完整版本（所有阶段）
**目标**: 19-27天内完成生产级系统

**增强功能**:
- ✅ 向量库迁移（Milvus ↔ Qdrant ↔ Weaviate）
- ✅ Embedding 模型更换与重新向量化
- ✅ 批量操作（删除、重新处理、标签管理）
- ✅ 文档预览功能
- ✅ 操作引导系统
- ✅ 通知中心
- ✅ 完善的帮助文档

---

## 🏗️ 技术架构

### 后端
- **语言**: Python 3.11+
- **框架**: FastAPI
- **数据库**: PostgreSQL 15+ (元数据)
- **向量库**: Milvus / Qdrant / Weaviate（推荐 Qdrant）
- **缓存**: Redis 7+
- **对象存储**: MinIO
- **任务队列**: Celery

### 前端
- **框架**: React 18 + TypeScript
- **UI 库**: Ant Design 5
- **状态管理**: Zustand
- **图表**: ECharts

### AI 模型
- **Embedding**: 通过 API 调用（OpenAI、Azure、自定义）
- **Rerank**: 通过 API 调用（Cohere、Jina、自定义）
- **配置管理**: 三级配置体系（系统/知识库/用户）

---

## 📋 功能清单

### 核心功能 ✅
- [x] 用户认证与权限管理
- [x] 知识库 CRUD
- [x] 文档上传（多格式支持）
- [x] Git/SVN 同步
- [x] 文档解析与分块
- [x] 向量化（通过 API）
- [x] 语义检索
- [x] 混合检索 + Rerank
- [x] 召回测试系统
- [x] 模型配置管理（三级配置）

### 运维功能 ✅
- [x] 向量库迁移
- [x] Embedding 模型更换
- [x] 批量操作
- [x] 监控仪表板
- [x] 搜索日志与召回分析
- [x] 审计日志

### 用户体验 ✅
- [x] Web 管理后台
- [x] 操作引导系统
- [x] 文档预览
- [x] 通知中心
- [x] 个性化设置
- [x] 帮助文档

---

## 🔍 关键特性

### 1. 向量库灵活切换 ⭐
支持在 Milvus、Qdrant、Weaviate 之间无缝迁移：
- 在线迁移，无需停机
- 自动数据验证
- 进度实时监控
- 失败自动回滚

### 2. 模型配置管理 ⭐
三级配置体系，灵活强大：
- **系统默认配置**：管理员设置全局默认
- **知识库配置**：为特定知识库定制模型
- **用户个人配置**：用户自定义模型（优先级最高）

### 3. 模型更换与重新向量化 ⭐
支持更换 Embedding 模型：
- 自动检测模型变更
- 批量重新向量化
- 维度变化自动重建 Collection
- 失败重试机制

### 4. 简易监控与排查 ⭐
方便的监控和问题排查：
- **模型调用统计**：成本、延迟、频次
- **召回情况分析**：分数分布、低分查询列表
- **搜索日志查询**：详细记录每次搜索

### 5. 界面友好 ⭐
注重用户体验：
- 新手引导系统
- 操作提示气泡
- 友好的错误提示
- 快捷操作面板
- 文档预览功能

---

## 📊 数据库设计

### 核心表
- `users` - 用户表
- `knowledge_bases` - 知识库表
- `documents` - 文档表
- `chunks` - 文档分块表（元数据，向量存在向量库）
- `user_kb_permissions` - 权限表
- `api_keys` - API 密钥表

### 配置与任务
- `model_configs` - 模型配置表（三级配置）
- `processing_tasks` - 文档处理任务
- `vector_migrations` - 向量库迁移任务
- `reembedding_tasks` - 重新向量化任务

### 监控与日志
- `model_call_logs` - 模型调用日志
- `search_logs` - 搜索日志
- `api_request_logs` - API 请求日志
- `audit_logs` - 审计日志

---

## 🎯 验收标准

### 功能完整性
- [x] 用户可以登录、创建知识库
- [x] 可以上传文档并自动向量化
- [x] 可以搜索知识库并获得准确结果
- [x] 可以配置 Embedding 和 Rerank 模型
- [x] 可以测试召回效果
- [x] **可以迁移向量库**
- [x] **可以更换模型并重新向量化**
- [x] 可以批量操作文档
- [x] 界面友好，操作流畅

### 性能指标
- 搜索响应时间 < 500ms (P95)
- 支持并发搜索 1000 QPS
- 文档处理速度 > 10个/分钟

### 监控与运维
- 可以查看模型调用成本和延迟
- 可以分析召回情况，定位低分查询
- 可以查询搜索日志，排查问题
- 关键操作有审计日志

---

## 🛠️ 开发环境要求

### 必需
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### 选择其中一个向量库
- Milvus 2.3+
- **Qdrant 1.7+** （推荐）
- Weaviate 1.23+

---

## 📖 参考资料

### 向量数据库
- [Qdrant 文档](https://qdrant.tech/documentation/)
- [Milvus 文档](https://milvus.io/docs)
- [Weaviate 文档](https://weaviate.io/developers/weaviate)

### Embedding 模型
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

### Rerank 模型
- [Cohere Rerank](https://docs.cohere.com/docs/reranking)
- [Jina Reranker](https://jina.ai/reranker/)

---

## 🤝 贡献指南

### 开发流程
1. 从对应阶段文档开始
2. 按照任务清单逐项完成
3. 每完成一个模块编写单元测试
4. 提交代码时附上清晰的 commit message
5. 完成阶段后进行代码审查

### 代码规范
- 后端：遵循 PEP 8
- 前端：使用 ESLint + Prettier
- Git Commit：使用语义化提交信息

---

## 📞 联系方式

如有问题或建议，请查看项目文档或提交 Issue。

---

## 📝 许可证

待定

---

**开发愉快！🎉**
