import { test, expect } from "@playwright/test";
import { product } from "../src/tests/fixture";
for (const width of [375, 1280]) {
  test(`purchase flow and layout at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    let count = 0;
    let requests = 0;
    await page.route("**/api/products/1", (route) =>
      route.fulfill({ json: product }),
    );
    await page.route("**/api/cart", (route) =>
      route.fulfill({ json: { id: 1, items: [], total_item_count: count } }),
    );
    await page.route("**/api/cart/items", async (route) => {
      requests++;
      await new Promise((resolve) => setTimeout(resolve, 250));
      count++;
      await route.fulfill({
        status: 201,
        json: {
          id: 1,
          sku_id: 1,
          quantity: 1,
          sku: { ...product.skus[0], available_quantity: 9 },
        },
      });
    });
    await page.goto("/products/1");
    await expect(
      page.getByRole("heading", { name: product.name }),
    ).toBeVisible();
    await page.getByRole("button", { name: "曜石黑", exact: true }).click();
    await page.getByRole("button", { name: "S", exact: true }).click();
    const image = page.getByRole("img", { name: /Everyday Cotton Tee/ });
    await expect(image).toHaveJSProperty("complete", true);
    expect(
      await image.evaluate((img: HTMLImageElement) => img.naturalWidth),
    ).toBeGreaterThan(0);
    await page.getByLabel("购买数量").fill("8");
    await page.getByRole("button", { name: "云朵白", exact: true }).click();
    await expect(page.getByLabel("购买数量")).toHaveValue("3");
    await expect(page.getByText("现货 · 库存 3 件")).toBeVisible();
    await expect(image).toHaveAttribute("src", product.skus[2].image!);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/product-${width}.png`,
      fullPage: true,
      style: "nextjs-portal { visibility: hidden; }",
    });
    await page.getByRole("button", { name: "曜石黑", exact: true }).click();
    await expect(page.getByRole("button", { name: /M\s*售罄/ })).toBeDisabled();
    await expect(
      page.getByRole("button", { name: /L\s*不可用/ }),
    ).toBeDisabled();
    await page.getByRole("button", { name: "清除规格选择" }).click();
    await expect(
      page.getByRole("button", { name: "加入购物车" }),
    ).toBeDisabled();
    await page.getByRole("button", { name: "曜石黑", exact: true }).click();
    await page.getByRole("button", { name: "S", exact: true }).click();
    await page.getByLabel("购买数量").fill("1");
    const buy = page.getByRole("button", { name: "加入购物车" });
    await buy.focus();
    await expect(buy).toBeFocused();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Enter");
    await expect(page.getByText("已成功加入购物车，共 1 件。")).toBeVisible();
    await expect(page.locator(".cart b")).toHaveText("1");
    expect(requests).toBe(1);
  });
}
