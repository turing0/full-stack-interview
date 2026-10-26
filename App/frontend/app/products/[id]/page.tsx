import { Suspense } from "react";
import { notFound } from "next/navigation";
import { ProductPage } from "@/src/components/product-page";

async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const productId = Number(id);
  if (!/^\d+$/.test(id) || !Number.isSafeInteger(productId) || productId < 1)
    notFound();
  return <ProductPage key={productId} productId={productId} />;
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense
      fallback={
        <main className="load-error" role="status">
          正在加载商品详情…
        </main>
      }
    >
      <Detail params={params} />
    </Suspense>
  );
}
