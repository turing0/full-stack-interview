import { expect, it } from "vitest";
import { groupCartItems } from "../domain/cart";
import { product } from "./fixture";

it("merges repeated SKU IDs, keeps different variants separate, and preserves API records", () => {
  const items = [
    { id: 1, sku_id: 1, quantity: 2, sku: product.skus[0] },
    { id: 2, sku_id: 3, quantity: 1, sku: product.skus[2] },
    { id: 3, sku_id: 1, quantity: 3, sku: product.skus[0] },
  ];
  const before = structuredClone(items);
  const result = groupCartItems(items);
  expect(result.map((line) => [line.sku_id, line.quantity])).toEqual([
    [1, 5],
    [3, 1],
  ]);
  expect(items).toEqual(before);
  expect(groupCartItems(items)).toEqual(result);
  expect(groupCartItems([])).toEqual([]);
});
