"use client";
import { APP_CONFIG } from "@/lib/config";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

export default function NewPasswordPage() {
    const router = useRouter();
    const [resetToken, setResetToken] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [showSuccess, setShowSuccess] = useState(false);

    // Check if reset_token exists in sessionStorage
    useEffect(() => {
        const token = sessionStorage.getItem("reset_token");
        if (!token) {
            // No token - redirect to step 1
            router.push("/reset-password");
            return;
        }
        setResetToken(token);
    }, [router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        // Validation
        if (!newPassword || !confirmPassword) {
            setError("Заполните все поля");
            setIsLoading(false);
            return;
        }

        if (newPassword.length < 6) {
            setError("Пароль должен быть не менее 6 символов");
            setIsLoading(false);
            return;
        }

        if (newPassword !== confirmPassword) {
            setError("Пароли не совпадают");
            setIsLoading(false);
            return;
        }

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            const res = await fetch(`${API_URL}/auth/reset-password/confirm`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reset_token: resetToken,
                    new_password: newPassword
                }),
            });

            const data = await res.json();

            if (!res.ok) {
                // Handle specific errors
                if (data.detail?.error === "invalid_token") {
                    setError("Недействительный или истекший токен. Пройдите процедуру сброса заново.");
                    setTimeout(() => router.push("/reset-password"), 3000);
                } else if (data.detail?.error === "token_already_used") {
                    setError("Этот код уже был использован. Запросите новый код для повторного сброса пароля.");
                    setTimeout(() => router.push("/reset-password"), 3000);
                } else if (data.detail?.error === "token_expired") {
                    setError("Время действия кода истекло. Запросите новый код.");
                    setTimeout(() => router.push("/reset-password"), 3000);
                } else {
                    setError(data.detail?.message || "Ошибка установки пароля");
                }
                setIsLoading(false);
                return;
            }

            // Success!
            sessionStorage.removeItem("reset_email");
            sessionStorage.removeItem("reset_token");
            setShowSuccess(true);

            // Redirect to login after 3 seconds
            setTimeout(() => {
                router.push("/login");
            }, 3000);

        } catch (err: any) {
            console.error(err);
            setError("Ошибка соединения с сервером");
            setIsLoading(false);
        }
    };

    if (!resetToken) {
        return null; // Loading or redirecting
    }

    if (showSuccess) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center px-8">
                <div className="text-center">
                    <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                        <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h1 className="text-3xl font-semibold text-black mb-3">
                        Пароль успешно изменен!
                    </h1>
                    <p className="text-gray-600 mb-6">
                        Сейчас вы будете перенаправлены на страницу входа
                    </p>
                    <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                        <div className="w-2 h-2 bg-[#0088cc] rounded-full animate-pulse"></div>
                        Перенаправление...
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-white flex flex-col">
            <header className="px-8 py-6">
                <Link href="/login" className="flex items-center gap-3 w-fit">
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
                        Придумайте новый пароль
                    </h1>
                    <p className="text-[#7e95b1] text-center mb-8">
                        Минимум 6 символов
                    </p>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                {error}
                            </div>
                        )}

                        <div>
                            <label htmlFor="newPassword" className="block text-sm font-medium text-black mb-2">
                                Новый пароль
                            </label>
                            <input
                                id="newPassword"
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent outline-none transition-all text-black"
                                placeholder="Введите новый пароль"
                                disabled={isLoading}
                                autoFocus
                            />
                        </div>

                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-black mb-2">
                                Повторите пароль
                            </label>
                            <input
                                id="confirmPassword"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent outline-none transition-all text-black"
                                placeholder="Повторите пароль"
                                disabled={isLoading}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full bg-[#0088cc] text-white py-3 rounded-lg font-medium hover:bg-[#006699] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? "Сохранение..." : "Сохранить пароль"}
                        </button>
                    </form>

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
