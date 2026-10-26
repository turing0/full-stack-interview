# Full-Stack App - Variant PDP

后端使用 FastAPI、SQLAlchemy 和 SQLite，前端使用 Next.js、React 和 TypeScript。
支持商品列表、规格选择、库存展示、加入购物车及购物车查看。

## AI 生成说明

**本项目所有测试代码均由 AI 生成**，包括后端 `backend/tests/` 中的 API 测试、
前端 `frontend/src/tests/` 中的单元及组件测试，以及 `frontend/e2e/` 中的浏览器测试。
测试覆盖及运行结果仍需结合业务要求审查；
初始数据脚本 `backend/seed.py` 也由 AI 生成。
此外，前端的界面代码也由ai生成，经过多轮多次对话实现。

## 快速启动

以下命令使用 Windows PowerShell，起始目录为仓库中的 **App 目录**。
需要 Python 3.11 或以上，以及满足前端依赖要求的 Node.js 和 pnpm
（前端声明的包管理器版本为 `pnpm@12.15.0`）。

### 1. 安装后端依赖并初始化数据

```powershell
# 在 App 目录执行，复用已有虚拟环境
& ..\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
& ..\.venv\Scripts\python.exe .\backend\seed.py
```

`backend/seed.py` 创建缺失的数据表，并补充演示商品、规格、SKU 和购物车。
重复执行不会重复插入已有演示数据，也不会重置已扣减的库存。

### 2. 启动后端

```powershell
& ..\.venv\Scripts\python.exe .\backend\main.py
```

以上命令均在 App 目录执行。后端按普通 Python 脚本运行，直接执行 `backend/main.py` 即可。
API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)。
完整的请求、响应、状态码和错误格式见 [后端接口 README](backend/README.md)。

### 3. 启动前端

另开一个终端，从 App 目录执行：

```powershell
cd frontend
pnpm install
pnpm dev
```

访问 [http://localhost:3000](http://localhost:3000)。前端默认将 `/api/*` 转发到
`http://127.0.0.1:8000`。

## 运行测试

### 后端 API 测试


将测试依赖安装到虚拟环境，之后不需要设置 `PYTHONPATH`：

```powershell
& ..\.venv\Scripts\python.exe -m pip install -r backend/requirements-test.txt
& ..\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
```

```powershell
$env:PYTHONPATH = "$PWD\backend\.test-deps"
& ..\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
```

仅运行并发测试（同样需要先设置上面的 `PYTHONPATH`）：

```powershell
& ..\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -m concurrency -v
```

### 前端测试

在 frontend 目录执行：

```powershell
pnpm.cmd test
pnpm.cmd test:e2e
```

浏览器测试使用本机 Chrome，自动启动或复用 3000 端口服务，并拦截 API 使用测试数据。
更多前端运行、构建和交互说明见 [frontend/README.md](frontend/README.md)。

## 新机器首次创建 Python 环境

仅当 App 上一级目录没有 `.venv` 时，在 App 目录执行：

```powershell
python -m venv ..\.venv
& ..\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -r backend/requirements-test.txt
```

创建后即可使用上面的启动和测试命令；已有虚拟环境保留原位即可。

