import { test, expect } from "@playwright/test";
import { product } from "../src/tests/fixture";
for (const width of [375, 1280]) {
  test(`view cart from catalog and detail at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/api/products", (route) =>
      route.fulfill({ json: [product] }),
    );
    await page.route("**/api/products/1", (route) =>
      route.fulfill({ json: product }),
    );
    await page.route("**/api/cart", (route) =>
      route.fulfill({
        json: {
          id: 1,
          total_item_count: 2,
          items: [
            { id: 1, sku_id: 1, quantity: 1, sku: product.skus[0] },
            { id: 2, sku_id: 1, quantity: 1, sku: product.skus[0] },
          ],
        },
      }),
    );
    await page.goto("/");
    await page.getByRole("link", { name: /购物车/ }).click();
    await expect(page).toHaveURL(/\/cart$/);
    await expect(
      page.getByRole("heading", { name: "我的购物车" }),
    ).toBeVisible();
    await expect(page.getByText("数量：2")).toBeVisible();
    await expect(page.getByRole("listitem")).toHaveCount(1);
    await expect(
      page.getByLabel("购物车汇总").getByText("¥258.00"),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/cart-${width}.png`,
      fullPage: true,
      style: "nextjs-portal { visibility: hidden; }",
    });
    await page.getByRole("link", { name: "查看商品详情 →" }).click();
    await expect(page).toHaveURL(/\/products\/1$/);
    await page.getByRole("link", { name: /购物车/ }).click();
    await expect(page.getByText("数量：2")).toBeVisible();
    await page.reload();
    await expect(page.getByText("数量：2")).toBeVisible();
  });
}
