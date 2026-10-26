import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "日常 / EVERYDAY — 精选基础款",
  description: "选一件喜欢的日常。查看商品规格、实时库存并加入购物车。",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
