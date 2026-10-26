import type { CartItem, SKU } from "./product";

export interface CartLine {
  sku_id: number;
  quantity: number;
  sku: SKU;
}

// The API keeps individual add operations; the cart displays one line per SKU.
export function groupCartItems(items: CartItem[]): CartLine[] {
  const lines = new Map<number, CartLine>();
  for (const item of items) {
    const existing = lines.get(item.sku_id);
    if (existing) existing.quantity += item.quantity;
    else
      lines.set(item.sku_id, {
        sku_id: item.sku_id,
        quantity: item.quantity,
        sku: item.sku,
      });
  }
  return [...lines.values()];
}
