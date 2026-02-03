"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { useEffect } from "react";

export default function ExpiredLinkPage() {
    const router = useRouter();

    // Check if user is actually logged in?
    useEffect(() => {
        const token = Cookies.get("token");
        if (token) {
            router.replace("/platform");
        }
    }, [router]);

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
                <div className="w-16 h-16 bg-red-100 text-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Ссылка устарела</h1>
                <p className="text-gray-500 mb-8">
                    Срок действия этой ссылки истек или она уже была использована.
                    В целях безопасности ссылки для входа работают только один раз.
                </p>

                <div className="space-y-3">
                    <Link
                        href="https://t.me/AiUniversityBot"
                        target="_blank"
                        className="block w-full bg-[#FF6B35] text-white py-3 rounded-xl font-medium hover:bg-[#1a5bb0] transition-colors"
                    >
                        Запросить новую в Telegram
                    </Link>

                    <Link
                        href="/login"
                        className="block w-full border border-gray-200 text-gray-600 py-3 rounded-xl font-medium hover:bg-gray-50 transition-colors"
                    >
                        Войти по паролю
                    </Link>
                </div>
            </div>
        </div>
    );
}
