import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CartPage } from "../components/cart-page";
import { shopApi } from "../api/shop";
import { product } from "./fixture";
vi.mock("../api/shop", () => ({
  shopApi: { products: vi.fn(), cart: vi.fn() },
}));
const cart = {
  id: 1,
  total_item_count: 3,
  items: [
    { id: 1, sku_id: 1, quantity: 1, sku: product.skus[0] },
    { id: 3, sku_id: 1, quantity: 1, sku: product.skus[0] },
    { id: 2, sku_id: 3, quantity: 1, sku: product.skus[2] },
  ],
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(shopApi.cart).mockResolvedValue(cart);
  vi.mocked(shopApi.products).mockResolvedValue([product]);
});
it("shows server cart items, resolved specifications and accurate subtotals", async () => {
  render(<CartPage />);
  const items = await screen.findAllByRole("listitem");
  expect(items).toHaveLength(2);
  expect(
    within(items[0]).getByText("颜色：曜石黑 / 尺码：S"),
  ).toBeInTheDocument();
  expect(within(items[0]).getByText("数量：2")).toBeInTheDocument();
  expect(within(items[0]).getByText("¥258.00")).toBeInTheDocument();
  expect(screen.getByText("¥407.00")).toBeInTheDocument();
  expect(
    within(items[0]).getByRole("link", { name: product.name }),
  ).toHaveAttribute("href", "/products/1");
});
it("supports retry after a cart failure and shows the empty-cart action", async () => {
  vi.mocked(shopApi.cart)
    .mockRejectedValueOnce(new Error("购物车请求失败"))
    .mockResolvedValueOnce({ id: 1, total_item_count: 0, items: [] });
  render(<CartPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("购物车请求失败");
  fireEvent.click(screen.getByRole("button", { name: "重新加载购物车" }));
  expect(await screen.findByText("购物车还是空的")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "去逛逛全部商品 →" }),
  ).toHaveAttribute("href", "/");
});
it("keeps quantities and totals visible if catalog enrichment fails", async () => {
  vi.mocked(shopApi.products).mockRejectedValue(new Error("商品请求失败"));
  render(<CartPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "商品名称与规格暂时无法加载",
  );
  expect(screen.getByText("商品 SKU #1")).toBeInTheDocument();
  expect(screen.getByText("¥407.00")).toBeInTheDocument();
  vi.mocked(shopApi.products).mockResolvedValue([product]);
  fireEvent.click(screen.getByRole("button", { name: "重新同步商品信息" }));
  await screen.findAllByRole("link", { name: product.name });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
