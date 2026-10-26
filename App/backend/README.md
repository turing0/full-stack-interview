> 本文档由ai协助编写

# 后端 API 接口说明

后端使用 FastAPI、SQLAlchemy 和 SQLite。以下示例以
`http://127.0.0.1:8000` 为基础地址，请求示例使用 HTTP 报文格式。
所有业务接口成功响应均为 JSON；异常响应格式见文末。

本项目未实现身份认证，所有请求共用默认购物车，不按用户或浏览器隔离。
示例 ID、库存和商品数据用于说明响应结构，不保证与本地 seed 数据完全相同；
实际调用时请先查询商品列表获取 SKU ID。

## 启动与初始化

在 **App 目录**执行，使用当前项目上一级的虚拟环境：

```powershell
& ..\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
& ..\.venv\Scripts\python.exe .\backend\seed.py
& ..\.venv\Scripts\python.exe .\backend\main.py
```

数据文件为 `backend/data.db`。seed 创建表、唯一约束及演示数据；重复执行不重置库存。
旧数据库若尚未包含幂等键唯一约束，需要停止后端、删除数据库文件后重新运行 seed。
仅删除表内记录不会更新结构。本项目没有旧数据库升级脚本。

新环境的创建方式见 [项目 README](../README.md)。

## 接口总览

| 方法 | 路径 | 成功状态码 | 接口相关错误状态码 |
| --- | --- | --- | --- |
| GET | `/` | 200 | 作为健康检查 |
| GET | `/api/products` | 200 | 500：未处理的服务端异常 |
| GET | `/api/products/{id}` | 200 | 404：商品不存在；422：路径参数无效；500 |
| GET | `/api/cart` | 200 | 500 |
| POST | `/api/cart/items` | 201（包括幂等重放） | 400：SKU 无效或库存不足；422：请求校验失败；500 |

## 1. 健康检查

### 请求

```http
GET / HTTP/1.1
Host: 127.0.0.1:8000
```

无请求体或参数。

### 响应：200 OK

```json
{"status": "OK"}
```

此接口仅确认应用能响应，不检查数据库连接。

## 2. 查询商品列表

### 请求

```http
GET /api/products HTTP/1.1
Host: 127.0.0.1:8000
```

无请求体，不提供分页或搜索参数。商品按 ID 升序返回。

### 响应：200 OK

```json
[
  {
    "id": 1,
    "title": "Everyday Cotton Tee",
    "description": "A comfortable cotton T-shirt.",
    "image": "/static/products/tee-black-s.svg",
    "dimensions": [
      {"id": 1, "name": "Color", "values": [{"id": 1, "value": "Black"}]},
      {"id": 2, "name": "Size", "values": [{"id": 4, "value": "S"}]}
    ],
    "skus": [
      {
        "id": 1,
        "price": 129.0,
        "available_quantity": 5,
        "image": "/static/products/tee-black-s.svg",
        "is_available": true,
        "option_value_ids": [1, 4]
      }
    ]
  }
]
```

无商品时仍返回 **200**，响应为 `[]`。

字段说明：

| 字段 | 含义 |
| --- | --- |
| `title` | 商品名称；API 字段为 `title`，不是 `name` |
| `description`、`image` | 商品描述、图片地址，允许为 `null` |
| `dimensions` | 规格维度及规格值，可为空数组 |
| `skus` | 实际存在的规格组合，可为空数组；不存在的组合不生成 SKU |
| `price` | SKU 单价，当前演示数据以人民币计价 |
| `available_quantity` | 查询时的可用库存，提交时服务端会再次检查 |
| `is_available` | 规格是否允许购买；`true` 不代表有库存 |
| `option_value_ids` | 对应 `dimensions[].values[].id`，用于确定规格组合 |

## 3. 查询商品详情

### 请求

```http
GET /api/products/1 HTTP/1.1
Host: 127.0.0.1:8000
```

路径参数 `id` 必须可解析为整数。

### 响应：200 OK

```json
{
  "id": 1,
  "title": "Everyday Cotton Tee",
  "description": "A comfortable cotton T-shirt.",
  "image": "/static/products/tee-black-s.svg",
  "dimensions": [
    {"id": 1, "name": "Color", "values": [{"id": 1, "value": "Black"}]},
    {"id": 2, "name": "Size", "values": [{"id": 4, "value": "S"}]}
  ],
  "skus": [
    {
      "id": 1,
      "price": 129.0,
      "available_quantity": 5,
      "image": "/static/products/tee-black-s.svg",
      "is_available": true,
      "option_value_ids": [1, 4]
    }
  ]
}
```

直接返回商品对象，不额外包裹 `product` 字段。
商品不存在返回 **404 / PRODUCT_NOT_FOUND**；例如 `/api/products/abc` 返回 **422**。

## 4. 添加商品到购物车

### 请求

```http
POST /api/cart/items HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
Idempotency-Key: purchase-001

{"sku_id": 1, "quantity": 3}
```

| 参数 | 位置 | 必填 | 说明 |
| --- | --- | --- | --- |
| `sku_id` | JSON 请求体 | 是 | 整数，必须对应存在且可购买的 SKU |
| `quantity` | JSON 请求体 | 是 | 大于 0 的整数；零及负数返回 422 |
| `Idempotency-Key` | 请求头 | 否 | 一次购买操作的唯一标识；同一操作重试必须复用 |

当前使用 Pydantic 默认整数解析，部分可转换的值（如数字字符串）会被转换；
调用方应发送 JSON 整数。超过库存属于业务错误，返回 400，而非 422。

### 响应：201 Created

假设 SKU 原有库存为 5，购买 3 件后：

```json
{
  "id": 10,
  "sku_id": 1,
  "quantity": 3,
  "sku": {
    "id": 1,
    "price": 129.0,
    "available_quantity": 2,
    "image": "/static/products/tee-black-s.svg",
    "is_available": true,
    "option_value_ids": [1, 4]
  }
}
```

`id` 是购物车条目 ID。成功响应不包含整个购物车或总数量，可再调用 `GET /api/cart`。
不同键或未传键的请求各自创建条目，不将同一 SKU 自动合并。

### 幂等性与并发约定

- `(cart_id, idempotency_key)` 由数据库唯一约束保护。相同键并发或重试返回同一条目，状态码仍为 **201**，不重复扣库存。
- 未传键或传空字符串按无键处理，没有重试去重保障。
- 同键但不同请求体，目前返回该键已成功创建的条目，不返回 409；调用方不得把同一个键用于不同购买操作。
- 重放返回的是已有条目，嵌套 `sku` 为当前读取的数据，不保证与首次响应逐字相同。
- 插入条目及条件扣库存处于同一事务。库存不足时回滚条目，失败不会占用幂等键。
- 两个不同键抢最后一件库存时，只能一个返回 201，另一个返回 **400 / INSUFFICIENT_STOCK**。
- 网络超时不代表服务端未提交；同一操作重试应使用原键。

## 5. 查询购物车

### 请求

```http
GET /api/cart HTTP/1.1
Host: 127.0.0.1:8000
```

无请求体。默认购物车不存在时会创建一个。

### 响应：200 OK

```json
{
  "id": 1,
  "items": [
    {
      "id": 10,
      "sku_id": 1,
      "quantity": 3,
      "sku": {
        "id": 1,
        "price": 129.0,
        "available_quantity": 2,
        "image": "/static/products/tee-black-s.svg",
        "is_available": true,
        "option_value_ids": [1, 4]
      }
    }
  ],
  "total_item_count": 3
}
```

`total_item_count` 为所有条目的 `quantity` 之和，不是条目数。
空购物车返回 **200**：

```json
{"id": 1, "items": [], "total_item_count": 0}
```

## 错误响应格式

### 404：商品不存在

请求示例：`GET /api/products/999999`。

```json
{
  "detail": {
    "error": "Product not found",
    "code": "PRODUCT_NOT_FOUND"
  }
}
```

### 400：SKU 不存在或不可购买

请求示例：`POST /api/cart/items`，请求体 `{"sku_id": 999999, "quantity": 1}`。
禁用的 SKU 返回同样格式：

```json
{
  "detail": {
    "error": "Selected SKU is invalid, unavailable, or does not exist.",
    "code": "INVALID_SKU"
  }
}
```

### 400：库存不足或售罄

请求示例：`POST /api/cart/items`，请求体 `{"sku_id": 1, "quantity": 3}`，
而提交时只剩 1 件：

```json
{
  "detail": {
    "error": "Insufficient stock for this SKU.",
    "code": "INSUFFICIENT_STOCK",
    "available_quantity": 1
  }
}
```

售罄时 `available_quantity` 为 `0`。前端应以这个值更新库存展示，调整数量后再次提交，
而不是继续使用首次加载时的库存；此值是检查时的库存，后续提交仍可能发生变化。

### 422：请求参数校验失败

此类错误的 `detail` 是**数组**，区别于上述业务错误的对象结构。
请求示例：`POST /api/cart/items`，请求体 `{"sku_id": 1, "quantity": 0}`：

```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "quantity"],
      "msg": "Input should be greater than 0",
      "input": 0,
      "ctx": {"gt": 0}
    }
  ]
}
```

负数量同样返回 `greater_than`。缺失字段，例如请求体仅为 `{"sku_id": 1}`：

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "quantity"],
      "msg": "Field required",
      "input": {"sku_id": 1}
    }
  ]
}
```

非法路径参数，例如 `GET /api/products/abc`：

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["path", "id"],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "input": "abc"
    }
  ]
}
```

其他 422 情况包括：缺少请求体、`null` 字段、不合法 JSON、不能转换为整数的字段、
带非零小数部分的数值。均采用 `detail` 数组，`type`、`msg`、`input`、`ctx` 随错误变化；
不合法 JSON 通常为 `json_invalid`，`loc` 中还可能包含字符位置。
客户端应遍历 `detail` 并展示字段位置与错误说明，不应假设所有错误都有 `code`。

### 404 / 405：未知路径或方法不允许

`GET /api/unknown` 返回 **404**：

```json
{"detail": "Not Found"}
```

`DELETE /api/cart` 返回 **405**（当前不提供删除接口）：

```json
{"detail": "Method Not Allowed"}
```

此类框架错误的 `detail` 是字符串。

### 500：未处理的服务端异常

当前没有自定义全局异常处理器。数据库连接失败等未处理异常，默认返回
**500 Internal Server Error**，响应为 `text/plain`：

```text
Internal Server Error
```

因此不能假设所有错误响应都是 JSON；代理产生的 502/503 也不受本应用的响应格式约束。
前端应显示通用错误并允许重试，购买重试仍需复用原幂等键。

## 测试和补充文档

所有测试代码均由 AI 生成。当前机器在 App 目录执行：

```powershell
$env:PYTHONPATH = "$PWD\backend\.test-deps"
& ..\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
```
