"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import "@/app/globals.css"; // Ensure global styles are loaded

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [isAuthorized, setIsAuthorized] = useState(false);

    useEffect(() => {
        const checkAuth = async () => {
            const token = Cookies.get("token");
            if (!token) {
                router.replace("/login");
                return;
            }

            // Check role via API
            try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
                const res = await fetch(`${API_URL}/users/me`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });

                if (!res.ok) throw new Error("Auth failed");

                const user = await res.json();
                if (user.role !== "admin" && user.role !== "Администратор") { // Checking both enum values just in case
                    console.warn("Access denied: User is not admin");
                    router.replace("/platform");
                    return;
                }

                setIsAuthorized(true);
            } catch (e) {
                console.error("Auth check error", e);
                router.replace("/login");
            }
        };
        checkAuth();
    }, []);

    if (!isAuthorized) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-white font-mono">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                    <div className="text-xs tracking-widest uppercase opacity-50">System Link...</div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
            {/* Minimal Header */}
            <header className="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-zinc-900 rounded-lg flex items-center justify-center text-white font-bold text-xs">SYS</div>
                    <div className="font-bold text-lg tracking-tight text-zinc-900">System Control</div>
                </div>

                <div className="flex items-center gap-6">
                    <button
                        onClick={() => router.push("/platform")}
                        className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-black hover:bg-gray-100 rounded-md transition-colors"
                    >
                        Exit to Platform
                    </button>
                </div>
            </header>
            <main className="p-8 max-w-7xl mx-auto">
                {children}
            </main>
        </div>
    );
}
