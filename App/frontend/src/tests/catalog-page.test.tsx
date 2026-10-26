import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CatalogPage } from "../components/catalog-page";
import { shopApi } from "../api/shop";
import { product } from "./fixture";
vi.mock("../api/shop", () => ({
  shopApi: { products: vi.fn(), cart: vi.fn() },
}));
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(shopApi.cart).mockResolvedValue({
    id: 1,
    items: [],
    total_item_count: 2,
  });
});
it("loads distinct products and links each to its own detail route", async () => {
  vi.mocked(shopApi.products).mockResolvedValue([
    product,
    { ...product, id: 7, name: "Linen Shirt" },
  ]);
  render(<CatalogPage />);
  expect(screen.getByRole("status")).toHaveTextContent("正在加载商品列表");
  expect(
    await screen.findByRole("link", { name: `查看 ${product.name} 详情` }),
  ).toHaveAttribute("href", "/products/1");
  expect(
    screen.getByRole("link", { name: "查看 Linen Shirt 详情" }),
  ).toHaveAttribute("href", "/products/7");
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "Linen" },
  });
  expect(
    screen.queryByRole("link", { name: `查看 ${product.name} 详情` }),
  ).not.toBeInTheDocument();
});
it("can retry failed list requests and displays an empty catalog", async () => {
  vi.mocked(shopApi.products)
    .mockRejectedValueOnce(new Error("列表请求失败"))
    .mockResolvedValueOnce([]);
  render(<CatalogPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("列表请求失败");
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "重新加载商品列表" })),
  );
  expect(screen.getByText("暂时没有商品")).toBeInTheDocument();
});
