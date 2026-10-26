export interface Dimension {
  id: number;
  name: string;
  values: { id: number; value: string }[];
}
export interface SKU {
  id: number;
  price: number;
  available_quantity: number;
  image: string | null;
  is_available: boolean;
  option_value_ids: number[];
}
export interface Product {
  id: number;
  name: string;
  description: string | null;
  image: string | null;
  dimensions: Dimension[];
  skus: SKU[];
}
export interface Cart {
  id: number;
  total_item_count: number;
  items: CartItem[];
}
export interface CartItem {
  id: number;
  sku_id: number;
  quantity: number;
  sku: SKU;
}
export type Selection = Record<number, number>;

export function resolveVariant(
  product: Product,
  selection: Selection,
): SKU | undefined {
  if (
    !product.dimensions.every((d) =>
      d.values.some((v) => v.id === selection[d.id]),
    )
  )
    return;
  const ids = product.dimensions.map((d) => selection[d.id]);
  return product.skus.find(
    (s) =>
      s.option_value_ids.length === ids.length &&
      ids.every((id) => s.option_value_ids.includes(id)),
  );
}

export function optionStatus(
  product: Product,
  selection: Selection,
  dimensionId: number,
  valueId: number,
) {
  const ids = Object.values({ ...selection, [dimensionId]: valueId });
  const candidates = product.skus.filter((s) =>
    ids.every((id) => s.option_value_ids.includes(id)),
  );
  if (!candidates.some((s) => s.is_available)) return "不可用";
  return candidates.some((s) => s.is_available && s.available_quantity > 0)
    ? ""
    : "售罄";
}

// Sold-out SKUs use zero only for disabled controls; it is never submitted.
export function clampQuantity(quantity: number, stock: number) {
  if (stock <= 0) return 0;
  return Math.min(
    stock,
    Math.max(1, Number.isFinite(quantity) ? Math.floor(quantity) : 1),
  );
}
export const label = (value: string) =>
  ({
    Color: "颜色",
    Size: "尺码",
    Black: "曜石黑",
    White: "云朵白",
    Blue: "雾霾蓝",
  })[value] ?? value;
export const money = (value: number) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY" }).format(
    value,
  );
