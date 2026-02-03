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

    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', text: string, created_at?: string }[]>([
        { role: 'assistant', text: 'Здравствуйте! Я ваш AI-помощник. Чем могу помочь по учебной программе или платформе?' }
    ]);
    const [input, setInput] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Tooltip status
    const [showTooltip, setShowTooltip] = useState(false);
    const [lastTooltipMessageIndex, setLastTooltipMessageIndex] = useState<number>(-1);

    // Ref to track initial history load to prevent tooltip spam on refresh
    const isInitialLoad = useRef(true);

    const toggle = () => setIsOpen(!isOpen);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping, isOpen]);

    // Helper to mark as read on Server (returns Promise)
    const markAsRead = async (): Promise<boolean> => {
        const token = Cookies.get("token");
        if (!token) return false;
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
        try {
            const res = await fetch(`${API_URL}/chat/read?agent_id=main_assistant`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });
            return res.ok;
        } catch (e) {
            console.error("Failed to mark as read", e);
            return false;
        }
    };

    // Load History Logic (only once on mount)
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

                    // Helper to safely parse UTC date
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

                        // Sync tooltip index with loaded history to prevent firing
                        setLastTooltipMessageIndex(uiMsgs.length - 1);

                        // Calculate unread status
                        const lastAssistantMsg = uiMsgs[uiMsgs.length - 1];

                        if (lastAssistantMsg.role === 'assistant') {
                            const msgTime = parseDate(lastAssistantMsg.created_at);
                            // If message is newer than last_read_at -> Unread
                            setHasUnreadMessages(msgTime > lastReadServer);
                        } else {
                            // User sent last message -> obviously viewed
                            setHasUnreadMessages(false);
                        }
                    } else {
                        // No history -> nothing to read
                        setHasUnreadMessages(false);
                    }
                }
            } catch (e) {
                console.error("Failed to load history", e);
            } finally {
                // Mark initial load as done after processing history
                setTimeout(() => {
                    isInitialLoad.current = false;
                }, 1000);
            }
        };

        fetchHistory();
    }, []); // Only fetch history once on mount

    // Unified Notification & Tracker Logic
    useEffect(() => {
        if (messages.length === 0) return;
        const currentIndex = messages.length - 1;

        if (isOpen) {
            // SCENARIO 1: Sidebar is OPEN. 
            // We are viewing the chat. Update "last seen" pointer immediately.
            // This prevents the "Close -> Notify" bug because we confirm we've seen this index.
            // Even if message is default/old, we mark it as seen.
            setLastTooltipMessageIndex(currentIndex);

            // Also ensure UI is clean
            if (hasUnreadMessages) {
                setHasUnreadMessages(false);
            }
        } else {
            // SCENARIO 2: Sidebar is CLOSED.
            // Check for NEW messages to notify about.
            if (isInitialLoad.current) return;

            const lastMessage = messages[currentIndex];

            // Only notify if it's Assistant AND (it's actually new)
            if (lastMessage.role === 'assistant' && currentIndex > lastTooltipMessageIndex) {
                setShowTooltip(true);
                setLastTooltipMessageIndex(currentIndex);
                setHasUnreadMessages(true);

                // Auto-hide tooltip
                const timer = setTimeout(() => {
                    setShowTooltip(false);
                }, 5000);
                return () => clearTimeout(timer);
            }
        }
    }, [messages, isOpen, lastTooltipMessageIndex, hasUnreadMessages]);

    // Server Sync Logic (Mark as Read)
    useEffect(() => {
        if (isOpen) {
            // When opened, always try to mark as read on server (idempotent)
            markAsRead().catch(console.error);
        }
    }, [isOpen]);

    // Click Outside Logic
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (isOpen && sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
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

        // Add User Message (Optimistic)
        setMessages(prev => [...prev, { role: 'user', text: userText }]);
        setIsTyping(true);

        // Add Placeholder for Assistant Message
        setMessages(prev => [...prev, { role: 'assistant', text: "" }]);

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            const res = await fetch(`${API_URL}/chat/completions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    messages: [...messages, { role: 'user', text: userText }].map(m => ({ role: m.role, content: m.text })),
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

                // Update the last message (assistant's placeholder)
                setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastMsg = newMsgs[newMsgs.length - 1];
                    if (lastMsg.role === 'assistant') {
                        lastMsg.text = accumulatedText;
                    }
                    return newMsgs;
                });
            }

        } catch (e: any) {
            console.error("Chat Error:", e);
            setMessages(prev => {
                const newMsgs = [...prev];
                if (newMsgs[newMsgs.length - 1].text === "") {
                    newMsgs[newMsgs.length - 1].text = `Прошу прощения, произошла ошибка соединения. (${e.message || "Unknown error"})`;
                }
                return newMsgs;
            });
        } finally {
            setIsTyping(false);
        }
    };

    return (
        <div ref={sidebarRef}>
            {/* Collapsed Tab (Always Visible when closed) */}
            <button
                onClick={() => {
                    toggle();
                    setShowTooltip(false); // Hide tooltip when opening
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

                    {/* Red Badge (visible when there are unread messages) */}
                    {!isOpen && hasUnreadMessages && (
                        <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-red-500 rounded-full border-2 border-white pointer-events-none"></div>
                    )}

                    {/* Tooltip Animation (shows only for NEW messages) */}
                    {FEATURE_TOOLTIP_ANIMATION && showTooltip && !isOpen && (
                        <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-[#206ecf] text-white text-xs px-3 py-2 rounded-lg shadow-lg whitespace-nowrap animate-fade-in-right">
                            У вас новое сообщение! 💬
                            <div className="absolute left-full top-1/2 -translate-y-1/2 border-4 border-transparent border-l-[#206ecf]"></div>
                        </div>
                    )}
                </div>
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest [writing-mode:vertical-rl] rotate-180">
                    AI Помощник
                </span>
            </button>


            {/* Expanded Sidebar (Drawer) */}
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
                    {messages.map((msg, idx) => {
                        // Skip rendering empty assistant bubbles (ghost bubbles)
                        if (msg.role === 'assistant' && !msg.text) return null;

                        return (
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
                        );
                    })}

                    {/* Typing Indicator */}
                    {isTyping && messages[messages.length - 1].role === 'user' && (
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
