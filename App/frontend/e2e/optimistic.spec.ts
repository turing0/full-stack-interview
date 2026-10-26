import { test, expect } from "@playwright/test";
import { product } from "../src/tests/fixture";
for (const width of [375, 1280]) {
  test(`optimistic count rolls back on stock conflict at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let count = 2;
    let requests = 0;
    await page.route("**/api/products/1", (route) =>
      route.fulfill({ json: product }),
    );
    await page.route("**/api/cart", (route) =>
      route.fulfill({ json: { id: 1, total_item_count: count, items: [] } }),
    );
    await page.route("**/api/cart/items", async (route) => {
      requests++;
      if (requests === 1) {
        await gate;
        await route.fulfill({
          status: 400,
          json: {
            detail: { code: "INSUFFICIENT_STOCK", available_quantity: 1 },
          },
        });
      } else {
        count = 3;
        await route.fulfill({
          status: 201,
          json: {
            id: 1,
            sku_id: 1,
            quantity: 1,
            sku: { ...product.skus[0], available_quantity: 0 },
          },
        });
      }
    });
    await page.goto("/products/1");
    await expect(page.locator(".cart b")).toHaveText("2");
    await page.getByRole("button", { name: "曜石黑", exact: true }).click();
    await page.getByRole("button", { name: "S", exact: true }).click();
    await page.getByLabel("购买数量").fill("2");
    await page.getByRole("button", { name: "加入购物车" }).click();
    await expect(page.locator(".cart b")).toHaveText("4");
    await expect(page.getByText("待确认")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "清除规格选择" }),
    ).toBeDisabled();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    release();
    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      "库存发生变化",
    );
    await expect(page.locator(".cart b")).toHaveText("2");
    await expect(page.getByText("待确认")).toHaveCount(0);
    await expect(page.getByLabel("购买数量")).toHaveValue("1");
    await page.getByRole("button", { name: "加入购物车" }).click();
    await expect(page.locator(".cart b")).toHaveText("3");
    await expect(
      page.getByRole("button", { name: "加入购物车" }),
    ).toBeDisabled();
    await expect(page.getByRole("button", { name: /S\s*售罄/ })).toBeDisabled();
    await expect(page.getByText("该规格已售罄，请选择其他规格")).toBeVisible();
    expect(requests).toBe(2);
  });
}
