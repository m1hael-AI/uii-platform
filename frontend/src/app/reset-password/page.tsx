"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

export default function ResetPasswordPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [canResend, setCanResend] = useState(true);
    const [countdown, setCountdown] = useState(0);

    // Countdown timer for resend button
    useEffect(() => {
        if (countdown > 0) {
            const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
            return () => clearTimeout(timer);
        } else {
            setCanResend(true);
        }
    }, [countdown]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        if (!email) {
            setError("Введите email");
            setIsLoading(false);
            return;
        }

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            const res = await fetch(`${API_URL}/auth/reset-password/request`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email }),
            });

            const data = await res.json();

            if (!res.ok) {
                // Handle specific errors
                if (data.detail?.error === "user_not_found") {
                    setError("Пользователь с таким email не найден. Проверьте правильность ввода.");
                } else if (data.detail?.error === "telegram_not_connected") {
                    setError("Ваш аккаунт не связан с Telegram. Сброс пароля возможен только через Telegram-бота.");
                } else if (data.detail?.error === "too_many_requests") {
                    setError(`Код уже отправлен. Подождите ${data.detail.retry_after} секунд.`);
                    setCountdown(data.detail.retry_after);
                    setCanResend(false);
                } else {
                    setError(data.detail?.message || "Ошибка отправки кода");
                }
                setIsLoading(false);
                return;
            }

            // Success - save email and redirect to verify page
            sessionStorage.setItem("reset_email", email);
            router.push("/reset-password/verify");

        } catch (err: any) {
            console.error(err);
            setError("Ошибка соединения с сервером");
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-white flex flex-col">
            <header className="px-8 py-6">
                <Link href="/login" className="flex items-center gap-3 w-fit">
                    <Image
                        src="/logo.jpg"
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
                        Сброс пароля
                    </h1>
                    <p className="text-[#7e95b1] text-center mb-8">
                        Введите email, код придет в Telegram
                    </p>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                {error}
                            </div>
                        )}

                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-black mb-2">
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent outline-none transition-all text-black"
                                placeholder="your@email.com"
                                disabled={isLoading}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading || !canResend}
                            className="w-full bg-[#0088cc] text-white py-3 rounded-lg font-medium hover:bg-[#006699] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? "Отправка..." : canResend ? "Отправить код в Telegram" : `Подождите ${countdown}с`}
                        </button>
                    </form>

                    <div className="mt-8 pt-8 border-t border-gray-100 text-center">
                        <p className="text-sm text-[#7e95b1]">
                            Вспомнили пароль?{" "}
                            <Link href="/login" className="text-[#FF6B35] hover:underline">
                                Войти
                            </Link>
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}
