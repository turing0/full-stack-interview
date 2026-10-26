> 本前端项目代码由ai生成

# 日常 / EVERYDAY 商品详情页

Next.js 16.4.3、React、TypeScript。使用项目内 Next.js 文档中的 App Router / Client Component / rewrites 约定。

## 运行

```powershell
pnpm install
# 默认将 /api/* 转发至 http://127.0.0.1:8000
# 可通过服务端环境变量调整（修改后重新启动 Next.js）：
$env:API_ORIGIN = "http://127.0.0.1:8000"
pnpm dev
```

首页 `/` 为商品列表，点击商品进入 `/products/[id]` 独立详情页，支持直接访问、刷新及返回列表。列表支持搜索、加载失败重试与空列表状态。商品图片来自已有 seed 素材，复制在 public/static/products 中，不依赖外部图片服务。生产界面始终请求真实 API；接口失败显示错误和重试，不回退到虚构数据。

## 验证

```powershell
pnpm test       # Vitest + React Testing Library
pnpm lint
pnpm build
pnpm test:e2e   # Playwright；使用本机 Chrome，自动启动或复用 3000 端口服务
```

浏览器测试拦截 API，模拟延迟及权威购物车响应，验证 375px / 1280px 无横向溢出、图片加载、数量收敛、售罄禁购、键盘重复提交，并将截图写入 test-results/。测试数据仅位于 src/tests/fixture.ts，不会进入生产数据流。没有 Chrome 的环境可安装 Chrome，或修改 playwright.config.ts 的 channel 并安装相应浏览器。

## 代码结构

- src/api/shop.ts：HTTP、20 秒超时、错误解析和幂等键。
- src/domain/product.ts：数据类型、SKU 解析、选项可用性与数量约束。
- src/components/product-page.tsx：加载/错误/购买状态与无障碍表单。
- src/tests：领域、组件和 API 合约测试。
- e2e：两种视口的浏览器交互测试。

## 行为约定

- 初始不默认选规格，提示补全颜色、尺码。不存在、停售及售罄的组合有文字标识，规格按钮使用原生 disabled 禁用。候选选项根据其他已选维度判断；未选完整时，只要存在可购买组合就允许选择。提供“清除规格选择”，避免互斥规格导致选择死锁。服务端返回已售罄或不可用时，保留当前选择以展示原因，同时禁用选项与购买。
- 价格、图片、库存从当前规格直接派生，不用多个 effect 同步，避免旧 SKU 数据残留。不存在的组合清空旧价格与图片。
- 可购数量始终是 1 到库存之间的整数。售罄时禁用数量框并显示 0（不允许提交）。规格变化将已有数量立即截断到新库存。
- 同步 ref 锁阻止同一事件周期的重复提交；请求期间禁用规格、数量和购买按钮。
- 网络错误或 5xx 的结果可能不确定；相同 SKU + 数量重试复用幂等键。已明确拒绝或成功的请求才释放该键。服务端必须真正保证幂等性；前端锁无法防止跨标签页或跨设备的重复请求。
- 成功使用 POST 返回的 sku 更新库存，再 GET /api/cart 同步权威总数量。购物车同步失败单独重试，不重复执行添加。
- 库存冲突使用 available_quantity 更新对应 SKU，并自动收敛数量，用户可继续提交。商品请求支持取消；购物车读取用版本号避免迟到响应覆盖新结果。
- 成功反馈使用 role=status，错误使用 role=alert；规格按钮使用 aria-pressed，保留键盘焦点样式。

## API 合约

- GET /api/products：商品数组。
- GET /api/products/{id}：Product，或 `{ product: Product }`。Product 包含 id、name（兼容后端 title）、description、image、两个 dimensions 和 skus。
- SKU：id、price、available_quantity、image、is_available、option_value_ids。
- POST /api/cart/items：JSON `{ sku_id, quantity }`，请求头 Idempotency-Key；成功返回 `{ id, sku_id, quantity, sku }`。
- GET /api/cart：`{ id, items, total_item_count }`。
- 错误支持 FastAPI `{ detail: { code, available_quantity? } }`，以及 422 校验错误数组。

## 后端联调说明

现有后端已提供商品列表与按 ID 查询接口，以及 SKU option_value_ids 序列化。前端兼容响应中的 title / name 字段。本次浏览器回归使用拦截 API 的测试数据，生产页面始终使用真实接口；运行时需要启动后端服务。

前端防重复提交不能替代服务端并发保证。后端仍应校验 quantity 为正整数，并提供数据库层面的幂等键唯一性和库存并发保护。

## 购物车

顶部购物车入口进入 `/cart`，展示服务端记录的商品图片、名称、规格、数量、小计和商品合计。相同 SKU ID 合并为一行并累加数量，不同规格保持独立；合并仅用于展示，不修改服务端原始添加记录。支持空状态、失败重试、刷新和返回详情。商品名称补充请求失败时仍展示 SKU 编号、数量与金额，并可单独触发同步。当前为查看页面，金额按当前 SKU 单价计算、不含运费。

## 乐观 UI 与回滚策略

仅对详情页顶部购物车件数做乐观更新。将已确认总数与待确认增量分开保存：已知总数时，点击加入立即显示“原数量 + 本次数量”，标注“待确认”；初始购物车数量未知时保持“—”，不假设为 0。库存、价格和成功提示不提前更新。

- POST 失败（校验、库存不足、网络、超时或服务端错误）：清除待确认增量，恢复已确认件数；库存冲突仍应用服务端最新库存并调整数量。
- POST 成功：使用返回的 SKU 更新库存；随后 GET /api/cart，原子地用权威总数替换显示并清除增量，避免重复加算。
- POST 成功但 GET 同步失败：添加成功提示保留，件数显示未知并允许重新同步；不显示虚假的确认总数，也不回滚已成功的添加操作。
- 请求期间禁止重复添加、规格更改及手动数量同步；读取版本号防止迟到响应覆盖新数据。未确定结果的重试复用幂等键。
- 页面离开后临时增量自然丢弃，购物车页面重新从服务器读取。网络失败后的本地回滚不代表服务器一定没有提交成功，跨页面防重复仍依赖服务端幂等保障。
