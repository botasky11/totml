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

**修复日期**: 2024-12-02  
**修复版本**: commit ace76cc  
**影响范围**: 前端页面加载和实验详情展示
