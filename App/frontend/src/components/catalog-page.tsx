"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { shopApi } from "../api/shop";
import { money, type Product } from "../domain/product";
import { ProductImage } from "./product-page";

export function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [cartCount, setCartCount] = useState<number | null>(null);
  const [cartError, setCartError] = useState(false);
  const controller = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    try {
      const result = await shopApi.products(
        AbortSignal.any([current.signal, AbortSignal.timeout(20000)]),
      );
      if (!Array.isArray(result))
        throw new Error("商品列表数据格式不正确，请重试。");
      if (!current.signal.aborted) setProducts(result);
    } catch (cause) {
      if (!current.signal.aborted)
        setError(
          cause instanceof Error ? cause.message : "商品列表加载失败，请重试。",
        );
    } finally {
      if (!current.signal.aborted) setLoading(false);
    }
  }, []);

  const loadCart = useCallback(async () => {
    try {
      const cart = await shopApi.cart();
      setCartCount(cart.total_item_count);
      setCartError(false);
    } catch {
      setCartError(true);
    }
  }, []);

  useEffect(() => {
    // Starts API requests; state updates are their completion callbacks.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    void loadCart();
    return () => controller.current?.abort();
  }, [load, loadCart]);

  const visible = products.filter((p) =>
    `${p.name} ${p.description ?? ""}`
      .toLocaleLowerCase()
      .includes(query.trim().toLocaleLowerCase()),
  );
  return (
    <>
      <header className="header">
        <Link className="brand" href="/" aria-label="日常首页">
          日常<span>EVERYDAY</span>
          <i>®</i>
        </Link>
        <span className="header-note">简单，刚刚好。</span>
        <Link href="/cart" className="cart" aria-live="polite">
          购物车 <b>{cartCount ?? "—"}</b>
        </Link>
      </header>
      <main className="catalog">
        <section className="catalog-hero">
          <span className="eyebrow">THE EVERYDAY COLLECTION</span>
          <h1>日常衣橱</h1>
          <p>找到喜欢的那一件，让每一天都舒适自在。</p>
          <span className="catalog-hero-mark" aria-hidden="true">
            日常。
          </span>
        </section>
        {cartError && (
          <div className="cart-warning" role="alert">
            购物车数量同步失败，
            <button onClick={() => void loadCart()}>重新同步</button>
          </div>
        )}
        <div className="catalog-toolbar">
          <h2>
            全部商品 <span>{loading ? "" : `${products.length} 件`}</span>
          </h2>
          <label className="catalog-search">
            搜索商品
            <input
              type="search"
              value={query}
              placeholder="搜索你喜欢的商品"
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>
        {loading ? (
          <div className="catalog-loading" role="status">
            正在加载商品列表…
            <div className="catalog-grid">
              {[0, 1, 2].map((n) => (
                <div className="skeleton" key={n} />
              ))}
            </div>
          </div>
        ) : error ? (
          <section className="load-error">
            <h2>商品列表暂时未能加载</h2>
            <p role="alert">{error}</p>
            <button
              className="primary"
              onClick={() => {
                setLoading(true);
                setError("");
                void load();
              }}
            >
              重新加载商品列表
            </button>
          </section>
        ) : visible.length === 0 ? (
          <section className="catalog-empty" role="status">
            <h2>{products.length ? "没有找到相关商品" : "暂时没有商品"}</h2>
            <p>
              {products.length
                ? "试试其他关键词，或查看全部商品。"
                : "商品上架后将在这里展示。"}
            </p>
            {query && (
              <button className="primary" onClick={() => setQuery("")}>
                查看全部商品
              </button>
            )}
          </section>
        ) : (
          <div className="catalog-grid">
            {visible.map((product) => {
              const prices = product.skus
                .filter((s) => s.is_available)
                .map((s) => s.price);
              const lowest = prices.length ? Math.min(...prices) : undefined;
              const available = product.skus.some(
                (s) => s.is_available && s.available_quantity > 0,
              );
              return (
                <article className="product-card" key={product.id}>
                  <Link
                    href={`/products/${product.id}`}
                    aria-label={`查看 ${product.name} 详情`}
                  >
                    <div className="card-image">
                      {product.image ? (
                        <ProductImage src={product.image} alt={product.name} />
                      ) : (
                        <div className="no-image">暂无商品图片</div>
                      )}
                      <span className="card-badge">
                        {available ? "可选规格" : "暂时售罄"}
                      </span>
                      <span className="card-arrow" aria-hidden="true">
                        ↗
                      </span>
                    </div>
                    <div className="card-heading">
                      <h3>{product.name}</h3>
                      <span>
                        {lowest === undefined
                          ? "暂无售价"
                          : `${money(lowest)}${prices.some((p) => p !== lowest) ? " 起" : ""}`}
                      </span>
                    </div>
                    <p>{product.description}</p>
                    <span className="card-detail">查看商品详情 →</span>
                  </Link>
                </article>
              );
            })}
          </div>
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
