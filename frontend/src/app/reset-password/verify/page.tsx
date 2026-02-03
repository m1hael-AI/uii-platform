"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

export default function VerifyCodePage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [code, setCode] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    // Check if email exists in sessionStorage
    useEffect(() => {
        const savedEmail = sessionStorage.getItem("reset_email");
        if (!savedEmail) {
            // No email - redirect to step 1
            router.push("/reset-password");
            return;
        }
        setEmail(savedEmail);
    }, [router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        if (!code || code.length !== 6) {
            setError("Введите 6-значный код");
            setIsLoading(false);
            return;
        }

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            const res = await fetch(`${API_URL}/auth/reset-password/verify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, code }),
            });

            const data = await res.json();

            if (!res.ok) {
                // Handle specific errors
                if (data.detail?.error === "code_not_found") {
                    setError("Неверный код. Проверьте правильность ввода или запросите новый код.");
                } else if (data.detail?.error === "code_expired") {
                    setError("Код истек. Срок действия кода — 10 минут. Запросите новый код.");
                } else if (data.detail?.error === "max_attempts_exceeded") {
                    setError(data.detail.message);
                } else {
                    setError(data.detail?.message || "Ошибка проверки кода");
                }
                setIsLoading(false);
                return;
            }

            // Success - save reset_token and redirect to new password page
            sessionStorage.setItem("reset_token", data.reset_token);
            router.push("/reset-password/new");

        } catch (err: any) {
            console.error(err);
            setError("Ошибка соединения с сервером");
            setIsLoading(false);
        }
    };

    const handleResend = () => {
        router.push("/reset-password");
    };

    if (!email) {
        return null; // Loading or redirecting
    }

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
                    <div className="text-center mb-8">
                        <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <svg className="w-8 h-8 text-[#0088cc]" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.18-.357.295-.6.295-.002 0-.003 0-.005 0l.213-3.054 5.56-5.022c.24-.213-.054-.334-.373-.121l-6.869 4.326-2.96-.924c-.64-.203-.658-.64.135-.954l11.566-4.458c.538-.196 1.006.128.832.941z" />
                            </svg>
                        </div>
                        <h1 className="text-2xl font-medium text-black mb-2">
                            Код отправлен в Telegram
                        </h1>
                        <p className="text-[#7e95b1]">
                            Проверьте сообщения от бота
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                {error}
                            </div>
                        )}

                        <div>
                            <label htmlFor="code" className="block text-sm font-medium text-black mb-2">
                                Введите код из Telegram
                            </label>
                            <input
                                id="code"
                                type="text"
                                value={code}
                                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent outline-none transition-all text-black text-center text-2xl tracking-widest font-mono"
                                placeholder="000000"
                                maxLength={6}
                                disabled={isLoading}
                                autoFocus
                            />
                            <p className="text-xs text-gray-500 mt-2 text-center">
                                Код действителен 10 минут
                            </p>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading || code.length !== 6}
                            className="w-full bg-[#0088cc] text-white py-3 rounded-lg font-medium hover:bg-[#006699] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? "Проверка..." : "Подтвердить"}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <button
                            onClick={handleResend}
                            className="text-sm text-[#FF6B35] hover:underline"
                        >
                            Не пришел код? Отправить снова
                        </button>
                    </div>

                    <div className="mt-8 pt-8 border-t border-gray-100 text-center">
                        <p className="text-sm text-[#7e95b1]">
                            <Link href="/login" className="text-[#FF6B35] hover:underline">
                                Вернуться к входу
                            </Link>
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}
