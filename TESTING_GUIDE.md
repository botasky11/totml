# 🧪 TOT ML Enterprise - 测试指南

## 快速验证修复

### 前提条件
- 后端服务运行中（端口8000）
- 前端服务运行中（端口3000）
- 已配置OpenAI API密钥

### 测试步骤

#### 1. 重启服务

```bash
# 停止所有服务 (Ctrl+C)

# 重启后端
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 在新终端重启前端
cd frontend
npm run dev
```

#### 2. 清除浏览器缓存
- 打开浏览器开发者工具（F12）
- 右键点击刷新按钮
- 选择"清空缓存并硬性重新加载"

#### 3. 测试实验创建流程

**步骤**：
1. 访问 http://localhost:3000
2. 点击 "New Experiment"
3. 填写表单：
   ```
   名称: Test House Prices
   描述: Testing the bug fixes
   目标: Predict house prices
   评估指标: RMSE
   步数: 5
   ```
4. 上传测试CSV文件
5. 点击 "Create & Run Experiment"

**预期结果**：
- ✅ 不应看到 "Cannot access experiment before initialization" 错误
- ✅ 成功跳转到实验详情页面
- ✅ 页面正常显示实验信息

#### 4. 测试实验运行

**步骤**：
1. 在实验详情页面点击 "Run Experiment"
2. 观察控制台和后端日志

**预期结果**：
- ✅ 后端不应报 "session in prepared state" 错误
- ✅ 实验状态变为 "running"
- ✅ 进度条开始更新
- ✅ 能看到实时日志（如果有WebSocket连接）

#### 5. 测试Dashboard

**步骤**：
1. 返回Dashboard (http://localhost:3000)
2. 刷新页面

**预期结果**：
- ✅ 不应看到 500 Internal Server Error
- ✅ 正确显示实验列表
- ✅ 每个实验卡片显示正确的状态

## 详细测试用例

### Test Case 1: 前端循环依赖修复

**目标**: 验证ExperimentDetail页面不会出现初始化错误

**步骤**:
1. 创建新实验
2. 观察浏览器控制台

**预期**:
- 无 "ReferenceError: Cannot access 'experiment' before initialization"
- 页面正常渲染
- useQuery正常工作

**验证点**:
```javascript
// frontend/src/pages/ExperimentDetail.tsx
// refetchInterval 应该使用回调函数
refetchInterval: (data) => data?.status === 'running' ? 2000 : false
```

---

### Test Case 2: 数据库会话隔离

**目标**: 验证后台任务使用独立数据库会话

**步骤**:
1. 创建实验并运行
2. 观察后端日志
3. 检查数据库更新

**预期**:
- 无 SQLAlchemy InvalidRequestError
- 后台任务正常执行
- 实验状态正确更新

**验证点**:
```python
# backend/api/experiments.py
# 应该创建独立会话
async with async_session_maker() as bg_db:
    bg_service = ExperimentService(bg_db)
```

---

### Test Case 3: 错误处理

**目标**: 验证错误情况下的处理

**步骤**:
1. 创建实验但不上传文件
2. 运行实验
3. 观察错误处理

**预期**:
- 显示友好的错误消息
- 实验状态更新为 "failed"
- 错误信息记录到日志

---

### Test Case 4: WebSocket连接

**目标**: 验证实时更新功能

**步骤**:
1. 运行实验
2. 保持在详情页面
3. 切换到"Logs"标签

**预期**:
- WebSocket连接成功
- 收到实时进度更新
- 日志实时显示

**验证命令**:
```bash
# 在浏览器控制台查看WebSocket
console.log(window.WebSocket)

# 应该看到活跃的WebSocket连接
```

---

### Test Case 5: 并发实验

**目标**: 验证多个实验可以同时运行

**步骤**:
1. 创建实验A并运行
2. 不等待完成，创建实验B并运行
3. 观察两个实验的状态

**预期**:
- 两个实验都能正常运行
- 互不干扰
- 各自的会话独立

---

## 性能测试

### 负载测试

```bash
# 使用curl测试API
for i in {1..10}; do
  curl -X GET http://localhost:8000/api/v1/experiments/ &
done
wait

# 预期: 所有请求成功返回
```

### 内存泄漏检查

```bash
# 监控后端进程
watch -n 1 'ps aux | grep uvicorn'

# 运行多个实验后检查内存使用
# 预期: 内存使用稳定，无持续增长
```

## 调试技巧

### 前端调试

```javascript
// 在浏览器控制台
// 查看React Query缓存
window.queryClient.getQueryCache().getAll()

// 查看当前查询状态
window.queryClient.getQueryState(['experiment', experimentId])
```

### 后端调试

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用日志
logger.debug(f"Session state: {db.info}")
logger.debug(f"Experiment status: {experiment.status}")
```

### 数据库调试

```bash
# 查看SQLite数据库
sqlite3 tot.db

# 查询实验
SELECT id, name, status, created_at FROM experiments;

# 查看会话状态
.tables
.schema experiments
```

## 常见问题排查

### 问题: 页面空白

**检查**:
1. 浏览器控制台是否有错误
2. 前端服务是否运行
3. API是否可访问

**解决**:
```bash
# 重启前端
cd frontend
npm run dev
```

### 问题: 实验不运行

**检查**:
1. 后端日志错误
2. API密钥是否配置
3. 文件是否上传成功

**解决**:
```bash
# 检查环境变量
echo $OPENAI_API_KEY

# 查看上传目录
ls -la uploads/exp_*
```

### 问题: WebSocket连接失败

**检查**:
1. WebSocket端点是否正确
2. 防火墙设置
3. 代理配置

**解决**:
```javascript
// 在前端检查WebSocket URL
console.log(import.meta.env.VITE_WS_URL)
```

## 自动化测试脚本

### 快速验证脚本

```bash
#!/bin/bash
# save as test_fixes.sh

echo "Testing TOT ML Fixes..."

# Test API health
echo "1. Testing API health..."
curl -s http://localhost:8000/health | grep healthy && echo "✅ API healthy" || echo "❌ API failed"

# Test experiment list
echo "2. Testing experiment list..."
curl -s http://localhost:8000/api/v1/experiments/ | grep -q '\[' && echo "✅ Can list experiments" || echo "❌ List failed"

# Test frontend
echo "3. Testing frontend..."
curl -s http://localhost:3000 | grep -q "root" && echo "✅ Frontend accessible" || echo "❌ Frontend failed"

echo "Basic tests complete!"
```

运行测试:
```bash
chmod +x test_fixes.sh
./test_fixes.sh
```

## 回归测试清单

在发布前确保：

- [ ] 所有原有功能正常工作
- [ ] 新修复的bug不再出现
- [ ] 没有引入新的bug
- [ ] 性能没有明显下降
- [ ] 日志正常输出
- [ ] 错误处理正确
- [ ] UI/UX体验流畅
- [ ] 文档已更新

## 报告问题

如果发现新问题，请提供：

1. **重现步骤**: 详细的操作步骤
2. **预期行为**: 应该发生什么
3. **实际行为**: 实际发生了什么
4. **环境信息**: 
   - 操作系统
   - Python版本
   - Node版本
   - 浏览器版本
5. **错误日志**: 控制台和后端日志
6. **截图**: 如果可能的话

## 下一步

修复验证通过后：
1. 合并到主分支
2. 创建Release tag
3. 更新CHANGELOG
4. 通知团队

---

**测试日期**: 2024-12-02  
**测试版本**: v2.0.1 (包含bug修复)  
**测试人员**: 开发团队
