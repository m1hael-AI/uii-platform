"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Cookies from "js-cookie";

function AuthMagicContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [status, setStatus] = useState("Обработка входа...");

    useEffect(() => {
        const magicToken = searchParams.get("token");

        if (!magicToken) {
            router.push("/login");
            return;
        }

        // Exchange Magic Token for JWT
        const exchangeToken = async () => {
            try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
                const res = await fetch(`${API_URL}/auth/magic?token=${magicToken}`);

                if (res.ok) {
                    const data = await res.json();
                    Cookies.set("token", data.access_token, { expires: 7 });
                    router.push("/platform");
                } else {
                    const errorText = await res.text();
                    console.warn("⚠️ Magic Link Failed:", {
                        status: res.status,
                        statusText: res.statusText,
                        response: errorText,
                        token: magicToken?.substring(0, 10) + "...",
                        timestamp: new Date().toISOString()
                    });
                    router.push("/expired-link");
                }
            } catch (e) {
                console.error("Network error", e);
                setStatus("Ошибка сети. Попробуйте обновить.");
            }
        };

        exchangeToken();
    }, [searchParams, router]);

    return (
        <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-black mx-auto mb-4"></div>
            <p className="text-gray-500">{status}</p>
        </div>
    );
}

export default function AuthMagicPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-white">
            <Suspense fallback={<div className="text-center">Загрузка...</div>}>
                <AuthMagicContent />
            </Suspense>
        </div>
    );
}
