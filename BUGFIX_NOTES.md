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

## Bug #3: None Metric Value 类型转换错误

### 问题描述
```
TypeError: float() argument must be a string or a real number, not 'NoneType'
```

实验运行时后端报错，无法处理 metric value 为 None 的情况。

### 根本原因

在处理 TOT 生成的节点时，代码假设如果 `node.metric` 存在，那么 `node.metric.value` 就一定有值：

```python
# ❌ 错误：只检查了 metric 存在，没有检查 value
metric_value=float(node.metric.value) if node.metric else None
```

但实际上 TOT 可能会创建 metric 对象，但 value 仍然是 None（例如代码执行失败、评估失败等情况）。

**错误发生的场景**：
1. TOT 执行代码但没有产生有效的评估结果
2. 代码运行出错，无法计算 metric
3. 评估函数返回 None
4. 节点被标记为 buggy，metric 为空

### 解决方案

添加对 `metric.value` 的 None 检查：

```python
# ✅ 正确：同时检查 metric 和 value
metric_value=float(node.metric.value) if (node.metric and node.metric.value is not None) else None
```

**修复位置**（三处）：

1. **create_node** - 创建节点时
```python
metric_value=float(node.metric.value) if (node.metric and node.metric.value is not None) else None
```

2. **best_metric_value** - 获取最佳指标时
```python
best_metric_value = float(best_node.metric.value) if (best_node and best_node.metric and best_node.metric.value is not None) else None
```

3. **journal_data** - 收集日志数据时
```python
"metric": float(node.metric.value) if (node.metric and node.metric.value is not None) else None
```

### 防御性编程最佳实践

#### ❌ 脆弱的代码
```python
# 假设链式属性都存在
value = obj.attr1.attr2.attr3

# 只检查第一层
value = float(obj.metric.value) if obj.metric else None
```

#### ✅ 健壮的代码
```python
# 检查所有层级
value = obj.attr1.attr2.attr3 if (obj and obj.attr1 and obj.attr1.attr2) else None

# 完整检查
value = float(obj.metric.value) if (obj.metric and obj.metric.value is not None) else None
```

### Python 特性说明

**None 是特殊的**：
```python
if obj:           # obj 为 None 时为 False
if obj is None:   # 显式检查 None（推荐）
if obj is not None:  # 显式检查非 None

# 0, False, "", [] 等也是 False，但不是 None！
if value:  # 危险！0 也会被判断为 False
if value is not None:  # 安全！只排除 None
```

### 相关文件

- `backend/services/experiment_service.py`

### 提交信息

```
fix: handle None metric values in experiment service

- Add additional None check for node.metric.value before float conversion
- Prevent 'float() argument must be a string or a real number' error
- Check both node.metric existence and node.metric.value is not None
```

### 验证测试

修复后应验证：
1. ✅ 实验可以正常运行
2. ✅ 失败的节点不会导致崩溃
3. ✅ None metric 正确保存为 NULL
4. ✅ 最佳节点选择不报错
5. ✅ Journal 数据正确收集

### 扩展思考

这个问题提醒我们：
1. **不要假设对象结构** - 即使文档说会有某个属性，实际运行时可能为 None
2. **类型提示不够** - Python 的 Optional[float] 不能防止运行时错误
3. **测试边界情况** - 需要测试 None、空值、异常等边界情况
4. **日志很重要** - 如果没有日志，很难定位是哪个节点的 metric 为 None

### 未来改进建议

1. **添加类型守卫**：
```python
def safe_float(value) -> Optional[float]:
    """Safely convert to float, return None if not possible"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
```

2. **使用数据类验证**：
```python
from pydantic import BaseModel, validator

class MetricValue(BaseModel):
    value: Optional[float]
    
    @validator('value')
    def validate_value(cls, v):
        if v is not None and not isinstance(v, (int, float)):
            raise ValueError('Value must be numeric')
        return v
```

3. **添加单元测试**：
```python
def test_none_metric_handling():
    node = Node(metric=Metric(value=None))
    assert safe_get_metric_value(node) is None
```

---

**更新日期**: 2024-12-02  
**修复版本**: 
- Bug #1: commit ace76cc (前端循环依赖)
- Bug #2: commit d6638e9 (数据库会话管理)
- Bug #3: commit cb07036 (None metric 类型转换)
**影响范围**: 前端页面加载、实验详情展示、后台任务执行、实验运行
