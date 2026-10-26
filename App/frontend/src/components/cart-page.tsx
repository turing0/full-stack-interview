"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { shopApi } from "../api/shop";
import { groupCartItems } from "../domain/cart";
import { label, money, type Cart, type Product } from "../domain/product";
import { ProductImage } from "./product-page";

export function CartPage() {
  const [cart, setCart] = useState<Cart>();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [catalogError, setCatalogError] = useState(false);
  const controller = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    const signal = AbortSignal.any([
      current.signal,
      AbortSignal.timeout(20000),
    ]);
    const [cartResult, catalogResult] = await Promise.allSettled([
      shopApi.cart(signal),
      shopApi.products(signal),
    ]);
    if (current.signal.aborted) return;
    if (cartResult.status === "fulfilled") {
      setCart(cartResult.value);
      setError("");
    } else {
      setError(
        cartResult.reason instanceof Error
          ? cartResult.reason.message
          : "购物车加载失败，请重试。",
      );
    }
    setProducts(
      catalogResult.status === "fulfilled" ? catalogResult.value : [],
    );
    setCatalogError(catalogResult.status === "rejected");
    setLoading(false);
  }, []);

  useEffect(() => {
    // Starts external requests; state updates follow their completion.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    return () => controller.current?.abort();
  }, [load]);

  function refresh() {
    setLoading(true);
    setError("");
    void load();
  }
  // Prices are currently provided by the API's SKU, not a checkout quote.
  const lines = groupCartItems(cart?.items ?? []);
  const totalCents =
    lines.reduce(
      (sum, item) => sum + Math.round(item.sku.price * 100) * item.quantity,
      0,
    ) ?? 0;

  return (
    <>
      <header className="header">
        <Link className="brand" href="/" aria-label="日常首页">
          日常<span>EVERYDAY</span>
          <i>®</i>
        </Link>
        <span className="header-note">简单，刚刚好。</span>
        <Link className="cart" href="/cart" aria-current="page">
          购物车{" "}
          <b>{loading || error ? "—" : (cart?.total_item_count ?? "—")}</b>
        </Link>
      </header>
      <main className="cart-page">
        <nav className="breadcrumb" aria-label="面包屑">
          <Link href="/">全部商品</Link>
          <span>/</span>购物车
        </nav>
        <div className="cart-title">
          <div>
            <span className="eyebrow">YOUR EVERYDAY PICKS</span>
            <h1>我的购物车</h1>
          </div>
          <button className="refresh-cart" disabled={loading} onClick={refresh}>
            {loading ? "正在同步…" : "刷新购物车 ↻"}
          </button>
        </div>
        {loading ? (
          <section className="cart-empty" role="status">
            正在加载购物车…
          </section>
        ) : error ? (
          <section className="cart-empty">
            <h2>购物车暂时未能加载</h2>
            <p role="alert">{error}</p>
            <button className="primary" onClick={refresh}>
              重新加载购物车
            </button>
          </section>
        ) : !cart?.items.length ? (
          <section className="cart-empty">
            <span className="eyebrow">A LITTLE ROOM FOR SOMETHING GOOD</span>
            <h2>购物车还是空的</h2>
            <p>去挑一件喜欢的商品，开启舒适日常。</p>
            <Link className="primary" href="/">
              去逛逛全部商品 →
            </Link>
          </section>
        ) : (
          <>
            {catalogError && (
              <div className="cart-warning" role="alert">
                商品名称与规格暂时无法加载，数量和金额仍来自购物车。
                <button onClick={refresh}>重新同步商品信息</button>
              </div>
            )}
            <div className="cart-layout">
              <ul className="cart-items" aria-label="购物车商品">
                {lines.map((item) => {
                  const product = products.find((p) =>
                    p.skus.some((s) => s.id === item.sku_id),
                  );
                  const name = product?.name ?? `商品 SKU #${item.sku_id}`;
                  const variants = product?.dimensions
                    .map((d) => {
                      const value = d.values.find((v) =>
                        item.sku.option_value_ids.includes(v.id),
                      );
                      return `${label(d.name)}：${value ? label(value.value) : "未提供"}`;
                    })
                    .join(" / ");
                  const image = item.sku.image ?? product?.image;
                  return (
                    <li className="cart-item" key={item.sku_id}>
                      <div className="cart-item-image">
                        {image ? (
                          <ProductImage src={image} alt={name} />
                        ) : (
                          <div className="no-image">暂无图片</div>
                        )}
                      </div>
                      <div className="cart-item-info">
                        <h2>
                          {product ? (
                            <Link href={`/products/${product.id}`}>{name}</Link>
                          ) : (
                            name
                          )}
                        </h2>
                        <p>{variants ?? `规格编号：${item.sku_id}`}</p>
                        <p>单价 {money(item.sku.price)}</p>
                        <span className="cart-item-quantity">
                          数量：{item.quantity}
                        </span>
                        {product && (
                          <Link
                            className="card-detail"
                            href={`/products/${product.id}`}
                          >
                            查看商品详情 →
                          </Link>
                        )}
                      </div>
                      <div className="cart-item-subtotal">
                        <span>小计</span>
                        <strong>
                          {money(
                            (Math.round(item.sku.price * 100) * item.quantity) /
                              100,
                          )}
                        </strong>
                      </div>
                    </li>
                  );
                })}
              </ul>
              <aside className="cart-summary" aria-label="购物车汇总">
                <h2>购物车汇总</h2>
                <div>
                  <span>商品总数量</span>
                  <b>{cart.total_item_count} 件</b>
                </div>
                <div className="cart-total">
                  <span>商品合计</span>
                  <strong>{money(totalCents / 100)}</strong>
                </div>
                <p>按当前商品价格计算，不含运费。</p>
                <Link className="primary" href="/">
                  继续选购 →
                </Link>
              </aside>
            </div>
          </>
        )}
      </main>
      <footer>
        <Link className="brand" href="/">
          日常<span>EVERYDAY</span>
        </Link>
        <span>为每一个平凡而美好的日子。</span>
        <small>© EVERYDAY</small>
      </footer>
    </>
  );
}
