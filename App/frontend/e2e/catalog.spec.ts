import { test, expect } from "@playwright/test";
import { product } from "../src/tests/fixture";
for (const width of [375, 1280]) {
  test(`catalog to distinct detail and back at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const second = { ...product, id: 7, name: "Linen Shirt" };
    await page.route("**/api/products", (route) =>
      route.fulfill({ json: [product, second] }),
    );
    await page.route("**/api/products/7", (route) =>
      route.fulfill({ json: second }),
    );
    await page.route("**/api/cart", (route) =>
      route.fulfill({ json: { id: 1, items: [], total_item_count: 2 } }),
    );
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "日常衣橱" })).toBeVisible();
    await expect(
      page.getByRole("link", { name: "查看 Linen Shirt 详情" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/catalog-${width}.png`,
      fullPage: true,
      style: "nextjs-portal { visibility: hidden; }",
    });
    await page.getByRole("link", { name: "查看 Linen Shirt 详情" }).click();
    await expect(page).toHaveURL(/\/products\/7$/);
    await expect(
      page.getByRole("heading", { name: "Linen Shirt" }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Linen Shirt" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "全部商品", exact: true }).click();
    await expect(
      page.getByRole("link", { name: `查看 ${product.name} 详情` }),
    ).toBeVisible();
  });
}
