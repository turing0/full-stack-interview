import { afterEach, describe, expect, it, vi } from "vitest";
import { shopApi } from "../api/shop";
import { product } from "./fixture";
afterEach(() => vi.unstubAllGlobals());
describe("API contract", () => {
  it("sends only SKU and quantity with an idempotency key", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: 1 }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    await shopApi.add(3, 2, "retry-key");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/cart/items",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ sku_id: 3, quantity: 2 }),
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": "retry-key",
        },
        cache: "no-store",
      }),
    );
  });
  it("accepts both the declared and wrapped product response", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(new Response(JSON.stringify(product)))
        .mockResolvedValueOnce(new Response(JSON.stringify({ product }))),
    );
    expect(await shopApi.product()).toEqual(product);
    expect(await shopApi.product()).toEqual(product);
  });
  it("preserves authoritative stock on conflict", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: { code: "INSUFFICIENT_STOCK", available_quantity: 1 },
          }),
          { status: 400 },
        ),
      ),
    );
    await expect(shopApi.add(1, 3, "key")).rejects.toMatchObject({
      code: "INSUFFICIENT_STOCK",
      stock: 1,
    });
  });
  it("exposes specific validation errors and handles non-JSON server failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              detail: [{ loc: ["body", "quantity"], msg: "must be positive" }],
            }),
            { status: 422 },
          ),
        )
        .mockResolvedValueOnce(new Response("Bad gateway", { status: 502 })),
    );
    await expect(shopApi.add(1, 0, "key")).rejects.toMatchObject({
      code: "VALIDATION_ERROR",
      message: expect.stringContaining("quantity"),
    });
    await expect(shopApi.cart()).rejects.toMatchObject({
      code: "SERVER_ERROR",
    });
  });
});

it("normalizes backend title and requests the selected product ID", async () => {
  const { name, ...rest } = product;
  const wire = { ...rest, id: 7, title: name };
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(new Response(JSON.stringify([wire])))
    .mockResolvedValueOnce(new Response(JSON.stringify(wire)));
  vi.stubGlobal("fetch", fetchMock);
  expect((await shopApi.products())[0].name).toBe(name);
  expect((await shopApi.product(7)).id).toBe(7);
  expect(fetchMock).toHaveBeenLastCalledWith(
    "/api/products/7",
    expect.any(Object),
  );
});
