"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { motion, AnimatePresence } from "framer-motion";

const ADMIN_MENU = [
    { name: "Агенты", href: "/admin/agents", icon: "🤖" },
    { name: "Вебинары", href: "/admin/webinars", icon: "📚" },
    { name: "Пользователи", href: "/admin/users", icon: "👥" },
    { name: "Мониторинг", href: "/admin/monitoring", icon: "📊" },
    { name: "Настройки", href: "/admin/settings", icon: "⚙️" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const [isAuthorized, setIsAuthorized] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        checkAdmin();
    }, []);

    const checkAdmin = async () => {
        const token = Cookies.get("token");
        if (!token) {
            router.push("/login");
            return;
        }

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const res = await fetch(`${API_URL}/users/me`, {
                headers: { Authorization: `Bearer ${token}` }
            });

            if (res.ok) {
                const user = await res.json();
                console.log("Admin Check User:", user);
                if (user.role && user.role.toLowerCase() === "admin") {
                    setIsAuthorized(true);
                } else {
                    console.warn("User is not admin, role:", user.role);
                    router.push("/platform"); // Redirect non-admins
                }
            } else {
                router.push("/login");
            }
        } catch (e) {
            console.error(e);
            router.push("/login");
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) return <div className="h-screen flex items-center justify-center">Загрузка...</div>;
    if (!isAuthorized) return null;

    return (
        <div className="min-h-screen bg-gray-100 flex font-sans text-gray-900">
            {/* Sidebar */}
            <aside className="w-64 bg-gray-900 text-white flex flex-col fixed inset-y-0 left-0 z-50">
                <div className="h-16 flex items-center justify-center border-b border-gray-800">
                    <span className="font-bold text-lg tracking-wider">AI ADMIN</span>
                </div>

                <nav className="flex-1 py-6 px-3 space-y-1">
                    {ADMIN_MENU.map((item) => {
                        const isActive = pathname.startsWith(item.href);
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center px-4 py-3 rounded-lg transition-colors ${isActive
                                    ? "bg-orange-600 text-white"
                                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                                    }`}
                            >
                                <span className="mr-3">{item.icon}</span>
                                <span className="font-medium">{item.name}</span>
                            </Link>
                        )
                    })}
                </nav>

                <div className="p-4 border-t border-gray-800">
                    <Link
                        href="/platform"
                        className="flex items-center text-gray-400 hover:text-white transition-colors"
                    >
                        <span className="mr-2">←</span> Вернуться на сайт
                    </Link>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 ml-64 p-8">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={pathname}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="max-w-6xl mx-auto"
                    >
                        {children}
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
    );
}
