"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, shopApi } from "../api/shop";
import {
  clampQuantity,
  label,
  money,
  optionStatus,
  resolveVariant,
  type Product,
  type Selection,
  type SKU,
} from "../domain/product";

export function ProductPage({ productId = 1 }: { productId?: number }) {
  const [product, setProduct] = useState<Product>();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [selection, setSelection] = useState<Selection>({});
  const [requestedQuantity, setQuantity] = useState(1);
  const [pending, setPending] = useState(false);
  const [feedback, setFeedback] = useState<{ error: boolean; text: string }>({
    error: false,
    text: "",
  });
  const [cartCount, setCartCount] = useState<number | null>(null);
  // Keep the confirmed count separate so rollback never subtracts from newer data.
  const [optimisticQuantity, setOptimisticQuantity] = useState(0);
  const [cartError, setCartError] = useState("");
  const [cartLoading, setCartLoading] = useState(true);
  const inFlight = useRef(false);
  const cartVersion = useRef(0);
  const intents = useRef(new Map<string, string>());
  const loadController = useRef<AbortController | null>(null);

  const refreshCart = useCallback(async () => {
    const version = ++cartVersion.current;
    try {
      const cart = await shopApi.cart();
      if (version === cartVersion.current) {
        setCartCount(cart.total_item_count);
        setOptimisticQuantity(0);
        setCartError("");
      }
    } catch {
      if (version === cartVersion.current) {
        setCartCount(null);
        setOptimisticQuantity(0);
        setCartError("购物车数量同步失败");
      }
    } finally {
      if (version === cartVersion.current) setCartLoading(false);
    }
  }, []);

  const load = useCallback(async () => {
    loadController.current?.abort();
    const controller = new AbortController();
    loadController.current = controller;
    try {
      const result = await shopApi.product(
        productId,
        AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]),
      );
      if (!controller.signal.aborted) setProduct(result);
    } catch (error) {
      if (!controller.signal.aborted)
        setLoadError(
          error instanceof Error ? error.message : "商品加载失败，请重试。",
        );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    // Starts external requests; state updates occur in their completion handlers.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    void refreshCart();
    return () => loadController.current?.abort();
  }, [load, refreshCart]);

  const sku = product ? resolveVariant(product, selection) : undefined;
  const complete = product?.dimensions.every(
    (d) => selection[d.id] !== undefined,
  );
  const stock = sku?.is_available ? sku.available_quantity : 0;
  const quantity = clampQuantity(requestedQuantity, stock);
  const canBuy = !!sku?.is_available && stock > 0;
  const status = !complete
    ? "请选择颜色和尺码，查看价格与库存"
    : !sku?.is_available
      ? "该规格组合不可用，请选择其他规格"
      : stock === 0
        ? "该规格已售罄，请选择其他规格"
        : `现货 · 库存 ${stock} 件`;
  const patchSku = (id: number, patch: Partial<SKU>) =>
    setProduct((current) =>
      current
        ? {
            ...current,
            skus: current.skus.map((s) =>
              s.id === id ? { ...s, ...patch } : s,
            ),
          }
        : current,
    );

  function select(dimensionId: number, valueId: number) {
    if (
      !product ||
      inFlight.current ||
      optionStatus(product, selection, dimensionId, valueId)
    )
      return;
    const next = { ...selection, [dimensionId]: valueId };
    const nextSku = product && resolveVariant(product, next);
    setSelection(next);
    setQuantity(
      clampQuantity(quantity || 1, nextSku?.available_quantity ?? 0) || 1,
    );
    setFeedback({ error: false, text: "" });
  }

  async function add() {
    if (inFlight.current || !sku || !canBuy || quantity < 1) return;
    inFlight.current = true;
    setPending(true);
    // Without a confirmed baseline, keep the unknown count instead of inventing one.
    setOptimisticQuantity(cartCount === null ? 0 : quantity);
    setFeedback({ error: false, text: "" });
    const signature = `${sku.id}:${quantity}`;
    const key = intents.current.get(signature) ?? crypto.randomUUID();
    intents.current.set(signature, key);
    try {
      const item = await shopApi.add(sku.id, quantity, key);
      intents.current.delete(signature);
      patchSku(sku.id, item.sku);
      setQuantity(clampQuantity(quantity, item.sku.available_quantity) || 1);
      setFeedback({
        error: false,
        text: `已成功加入购物车，共 ${item.quantity} 件。`,
      });
      setCartLoading(true);
      await refreshCart();
    } catch (error) {
      setOptimisticQuantity(0);
      if (error instanceof ApiError) {
        if (
          ["INSUFFICIENT_STOCK", "INVALID_SKU", "VALIDATION_ERROR"].includes(
            error.code,
          )
        )
          intents.current.delete(signature);
        if (
          error.code === "INSUFFICIENT_STOCK" &&
          typeof error.stock === "number"
        ) {
          patchSku(sku.id, { available_quantity: Math.max(0, error.stock) });
          setQuantity(clampQuantity(quantity, error.stock) || 1);
        }
        if (error.code === "INVALID_SKU")
          patchSku(sku.id, { is_available: false });
      }
      setFeedback({
        error: true,
        text: error instanceof Error ? error.message : "添加失败，请重试。",
      });
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }

  return (
    <>
      <header className="header">
        <Link className="brand" href="/" aria-label="日常首页">
          日常<span>EVERYDAY</span>
          <i>®</i>
        </Link>
        <span className="header-note">简单，刚刚好。</span>
        <Link href="/cart" className="cart" aria-live="polite">
          <Bag />
          购物车{" "}
          <b>{cartCount === null ? "—" : cartCount + optimisticQuantity}</b>
          {optimisticQuantity > 0 && (
            <small className="cart-pending">待确认</small>
          )}
        </Link>
      </header>
      <main>
        <div className="breadcrumb">
          <Link href="/">全部商品</Link> <span>/</span>{" "}
          {product?.name ?? "商品详情"}
        </div>
        {cartError && (
          <div className="cart-warning" role="alert">
            {cartError}，
            <button
              disabled={cartLoading || pending}
              onClick={() => {
                setCartLoading(true);
                void refreshCart();
              }}
            >
              {cartLoading ? "同步中…" : "重新同步"}
            </button>
          </div>
        )}
        {loading ? (
          <section className="loading" role="status">
            <div className="skeleton" />
            <div>
              <span className="eyebrow">EVERYDAY ESSENTIALS</span>
              <h1>正在准备你的日常…</h1>
              <p>正在加载商品和最新库存</p>
            </div>
          </section>
        ) : loadError || !product ? (
          <section className="load-error">
            <span className="eyebrow">LET’S TRY AGAIN</span>
            <h1>商品暂时未能加载</h1>
            <p role="alert">{loadError}</p>
            <button
              className="primary"
              onClick={() => {
                setLoading(true);
                setLoadError("");
                void load();
              }}
            >
              重新加载商品 ↻
            </button>
          </section>
        ) : (
          <>
            <section className="product-layout">
              <div className="gallery">
                <div className="image-wrap">
                  <span className="image-tag">THE EVERYDAY EDIT / 01</span>
                  {(complete ? sku?.image : product.image) ? (
                    <ProductImage
                      src={(complete ? sku?.image : product.image)!}
                      alt={`${product.name}${sku ? ` · ${product.dimensions.map((d) => label(d.values.find((v) => v.id === selection[d.id])?.value ?? "")).join(" / ")}` : ""}`}
                    />
                  ) : (
                    <div className="no-image">
                      {complete ? "请选择可用规格" : "暂无商品图片"}
                    </div>
                  )}
                  <span className="image-caption">
                    简单的设计，长久的陪伴。
                  </span>
                </div>
                <div className="gallery-footer">
                  <span>01 — 日常基础系列</span>
                  <span>细节，让日常更好 ↗</span>
                </div>
              </div>
              <div className="product-info">
                <span className="eyebrow">LESS, BUT BETTER.</span>
                <h1>{product.name}</h1>
                <p className="description">{product.description}</p>
                <div className="price" aria-live="polite">
                  {sku ? money(sku.price) : "选择规格查看价格"}
                  <span>人民币 / CNY</span>
                </div>
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void add();
                  }}
                >
                  <fieldset className="variants" disabled={pending}>
                    {product.dimensions.map((d) => (
                      <fieldset className="dimension" key={d.id}>
                        <legend>
                          {label(d.name)}
                          <span>
                            {label(
                              d.values.find((v) => v.id === selection[d.id])
                                ?.value ?? "请选择",
                            )}
                          </span>
                        </legend>
                        <div className="options">
                          {d.values.map((v) => {
                            const unavailable = optionStatus(
                              product,
                              selection,
                              d.id,
                              v.id,
                            );
                            return (
                              <button
                                type="button"
                                className={`option ${selection[d.id] === v.id ? "selected" : ""} ${unavailable ? "unavailable" : ""}`}
                                aria-pressed={selection[d.id] === v.id}
                                disabled={pending || Boolean(unavailable)}
                                key={v.id}
                                onClick={() => select(d.id, v.id)}
                              >
                                {["Black", "White", "Blue"].includes(
                                  v.value,
                                ) && (
                                  <span
                                    className={`swatch ${v.value.toLowerCase()}`}
                                  />
                                )}
                                {label(v.value)}
                                {unavailable && <small>{unavailable}</small>}
                              </button>
                            );
                          })}
                        </div>
                      </fieldset>
                    ))}
                    {Object.keys(selection).length > 0 && (
                      <button
                        type="button"
                        className="reset-selection"
                        onClick={() => {
                          if (inFlight.current) return;
                          setSelection({});
                          setQuantity(1);
                          setFeedback({
                            error: false,
                            text: "已清除规格，请重新选择颜色和尺码。",
                          });
                        }}
                      >
                        清除规格选择
                      </button>
                    )}
                  </fieldset>
                  <div
                    className={`stock ${canBuy ? "available" : ""}`}
                    role="status"
                  >
                    <span aria-hidden="true">{canBuy ? "●" : "○"}</span>{" "}
                    {status}
                  </div>
                  <div className="quantity-row">
                    <label htmlFor="quantity">购买数量</label>
                    <div className="stepper">
                      <button
                        type="button"
                        aria-label="减少数量"
                        disabled={pending || !canBuy || quantity <= 1}
                        onClick={() => setQuantity(quantity - 1)}
                      >
                        −
                      </button>
                      <input
                        id="quantity"
                        type="number"
                        inputMode="numeric"
                        min={canBuy ? 1 : 0}
                        max={stock}
                        value={quantity}
                        disabled={pending || !canBuy}
                        onChange={(e) =>
                          setQuantity(
                            clampQuantity(e.target.valueAsNumber, stock),
                          )
                        }
                      />
                      <button
                        type="button"
                        aria-label="增加数量"
                        disabled={pending || !canBuy || quantity >= stock}
                        onClick={() => setQuantity(quantity + 1)}
                      >
                        +
                      </button>
                    </div>
                  </div>
                  <button
                    className="primary add-button"
                    disabled={pending || !canBuy}
                    type="submit"
                    aria-busy={pending}
                  >
                    <Bag />
                    {pending ? "正在加入购物车…" : "加入购物车"}
                    <span aria-hidden="true">↗</span>
                  </button>
                  <div
                    className={`feedback ${feedback.error ? "error" : "success"}`}
                    role={feedback.error ? "alert" : "status"}
                    aria-atomic="true"
                  >
                    {feedback.text}
                  </div>
                </form>
                <div className="purchase-note">
                  <span>✓ 按最新库存确认订单</span>
                  <span>✓ 安心选购</span>
                </div>
                <details>
                  <summary>
                    商品与保养 <span>+</span>
                  </summary>
                  <p>{product.description}</p>
                  <p>请以商品实际水洗标上的洗护说明为准。</p>
                </details>
                <details>
                  <summary>
                    购买须知 <span>+</span>
                  </summary>
                  <p>
                    价格和库存随所选规格更新。库存以提交时服务端的确认为准；如库存有变化，可调整数量后重新添加。
                  </p>
                </details>
              </div>
            </section>
            <section className="editorial">
              <span className="eyebrow">THE BEAUTY OF EVERYDAY</span>
              <h2>
                穿得舒服，
                <br />
                就很有风格。
              </h2>
              <p>
                从一件简单的 T 恤开始，
                <br />
                留更多空间，给生活本来的样子。
              </p>
              <span className="editorial-mark" aria-hidden="true">
                日常。
              </span>
            </section>
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

export function ProductImage({ src, alt }: { src: string; alt: string }) {
  const [failedSrc, setFailedSrc] = useState<string>();
  if (failedSrc === src)
    return (
      <div className="no-image" role="img" aria-label={alt}>
        商品图片暂时无法显示
      </div>
    );
  // API images may be SVGs or external URLs; native images do not require an optimization allowlist.
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      key={src}
      className="product-image"
      src={src}
      alt={alt}
      onError={() => setFailedSrc(src)}
    />
  );
}
function Bag() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path d="M5 7h14l1 14H4L5 7Z" />
      <path d="M8 8V6a4 4 0 0 1 8 0v2" />
    </svg>
  );
}
