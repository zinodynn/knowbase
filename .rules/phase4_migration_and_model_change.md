# KnowBase 项目实现 - 阶段四：向量库迁移与模型更换

## 实施进度

### ✅ 已完成 (2024-12-23)

#### 数据库迁移 (003_phase4_tables)

**新增表:**
- `vector_migrations` - 向量库迁移任务表
- `migration_logs` - 迁移日志表  
- `reembedding_tasks` - 重新向量化任务表
- `batch_operations` - 批量操作记录表
- `rollback_checkpoints` - 回滚检查点表

**字段变更:**
- `chunks` 表新增 `embedding_model_version` 字段

**新增枚举类型:**
- `migrationstatus` - 迁移状态
- `reembeddingstrategy` - 重新向量化策略
- `batchoperationtype` - 批量操作类型
- `batchoperationstatus` - 批量操作状态

**新增文件:**
- `backend/app/models/migration.py` - SQLAlchemy 模型
- `backend/app/schemas/migration.py` - Pydantic schemas
- `backend/alembic/versions/003_phase4_tables.py` - 迁移脚本

**回滚命令:**
```bash
cd backend
alembic downgrade 002_phase2_tables
```

---

## 前置条件
- 阶段一完成：用户系统、模型配置管理
- 阶段二完成：文档处理、向量化
- 阶段三完成：高级检索、基础运营功能

## 目标
实现向量库迁移、Embedding 模型更换、批量操作等关键运维功能

## 任务清单

### 1. 向量库迁移功能

#### 1.1 数据库设计

**vector_migrations 表**
```sql
CREATE TABLE vector_migrations (
    id UUID PRIMARY KEY,
    kb_id UUID,  -- NULL 表示迁移所有知识库
    source_type VARCHAR(50),  -- milvus, qdrant, weaviate
    target_type VARCHAR(50),
    source_config JSON,
    target_config JSON,
    status ENUM('pending', 'running', 'paused', 'completed', 'failed', 'cancelled'),
    total_collections INTEGER,
    migrated_collections INTEGER,
    total_vectors INTEGER,
    migrated_vectors INTEGER,
    progress INTEGER,  -- 0-100
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_vector_migrations_status ON vector_migrations(status);
CREATE INDEX idx_vector_migrations_created_by ON vector_migrations(created_by);
```

**migration_logs 表** (详细日志)
```sql
CREATE TABLE migration_logs (
    id UUID PRIMARY KEY,
    migration_id UUID REFERENCES vector_migrations(id),
    log_level VARCHAR(20),  -- info, warning, error
    message TEXT,
    details JSON,
    created_at TIMESTAMP
);

CREATE INDEX idx_migration_logs_migration_id ON migration_logs(migration_id);
```

#### 1.2 迁移服务 (app/services/vector_migration.py)

**核心类**:
```python
class VectorMigrationService:
    def __init__(self, migration_id: str):
        self.migration = self.load_migration(migration_id)
        self.source_client = self.create_vector_client(
            self.migration.source_type,
            self.migration.source_config
        )
        self.target_client = self.create_vector_client(
            self.migration.target_type,
            self.migration.target_config
        )
    
    async def migrate(self):
        """执行迁移"""
        try:
            # 1. 获取需要迁移的知识库列表
            kbs = self.get_knowledge_bases()
            
            for kb in kbs:
                # 2. 在目标向量库创建 Collection
                await self.create_target_collection(kb)
                
                # 3. 分批迁移向量
                await self.migrate_kb_vectors(kb)
                
                # 4. 验证数据完整性
                await self.verify_migration(kb)
                
                # 5. 更新 chunks 表的 vector_id
                await self.update_chunk_vector_ids(kb)
            
            # 6. 更新系统配置
            await self.update_system_config()
            
        except Exception as e:
            self.handle_error(e)
    
    async def migrate_kb_vectors(self, kb: KnowledgeBase):
        """迁移单个知识库的向量"""
        batch_size = 1000
        offset = 0
        
        while True:
            # 从源向量库读取
            vectors = await self.source_client.get_vectors(
                kb_id=kb.id,
                limit=batch_size,
                offset=offset
            )
            
            if not vectors:
                break
            
            # 写入目标向量库
            new_ids = await self.target_client.insert_vectors(
                kb_id=kb.id,
                vectors=vectors
            )
            
            # 记录映射关系
            self.record_id_mapping(vectors, new_ids)
            
            # 更新进度
            self.update_progress(len(vectors))
            
            offset += batch_size
    
    async def verify_migration(self, kb: KnowledgeBase):
        """验证迁移结果"""
        source_count = await self.source_client.count(kb.id)
        target_count = await self.target_client.count(kb.id)
        
        if source_count != target_count:
            raise MigrationError(
                f"Vector count mismatch: {source_count} != {target_count}"
            )
        
        # 抽样验证向量内容
        sample_size = min(100, source_count)
        samples = await self.source_client.sample(kb.id, sample_size)
        
        for sample in samples:
            target_vector = await self.target_client.get_by_id(
                kb.id, 
                self.get_new_id(sample.id)
            )
            if not self.vectors_equal(sample.vector, target_vector.vector):
                raise MigrationError(f"Vector mismatch for {sample.id}")
```

#### 1.3 后台任务

```python
@celery_app.task(bind=True)
def migrate_vector_store_task(self, migration_id: str):
    """向量库迁移任务"""
    migration_service = VectorMigrationService(migration_id)
    
    try:
        migration_service.update_status('running')
        migration_service.migrate()
        migration_service.update_status('completed')
        
        # 发送完成通知
        send_notification(
            user_id=migration_service.migration.created_by,
            title="向量库迁移完成",
            message=f"成功迁移 {migration_service.total_vectors} 个向量"
        )
        
    except Exception as e:
        migration_service.update_status('failed', error_message=str(e))
        send_notification(
            user_id=migration_service.migration.created_by,
            title="向量库迁移失败",
            message=str(e),
            type="error"
        )
        raise
```

#### 1.4 迁移管理 API

**端点**:
- `POST /api/v1/admin/vector-migrations` - 创建迁移任务
  ```json
  {
    "kb_id": "uuid",  // 可选，为空则迁移所有
    "source_type": "milvus",
    "target_type": "qdrant",
    "source_config": {
      "host": "localhost",
      "port": 19530
    },
    "target_config": {
      "url": "http://localhost:6333",
      "api_key": "xxx"
    },
    "auto_start": true  // 是否立即开始
  }
  ```

- `GET /api/v1/admin/vector-migrations` - 获取迁移任务列表
  - 参数: `status`, `created_by`, `page`, `page_size`

- `GET /api/v1/admin/vector-migrations/{migration_id}` - 获取迁移详情
  ```json
  {
    "id": "uuid",
    "status": "running",
    "progress": 65,
    "total_vectors": 100000,
    "migrated_vectors": 65000,
    "started_at": "2024-12-12T10:00:00Z",
    "estimated_remaining_time": "5 minutes"
  }
  ```

- `POST /api/v1/admin/vector-migrations/{migration_id}/start` - 开始迁移
- `POST /api/v1/admin/vector-migrations/{migration_id}/pause` - 暂停迁移
- `POST /api/v1/admin/vector-migrations/{migration_id}/resume` - 恢复迁移
- `POST /api/v1/admin/vector-migrations/{migration_id}/cancel` - 取消迁移
- `POST /api/v1/admin/vector-migrations/{migration_id}/verify` - 验证迁移结果
- `GET /api/v1/admin/vector-migrations/{migration_id}/logs` - 获取迁移日志

### 2. Embedding 模型更换功能

#### 2.1 数据库设计

**reembedding_tasks 表**
```sql
CREATE TABLE reembedding_tasks (
    id UUID PRIMARY KEY,
    kb_id UUID REFERENCES knowledge_bases(id),
    old_model_config JSON,
    new_model_config JSON,
    status ENUM('pending', 'running', 'paused', 'completed', 'failed', 'cancelled'),
    strategy VARCHAR(50),  -- replace, create_new_collection, incremental
    total_chunks INTEGER,
    processed_chunks INTEGER,
    failed_chunks INTEGER,
    progress INTEGER,  -- 0-100
    error_message TEXT,
    batch_size INTEGER DEFAULT 100,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_reembedding_tasks_kb_id ON reembedding_tasks(kb_id);
CREATE INDEX idx_reembedding_tasks_status ON reembedding_tasks(status);
```

**添加模型版本追踪字段**:
```sql
ALTER TABLE knowledge_bases ADD COLUMN embedding_model_info JSON;
-- 存储格式: {"provider": "openai", "model": "text-embedding-3-small", "dimension": 1536, "updated_at": "..."}

ALTER TABLE chunks ADD COLUMN embedding_model_version VARCHAR(50);
-- 用于标识该 chunk 使用的模型版本
```

#### 2.2 重新向量化服务 (app/services/reembedding.py)

```python
class ReembeddingService:
    def __init__(self, task_id: str):
        self.task = self.load_task(task_id)
        self.kb = self.load_kb(self.task.kb_id)
        self.new_embedding_service = EmbeddingService(
            self.task.new_model_config
        )
    
    async def reembed(self):
        """执行重新向量化"""
        try:
            # 1. 检测维度变化
            dimension_changed = self.check_dimension_change()
            
            if dimension_changed:
                # 需要重建 Collection
                await self.recreate_collection()
            
            # 2. 获取所有 chunks
            chunks = self.get_all_chunks()
            
            # 3. 批量处理
            batch_size = self.task.batch_size
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i+batch_size]
                await self.process_batch(batch)
                self.update_progress(len(batch))
            
            # 4. 更新知识库模型信息
            await self.update_kb_model_info()
            
            self.update_status('completed')
            
        except Exception as e:
            self.handle_error(e)
    
    async def process_batch(self, chunks: List[Chunk]):
        """处理一批 chunks"""
        texts = [chunk.content for chunk in chunks]
        
        try:
            # 调用新模型生成向量
            vectors = await self.new_embedding_service.embed_batch(
                texts=texts,
                user_id=self.task.created_by,
                kb_id=self.task.kb_id
            )
            
            # 更新向量库
            await self.update_vectors(chunks, vectors)
            
            # 更新 chunks 表的模型版本
            await self.update_chunk_model_version(
                chunk_ids=[c.id for c in chunks],
                model_version=self.get_model_version()
            )
            
        except Exception as e:
            self.record_failed_chunks(chunks, str(e))
            raise
    
    async def recreate_collection(self):
        """维度变化时重建 Collection"""
        vector_client = get_vector_client()
        
        # 创建新 Collection
        new_collection_name = f"kb_{self.kb.id}_v{int(time.time())}"
        await vector_client.create_collection(
            name=new_collection_name,
            dimension=self.task.new_model_config['dimension']
        )
        
        # 记录新 Collection 名称
        self.task.new_collection_name = new_collection_name
```

#### 2.3 重新向量化 API

**端点**:
- `POST /api/v1/knowledge-bases/{kb_id}/reembed` - 创建重新向量化任务
  ```json
  {
    "new_model_config": {
      "provider": "openai",
      "model_name": "text-embedding-3-large",
      "dimension": 3072,
      "api_url": "...",
      "api_key": "..."
    },
    "strategy": "replace",  // replace, create_new_collection
    "batch_size": 100,
    "auto_start": true
  }
  ```

- `GET /api/v1/knowledge-bases/{kb_id}/reembedding-tasks` - 获取任务列表
- `GET /api/v1/reembedding-tasks/{task_id}` - 获取任务详情
- `POST /api/v1/reembedding-tasks/{task_id}/start` - 开始任务
- `POST /api/v1/reembedding-tasks/{task_id}/pause` - 暂停任务
- `POST /api/v1/reembedding-tasks/{task_id}/resume` - 恢复任务
- `POST /api/v1/reembedding-tasks/{task_id}/cancel` - 取消任务
- `POST /api/v1/reembedding-tasks/{task_id}/retry-failed` - 重试失败的 chunks

**模型变更检测 API**:
- `GET /api/v1/knowledge-bases/{kb_id}/model-change-check` - 检测模型是否变更
  ```json
  {
    "current_model": {
      "provider": "openai",
      "model": "text-embedding-3-small",
      "dimension": 1536
    },
    "configured_model": {
      "provider": "openai",
      "model": "text-embedding-3-large",
      "dimension": 3072
    },
    "needs_reembed": true,
    "dimension_changed": true,
    "estimated_cost": 15.50,
    "estimated_time": "30 minutes"
  }
  ```

### 3. 批量操作功能

#### 3.1 批量文档操作 API

**端点**:
- `POST /api/v1/knowledge-bases/{kb_id}/documents/batch-delete` - 批量删除
  ```json
  {
    "document_ids": ["uuid1", "uuid2", ...],
    "delete_from_storage": true,  // 是否删除 MinIO 中的文件
    "delete_vectors": true  // 是否删除向量
  }
  ```

- `POST /api/v1/knowledge-bases/{kb_id}/documents/batch-reprocess` - 批量重新处理
  ```json
  {
    "document_ids": ["uuid1", "uuid2", ...],
    "reparse": true,  // 是否重新解析
    "rechunk": true,  // 是否重新分块
    "reembed": true  // 是否重新向量化
  }
  ```

- `POST /api/v1/knowledge-bases/{kb_id}/documents/batch-update-metadata` - 批量更新元数据
  ```json
  {
    "document_ids": ["uuid1", "uuid2", ...],
    "metadata": {
      "tags": ["add_tag1", "add_tag2"],
      "remove_tags": ["remove_tag1"]
    }
  }
  ```

#### 3.2 批量标签操作 API

**端点**:
- `POST /api/v1/knowledge-bases/{kb_id}/tags/batch-add` - 批量添加标签
  ```json
  {
    "document_ids": ["uuid1", "uuid2", ...],
    "tags": ["tag1", "tag2"]
  }
  ```

- `POST /api/v1/knowledge-bases/{kb_id}/tags/batch-remove` - 批量删除标签
  ```json
  {
    "document_ids": ["uuid1", "uuid2", ...],
    "tags": ["tag1", "tag2"]
  }
  ```

#### 3.3 批量任务状态查询

**batch_operations 表** (可选，用于追踪批量操作)
```sql
CREATE TABLE batch_operations (
    id UUID PRIMARY KEY,
    kb_id UUID REFERENCES knowledge_bases(id),
    operation_type VARCHAR(50),  -- delete, reprocess, update_metadata
    target_ids JSON,  -- 目标文档 IDs
    parameters JSON,
    status ENUM('pending', 'running', 'completed', 'failed'),
    total_items INTEGER,
    processed_items INTEGER,
    failed_items INTEGER,
    progress INTEGER,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**端点**:
- `GET /api/v1/batch-operations/{operation_id}` - 查询批量操作状态

### 4. Web 管理界面

#### 4.1 向量库迁移页面

**路由**: `/admin/vector-migration`

**功能**:
- [ ] 创建迁移任务表单
  - 选择源向量库类型和配置
  - 选择目标向量库类型和配置
  - 选择迁移范围（全部/指定知识库）
  - 测试连接按钮
- [ ] 迁移任务列表
  - 显示状态、进度、开始时间
  - 操作按钮：开始、暂停、恢复、取消
- [ ] 迁移详情页
  - 实时进度条
  - 详细日志输出
  - 错误信息展示
  - 验证结果

#### 4.2 模型更换页面

**路由**: `/knowledge-bases/{kb_id}/model-change`

**功能**:
- [ ] 当前模型信息展示
- [ ] 模型变更检测
  - 自动检测配置是否变更
  - 显示变更影响（维度变化、预估成本、预估时间）
  - 变更警告提示
- [ ] 重新向量化任务表单
  - 选择新模型配置
  - 选择策略（替换/新建Collection）
  - 设置批量大小
- [ ] 任务进度监控
  - 实时进度条
  - 已处理/总数
  - 失败数量
  - 预计剩余时间
- [ ] 失败重试功能

#### 4.3 批量操作页面

**位置**: 知识库文档管理页面增强

**功能**:
- [ ] 文档列表支持多选（Checkbox）
- [ ] 批量操作工具栏
  - 批量删除按钮（带确认对话框）
  - 批量重新处理按钮
  - 批量添加标签按钮
  - 批量删除标签按钮
- [ ] 批量操作进度提示
  - Toast 通知
  - 后台任务状态显示

### 5. 数据一致性保证

#### 5.1 事务处理
- [ ] 向量库操作与 PostgreSQL 操作的一致性
- [ ] 失败回滚机制
- [ ] 幂等性设计

#### 5.2 数据验证
- [ ] 迁移后验证向量数量
- [ ] 抽样验证向量内容
- [ ] 元数据完整性检查

#### 5.3 备份机制
- [ ] 迁移前自动备份配置
- [ ] 支持回滚到旧配置
- [ ] 保留迁移历史记录

### 6. 并发控制与锁机制

#### 6.1 分布式锁设计
```python
# app/core/distributed_lock.py
import redis
from contextlib import asynccontextmanager
import time
import uuid

class DistributedLock:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    @asynccontextmanager
    async def acquire(
        self, 
        resource: str, 
        ttl: int = 300,  # 锁超时时间（秒）
        retry_times: int = 3,
        retry_delay: float = 1.0
    ):
        """
        获取分布式锁
        
        使用场景:
        - 向量库迁移时锁定知识库
        - 重新向量化时锁定知识库
        - 批量操作时防止并发冲突
        """
        lock_key = f"lock:{resource}"
        lock_value = str(uuid.uuid4())
        acquired = False
        
        for _ in range(retry_times):
            # 使用 SET NX EX 原子操作
            acquired = self.redis.set(
                lock_key, 
                lock_value, 
                nx=True, 
                ex=ttl
            )
            if acquired:
                break
            await asyncio.sleep(retry_delay)
        
        if not acquired:
            raise LockAcquisitionError(f"Failed to acquire lock for {resource}")
        
        try:
            yield
        finally:
            # 使用 Lua 脚本保证原子性释放
            release_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            self.redis.eval(release_script, 1, lock_key, lock_value)

# 使用示例
async def migrate_kb_vectors(kb_id: str):
    lock = DistributedLock(redis_client)
    async with lock.acquire(f"kb:{kb_id}:migration"):
        # 执行迁移操作
        pass
```

#### 6.2 并发控制策略
```python
# 迁移任务并发控制
class MigrationConcurrencyManager:
    MAX_CONCURRENT_MIGRATIONS = 2  # 最大并发迁移数
    MAX_CONCURRENT_KB_OPERATIONS = 1  # 每个知识库最大并发操作数
    
    async def can_start_migration(self, kb_id: str = None) -> bool:
        """检查是否可以开始新的迁移任务"""
        # 检查全局并发数
        running_migrations = await self.get_running_migrations_count()
        if running_migrations >= self.MAX_CONCURRENT_MIGRATIONS:
            return False
        
        # 检查知识库级别并发
        if kb_id:
            kb_operations = await self.get_kb_operations_count(kb_id)
            if kb_operations >= self.MAX_CONCURRENT_KB_OPERATIONS:
                return False
        
        return True
    
    async def wait_for_slot(self, kb_id: str = None, timeout: int = 300):
        """等待可用的执行槽位"""
        start_time = time.time()
        while not await self.can_start_migration(kb_id):
            if time.time() - start_time > timeout:
                raise TimeoutError("Waiting for migration slot timed out")
            await asyncio.sleep(5)
```

### 7. 详细回滚策略

#### 7.1 向量库迁移回滚
```python
class MigrationRollbackService:
    """
    迁移回滚策略:
    1. 保留源向量库数据直到迁移完全验证通过
    2. 迁移过程中记录所有操作日志
    3. 支持自动和手动回滚
    """
    
    async def rollback_migration(self, migration_id: str) -> bool:
        migration = await self.get_migration(migration_id)
        
        # 1. 检查是否可以回滚
        if migration.status == 'completed' and migration.source_deleted:
            raise RollbackError("Source data already deleted, cannot rollback")
        
        # 2. 更新系统配置指向源向量库
        await self.update_vector_store_config(
            migration.source_type,
            migration.source_config
        )
        
        # 3. 删除目标向量库中的数据（如果有）
        if migration.target_collection_created:
            target_client = self.create_vector_client(
                migration.target_type,
                migration.target_config
            )
            for kb_id in migration.migrated_kb_ids:
                await target_client.delete_collection(f"kb_{kb_id}")
        
        # 4. 恢复 chunks 表的 vector_id
        if migration.id_mapping:
            await self.restore_chunk_vector_ids(migration.id_mapping)
        
        # 5. 更新迁移状态
        migration.status = 'rolled_back'
        await self.save_migration(migration)
        
        return True

    async def create_rollback_checkpoint(self, migration_id: str):
        """创建回滚检查点"""
        migration = await self.get_migration(migration_id)
        
        checkpoint = {
            'migration_id': migration_id,
            'timestamp': datetime.utcnow(),
            'source_config': migration.source_config,
            'system_config_backup': await self.backup_system_config(),
            'id_mappings': {}  # 旧ID -> 新ID 映射
        }
        
        await self.save_checkpoint(checkpoint)
        return checkpoint
```

#### 7.2 重新向量化回滚
```python
class ReembeddingRollbackService:
    """
    重新向量化回滚策略:
    1. 维度不变时: 保留旧向量，失败时恢复
    2. 维度变化时: 创建新 Collection，失败时删除新 Collection
    """
    
    async def rollback_reembedding(self, task_id: str) -> bool:
        task = await self.get_task(task_id)
        
        if task.strategy == 'replace':
            # 策略1: 替换模式 - 从备份恢复
            if not task.backup_exists:
                raise RollbackError("No backup available for rollback")
            
            await self.restore_from_backup(task)
            
        elif task.strategy == 'create_new_collection':
            # 策略2: 新建 Collection 模式 - 删除新 Collection
            if task.new_collection_name:
                await self.vector_client.delete_collection(
                    task.new_collection_name
                )
            
            # 恢复知识库配置
            await self.restore_kb_model_config(task.kb_id)
        
        # 恢复 chunks 的 embedding_model_version
        await self.restore_chunk_model_versions(task)
        
        task.status = 'rolled_back'
        await self.save_task(task)
        
        return True
```

#### 7.3 回滚检查点管理
```sql
-- 回滚检查点表
CREATE TABLE rollback_checkpoints (
    id UUID PRIMARY KEY,
    operation_type VARCHAR(50),  -- migration, reembedding
    operation_id UUID,
    checkpoint_data JSONB,
    created_at TIMESTAMP,
    expires_at TIMESTAMP  -- 检查点过期时间
);

CREATE INDEX idx_checkpoints_operation ON rollback_checkpoints(operation_type, operation_id);
```

## 验收标准

### 向量库迁移
- [ ] 可以成功从 Milvus 迁移到 Qdrant
- [ ] 可以成功从 Qdrant 迁移到 Weaviate
- [ ] 迁移过程可以暂停和恢复
- [ ] 迁移失败可以取消并回滚
- [ ] 迁移完成后数据完整性验证通过
- [ ] Web 界面显示实时进度

### 模型更换
- [ ] 检测到模型配置变更时自动提示
- [ ] 可以创建重新向量化任务
- [ ] 维度变化时自动重建 Collection
- [ ] 支持分批处理，不阻塞系统
- [ ] 失败的 chunks 可以重试
- [ ] 完成后知识库可以正常搜索

### 批量操作
- [ ] 可以批量删除多个文档
- [ ] 可以批量重新处理文档
- [ ] 可以批量添加/删除标签
- [ ] 批量操作有进度提示
- [ ] 操作失败有详细错误信息

### 界面友好性
- [ ] 操作流程清晰，有引导提示
- [ ] 关键操作有确认对话框
- [ ] 错误信息友好易懂
- [ ] 进度显示准确实时

## 依赖项（新增）

```python
# requirements.txt 新增
aiofiles==23.2.1  # 异步文件操作
tqdm==4.66.1  # 进度条（用于命令行工具）
```

## 预计时间
3-4天

## 下一阶段
完成后进入**阶段五：用户体验优化**
