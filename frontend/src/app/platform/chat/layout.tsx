"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const AGENTS = [
    { id: "mentor", name: "AI Ментор", role: "Куратор", avatar: "A", color: "bg-orange-50 text-orange-600", lastMsg: "Персональный куратор по всем вопросам." },
    { id: "python", name: "Python Эксперт", role: "Tutor", avatar: "P", color: "bg-yellow-50 text-yellow-600", lastMsg: "Помогу с кодом и архитектурой." },
    { id: "analyst", name: "Data Analyst", role: "Expert", avatar: "D", color: "bg-green-50 text-green-600", lastMsg: "Анализ данных и Pandas." },
    { id: "hr", name: "HR Консультант", role: "Assistant", avatar: "H", color: "bg-purple-50 text-purple-600", lastMsg: "Помощь с резюме и карьерой." },
];

export default function ChatLayout({ children }: { children: React.ReactNode }) {
    const params = useParams();
    const pathname = usePathname();

    // Search
    const [search, setSearch] = useState("");
    const [sessions, setSessions] = useState<Record<string, any>>({});
    const [typingAgents, setTypingAgents] = useState<Record<string, boolean>>({});

    // Fetch sessions to get real last messages
    // Fetch sessions logic
    const fetchSessions = async () => {
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            // Check for token safely
            const { default: Cookies } = await import("js-cookie");
            const token = Cookies.get("token");

            if (!token) return;

            const res = await fetch(`${API_URL}/chat/sessions`, {
                headers: { Authorization: `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                const sessionMap: Record<string, any> = {};
                data.forEach((s: any) => {
                    // 🛡️ ANTI-FLICKER: If we are currently on this agent's page, ignore server's "unread" status
                    // current pathname might be /platform/chat/mentor
                    // s.agent_id is "mentor"
                    if (window.location.pathname.includes(`/chat/${s.agent_id}`)) {
                        s.has_unread = false;
                    }
                    sessionMap[s.agent_id] = s;
                });
                setSessions(sessionMap);
            }
        } catch (e) {
            console.error("Failed to fetch sessions", e);
        }
    };

    // Initial load + Event Listener for updates
    useEffect(() => {
        fetchSessions();

        const handleUpdate = () => fetchSessions();
        const handleTyping = (e: Event) => {
            const detail = (e as CustomEvent).detail;
            setTypingAgents(prev => ({
                ...prev,
                [detail.agentId]: detail.isTyping
            }));
        };

        window.addEventListener("chatStatusUpdate", handleUpdate);
        window.addEventListener("chatTypingStatus", handleTyping);

        return () => {
            window.removeEventListener("chatStatusUpdate", handleUpdate);
            window.removeEventListener("chatTypingStatus", handleTyping);
        };
    }, []);

    const filteredAgents = AGENTS.filter(a => a.name.toLowerCase().includes(search.toLowerCase()));

    return (
        // Mobile: Fixed position to fill space between Header (h-16) and BottomNav (h-16)
        // Desktop: Calculated height within container
        <div className={`
            flex bg-white overflow-hidden
            fixed top-16 bottom-16 left-0 right-0 z-0
            lg:static lg:h-[calc(100vh-140px)] lg:rounded-2xl lg:border lg:border-gray-100 lg:shadow-sm
        `}>
            {/* Left Sidebar (Contact List) - Hidden on mobile/tablet */}
            <div className="w-80 bg-gray-50 border-r border-gray-100 flex-col shrink-0 hidden lg:flex">
                {/* Search Header */}
                <div className="p-4 border-b border-gray-100 bg-white">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Поиск агента..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-9 pr-4 py-2 bg-gray-100 border-none rounded-lg text-sm focus:ring-1 focus:ring-orange-500 outline-none transition-all"
                        />
                        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                </div>

                {/* List */}
                <div className="flex-1 overflow-y-auto">
                    {filteredAgents.map(agent => {
                        const isActive = pathname.includes(`/chat/${agent.id}`);
                        const session = sessions[agent.id];
                        const isTyping = typingAgents[agent.id];

                        // Display Logic: Typing > Last Message > Default
                        const displayMsg = isTyping
                            ? <span className="text-[#206ecf] animate-pulse">Печатает...</span>
                            : (session?.last_message || agent.lastMsg);

                        const hasUnread = session?.has_unread || false;

                        return (
                            <Link
                                key={agent.id}
                                href={`/platform/chat/${agent.id}`}
                                onClick={() => {
                                    // 💨 INSTANT LOCAL UPDATE
                                    setSessions(prev => ({
                                        ...prev,
                                        [agent.id]: { ...prev[agent.id], has_unread: false }
                                    }));
                                }}
                                className={`flex items-center gap-3 p-3 mx-2 mt-1 rounded-xl transition-colors ${isActive ? "bg-white shadow-sm border border-gray-100" : "hover:bg-gray-100/50"
                                    }`}
                            >
                                <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm shrink-0 ${agent.color} relative`}>
                                    {agent.avatar}
                                    {hasUnread && !isTyping && <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full border-2 border-white"></span>}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-center mb-0.5">
                                        <h4 className="font-medium text-gray-900 truncate">{agent.name}</h4>
                                        {session?.last_message_at && (
                                            <span className="text-[10px] text-gray-400">
                                                {new Date(session.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        )}
                                    </div>
                                    <p className={`text-xs truncate ${isActive || hasUnread ? "text-gray-700 font-medium" : "text-gray-500"}`}>
                                        {displayMsg}
                                    </p>
                                </div>
                            </Link>
                        );
                    })}
                </div>
            </div>

            {/* Right Content (Chat Window or Empty State) */}
            <div className="flex-1 flex flex-col min-w-0 bg-white">
                {children}
            </div>
        </div>
    );
}
