"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Cookies from "js-cookie";
import { useRouter, useSearchParams } from "next/navigation";

interface ChatSession {
    id: number;
    agent_id: string; // slug
    agent_name: string;
    agent_avatar: string | null;
    last_message: string;
    last_message_at: string | null;
    has_unread: boolean;
}

export default function ChatIndexPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [loading, setLoading] = useState(true);

    // Deep Link Logic: ?agent=mentor
    useEffect(() => {
        const agentSlug = searchParams.get("agent");
        if (agentSlug) {
            router.push(`/platform/chat/${agentSlug}`);
        }
    }, [searchParams, router]);

    // Fetch Sessions
    const fetchSessions = async () => {
        const token = Cookies.get("token");
        if (!token) {
            setLoading(false);
            return;
        }

        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
        try {
            const res = await fetch(`${API_URL}/chat/sessions`, {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                setSessions(data);
            }
        } catch (e) {
            console.error("Failed to fetch sessions", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();

        // 🔔 Listen for global updates (e.g. from Sidebar or Header or ChatPage)
        const handleUpdate = () => {
            // Re-fetch to sync backend state with UI
            fetchSessions();
        };

        window.addEventListener("chatStatusUpdate", handleUpdate);
        return () => window.removeEventListener("chatStatusUpdate", handleUpdate);
    }, []);

    // Get color based on agent ID (consistent with mock)
    const getAgentStyle = (slug: string) => {
        switch (slug) {
            case "startup_expert": return "bg-orange-50 text-orange-600";
            case "python": return "bg-yellow-50 text-yellow-600";
            case "analyst": return "bg-green-50 text-green-600";
            case "hr": return "bg-purple-50 text-purple-600";
            default: return "bg-blue-50 text-blue-600";
        }
    };

    const getAgentAvatar = (name: string) => {
        return name ? name[0].toUpperCase() : "A";
    };

    if (loading) {
        return <div className="p-8 text-center text-gray-400">Загрузка...</div>;
    }

    return (
        <>
            {/* Desktop: Empty state */}
            <div className="hidden lg:flex flex-1 flex-col items-center justify-center p-8 text-center text-gray-500 bg-gray-50/30">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-gray-400">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-1">Выберите собеседника</h3>
                <p className="text-sm max-w-xs mx-auto">
                    Выберите одного из AI-агентов в списке слева, чтобы начать диалог.
                </p>
            </div>

            {/* Mobile/Tablet: Agent list */}
            <div className="lg:hidden flex-1 flex flex-col bg-gray-50 overflow-y-auto">
                <div className="p-4 bg-white border-b border-gray-100">
                    <h2 className="text-lg font-semibold text-gray-900">AI Агенты</h2>
                    <p className="text-sm text-gray-500 mt-1">
                        {sessions.length > 0 ? "Выберите агента для начала диалога" : "У вас пока нет активных диалогов"}
                    </p>
                </div>

                <div className="p-4 space-y-3">
                    {sessions.map(session => (
                        <Link
                            key={session.id}
                            href={`/platform/chat/${session.agent_id}`}
                            onClick={() => {
                                // 💨 INSTANT LOCAL UPDATE
                                setSessions(prev => prev.map(s =>
                                    s.id === session.id ? { ...s, has_unread: false } : s
                                ));
                                // We do NOT dispatch 'chatStatusUpdate' here to avoid race condition 
                                // (re-fetching before backend marks it read).
                                // The chat page itself will fetch history and mark read.
                            }}
                            className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all active:scale-98 relative"
                        >
                            <div className={`w-14 h-14 rounded-full flex items-center justify-center font-bold text-lg shrink-0 ${getAgentStyle(session.agent_id)}`}>
                                {getAgentAvatar(session.agent_name)}
                            </div>

                            <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-1">
                                    <h3 className="font-semibold text-gray-900">{session.agent_name}</h3>
                                    {session.has_unread && (
                                        <span className="w-2.5 h-2.5 bg-red-500 rounded-full shrink-0"></span>
                                    )}
                                </div>
                                <p className={`text-xs line-clamp-1 ${session.has_unread ? "text-gray-900 font-medium" : "text-gray-500"}`}>
                                    {session.last_message}
                                </p>
                            </div>

                            <svg className="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                        </Link>
                    ))}

                    {sessions.length === 0 && !loading && (
                        <div className="text-center py-8 text-gray-400 text-sm">
                            Диалоги еще не созданы. Подождите немного...
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}
