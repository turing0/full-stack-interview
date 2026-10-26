import type { Cart, CartItem, Product } from "../domain/product";

export class ApiError extends Error {
  constructor(
    message: string,
    public code = "NETWORK_ERROR",
    public stock?: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      cache: "no-store",
      signal: init?.signal ?? AbortSignal.timeout(20000),
    });
  } catch {
    throw new ApiError("网络连接失败或请求超时，请重试。");
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const body = data as {
      detail?:
        | { code?: string; available_quantity?: number; error?: string }
        | { loc?: string[]; msg?: string }[];
    } | null;
    const detail = body?.detail;
    if (Array.isArray(detail))
      throw new ApiError(
        `参数校验失败：${detail.map((e) => `${e.loc?.join(".") ?? "参数"} ${e.msg ?? "无效"}`).join("；")}`,
        "VALIDATION_ERROR",
      );
    const code =
      detail?.code ??
      (response.status === 422 ? "VALIDATION_ERROR" : "SERVER_ERROR");
    const messages: Record<string, string> = {
      INSUFFICIENT_STOCK: "库存发生变化，已更新最新库存，请调整数量后重试。",
      INVALID_SKU: "该规格暂时不可购买，请选择其他规格。",
      PRODUCT_NOT_FOUND: "未找到该商品。",
      VALIDATION_ERROR: "提交参数不正确，请检查规格和购买数量。",
    };
    throw new ApiError(
      messages[code] ?? "服务暂时不可用，请稍后重试。",
      code,
      detail?.available_quantity,
    );
  }
  if (!data)
    throw new ApiError("服务器返回的数据为空，请重试。", "SERVER_ERROR");
  return data as T;
}

type ApiProduct = Omit<Product, "name"> & { name?: string; title?: string };
function normalizeProduct(product: ApiProduct): Product {
  return { ...product, name: product.name ?? product.title ?? "未命名商品" };
}

export const shopApi = {
  async products(signal?: AbortSignal): Promise<Product[]> {
    const products = await request<ApiProduct[]>("/api/products", { signal });
    if (!Array.isArray(products))
      throw new ApiError("商品列表数据格式不正确，请重试。", "SERVER_ERROR");
    return products.map(normalizeProduct);
  },
  async product(id = 1, signal?: AbortSignal): Promise<Product> {
    const data = await request<ApiProduct | { product: ApiProduct }>(
      `/api/products/${id}`,
      { signal },
    );
    const product = "product" in data ? data.product : data;
    if (
      !Array.isArray(product.dimensions) ||
      product.dimensions.length !== 2 ||
      !Array.isArray(product.skus)
    )
      throw new ApiError("商品规格数据不完整，请重试。", "SERVER_ERROR");
    return normalizeProduct(product);
  },
  cart: (signal?: AbortSignal) => request<Cart>("/api/cart", { signal }),
  add: (skuId: number, quantity: number, key: string) =>
    request<CartItem>("/api/cart/items", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": key },
      body: JSON.stringify({ sku_id: skuId, quantity }),
    }),
};
