"use client";
import { APP_CONFIG } from "@/lib/config";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";

interface HeaderProps {
  isLoggedIn?: boolean;
}

export default function Header({ isLoggedIn = false }: HeaderProps) {
  const pathname = usePathname();

  return (
    <header className="border-b border-gray-200 bg-white sticky top-0 z-50">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <Link href={isLoggedIn ? "/dashboard" : "/"} className="flex items-center gap-3">
            <Image
              src={APP_CONFIG.LOGO_PATH}
              alt="UII Logo"
              width={40}
              height={40}
              className="rounded-lg"
            />
            <span className="text-xl font-bold text-gray-900">
              Университет ИИ
            </span>
          </Link>

          {isLoggedIn ? (
            <nav className="flex items-center gap-6">
              <Link
                href="/dashboard"
                className={`font-medium ${pathname === "/dashboard" ? "text-blue-600" : "text-gray-600 hover:text-gray-900"}`}
              >
                Главная
              </Link>
              <Link
                href="/chat"
                className={`font-medium ${pathname?.startsWith("/chat") ? "text-blue-600" : "text-gray-600 hover:text-gray-900"}`}
              >
                Чаты
              </Link>
              <Link
                href="/webinars"
                className={`font-medium ${pathname?.startsWith("/webinars") ? "text-blue-600" : "text-gray-600 hover:text-gray-900"}`}
              >
                Вебинары
              </Link>
              <Link
                href="/schedule"
                className={`font-medium ${pathname === "/schedule" ? "text-blue-600" : "text-gray-600 hover:text-gray-900"}`}
              >
                Расписание
              </Link>
              <Link
                href="/"
                className="text-gray-500 hover:text-red-600 font-medium"
              >
                Выйти
              </Link>
            </nav>
          ) : (
            <nav className="flex items-center gap-6">
              <Link
                href="/login"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Войти
              </Link>
            </nav>
          )}
        </div>
      </div>
    </header>
  );
}
