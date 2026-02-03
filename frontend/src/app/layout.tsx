import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI University - Образовательная платформа с AI-наставниками",
  description: "Персональные AI-агенты, библиотека вебинаров и умные напоминания для эффективного обучения",
  icons: {
    icon: "/logo.jpg",
    shortcut: "/logo.jpg",
    apple: "/logo.jpg",
  },
};

import PageLogger from "@/components/PageLogger";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body
        className={`antialiased bg-white font-sans`}
      >
        <PageLogger />
        {children}
      </body>
    </html>
  );
}
