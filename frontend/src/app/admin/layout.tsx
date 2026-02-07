"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import Cookies from "js-cookie";

const MENU_ITEMS = [
    {
        name: "LLM Аудит", href: "/admin/llm-audit", icon: (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
        )
    },
    // Add more admin items here later (Users, Agents, etc.)
];

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const router = useRouter();
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [user, setUser] = useState<{ name: string, role: string } | null>(null);
    const [isCheckingAuth, setIsCheckingAuth] = useState(true);

    useEffect(() => {
        const fetchUser = async () => {
            const token = Cookies.get("token");
            if (!token) {
                router.replace("/login");
                return;
            }
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            try {
                const res = await fetch(`${API_URL}/users/me`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (res.ok) {
                    const data = await res.json();

                    if (data.role !== "admin") {
                        router.replace("/platform"); // Redirect non-admins
                        return;
                    }

                    setUser({
                        name: data.tg_first_name || data.email,
                        role: data.role
                    });
                    setIsCheckingAuth(false);
                } else {
                    Cookies.remove("token");
                    router.replace("/login");
                }
            } catch (e) {
                console.error(e);
                setIsCheckingAuth(false);
            }
        };
        fetchUser();
    }, []);

    if (isCheckingAuth) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-500"></div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen bg-gray-50">
            {/* Sidebar */}
            <aside
                className={`bg-[#1a1c23] text-gray-400 border-r border-gray-800 fixed inset-y-0 left-0 z-40 transition-all duration-300 ease-in-out flex flex-col flex-shrink-0 ${isSidebarOpen ? "w-64" : "w-20"
                    }`}
            >
                {/* Logo */}
                <div className="h-16 flex items-center justify-center border-b border-gray-800">
                    <span className={`font-bold text-xl text-white tracking-wider ${!isSidebarOpen && "hidden"}`}>
                        ADMIN
                    </span>
                    {!isSidebarOpen && <span className="font-bold text-white">A</span>}
                </div>

                <nav className="flex-1 py-6 px-3 space-y-1">
                    {MENU_ITEMS.map((item) => {
                        const isActive = pathname.startsWith(item.href);
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center rounded-lg px-3 py-3 transition-colors ${isActive
                                    ? "bg-gray-800 text-white"
                                    : "hover:bg-gray-800 hover:text-white"
                                    }`}
                            >
                                <div className="shrink-0">
                                    {item.icon}
                                </div>
                                {isSidebarOpen && (
                                    <span className="ml-3 font-medium">
                                        {item.name}
                                    </span>
                                )}
                            </Link>
                        )
                    })}
                </nav>

                <div className="p-4 border-t border-gray-800">
                    <Link href="/platform" className="flex items-center text-sm hover:text-white transition-colors">
                        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 15l-3-3m0 0l3-3m-3 3h8M3 12a9 9 0 1118 0 9 9 0 01-18 0z" />
                        </svg>
                        {isSidebarOpen && "Back to Platform"}
                    </Link>
                </div>
            </aside>

            {/* Main Content */}
            <div className={`flex-1 min-w-0 flex flex-col min-h-screen transition-all duration-300 ${isSidebarOpen ? "ml-64" : "ml-20"}`}>
                <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-30">
                    <h1 className="text-xl font-semibold text-gray-800">
                        Показатели LLM
                    </h1>
                    <div className="flex items-center gap-4">
                        <div className="text-sm text-gray-600">
                            {user?.name}
                        </div>
                    </div>
                </header>

                <main className="flex-1 p-6 overflow-y-auto">
                    {children}
                </main>
            </div>
        </div>
    );
}
