"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import ReactMarkdown from "react-markdown";

// 🎛️ FEATURE FLAG: Set to false to disable tooltip animation
const FEATURE_TOOLTIP_ANIMATION = true;

export default function RightSidebar() {
    const [isOpen, setIsOpen] = useState(false);
    const sidebarRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    const [hasUnreadMessages, setHasUnreadMessages] = useState(false);

    // Committed history (Server + Completed Local)
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', text: string, created_at?: string }[]>([
        { role: 'assistant', text: 'Здравствуйте! Я ваш AI-помощник. Чем могу помочь по учебной программе или платформе?' }
    ]);

    // Active Streaming State (separate from messages array for performance)
    const [streamingMessage, setStreamingMessage] = useState("");
    const [input, setInput] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Tooltip status
    const [showTooltip, setShowTooltip] = useState(false);
    const [lastTooltipMessageIndex, setLastTooltipMessageIndex] = useState<number>(-1);

    // Ref to track initial history load
    const isInitialLoad = useRef(true);
    // 🆕 VARIANT 1: Track if history was empty (new user)
    const wasHistoryEmpty = useRef(false);

    const toggle = () => setIsOpen(!isOpen);

    // 🔗 DEEP LINK: ?assistant=open
    const searchParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
    useEffect(() => {
        if (searchParams?.get("assistant") === "open") {
            setIsOpen(true);
            // Optional: clean up URL after opening
            const newUrl = window.location.pathname;
            window.history.replaceState({}, '', newUrl);

            // 🔔 Instant Update
            window.dispatchEvent(new Event("chatStatusUpdate"));
        }
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, streamingMessage, isTyping, isOpen]);

    // Helper to mark as read on Server
    const markAsRead = async (): Promise<boolean> => {
        const token = Cookies.get("token");
        if (!token) return false;
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
        try {
            const res = await fetch(`${API_URL}/chat/read?agent_id=main_assistant`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                // 🔔 Trigger Global Refresh
                if (typeof window !== 'undefined') {
                    window.dispatchEvent(new Event("chatStatusUpdate"));
                }
            }
            return res.ok;
        } catch (e) {
            console.error("Failed to mark as read", e);
            return false;
        }
    };

    // Load History Logic
    useEffect(() => {
        const fetchHistory = async () => {
            const token = Cookies.get("token");
            if (!token) return;

            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const url = new URL(`${API_URL}/chat/history`);
            url.searchParams.append("agent_id", "main_assistant");

            try {
                const res = await fetch(url.toString(), {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    const historyMessages = data.messages || [];

                    const parseDate = (dateStr: string) => {
                        if (!dateStr) return new Date(0);
                        return new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z');
                    };
                    const lastReadServer = parseDate(data.last_read_at);

                    if (historyMessages.length > 0) {
                        const uiMsgs = historyMessages.map((m: any) => ({
                            role: m.role,
                            text: m.content,
                            created_at: m.created_at
                        }));
                        setMessages(uiMsgs);
                        setLastTooltipMessageIndex(uiMsgs.length - 1);
                        wasHistoryEmpty.current = false; // ← History was NOT empty

                        const lastAssistantMsg = uiMsgs[uiMsgs.length - 1];
                        if (lastAssistantMsg.role === 'assistant') {
                            const msgTime = parseDate(lastAssistantMsg.created_at);
                            setHasUnreadMessages(msgTime > lastReadServer);
                        } else {
                            setHasUnreadMessages(false);
                        }
                    } else {
                        setHasUnreadMessages(false);
                    }
                } else {
                    // 🆕 VARIANT 1: History was empty (new user)
                    wasHistoryEmpty.current = true;
                }
            } catch (e) {
                console.error("Failed to load history", e);
            } finally {
                setTimeout(() => {
                    isInitialLoad.current = false;
                }, 1000);
            }
        };

        fetchHistory();
    }, []);

    // 🔔 UNIFIED NOTIFICATION LOGIC
    // Only notifies on COMPLETED messages
    useEffect(() => {
        if (isOpen) {
            // SCENARIO 1: Sidebar is OPEN. 
            // We see everything. Clear alerts.
            if (hasUnreadMessages) setHasUnreadMessages(false);

            // Mark all current COMMITTED messages as seen
            if (messages.length > 0) {
                setLastTooltipMessageIndex(messages.length - 1);
            }
        } else {
            // SCENARIO 2: Sidebar is CLOSED.
            // 🆕 VARIANT 1: Allow notification if history was empty (new user)
            console.log("🔍 DEBUG Notification Check:", {
                isInitialLoad: isInitialLoad.current,
                wasHistoryEmpty: wasHistoryEmpty.current,
                messagesLength: messages.length,
                isOpen
            });

            if (isInitialLoad.current && !wasHistoryEmpty.current) {
                console.log("❌ Blocked: isInitialLoad=true and history was NOT empty");
                return;
            }

            // Trigger: New COMMITTED message (finished)
            const currentIndex = messages.length - 1;
            const lastMessage = messages[currentIndex];

            console.log("🔍 Last Message:", lastMessage);
            console.log("🔍 lastTooltipMessageIndex:", lastTooltipMessageIndex);

            // Allow notification ONLY if it's a new, untracked message
            // AND it's not a temporary user optimistic message (wait for assistant)
            const isNewCommitted = lastMessage && lastMessage.role === 'assistant' && currentIndex > lastTooltipMessageIndex;

            console.log("🔍 isNewCommitted:", isNewCommitted);

            if (isNewCommitted) {
                if (!hasUnreadMessages) {
                    console.log("✅ SHOWING TOOLTIP!");
                    setShowTooltip(true);
                    setLastTooltipMessageIndex(currentIndex);
                    setHasUnreadMessages(true);

                    // Auto-hide tooltip
                    const timer = setTimeout(() => setShowTooltip(false), 5000);
                    return () => clearTimeout(timer);
                }
            }
        }
    }, [messages, isOpen, lastTooltipMessageIndex, hasUnreadMessages]);

    // 🆕 VARIANT 4: Listen to SSE chatStatusUpdate for instant notifications
    useEffect(() => {
        const handleChatUpdate = () => {
            // SSE event received: new message from backend
            if (!isOpen && !isInitialLoad.current) {
                // Sidebar is closed AND initial load is done
                // Refetch history to get new message
                const refetchHistory = async () => {
                    const token = Cookies.get("token");
                    if (!token) return;

                    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
                    const url = new URL(`${API_URL}/chat/history`);
                    url.searchParams.append("agent_id", "main_assistant");

                    try {
                        const res = await fetch(url.toString(), {
                            headers: { "Authorization": `Bearer ${token}` }
                        });
                        if (res.ok) {
                            const data = await res.json();
                            const historyMessages = data.messages || [];
                            if (historyMessages.length > 0) {
                                const uiMsgs = historyMessages.map((m: any) => ({
                                    role: m.role,
                                    text: m.content,
                                    created_at: m.created_at
                                }));
                                setMessages(uiMsgs);
                                // Trigger notification via existing logic
                            }
                        }
                    } catch (e) {
                        console.error("Failed to refetch history on SSE", e);
                    }
                };
                refetchHistory();
            }
        };

        window.addEventListener("chatStatusUpdate", handleChatUpdate);
        return () => window.removeEventListener("chatStatusUpdate", handleChatUpdate);
    }, [isOpen]);

    // Sync Read Status with Server when Open
    useEffect(() => {
        if (isOpen) {
            // When opened OR when new messages arrive while open -> Mark as read
            markAsRead().catch(console.error);
        }
    }, [isOpen, messages.length]);

    // Click Outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (isOpen && sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [isOpen]);

    const handleSend = async () => {
        if (!input.trim() || isTyping) return;

        const token = Cookies.get("token");
        if (!token) {
            router.push("/login");
            return;
        }

        const userText = input;
        setInput("");

        // 1. Add User Message Immediately
        const tempUserMsg = { role: 'user' as const, text: userText };
        setMessages(prev => [...prev, tempUserMsg]);
        setIsTyping(true);
        setStreamingMessage(""); // Reset stream

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            // Prepare context (include user's new message)
            const contextMessages = [...messages, tempUserMsg].map(m => ({ role: m.role, content: m.text }));

            const res = await fetch(`${API_URL}/chat/completions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    messages: contextMessages,
                    agent_id: "main_assistant",
                    webinar_id: null
                })
            });

            if (!res.ok) throw new Error("API Error");
            if (!res.body) throw new Error("No response body");

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                accumulatedText += chunk;

                // 2. Update STREAMING state (cheap render)
                setStreamingMessage(accumulatedText);
            }

            // 3. DONE: Commit to history
            // Order important: Add to history -> Clear stream
            // This ensures no flickering (or minimal)
            setMessages(prev => [...prev, { role: 'assistant', text: accumulatedText }]);
            setStreamingMessage("");

        } catch (e: any) {
            console.error("Chat Error:", e);
            setMessages(prev => [...prev, {
                role: 'assistant',
                text: `Прошу прощения, произошла ошибка соединения. (${e.message || "Unknown error"})`
            }]);
        } finally {
            setIsTyping(false);
        }
    };

    return (
        <div ref={sidebarRef}>
            {/* Collapsed Tab */}
            <button
                onClick={() => {
                    toggle();
                    setShowTooltip(false);
                }}
                className={`fixed top-1/2 right-0 -translate-y-1/2 z-50 bg-white border border-gray-200 border-r-0 rounded-l-xl shadow-md p-2 flex flex-col items-center gap-2 transition-transform duration-300 hover:bg-gray-50 group hover:pr-3 ${isOpen ? "translate-x-full" : "translate-x-0"
                    }`}
                title="AI Помощник"
            >
                <div className="relative">
                    <div className="w-8 h-8 rounded-full bg-[#206ecf] text-white flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>

                    {/* Red Badge */}
                    {!isOpen && hasUnreadMessages && (
                        <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-red-500 rounded-full border-2 border-white pointer-events-none"></div>
                    )}

                    {/* Tooltip Animation */}
                    {FEATURE_TOOLTIP_ANIMATION && showTooltip && !isOpen && (
                        <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-white text-gray-800 border border-gray-200 text-xs px-3 py-2 rounded-lg shadow-xl whitespace-nowrap animate-fade-in-right flex items-center gap-2">
                            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                            Новое сообщение
                            <div className="absolute left-full top-1/2 -translate-y-1/2 border-4 border-transparent border-l-white drop-shadow-sm"></div>
                        </div>
                    )}
                </div>
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest [writing-mode:vertical-rl] rotate-180">
                    AI Помощник
                </span>
            </button>


            {/* Expanded Sidebar */}
            <div
                className={`fixed inset-y-0 right-0 z-50 w-full md:w-[400px] bg-white border-l border-gray-200 shadow-2xl transform transition-transform duration-500 ease-in-out flex flex-col ${isOpen ? "translate-x-0" : "translate-x-full"
                    }`}
            >
                {/* Header */}
                <div className="h-16 flex items-center justify-between px-6 border-b border-gray-100 bg-white/80 backdrop-blur-md">
                    <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors bg-[#206ecf]/10 text-[#206ecf]`}>
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <div>
                            <h3 className="font-bold text-gray-800">AI Помощник</h3>
                        </div>

                    </div>
                    <button
                        onClick={toggle}
                        className="p-2 text-gray-400 hover:text-black transition-colors rounded-lg hover:bg-gray-100"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50/50">
                    {/* 1. Committed Messages history */}
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${msg.role === 'user'
                                ? 'bg-[#206ecf] text-white rounded-tr-none'
                                : 'bg-white border border-gray-100 text-gray-800 rounded-tl-none'
                                }`}>
                                {msg.role === 'user' ? (
                                    msg.text
                                ) : (
                                    <div className="prose prose-sm max-w-none text-inherit dark:prose-invert">
                                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* 2. Active Streaming Message (Assistant) */}
                    {isTyping && streamingMessage && (
                        <div className="flex justify-start">
                            <div className="max-w-[85%] bg-white border border-gray-100 rounded-2xl rounded-tl-none px-4 py-3 text-sm leading-relaxed shadow-sm text-gray-800">
                                <div className="prose prose-sm max-w-none text-inherit dark:prose-invert">
                                    <ReactMarkdown>{streamingMessage}</ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* 3. Typing Indicator (Only if thinking and no text yet) */}
                    {isTyping && !streamingMessage && (
                        <div className="flex justify-start">
                            <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center gap-1">
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-gray-100 bg-white">
                    <div className="relative">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && !isTyping && handleSend()}
                            placeholder={isTyping ? "AI отвечает..." : "Задайте вопрос..."}
                            disabled={isTyping}
                            className={`w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#206ecf]/20 focus:border-[#206ecf] transition-all text-black placeholder:text-gray-400 ${isTyping ? "cursor-not-allowed opacity-70" : ""
                                }`}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || isTyping}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-[#ff8a35] hover:bg-[#ff8a35]/10 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        </button>
                    </div>
                    <div className="text-center mt-2">
                        <span className="text-[10px] text-gray-400">AI может ошибаться. Проверяйте важную информацию.</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
