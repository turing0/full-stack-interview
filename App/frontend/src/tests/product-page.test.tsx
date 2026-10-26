import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProductPage } from "../components/product-page";
import { ApiError, shopApi } from "../api/shop";
import { product } from "./fixture";
vi.mock("../api/shop", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/shop")>();
  return {
    ...actual,
    shopApi: { product: vi.fn(), cart: vi.fn(), add: vi.fn() },
  };
});
const choose = (name: string) =>
  fireEvent.click(screen.getByRole("button", { name }));
async function ready() {
  render(<ProductPage />);
  await screen.findByRole("heading", { name: product.name });
}
function selectBlackS() {
  choose("曜石黑");
  choose("S");
}
const added = {
  id: 1,
  sku_id: 1,
  quantity: 1,
  sku: { ...product.skus[0], available_quantity: 9 },
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(shopApi.product).mockResolvedValue(structuredClone(product));
  vi.mocked(shopApi.cart).mockResolvedValue({
    id: 1,
    total_item_count: 0,
    items: [],
  });
  vi.mocked(shopApi.add).mockResolvedValue(added);
});
describe("purchase interactions", () => {
  it("shows loading and recovers from product-load failure without reloading the page", async () => {
    vi.mocked(shopApi.product).mockRejectedValueOnce(
      new ApiError("商品加载失败"),
    );
    render(<ProductPage />);
    expect(screen.getByText("正在加载商品和最新库存")).toBeInTheDocument();
    await screen.findByRole("alert");
    choose("重新加载商品 ↻");
    await screen.findByRole("heading", { name: product.name });
  });
  it("switches price, image and stock together, clamping quantity", async () => {
    await ready();
    selectBlackS();
    fireEvent.change(screen.getByLabelText("购买数量"), {
      target: { value: "8" },
    });
    choose("云朵白");
    expect(screen.getByText("¥149.00")).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute(
      "src",
      product.skus[2].image,
    );
    expect(screen.getByText("现货 · 库存 3 件")).toBeInTheDocument();
    expect(screen.getByLabelText("购买数量")).toHaveValue(3);
  });
  it("disables sold-out, nonexistent and unavailable options without changing selection", async () => {
    await ready();
    expect(screen.getByRole("button", { name: "加入购物车" })).toBeDisabled();
    selectBlackS();
    for (const name of ["M售罄", "L不可用", "雾霾蓝不可用"]) {
      const button = screen.getByRole("button", { name });
      expect(button).toBeDisabled();
      fireEvent.click(button);
      expect(button).toHaveAttribute("aria-pressed", "false");
    }
    expect(screen.getByRole("button", { name: "S" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("现货 · 库存 10 件")).toBeInTheDocument();
    expect(shopApi.add).not.toHaveBeenCalled();
  });
  it("sends one request on rapid duplicate clicks and updates authoritative cart count", async () => {
    let finish!: (value: typeof added) => void;
    vi.mocked(shopApi.add).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    await ready();
    selectBlackS();
    const button = screen.getByRole("button", { name: "加入购物车" });
    act(() => {
      button.click();
      button.click();
    });
    expect(shopApi.add).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("link", { name: /购物车/ })).toHaveTextContent(
      "购物车 1待确认",
    );
    expect(
      screen.getByRole("button", { name: "正在加入购物车…" }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "云朵白" })).toBeDisabled();
    vi.mocked(shopApi.cart).mockResolvedValue({
      id: 1,
      total_item_count: 7,
      items: [],
    });
    await act(async () => finish(added));
    expect(screen.getByText("已成功加入购物车，共 1 件。")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.queryByText("待确认")).not.toBeInTheDocument();
  });
  it("updates stock after a conflict and permits a corrected purchase", async () => {
    vi.mocked(shopApi.add).mockRejectedValueOnce(
      new ApiError("库存发生变化", "INSUFFICIENT_STOCK", 1),
    );
    await ready();
    selectBlackS();
    fireEvent.change(screen.getByLabelText("购买数量"), {
      target: { value: "3" },
    });
    choose("加入购物车");
    await screen.findByRole("alert");
    expect(screen.getByLabelText("购买数量")).toHaveValue(1);
    expect(screen.getByText("现货 · 库存 1 件")).toBeInTheDocument();
    choose("加入购物车");
    await waitFor(() => expect(shopApi.add).toHaveBeenCalledTimes(2));
    expect(vi.mocked(shopApi.add).mock.calls[1][1]).toBe(1);
  });
  it("reuses the idempotency key after an ambiguous network failure", async () => {
    vi.mocked(shopApi.add).mockRejectedValueOnce(
      new ApiError("网络连接失败，请重试"),
    );
    await ready();
    selectBlackS();
    choose("加入购物车");
    expect(await screen.findByRole("alert")).toHaveTextContent("网络连接失败");
    choose("加入购物车");
    await screen.findByText("已成功加入购物车，共 1 件。");
    const calls = vi.mocked(shopApi.add).mock.calls;
    expect(calls[0][2]).toBe(calls[1][2]);
  });
  it("recovers cart sync failure separately without resubmitting the purchase", async () => {
    await ready();
    selectBlackS();
    vi.mocked(shopApi.cart).mockRejectedValueOnce(new ApiError("失败"));
    choose("加入购物车");
    await screen.findByText("重新同步");
    choose("重新同步");
    await waitFor(() =>
      expect(screen.queryByText("重新同步")).not.toBeInTheDocument(),
    );
    expect(shopApi.add).toHaveBeenCalledTimes(1);
  });
});

it("lets users clear mutually exclusive selections to reach another valid SKU", async () => {
  const sparse = structuredClone(product);
  sparse.skus[2].option_value_ids = [2, 5];
  vi.mocked(shopApi.product).mockResolvedValue(sparse);
  await ready();
  // M remains available before choosing a color because White / M is purchasable.
  expect(screen.getByRole("button", { name: "M" })).toBeEnabled();
  selectBlackS();
  expect(screen.getByRole("button", { name: "云朵白不可用" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "M售罄" })).toBeDisabled();
  choose("清除规格选择");
  expect(screen.getByRole("button", { name: "加入购物车" })).toBeDisabled();
  choose("M");
  choose("云朵白");
  expect(screen.getByRole("button", { name: "加入购物车" })).toBeEnabled();
  expect(screen.getByText("¥149.00")).toBeInTheDocument();
});

it.each([
  ["INSUFFICIENT_STOCK", "该规格已售罄，请选择其他规格", "S售罄"],
  ["INVALID_SKU", "该规格组合不可用，请选择其他规格", "S不可用"],
])(
  "disables a selected SKU after server response %s",
  async (code, status, option) => {
    vi.mocked(shopApi.add).mockRejectedValueOnce(
      new ApiError("规格库存已变化", code, 0),
    );
    await ready();
    selectBlackS();
    choose("加入购物车");
    await screen.findByRole("alert");
    expect(screen.getByText(status)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: option })).toBeDisabled();
    expect(screen.getByRole("button", { name: "加入购物车" })).toBeDisabled();
    expect(screen.getByLabelText("购买数量")).toHaveValue(0);
    expect(screen.getByRole("button", { name: "清除规格选择" })).toBeEnabled();
  },
);

it.each([
  "NETWORK_ERROR",
  "SERVER_ERROR",
  "VALIDATION_ERROR",
  "INSUFFICIENT_STOCK",
])("rolls back the optimistic cart count on %s", async (code) => {
  vi.mocked(shopApi.cart).mockResolvedValue({
    id: 1,
    total_item_count: 4,
    items: [],
  });
  let reject!: (error: ApiError) => void;
  vi.mocked(shopApi.add).mockImplementation(
    () =>
      new Promise((_, fail) => {
        reject = fail;
      }),
  );
  await ready();
  selectBlackS();
  fireEvent.change(screen.getByLabelText("购买数量"), {
    target: { value: "3" },
  });
  choose("加入购物车");
  expect(screen.getByRole("link", { name: /购物车/ })).toHaveTextContent(
    "购物车 7待确认",
  );
  expect(screen.getByText("现货 · 库存 10 件")).toBeInTheDocument();
  await act(async () => reject(new ApiError("请求失败，请重试", code, 1)));
  expect(screen.getByRole("link", { name: /购物车/ })).toHaveTextContent(
    "购物车 4",
  );
  expect(screen.queryByText("待确认")).not.toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("请求失败");
  expect(screen.getByRole("button", { name: "加入购物车" })).toBeEnabled();
});

it("does not invent an optimistic total when the initial count is unknown", async () => {
  vi.mocked(shopApi.cart).mockRejectedValue(new ApiError("同步失败"));
  let finish!: (value: typeof added) => void;
  vi.mocked(shopApi.add).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await ready();
  selectBlackS();
  choose("加入购物车");
  expect(screen.getByRole("link", { name: /购物车/ })).toHaveTextContent("—");
  expect(screen.queryByText("待确认")).not.toBeInTheDocument();
  vi.mocked(shopApi.cart).mockResolvedValue({
    id: 1,
    total_item_count: 5,
    items: [],
  });
  await act(async () => finish(added));
  expect(screen.getByRole("link", { name: /购物车/ })).toHaveTextContent(
    "购物车 5",
  );
});
