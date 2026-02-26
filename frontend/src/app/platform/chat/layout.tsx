"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useState, useEffect } from "react";

// Fallback colors for agents without avatar
const COLORS = [
    "bg-orange-50 text-orange-600",
    "bg-yellow-50 text-yellow-600",
    "bg-green-50 text-green-600",
    "bg-purple-50 text-purple-600",
    "bg-blue-50 text-blue-600",
    "bg-pink-50 text-pink-600",
];

interface Agent {
    id: number;
    slug: string;
    name: string;
    description?: string;
    avatar_url?: string;
    greeting_message?: string; // Added field
}

export default function ChatLayout({ children }: { children: React.ReactNode }) {
    const params = useParams();
    const pathname = usePathname();

    // Search & Data
    const [search, setSearch] = useState("");
    const [agents, setAgents] = useState<Agent[]>([]);
    const [sessions, setSessions] = useState<Record<string, any>>({});
    const [typingAgents, setTypingAgents] = useState<Record<string, boolean>>({});
    const [isLoading, setIsLoading] = useState(true);

    // Fetch Agents & Sessions
    const fetchData = async () => {
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const { default: Cookies } = await import("js-cookie");
            const token = Cookies.get("token");

            if (!token) return;

            // Parallel Request
            const [agentsRes, sessionsRes] = await Promise.all([
                fetch(`${API_URL}/chat/agents`, { headers: { Authorization: `Bearer ${token}` } }),
                fetch(`${API_URL}/chat/sessions?t=${Date.now()}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" })
            ]);

            if (agentsRes.ok) {
                const agentsData = await agentsRes.json();
                setAgents(agentsData);
            }

            if (sessionsRes.ok) {
                const sessionsData = await sessionsRes.json();
                const sessionMap: Record<string, any> = {};
                sessionsData.forEach((s: any) => {
                    const isActive = window.location.pathname.includes(`/chat/${s.agent_id}`);
                    sessionMap[s.agent_id] = s;
                });
                setSessions(sessionMap);
            }
        } catch (e) {
            console.error("Failed to fetch chat data", e);
        } finally {
            setIsLoading(false);
        }
    };

    // Initial load + Event Listener for updates
    useEffect(() => {
        fetchData();

        const handleUpdate = () => fetchData();
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

    const filteredAgents = agents.filter(a => a.name.toLowerCase().includes(search.toLowerCase()));

    return (
        // Mobile: Fixed position to fill space and BottomNav
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
                    {isLoading ? (
                        // SKELETON LOADER
                        <div className="animate-pulse space-y-2 p-2">
                            {[1, 2, 3, 4].map(i => (
                                <div key={i} className="flex items-center gap-3 p-3 rounded-xl">
                                    <div className="w-12 h-12 rounded-full bg-gray-200 shrink-0"></div>
                                    <div className="flex-1 space-y-2">
                                        <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                                        <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        filteredAgents.map((agent, idx) => {
                            const isActive = pathname.includes(`/chat/${agent.slug}`);
                            const session = sessions[agent.slug];
                            const isTyping = typingAgents[agent.slug];

                            // Display Logic: Typing > Last Message > Greeting > Description > Default
                            const displayMsg = isTyping
                                ? <span className="text-[#206ecf] animate-pulse">Печатает...</span>
                                : (session?.last_message || agent.greeting_message || agent.description || "Начать диалог");

                            const hasUnread = session?.has_unread || false;

                            // Deterministic color based on ID
                            const colorClass = COLORS[agent.id % COLORS.length];

                            return (
                                <Link
                                    key={agent.slug}
                                    href={`/platform/chat/${agent.slug}`}
                                    onClick={() => {
                                        // 💨 INSTANT LOCAL UPDATE
                                        setSessions(prev => ({
                                            ...prev,
                                            [agent.slug]: { ...prev[agent.slug], has_unread: false }
                                        }));
                                    }}
                                    className={`flex items-center gap-3 p-3 mx-2 mt-1 rounded-xl transition-colors ${isActive ? "bg-white shadow-sm border border-gray-100" : "hover:bg-gray-100/50"
                                        }`}
                                >
                                    <div className="relative w-12 h-12 shrink-0">
                                        <div className={`w-full h-full rounded-full flex items-center justify-center font-bold text-sm overflow-hidden ${!agent.avatar_url ? colorClass : "bg-gray-100"}`}>
                                            {agent.avatar_url ? (
                                                <img src={agent.avatar_url} alt={agent.name} className="w-full h-full object-cover" />
                                            ) : (
                                                agent.name[0]
                                            )}
                                        </div>
                                        {hasUnread && !isTyping && <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full border-2 border-white z-10"></span>}
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
                        })
                    )}
                </div>
            </div>

            {/* Right Content (Chat Window or Empty State) */}
            <div className="flex-1 flex flex-col min-w-0 bg-white">
                {children}
            </div>
        </div>
    );
}
