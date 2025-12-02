# Bug修复记录

## Bug #1: ExperimentDetail 循环依赖错误

### 问题描述
```
ReferenceError: Cannot access 'experiment' before initialization
```

在 `ExperimentDetail.tsx` 页面加载时，控制台报错提示无法在初始化前访问 `experiment` 变量。

### 根本原因

在 `useQuery` 的配置中，`refetchInterval` 选项直接引用了正在被定义的 `experiment` 变量：

```typescript
const { data: experiment, isLoading, refetch } = useQuery({
  queryKey: ['experiment', id],
  queryFn: () => experimentAPI.get(id!),
  enabled: !!id,
  refetchInterval: experiment?.status === 'running' ? 2000 : false, // ❌ 错误：循环引用
});
```

这创建了一个循环依赖：
1. `useQuery` 试图初始化并返回 `experiment`
2. 但在返回之前，它需要计算 `refetchInterval`
3. `refetchInterval` 又试图访问还未返回的 `experiment`

### 解决方案

TanStack Query (React Query) 的 `refetchInterval` 支持回调函数形式，该函数接收查询数据作为参数：

```typescript
const { data: experiment, isLoading, refetch } = useQuery({
  queryKey: ['experiment', id],
  queryFn: () => experimentAPI.get(id!),
  enabled: !!id,
  refetchInterval: (data) => data?.status === 'running' ? 2000 : false, // ✅ 正确：使用回调函数
});
```

**工作原理**：
- 回调函数在每次查询完成后被调用
- `data` 参数包含最新的查询结果
- 避免了对外部变量的直接依赖
- 实现了相同的功能：当状态为 'running' 时每2秒刷新

### 额外改进

同时添加了错误处理到实验创建流程：

```typescript
const createMutation = useMutation({
  mutationFn: async () => {
    // ... mutation logic
  },
  onSuccess: (experiment) => {
    navigate(`/experiments/${experiment.id}`);
  },
  onError: (error) => {
    console.error('Failed to create experiment:', error);
    alert('Failed to create experiment. Please check console for details.');
  },
});
```

### 测试验证

修复后应验证：
1. ✅ 页面正常加载不报错
2. ✅ 创建实验后正确导航到详情页
3. ✅ 实验运行时自动刷新状态
4. ✅ 实验完成后停止自动刷新

### 相关文件

- `frontend/src/pages/ExperimentDetail.tsx`
- `frontend/src/pages/NewExperiment.tsx`

### 提交信息

```
fix: resolve circular dependency in ExperimentDetail refetchInterval

- Change refetchInterval to use callback function instead of direct variable access
- Add error handling to experiment creation mutation
- Fix 'Cannot access experiment before initialization' error
```

### 学到的经验

1. **避免循环依赖**: 在 Hook 的配置选项中避免引用 Hook 返回的值
2. **使用回调函数**: 对于需要动态计算的配置选项，优先使用回调函数
3. **添加错误处理**: 总是为异步操作添加错误处理逻辑
4. **查看文档**: TanStack Query 等库通常提供多种配置方式，回调函数形式更灵活

## 如何避免类似问题

### 代码审查检查清单

- [ ] Hook 配置中是否引用了 Hook 返回值？
- [ ] 能否用回调函数替代直接引用？
- [ ] 是否为所有异步操作添加了错误处理？
- [ ] 变量声明顺序是否合理？

### TypeScript 帮助

TypeScript 通常能在编译时捕获这类错误，但在动态引用场景下可能会漏掉。建议：
- 启用严格模式 (`strict: true`)
- 使用 ESLint 规则检查循环依赖
- 代码审查时特别注意 Hook 配置

---

## Bug #2: 数据库会话管理问题

### 问题描述
```
sqlalchemy.exc.InvalidRequestError: This session is in 'prepared' state; 
no further SQL can be emitted within this transaction.
```

后端在运行实验时报错，前端获取实验列表时返回500错误。

### 根本原因

后台异步任务使用了API请求的数据库会话：

```python
@router.post("/{experiment_id}/run")
async def run_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    service = ExperimentService(db)  # 使用请求的会话
    
    # 后台任务仍在使用这个会话
    asyncio.create_task(service.run_experiment_async(experiment_id, callback))
    
    return {"message": "started"}  # API请求结束，会话被关闭
    # 但后台任务还在尝试使用已关闭的会话！
```

**问题流程**：
1. API请求创建数据库会话
2. 启动后台任务，传递会话引用
3. API请求返回，会话被提交并关闭
4. 后台任务继续运行，尝试使用已关闭的会话
5. SQLAlchemy报错："会话已处于prepared状态"

### 解决方案

为后台任务创建独立的数据库会话：

```python
@router.post("/{experiment_id}/run")
async def run_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    service = ExperimentService(db)
    experiment = await service.get_experiment(experiment_id)
    
    # 创建独立的后台任务
    async def run_background_task():
        from backend.database import async_session_maker
        
        # 为后台任务创建独立的会话
        async with async_session_maker() as bg_db:
            try:
                bg_service = ExperimentService(bg_db)
                await bg_service.run_experiment_async(experiment_id, callback)
            except Exception as e:
                logger.error(f"Background task error: {e}")
                # 错误处理
    
    asyncio.create_task(run_background_task())
    return {"message": "started"}
```

**关键改进**：
1. 使用 `async_session_maker()` 创建新会话
2. 后台任务有自己的会话生命周期
3. 使用 `async with` 确保会话正确关闭
4. 添加异常处理和错误状态更新

### 会话管理最佳实践

#### ❌ 错误做法
```python
# 不要在后台任务中使用请求会话
@app.post("/start")
async def start(db: AsyncSession = Depends(get_db)):
    asyncio.create_task(background_task(db))  # 错误！
```

#### ✅ 正确做法
```python
# 为后台任务创建独立会话
@app.post("/start")
async def start(db: AsyncSession = Depends(get_db)):
    async def task():
        async with async_session_maker() as task_db:
            await background_task(task_db)
    asyncio.create_task(task())
```

### 其他需要注意的场景

1. **Celery任务**: 也需要独立会话
2. **定时任务**: 使用独立会话
3. **WebSocket处理**: 长连接也需要独立会话管理
4. **批量操作**: 考虑会话超时和连接池

### 相关文件

- `backend/api/experiments.py`
- `backend/services/experiment_service.py`
- `backend/database/base.py`

### 提交信息

```
fix: resolve database session management issue in background tasks

- Create independent database session for background experiment execution
- Prevent 'session in prepared state' error by isolating task sessions
- Add proper error handling and failed status update for background tasks
```

### 验证测试

修复后应验证：
1. ✅ 创建实验后可以正常运行
2. ✅ 后台任务执行不报会话错误
3. ✅ 实验列表API返回200
4. ✅ 实验状态正确更新
5. ✅ 错误时状态更新为failed

---

**更新日期**: 2024-12-02  
**修复版本**: 
- Bug #1: commit ace76cc  
- Bug #2: commit d6638e9  
**影响范围**: 前端页面加载、实验详情展示、后台任务执行
