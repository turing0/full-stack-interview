import { describe, expect, it } from "vitest";
import { clampQuantity, optionStatus, resolveVariant } from "../domain/product";
import { product } from "./fixture";
describe("variant resolution", () => {
  it("matches option IDs independently of order and rejects partial or nonexistent selections", () => {
    expect(resolveVariant(product, { 2: 4, 1: 2 })?.id).toBe(3);
    expect(resolveVariant(product, { 1: 2 })).toBeUndefined();
    expect(resolveVariant(product, { 1: 3, 2: 6 })).toBeUndefined();
    expect(resolveVariant(product, { 1: 4, 2: 2 })).toBeUndefined();
  });
  it("distinguishes unavailable and sold-out options", () => {
    expect(optionStatus(product, { 1: 1 }, 2, 5)).toBe("售罄");
    expect(optionStatus(product, { 1: 3 }, 2, 6)).toBe("不可用");
    expect(optionStatus(product, { 2: 4 }, 1, 3)).toBe("不可用");
  });
  it("clamps stock changes and invalid numbers", () => {
    expect(clampQuantity(8, 3)).toBe(3);
    expect(clampQuantity(-2, 3)).toBe(1);
    expect(clampQuantity(NaN, 3)).toBe(1);
    expect(clampQuantity(2.8, 3)).toBe(2);
    expect(clampQuantity(8, 0)).toBe(0);
  });
});
