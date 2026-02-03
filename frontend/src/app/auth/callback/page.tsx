"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Cookies from "js-cookie";

function AuthCallbackContent() {
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
                const res = await fetch(`${API_URL}/auth/magic?token=${magicToken}`, {
                    method: "POST"
                });

                if (res.ok) {
                    const data = await res.json();
                    Cookies.set("token", data.access_token, { expires: 7 });
                    router.push("/platform");
                } else {
                    // Improved UX: If link is expired but user is already logged in, 
                    // just redirect to platform instead of showing error.
                    if (Cookies.get("token")) {
                        console.log("Magic link invalid/expired, but active session found. Redirecting to platform.");
                        router.push("/platform");
                        return;
                    }

                    console.error("Link invalid", res.status);
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

export default function AuthCallback() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-white">
            <Suspense fallback={<div className="text-center">Загрузка...</div>}>
                <AuthCallbackContent />
            </Suspense>
        </div>
    );
}
