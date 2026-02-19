"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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

        // 🔔 Listen for notification bell click
        const handleOpenSidebar = () => setIsOpen(true);
        window.addEventListener("openRightSidebar", handleOpenSidebar);

        return () => {
            window.removeEventListener("openRightSidebar", handleOpenSidebar);
        };
    }, [searchParams]);

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
                headers: {
                    Authorization: `Bearer ${token}`,
                    "X-Caller-Source": "RightSidebar"
                }
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

    // Ref to track generation status (prevents loops)
    const isGeneratingRef = useRef(false);

    // --- STREAMING HELPER (SMART RESUME) ---
    const streamResponse = async (currentMessages: { role: 'user' | 'assistant', text: string }[], saveUserMessage: boolean = true) => {
        const token = Cookies.get("token");
        if (!token) return;

        // Prevent concurrent generations
        if (isGeneratingRef.current) return;
        isGeneratingRef.current = true;

        setIsTyping(true);
        setStreamingMessage("");

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            // Prepare context
            // Note: 'messages' in state has 'created_at', but API expects clean {role, content}
            const contextMessages = currentMessages.map(m => ({ role: m.role, content: m.text }));

            const res = await fetch(`${API_URL}/chat/completions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    messages: contextMessages,
                    agent_id: "main_assistant",
                    webinar_id: null,
                    save_user_message: saveUserMessage, // 🚀 Key Param
                    page_context: {
                        url: window.location.pathname,
                        title: document.title
                    }
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
                setStreamingMessage(accumulatedText);
            }

            // Order important: Add to history -> Clear stream
            setMessages(prev => [...prev, { role: 'assistant', text: accumulatedText, created_at: new Date().toISOString() }]);
            setStreamingMessage("");

        } catch (e: any) {
            console.error("Chat Error:", e);
            setMessages(prev => [...prev, {
                role: 'assistant',
                text: `Прошу прощения, произошла ошибка соединения. (${e.message || "Unknown error"})`
            }]);
        } finally {
            setIsTyping(false);
            setStreamingMessage("");
            isGeneratingRef.current = false;
        }
    };

    // Load History Logic
    useEffect(() => {
        const fetchHistory = async (shouldMarkReadRefetch = true) => {
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
                        wasHistoryEmpty.current = false;

                        const lastAssistantMsg = uiMsgs[uiMsgs.length - 1];
                        if (lastAssistantMsg.role === 'assistant') {
                            const msgTime = parseDate(lastAssistantMsg.created_at);
                            setHasUnreadMessages(msgTime > lastReadServer);
                        } else {
                            setHasUnreadMessages(false);
                            // If last is user, and we are opening/active, we might want to mark read?
                            // But RightSidebar has separate markAsRead effect when open.
                        }


                        // 🚀 SMART RESUME: RESTORED (ONE-SHOT RETRY)
                        // Logic: If the server crashed, we try to resume ONCE.
                        // We use sessionStorage to act as a "Retry Counter = 1".
                        const lastMsg = uiMsgs[uiMsgs.length - 1];

                        // Check if we already tried to recover this specific message
                        const msgId = lastMsg.created_at || "unknown";
                        const retryKey = `smart_resume_attempt_${msgId}`;
                        const alreadyRetried = sessionStorage.getItem(retryKey);

                        // Condition: Last is User AND Not Generating AND Initial Load AND Not Retried yet
                        if (lastMsg.role === 'user' && !isGeneratingRef.current && isInitialLoad.current) {
                            if (!alreadyRetried) {
                                console.log("🚀 [Smart Resume] Crash recovery triggered. Attempt 1/1.");

                                // Mark as retried immediately
                                try {
                                    sessionStorage.setItem(retryKey, "true");
                                } catch (e) { /* ignore storage errors */ }

                                streamResponse(uiMsgs, false);
                            } else {
                                console.log("⚠️ [Smart Resume] Skipped. Max retries (1) reached for this message.");
                            }
                        }

                    } else {
                        // History was EMPTY (new user)
                        setHasUnreadMessages(false);
                        wasHistoryEmpty.current = true;
                    }
                } else {
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

        fetchHistory(true);
    }, []);

    // 🔔 UNIFIED NOTIFICATION LOGIC
    // Uses localStorage to track seen messages (prevent nagging but allow persistent notification)
    useEffect(() => {
        if (isOpen) {
            // SCENARIO 1: Sidebar is OPEN. 
            // We see everything. Clear alerts.
            if (hasUnreadMessages) setHasUnreadMessages(false);
            if (showTooltip) setShowTooltip(false);

            // Mark all current COMMITTED messages as seen in LocalStorage
            if (messages.length > 0) {
                const lastMsg = messages[messages.length - 1];
                setLastTooltipMessageIndex(messages.length - 1);

                // Save ID to prevent future alerts for this message
                if (lastMsg.created_at) {
                    localStorage.setItem("lastSeenTooltipMessageId", lastMsg.created_at);
                }
            }
        } else {
            // SCENARIO 2: Sidebar is CLOSED.
            const currentIndex = messages.length - 1;
            const lastMessage = messages[currentIndex];

            // Check if we have a valid assistant message with timestamp (ID)
            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.created_at) {
                const msgId = lastMessage.created_at;
                const seenMsgId = localStorage.getItem("lastSeenTooltipMessageId");

                // Logic: Show tooltip IF:
                // 1. Message ID is different from what we last saw (New message for us)
                // 2. AND the message is actually Unread (Red dot is active)
                if (msgId !== seenMsgId && hasUnreadMessages) {
                    console.log("✅ SHOWING TOOLTIP (Smart Notification)");
                    setShowTooltip(true);
                    setLastTooltipMessageIndex(currentIndex);

                    // Mark as "Seen Notification" immediately so we don't nag on refresh
                    localStorage.setItem("lastSeenTooltipMessageId", msgId);

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
                refetchHistory(); // No markAsRead here by default? 
                // Ah, the main fetchHistory WAS NOT calling markAsRead in RightSidebar.
                // RightSidebar calls markAsRead in a SEPARATE useEffect [isOpen].

                // Let's verify RightSidebar lines 316+
                // useEffect(() => { if(isOpen) markAsRead() }, [isOpen, messages.length])

                // So RightSidebar loop risk:
                // 1. SSE arrives -> refetchHistory -> update messages
                // 2. messages.length changes -> useEffect calls markAsRead()
                // 3. markAsRead() -> POST /read -> SSE "chatReadUpdate"
                // 4. SSE "chatReadUpdate" -> handleChatUpdate?

                // context/SSEContext.tsx handles "chatReadUpdate" by broadcasting "chatStatusUpdate"
                // RightSidebar listens to "chatStatusUpdate".

                // SO YES, RightSidebar HAS A LOOP too.
                // messages update -> markAsRead -> SSE -> messages update.

                // Fix: MarkAsRead should only fire if we are OPEN and the message is NEW and NOT READ.
                // But markAsRead just blindly posts.

                // Let's break the SSE listener loop first.
                // If the event is 'chatReadUpdate', we should maybe NOT refetch?
                // But we don't know the event type here, it's just 'chatStatusUpdate' window event.

                // Logic:
                // Only refetch if !isOpen.
                // If !isOpen, we don't trigger the markAsRead effect.
                // So the loop implies isOpen?

                // If isOpen:
                // handleChatUpdate condition: if (!isOpen && ...)
                // So if isOpen, handleChatUpdate DOES NOTHING.

                // So loop only happens if isOpen=false?
                // If isOpen=false:
                // SSE -> refetch -> setMessages -> useEffect(markAsRead) runs?
                // No, useEffect(markAsRead) checks `if (isOpen)`.

                // So RightSidebar loop is unlikely if isOpen=false.

                // What about when isOpen=true?
                // SSE listener DOES NOTHING.

                // Wait, if isOpen=true, we rely on `window.dispatchEvent`?
                // No, when isOpen, we rely on... nothing?

                // User said: "Notification bell responsiveness" which implies Sidebar Closed.
                // The loop in logs showed `/chat/history` calls.

                // Let's look at AgentPage again.
                // AgentPage was definitely looping because it called markAsRead inside fetchHistory.

                // RightSidebar seems safer regarding markAsRead.
                // Use strict refetch logic anyway to be safe.

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
        const tempUserMsg = { role: 'user' as const, text: userText, created_at: new Date().toISOString() };
        setMessages(prev => [...prev, tempUserMsg]);

        // 2. Trigger Smart Response (Clean separate function)
        await streamResponse([...messages, tempUserMsg], true);
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
                                    <div className="prose prose-sm max-w-none text-inherit prose-strong:text-gray-900 prose-strong:font-bold">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* 2. Active Streaming Message (Assistant) */}
                    {isTyping && streamingMessage && (
                        <div className="flex justify-start">
                            <div className="max-w-[85%] bg-white border border-gray-100 rounded-2xl rounded-tl-none px-4 py-3 text-sm leading-relaxed shadow-sm text-gray-800">
                                <div className="prose prose-sm max-w-none text-inherit prose-strong:text-gray-900 prose-strong:font-bold">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingMessage}</ReactMarkdown>
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
