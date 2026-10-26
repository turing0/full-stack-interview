
# 回答

## C1
1. 从数据库读取对应组织的 Access Token、Refresh Token、租户 ID 和授权范围。
检查 Access Token 是否过期。如果过期，先刷新 Token，并安全保存更新后的凭据。
2. 验证 OAuth 和租户连接
GET https://api.xero.com/connections
HTTP 200 表示当前 Token 可以访问 Connections API。
随后检查返回的 tenantId 是否包含当前内部组织绑定的 Xero 租户 ID。
如果找不到对应租户，停止同步并要求重新连接。 

https://developer.xero.com/documentation/guides/how-to-guides/integration-best-practices
https://developer.xero.com/documentation/api/accounting/accounts

## C2
1. 401 Unauthorized

原因 A: Access Token 已过期。 -> 检查 Token 存储与自动刷新机制。

原因 B: 凭据无效/被撤销。 -> 要求用户重新授权（Re-authentication）。

2. 403 Forbidden

原因 A: 缺少必要 Scope（例如缺少 accounting.transactions）。 -> 检查 OAuth 申请的权限范围。 

原因 B: 租户不匹配或无权访问该组织。 -> 检查请求头中的 `Xero-Tenant-Id` 是否正确。

3. 404 Not Found

原因 A: 错误的 API 终结点/URL 环境（例如测试环境 Sandbox 误用了生产环境 URL）。

原因 B: 请求的发票 ID（InvoiceID）在当前租户中不存在。 -> 校验 ID 格式与组织上下文。


## C3
1. 分页读取
通过 Xero Invoices API 的 page 参数分批读取数据
每次处理一页，直到所有需要同步的数据处理完成
2. 增量更新
利用 If-Modified-Since 请求头，只获取指定时间之后修改过的发票。
3. 游标持久化
同步开始时读取上次成功水位，记录本次同步窗口。
每页数据使用数据库事务写入。只有所有分页成功处理后，才更新最终完成水位。
4. 防止重复数据
在数据库建立唯一约束：
UNIQUE(internal_org_id, xero_invoice_id)
使用 UPSERT 操作。
5. 部分失败处理
保留已处理的，不更新游标，标记任务失败，恢复后从原来的窗口重新读取，upsert进行操作。
6. 同一个租户同时只能有一个有效的同步任务，避免并发修改同步游标。

## C4
1. 检查 Xero 返回的限流响应头（例如 Retry-After 或针对分钟/日限制的配额头），优先尊重 Xero 指定的等待时间。
2. 使用指数退避算法，并引入随机抖动，防止多线程重试风暴击垮 API
3. 为重试添加随机事件偏移，避免多个worker同时重试
4. 将不同租户的周期性任务错峰调度。
5. 明确 400 Bad Request、401 Unauthorized、403 Forbidden 和 404 Not Found 属于客户端逻辑或权限错误，绝对不能重试，应当直接告警并挂起任务。

https://developer.xero.com/documentation/guides/oauth2/limits/


## C5
1. 内部去重
对内部订单创建发票的操作建立唯一约束：
UNIQUE(internal_org_id, order_id, invoice_kind)
2. 使用 Idempotency-Key
创建发票时添加：
Idempotency-Key: <stable_operation_key>
对同一次创建操作进行安全重试时，必须使用相同的幂等键和相同的请求内容。
但是，Xero 的幂等请求缓存时间约为 6 分钟，因此不能依靠这个机制实现永久去重。
3. 请求成功但响应丢失
如果创建请求超时：
将内部操作状态标记为 UNKNOWN。不要立即认定创建失败。
查询 Xero 中是否已存在对应发票。
如果找到唯一且匹配的发票，保存对应 InvoiceID，并标记为 CONFIRMED。
如果结果不确定或发现多条匹配记录，进入人工对账流程。
如果超过安全的幂等窗口，不能未经核查就再次创建发票。

https://developer.xero.com/documentation/best-practices/data-integrity/idempotency/#best-practices

## C6
Logs：同步任务开始与结束。API 请求失败。OAuth Token 刷新。 发票同步成功或失败。任务重试与恢复。
Metrics：API 请求成功率和失败率。同步延迟。任务重试次数。同步队列积压数量。
Alerts：速率限制频繁触发。同步任务持续失败。大量认证失败。Token 刷新持续失败。
Correlation Identifiers：request_id，job_id，internal_org_id，tenant_id，invoice_id，Xero-Correlation-Id
Token、secret，password、Authorization等敏感凭据不能记录到日志
Token 和密钥必须经过高强度加密（如 AES-256）后存储在安全的数据库或专属秘钥管理服务中。定期对 Client Secrets 进行安全轮换，并依赖 OAuth 机制自动安全地轮换refresh_token。

https://developer.xero.com/documentation/api/accounting/invoices
