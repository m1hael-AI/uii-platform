"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import Image from "next/image";
import Cookies from "js-cookie";
// import AIWidget from "@/components/AIWidget"; // Removed
import RightSidebar from "@/components/RightSidebar"; // Added
import logger from "@/lib/clientLogger";
import { SSEProvider } from "@/context/SSEContext";

const MENU_ITEMS = [
    {
        name: "Главная", href: "/platform", icon: (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        )
    },
    {
        name: "Библиотека", href: "/platform/webinars", icon: (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        )
    },
    {
        name: "Расписание", href: "/platform/schedule", icon: (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        )
    },
    {
        name: "Агенты", href: "/platform/chat", icon: (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        )
    },
];





export default function PlatformLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const router = useRouter();
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    const [user, setUser] = useState<{ name: string, email: string, role: string, avatar?: string } | null>(null);
    const [avatarError, setAvatarError] = useState(false);
    const [isCheckingAuth, setIsCheckingAuth] = useState(true);

    const [hasGlobalUnread, setHasGlobalUnread] = useState(false);

    useEffect(() => {
        const checkUnread = async () => {
            const token = Cookies.get("token");
            if (!token) return;
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            try {
                const res = await fetch(`${API_URL}/chat/unread-status`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    // Check if ANY session (agents OR assistant) has unread
                    setHasGlobalUnread(data.has_unread);
                }
            } catch (e) {
                console.error("Unread check failed", e);
            }
        };

        checkUnread();
        // Polling removed in favor of SSE

        // 🔗 CUSTOM EVENT for instant updates (triggered by SSEContext)
        const handleStatusUpdate = () => checkUnread();
        window.addEventListener("chatStatusUpdate", handleStatusUpdate);

        return () => {
            window.removeEventListener("chatStatusUpdate", handleStatusUpdate);
        };
    }, []);

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

                    // CRITICAL SECURITY CHECK: FORCE ONBOARDING
                    if (data.is_onboarded === false) {
                        router.replace("/onboarding");
                        return; // Stop here, don't show platform
                    }

                    setUser({
                        name: data.tg_first_name || (data.email ? data.email.split('@')[0] : "Студент"),
                        email: data.email || "No email",
                        role: data.role === "admin" ? "Администратор" : "Студент",
                        avatar: data.tg_photo_url // Добавляем URL аватара из ответа API
                    });
                    setAvatarError(false);
                    setIsCheckingAuth(false);
                } else {
                    logger.warn("u26a0ufe0f Platform auth failed", { status: res.status, url: `${API_URL}/users/me` });
                    Cookies.remove("token"); // Clear invalid token to prevent loop
                    router.replace("/login");
                }
            } catch (e) {
                console.error(e);
                setIsCheckingAuth(false); // Let it fail gracefully or redirect?
            }
        };
        fetchUser();
    }, []);

    if (isCheckingAuth) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#FF6B35]"></div>
            </div>
        );
    }

    return (
        <SSEProvider>
            <div className="flex min-h-screen bg-gray-50">
                {/* Sidebar - Hidden on mobile/tablet */}
                <aside
                    className={`bg-white border-r border-gray-100 fixed inset-y-0 left-0 z-40 transition-all duration-300 ease-in-out flex-col hidden lg:flex flex-shrink-0 ${isSidebarOpen ? "w-64 min-w-[200px] max-w-[256px]" : "w-20 min-w-[80px] max-w-[80px]"
                        }`}
                >
                    {/* Logo */}
                    <div className="h-16 flex items-center pl-6 border-b border-gray-50 overflow-hidden whitespace-nowrap">
                        <span className="font-bold text-xl text-black shrink-0">
                            AI
                        </span>
                        <span className={`font-bold text-xl tracking-tight text-black ml-1 transition-all duration-500 ease-in-out ${isSidebarOpen ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4 w-0"
                            }`}>
                            University
                        </span>
                    </div>

                    <nav className="flex-1 py-6 px-3 space-y-1 flex flex-col">
                        {MENU_ITEMS.map((item) => {
                            const isActive = item.href === "/platform"
                                ? pathname === item.href
                                : pathname.startsWith(item.href);
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`flex items-center rounded-xl group py-3 relative overflow-hidden whitespace-nowrap ${isActive
                                        ? "bg-[#FF6B35]/10 text-[#FF6B35]"
                                        : "text-gray-500 hover:bg-gray-50 hover:text-black"
                                        }`}
                                >
                                    <div className={`shrink-0 transition-all duration-500 ease-in-out flex items-center justify-center w-12`}>
                                        <svg className={`w-6 h-6 transition-colors duration-500 ease-in-out ${isActive ? "text-[#FF6B35]" : "text-gray-400 group-hover:text-black"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            {item.icon}
                                        </svg>
                                    </div>

                                    <span className={`font-medium transition-all duration-500 ease-in-out ${isSidebarOpen ? "opacity-100 translate-x-0 ml-3" : "opacity-0 -translate-x-4 w-0"
                                        }`}>
                                        {item.name}
                                    </span>
                                </Link>
                            )
                        })}
                    </nav>

                    {/* Toggle (Footer) */}
                    <div className="p-4 border-t border-gray-50 flex justify-center">
                        <button
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className="p-2 rounded-lg hover:bg-gray-50 text-gray-400"
                        >
                            <svg className={`w-5 h-5 transition-transform ${isSidebarOpen ? "" : "rotate-180"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                            </svg>
                        </button>
                    </div>
                </aside>

                {/* Main Content Wrapper */}
                <div
                    className={`flex-1 min-w-0 flex flex-col min-h-screen transition-all duration-300 ${isSidebarOpen ? "lg:ml-64" : "lg:ml-20"
                        }`}
                >
                    {/* Header */}
                    <header className="h-16 bg-white border-b border-gray-100 sticky top-0 z-30 px-4 md:px-6 flex items-center justify-between">
                        <h1 className="text-base md:text-lg font-medium text-gray-800">
                            {pathname === "/platform" ? "Главная" :
                                pathname.includes("/webinars") ? "Библиотека" :
                                    pathname.includes("/schedule") ? "Расписание" :
                                        pathname.includes("/chat") ? "Агенты" : "Панель управления"}
                        </h1>

                        {/* Profile & Actions */}
                        <div className="flex items-center gap-2 md:gap-4">
                            <button
                                onClick={async () => {
                                    // Fetch unread status to determine where to navigate
                                    const token = Cookies.get("token");
                                    if (!token) return;
                                    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
                                    try {
                                        const res = await fetch(`${API_URL}/chat/unread-status`, {
                                            headers: { Authorization: `Bearer ${token}` }
                                        });
                                        if (res.ok) {
                                            const data = await res.json();
                                            // console.log("🔔 Unread Check Data:", data);

                                            const sessions = data.sessions || [];

                                            // Check for specific unreads
                                            const unreadAssistant = sessions.find(
                                                (s: any) => (s.agent_slug === "main_assistant" || s.agent_slug === "assistant") && s.unread_count > 0
                                            );
                                            const unreadAgents = sessions.find(
                                                (s: any) => s.agent_slug !== "main_assistant" && s.agent_slug !== "assistant" && s.unread_count > 0
                                            );

                                            if (unreadAssistant) {
                                                // Priority 1: Assistant
                                                window.dispatchEvent(new CustomEvent("openRightSidebar"));
                                            } else if (unreadAgents) {
                                                // Priority 2: Agents
                                                router.push("/platform/chat");
                                            } else {
                                                // Priority 3: No unread -> Open Assistant (Default context)
                                                window.dispatchEvent(new CustomEvent("openRightSidebar"));
                                            }
                                        }
                                    } catch (e) {
                                        console.error("Failed to check unread status", e);
                                        // Fallback -> Agents
                                        router.push("/platform/chat");
                                    }
                                }}
                                className={`relative p-2 transition-colors focus:outline-none ${hasGlobalUnread ? 'text-[#FF6B35]' : 'text-gray-400 hover:text-black'}`}
                            >
                                {hasGlobalUnread && (
                                    <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-[#FF6B35] rounded-full border-2 border-white animate-pulse"></span>
                                )}
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                </svg>
                            </button>

                            <div className="h-8 w-[1px] bg-gray-100 mx-1 hidden md:block"></div>

                            <Link href="/platform/profile" className="flex items-center gap-3 hover:bg-gray-50 p-1.5 rounded-lg transition-colors group">
                                <div className="text-right hidden md:block">
                                    <div className="text-sm font-medium text-black group-hover:text-[#206ecf] transition-colors">{user?.name || "Загрузка..."}</div>
                                    <div className="text-xs text-gray-400">{user?.email || ""}</div>
                                </div>
                                <div className="w-10 h-10 rounded-full bg-[#f0f9ff] text-[#206ecf] overflow-hidden border border-[#FF6B35]/10 flex items-center justify-center font-bold relative">
                                    {user?.avatar && !avatarError ? (
                                        <img
                                            src={user.avatar}
                                            alt={user.name}
                                            className="w-full h-full object-cover"
                                            onError={() => setAvatarError(true)}
                                        />
                                    ) : (
                                        user?.name ? user.name.charAt(0).toUpperCase() : "U"
                                    )}
                                </div>
                            </Link>


                        </div>
                    </header>

                    {/* Page Content */}
                    <main className="flex-1 p-4 md:p-6 pb-20 lg:pb-6 overflow-y-auto">
                        {children}
                    </main>

                    {/* Mobile Bottom Navigation - Visible on mobile & tablet */}
                    <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40 safe-area-inset-bottom">
                        <div className="flex items-center justify-around h-16 px-2">
                            {MENU_ITEMS.map((item) => {
                                const isActive = item.href === "/platform"
                                    ? pathname === item.href
                                    : pathname.startsWith(item.href);
                                return (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        className={`flex flex-col items-center justify-center gap-1 px-3 py-2 rounded-lg transition-colors min-w-[60px] ${isActive
                                            ? "text-[#FF6B35]"
                                            : "text-gray-400"
                                            }`}
                                    >
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            {item.icon}
                                        </svg>
                                        <span className="text-[10px] font-medium">{item.name}</span>
                                    </Link>
                                );
                            })}
                        </div>
                    </nav>
                </div>

                {/* AI Assistant (Right Sidebar) */}
                <RightSidebar />
            </div>
        </SSEProvider>
    );
}
