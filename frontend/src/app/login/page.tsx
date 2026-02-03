"use client";
import { APP_CONFIG } from "@/lib/config";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";

import Cookies from "js-cookie";

export default function LoginPage() {
  const router = useRouter();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Check if already logged in
  useEffect(() => {
    const token = Cookies.get("token");
    if (token) {
      // User already logged in, redirect to platform
      router.push("/platform");
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    if (!login || !password) {
      setError("Заполните все поля");
      setIsLoading(false);
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

      // OAuth2 Password Grant expects form-urlencoded
      const formData = new URLSearchParams();
      formData.append("username", login); // mapping login(email) to username
      formData.append("password", password);

      const res = await fetch(`${API_URL}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Ошибка входа. Проверьте логин и пароль.");
      }

      const data = await res.json();
      // Save token
      Cookies.set("token", data.access_token, { expires: 1 });

      // Redirect
      router.push("/platform");

    } catch (err: any) {
      console.error(err);
      setError(err.message || "Ошибка соединения с сервером");
      setIsLoading(false);
    }
  };

  const botUsername = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME || "YOUR_BOT";
  const botLink = `https://t.me/${botUsername}?start=login`;

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <header className="px-8 py-6">
        <Link href="/" className="flex items-center gap-3 w-fit">
          <Image
            src={APP_CONFIG.LOGO_PATH}
            alt="UII"
            width={32}
            height={32}
            className="rounded"
          />
          <span className="text-sm font-medium text-[#7e95b1] tracking-wide uppercase">
            University of Artificial Intelligence
          </span>
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-8">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-medium text-black mb-2 text-center">
            Вход в платформу
          </h1>
          <p className="text-[#7e95b1] text-center mb-8">
            Войдите через Telegram или Email
          </p>

          {/* Telegram Login Button (Magic Link) */}
          <div className="flex justify-center mb-6">
            <a
              href={botLink}
              target="_blank"
              rel="noopener noreferrer"
              className="group relative flex items-center justify-center gap-3 w-full bg-[#2AABEE] hover:bg-[#229ED9] text-white py-3 px-4 rounded-xl font-medium transition-all shadow-md hover:shadow-lg hover:-translate-y-0.5"
            >
              {/* Telegram Icon */}
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 11.944 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
              </svg>
              <span>Войти через Telegram</span>
            </a>
          </div>

          <div className="flex items-center gap-4 mb-6">
            <div className="h-px bg-gray-200 flex-1"></div>
            <span className="text-gray-400 text-sm">или</span>
            <div className="h-px bg-gray-200 flex-1"></div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="login" className="block text-sm font-medium text-black mb-2">
                Логин (Email)
              </label>
              <input
                id="login"
                type="text"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent outline-none transition-all text-black"
                placeholder="Введите Email"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-black mb-2">
                Пароль
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent outline-none transition-all text-black"
                placeholder="Введите пароль"
              />
            </div>

            <div className="text-right">
              <Link href="/reset-password" className="text-sm text-[#FF6B35] hover:underline">
                Забыли пароль?
              </Link>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-black text-white py-3 rounded-lg font-medium hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Вход..." : "Войти"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
