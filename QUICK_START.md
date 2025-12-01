# 🚀 AIDE ML Enterprise - 快速启动指南

## 最快的开始方式（5分钟）

### 使用 Docker Compose（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env

# 2. 编辑 .env 文件，添加你的 OpenAI API 密钥
# OPENAI_API_KEY=sk-your-key-here

# 3. 启动应用
docker-compose up --build

# 4. 打开浏览器访问
# http://localhost:3000
```

就这么简单！🎉

---

## 本地开发方式

### 前提条件
- Python 3.10+
- Node.js 18+
- npm 8+

### 第一步：后端设置

```bash
# 安装 Python 依赖
pip install -e .
pip install -r backend/requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 添加 API 密钥

# 初始化数据库
python -c "import asyncio; from backend.database import init_db; asyncio.run(init_db())"

# 启动后端
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端将在 http://localhost:8000 启动

### 第二步：前端设置

```bash
# 在新终端窗口中
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:3000 启动

---

## 使用自动化脚本

```bash
# 一键设置（首次运行）
bash scripts/setup.sh

# 一键启动（设置完成后）
bash scripts/start.sh
```

或使用 Makefile：

```bash
# 首次设置
make setup

# 启动开发服务器
make dev

# 使用 Docker
make docker-up
```

---

## 🎯 创建第一个实验

1. **打开浏览器**
   访问 http://localhost:3000

2. **点击 "New Experiment"**

3. **填写表单**
   - 实验名称：例如 "House Price Prediction"
   - 目标：例如 "Predict house prices based on features"
   - 评估指标：例如 "RMSE"
   - 步数：选择 10-20

4. **上传数据**
   - 拖拽或选择 CSV 文件

5. **点击 "Create & Run Experiment"**

6. **观察进度**
   - 实时进度条
   - 实时日志
   - 指标可视化

---

## 📊 访问不同功能

- **Dashboard（仪表盘）**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **API 健康检查**: http://localhost:8000/health

---

## 🐛 遇到问题？

### 端口被占用
```bash
# 更改后端端口
cd backend
uvicorn main:app --port 8001

# 更改前端端口
cd frontend
npm run dev -- --port 3001
```

### 依赖安装失败
```bash
# 清理并重新安装
pip cache purge
rm -rf frontend/node_modules
npm cache clean --force

# 重新安装
pip install -r backend/requirements.txt
cd frontend && npm install
```

### Docker 问题
```bash
# 清理并重建
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

---

## 📚 更多信息

- 完整文档：查看 `README_REFACTORED.md`
- 部署指南：查看 `DEPLOYMENT.md`
- 重构总结：查看 `REFACTORING_SUMMARY.md`

---

## 🎉 开始使用吧！

现在你已经准备好使用 AIDE ML Enterprise 了。

祝你使用愉快！🚀
