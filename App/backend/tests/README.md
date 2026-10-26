# 后端 API 测试

本目录所有测试代码均由 AI 生成，包括测试夹具、API 用例和并发竞态用例。

当前机器在 **App 目录**执行，使用上一级已有的 `.venv` 和已下载的测试依赖：

```powershell
$env:PYTHONPATH = "$PWD\backend\.test-deps"
& ..\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
# 仅运行并发测试
& ..\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -m concurrency -v
```

`backend/.venv` 并不存在，不要使用该路径。新机器的环境创建和依赖安装步骤见
[项目 README](../../README.md)。

测试依赖项目已有的 FastAPI、SQLAlchemy、Pydantic 和 uvicorn；无需启动服务器。
`TestClient` 通过 ASGI 调用真实路由，包含请求校验、依赖注入、序列化及数据库事务。
每个测试使用 pytest 临时目录中的独立 SQLite 文件，覆盖 `get_db` 依赖，
不读取或修改业务 `data.db`；测试结束后恢复依赖覆盖并释放连接。

## 覆盖范围

- `test_catalog_api.py`：健康检查、空列表、商品排序、详情及规格映射、无规格商品、商品不存在、非法路径参数。
- `test_cart_api.py`：空购物车创建及复用、成功添加、库存扣减、总数量、多 SKU、缺失/非法参数、零和负数量、非法 JSON、SKU 不存在或禁用、零库存、超库存、大数量、刚好耗尽库存。
- 幂等性：同键多次重放（包括已售罄）、不同键和无键请求独立执行、失败后复用键重试。
- `test_concurrency_api.py`：两个请求抢最后一件库存（独立数据库重复三次）、相同幂等键并发提交、不同键并发时库存账实一致。
- `test_seed.py`：种子数据重复执行不重复插入，新数据库的唯一约束拒绝重复幂等键。

并发用例使用两个线程、两个 TestClient 和独立数据库会话，通过 SQLAlchemy
加载事件中的 Barrier，让两个请求都读到扣减前的库存，再继续真实写入。
不 mock 路由、库存查询或提交，不使用 sleep 碰运气；同步有超时且事件监听器会清理。
库存测试不仅断言余额非负，还检查成功请求数、购物车条目和售出总量，避免漏掉
“两次成功，但库存丢失更新后仍为零”的超卖问题。

同步点位于 SKU 校验读取后、插入购物车记录及条件 UPDATE 之前，不会在持有写锁时
等待另一请求。相同键的并发测试同时覆盖库存充足与仅剩最后一件的情况。
测试不规定尚未定义的“同键不同请求体”冲突策略。


