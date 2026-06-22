import React from "react";
import type { Metadata } from "next";
import TelegramProvider from "@/components/TelegramProvider";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "OmniShop TMA",
  description:
    "Your premium e-commerce shopping experience directly in Telegram.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body suppressHydrationWarning>
        <TelegramProvider>{children}</TelegramProvider>
      </body>
    </html>
  );
}
