"use client";

import { useState, useEffect, useRef, memo } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import ReactMarkdown from "react-markdown";

import WebinarAction from "@/components/WebinarAction";

interface Webinar {
    id: number;
    title: string;
    description: string;
    video_url: string;
    iframe?: string;
    thumbnail_url?: string;
    date?: string;
    scheduled_at?: string;
    connection_link?: string;
    is_upcoming: boolean;
    category?: string;
    speaker?: string;
    duration?: string;
}

// --- Helper Functions ---
const getIframeHtml = (iframeString?: string) => {
    if (!iframeString) return null;
    if (iframeString.includes("<iframe")) {
        // Inject referrerPolicy if not present
        if (!iframeString.includes("referrerPolicy")) {
            return iframeString.replace("<iframe", '<iframe referrerpolicy="no-referrer"');
        }
        return iframeString;
    }

    let src = iframeString;
    const vkMatch = iframeString.match(/video(-?\d+)_(\d+)/);
    if (vkMatch) {
        src = `https://vk.com/video_ext.php?oid=${vkMatch[1]}&id=${vkMatch[2]}&hd=2`;
    } else if (iframeString.includes("youtube.com/watch?v=")) {
        src = iframeString.replace("watch?v=", "embed/");
    } else if (iframeString.includes("youtu.be/")) {
        src = iframeString.replace("youtu.be/", "youtube.com/embed/");
    }

    return `<iframe src="${src}" width="100%" height="100%" frameborder="0" allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerPolicy="no-referrer-when-downgrade"></iframe>`;
};

// --- Memoized Video Player ---
const VideoPlayer = memo(({ iframe }: { iframe?: string }) => {
    return (
        <div className="w-full aspect-video bg-black">
            {iframe ? (
                <div
                    className="w-full h-full [&>iframe]:!w-full [&>iframe]:!h-full"
                    dangerouslySetInnerHTML={{ __html: getIframeHtml(iframe) || "" }}
                />
            ) : (
                <div className="w-full h-full flex items-center justify-center bg-gray-900 text-gray-500 flex-col gap-2">
                    <span>Видео недоступно</span>
                </div>
            )}
        </div>
    );
});
VideoPlayer.displayName = "VideoPlayer";

export default function WebinarPage() {
    const params = useParams();
    const router = useRouter();
    const id = params.id as string;

    const [webinar, setWebinar] = useState<Webinar | null>(null);
    const [loading, setLoading] = useState(true);

    // Resizable logic
    const [chatWidth, setChatWidth] = useState(350);
    const [isDragging, setIsDragging] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    // 1. Fetch Webinar Data
    useEffect(() => {
        const fetchWebinar = async () => {
            const token = Cookies.get("token");
            if (!token) {
                router.push("/login");
                return;
            }

            try {
                const res = await fetch(`${API_URL}/webinars/library/${id}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const data = await res.json();
                    let cleanDesc = data.description || "";
                    cleanDesc = cleanDesc.replace(/STOP$/i, "").trim();

                    setWebinar({
                        ...data,
                        description: cleanDesc,
                        category: data.category || "Общее",
                        speaker: data.speaker_name || "Не указан",
                        date: new Date(data.created_at).toLocaleDateString("ru-RU", {
                            day: 'numeric', month: 'long', year: 'numeric'
                        }),
                        iframe: data.video_url,
                        scheduled_at: data.scheduled_at,
                        connection_link: data.connection_link,
                        is_upcoming: data.is_upcoming ?? false
                    });
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };

        fetchWebinar();
    }, [id, router]);

    const startResizing = () => setIsDragging(true);
    const stopResizing = () => setIsDragging(false);

    const resize = (e: MouseEvent) => {
        if (isDragging && containerRef.current) {
            const containerRect = containerRef.current.getBoundingClientRect();
            const newWidth = containerRect.right - e.clientX;
            if (newWidth > 250 && newWidth < 800) {
                setChatWidth(newWidth);
            }
        }
    };

    useEffect(() => {
        if (isDragging) {
            window.addEventListener("mousemove", resize);
            window.addEventListener("mouseup", stopResizing);
        }
        return () => {
            window.removeEventListener("mousemove", resize);
            window.removeEventListener("mouseup", stopResizing);
        };
    }, [isDragging]);

    // Chat Logic
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', text: string }[]>([]);
    const [input, setInput] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // --- STREAMING HELPER (SMART RESUME) ---
    const streamResponse = async (currentMessages: { role: 'user' | 'assistant', text: string }[], saveUserMessage: boolean = true) => {
        const token = Cookies.get("token");
        if (!token) return;

        setIsTyping(true);
        if (saveUserMessage) {
            // Placeholder for new assistant message
            setMessages(prev => [...prev, { role: 'assistant', text: "" }]);
        } else {
            // If resuming, we just add the assistant placeholder, user msg is already there
            setMessages(prev => [...prev, { role: 'assistant', text: "" }]);
        }

        try {
            const res = await fetch(`${API_URL}/chat/completions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    messages: currentMessages.map(m => ({ role: m.role, content: m.text })),
                    agent_id: "ai_tutor",
                    webinar_id: parseInt(id),
                    save_user_message: saveUserMessage, // IMPORTANT: Backend must support this!
                    page_context: {
                        url: window.location.pathname,
                        title: document.title
                    }
                })
            });

            if (!res.ok) throw new Error("API Error");
            if (!res.body) throw new Error("No body");

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            let accumulatedText = "";
            let firstChunk = true;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                // Hide typing indicator (if we had a separate visual one) when first chunk arrives
                if (firstChunk) firstChunk = false;

                const chunk = decoder.decode(value, { stream: true });
                accumulatedText += chunk;

                setMessages(prev => {
                    const newMsgs = [...prev];
                    const last = newMsgs[newMsgs.length - 1];
                    if (last.role === 'assistant') last.text = accumulatedText;
                    return newMsgs;
                });
            }

        } catch (e) {
            console.error(e);
            setMessages(prev => {
                const newMsgs = [...prev];
                const last = newMsgs[newMsgs.length - 1];
                if (last.role === 'assistant') last.text = "Ошибка сети. Попробуйте позже.";
                return newMsgs;
            });
        } finally {
            setIsTyping(false);
        }
    };

    // 2. Fetch Chat History & Trigget Smart Resume
    useEffect(() => {
        const fetchHistory = async () => {
            const token = Cookies.get("token");
            if (!token) return;

            try {
                const url = new URL(`${API_URL}/chat/history`);
                url.searchParams.append("webinar_id", id);
                url.searchParams.append("agent_id", "ai_tutor");

                const res = await fetch(url.toString(), {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const hist = await res.json();
                    if (hist?.messages && hist.messages.length > 0) {
                        const uiMsgs = hist.messages.map((m: any) => ({
                            role: m.role,
                            text: m.content
                        }));
                        setMessages(uiMsgs);

                        // 🚀 SMART RESUME LOGIC
                        const lastMsg = uiMsgs[uiMsgs.length - 1];
                        if (lastMsg.role === 'user') {
                            console.log("🚀 [Smart Resume] Last message was User. Resuming generation...");
                            // Call streamResponse without saving user message to DB again
                            // Note: we pass uiMsgs directly as context
                            streamResponse(uiMsgs, false);
                        }
                    }
                }
            } catch (e) {
                console.error("History error", e);
            }
        };

        if (id) fetchHistory();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [id]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isTyping]);

    const handleSend = async () => {
        if (!input.trim() || isTyping) return;

        const userText = input;

        // Optimistic UI update
        const newMessages = [...messages, { role: 'user' as const, text: userText }];
        setMessages(newMessages);
        setInput("");

        // Trigger Streaming
        await streamResponse(newMessages, true);
    };

    const [activeTab, setActiveTab] = useState<'info' | 'chat'>('info');

    if (loading) return <div className="p-8 text-center text-gray-500">Загрузка урока...</div>;
    if (!webinar) return <div className="p-8 text-center text-gray-500">Вебинар не найден</div>;

    const chatContent = (
        <div className="flex flex-col h-full w-full bg-white lg:border-l lg:border-gray-100 overflow-hidden">
            {/* Chat Header */}
            <div className="hidden lg:flex p-4 bg-white border-b border-gray-100 items-center justify-between shadow-sm z-10 shrink-0 w-full">
                <div className="flex items-center gap-2 min-w-0">
                    <div className={`w-2 h-2 rounded-full shrink-0 ${isTyping ? 'bg-orange-400 animate-pulse' : 'bg-green-500'}`}></div>
                    <h3 className="font-bold text-gray-900 truncate">
                        {isTyping ? "AI пишет..." : "AI Тьютор"}
                    </h3>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 p-4 space-y-4 overflow-y-auto bg-gray-50/50 custom-scrollbar w-full min-h-0">
                {messages.map((msg, idx) => {
                    if (msg.role === 'assistant' && !msg.text) return null;
                    return (
                        <div key={idx} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm break-words overflow-wrap-anywhere ${msg.role === 'user'
                                ? 'bg-[#FF6B35] text-white rounded-tr-none'
                                : 'bg-white border border-gray-100 text-gray-800 rounded-tl-none'
                                }`}>
                                {msg.role === 'user' ? (
                                    msg.text
                                ) : (
                                    <div className="prose prose-sm max-w-none text-inherit dark:prose-invert break-words">
                                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}

                {isTyping && (messages.length === 0 || messages[messages.length - 1].role !== 'assistant' || !messages[messages.length - 1].text) && (
                    <div className="flex justify-start w-full">
                        <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center gap-1">
                            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input (Full Width) */}
            <div className="p-4 bg-white border-t border-gray-100 shrink-0 w-full z-10">
                <div className="relative w-full">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !isTyping && handleSend()}
                        placeholder="Спросить по видео..."
                        disabled={isTyping}
                        className={`w-full pl-4 pr-10 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#FF6B35]/20 focus:border-[#FF6B35] transition-all text-black ${isTyping ? "cursor-not-allowed opacity-70" : ""
                            }`}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || isTyping}
                        className={`absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors ${input.trim()
                            ? "text-[#ff8a35] hover:bg-orange-50"
                            : "text-gray-300 cursor-default"
                            }`}
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );

    const infoContent = (
        <div className="p-4 lg:p-8 w-full max-w-4xl mx-auto">
            <div className="flex items-start justify-between gap-4 mb-6 w-full">
                <div className="w-full min-w-0 flex-1">
                    <h1 className="text-xl lg:text-2xl font-bold text-[#474648] mb-2 break-words">{webinar.title}</h1>
                    <p className="text-gray-600 leading-relaxed whitespace-pre-wrap text-sm lg:text-base break-words">{webinar.description}</p>
                </div>
                <div className="shrink-0">
                    <WebinarAction webinar={webinar} />
                </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 py-6 border-t border-gray-100 border-b mb-8 w-full">
                <div className="min-w-0">
                    <div className="text-xs text-gray-400 uppercase mb-1 font-bold">Спикер</div>
                    <div className="font-medium text-gray-900 break-words">{webinar.speaker}</div>
                </div>
                <div className="min-w-0">
                    <div className="text-xs text-gray-400 uppercase mb-1 font-bold">Дата</div>
                    <div className="font-medium text-gray-900 break-words">{webinar.date}</div>
                </div>
                <div className="min-w-0">
                    <div className="text-xs text-gray-400 uppercase mb-1 font-bold">Категория</div>
                    <div className="font-medium text-[#206ecf] break-words">{webinar.category}</div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="flex flex-col w-full h-[calc(100vh-6rem)] md:h-[calc(100vh-7rem)] bg-white lg:bg-transparent overflow-hidden">
            {/* Breadcrumbs */}
            <div className="hidden lg:flex mb-3 items-center gap-2 text-sm text-gray-500 px-1 w-full min-w-0 shrink-0">
                <Link href="/platform/webinars" className="hover:text-[#206ecf] transition-colors shrink-0">Библиотека</Link>
                <span className="shrink-0">/</span>
                <span className="text-gray-900 font-medium truncate min-w-0">{webinar.title}</span>
            </div>

            {/* Desktop Layout */}
            <div ref={containerRef} className="hidden lg:flex flex-1 overflow-hidden bg-white rounded-2xl shadow-sm border border-gray-100 relative w-full">
                {/* Left: Video & Content */}
                <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                    <div className="flex-1 overflow-y-auto custom-scrollbar w-full">
                        <VideoPlayer iframe={webinar.iframe} />
                        {infoContent}
                    </div>
                </div>

                {/* Resizer Handle */}
                <div
                    onMouseDown={startResizing}
                    className="w-px cursor-col-resize bg-gray-200 hover:bg-[#FF6B35] transition-colors z-10 flex items-center justify-center relative group shrink-0"
                >
                    <div className="absolute w-4 h-full -left-2 z-20" />
                    <div className="w-1 h-8 bg-gray-300 rounded-full group-hover:bg-[#FF6B35] transition-colors absolute" />
                </div>

                {/* Right: AI Tutor Chat */}
                <div style={{ width: chatWidth }} className="flex flex-col shrink-0">
                    {chatContent}
                </div>
            </div>

            {/* Mobile Layout */}
            <div className="lg:hidden flex flex-col flex-1 bg-white overflow-hidden w-full">
                {/* Video Player (Sticky Top) */}
                <div className="shrink-0 bg-black w-full">
                    <VideoPlayer iframe={webinar.iframe} />
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-100 bg-white shrink-0 w-full">
                    <button
                        onClick={() => setActiveTab('info')}
                        className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'info'
                            ? "border-[#FF6B35] text-[#FF6B35]"
                            : "border-transparent text-gray-500"
                            }`}
                    >
                        Описание
                    </button>
                    <button
                        onClick={() => setActiveTab('chat')}
                        className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors flex items-center justify-center gap-2 ${activeTab === 'chat'
                            ? "border-[#FF6B35] text-[#FF6B35]"
                            : "border-transparent text-gray-500"
                            }`}
                    >
                        AI Тьютор
                        {messages.length > 1 && (
                            <span className="bg-orange-100 text-orange-600 text-[10px] px-1.5 py-0.5 rounded-full">
                                {messages.length - 1}
                            </span>
                        )}
                    </button>
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-hidden relative w-full">
                    {activeTab === 'info' ? (
                        <div className="h-full overflow-y-auto w-full">
                            {infoContent}
                        </div>
                    ) : (
                        <div className="h-full w-full">
                            {chatContent}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
