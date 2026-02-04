"use client";

import { useState, useEffect, useRef, memo } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
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
    is_upcoming: boolean; // Ensure this is mapped!
    category?: string;
    speaker?: string;
    duration?: string;
}

// --- Helper Functions ---
// ... (keep usage same if possible, but replace tool matches exactly)
const getIframeHtml = (iframeString?: string) => {
    if (!iframeString) return null;
    if (iframeString.includes("<iframe")) return iframeString;

    let src = iframeString;
    const vkMatch = iframeString.match(/video(-?\d+)_(\d+)/);
    if (vkMatch) {
        src = `https://vk.com/video_ext.php?oid=${vkMatch[1]}&id=${vkMatch[2]}&hd=2`;
    } else if (iframeString.includes("youtube.com/watch?v=")) {
        src = iframeString.replace("watch?v=", "embed/");
    } else if (iframeString.includes("youtu.be/")) {
        src = iframeString.replace("youtu.be/", "youtube.com/embed/");
    }

    return `<iframe src="${src}" width="100%" height="100%" frameborder="0" allow="autoplay; encrypted-media; fullscreen; picture-in-picture"></iframe>`;
};

// ... (VideoPlayer omitted for brevity, Assuming I target interface separately?)
// I will split into multiple chunks in next turn if I can't match big block.
// Let's try matching interface first.

// Oh, I need to match specific block.
// I will specific replacing interface and then fetchLogic.


// --- Memoized Video Player to prevent re-renders on Chat Input ---
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
    const searchParams = useSearchParams();
    const id = params.id as string;
    const type = searchParams.get("type"); // 'library' or 'upcoming'

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
                // EXPLICIT ROUTING: Use specific endpoints based on type to avoid ID collisions
                let endpoint = `${API_URL}/webinars/${id}`;
                if (type === 'library') {
                    endpoint = `${API_URL}/webinars/library/${id}`;
                } else if (type === 'upcoming') {
                    endpoint = `${API_URL}/webinars/upcoming/${id}`;
                }

                const res = await fetch(endpoint, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const data = await res.json();

                    // CLEANUP: Remove "STOP" from description if present
                    let cleanDesc = data.description || "";
                    cleanDesc = cleanDesc.replace(/STOP$/i, "").trim();

                    setWebinar({
                        ...data,
                        description: cleanDesc,
                        // Fill defaults if missing
                        category: "AI Education",
                        speaker: "Дмитрий Романов",
                        duration: "1:00:00",
                        date: new Date(data.created_at).toLocaleDateString("ru-RU", {
                            day: 'numeric', month: 'long', year: 'numeric'
                        }),
                        iframe: data.video_url,
                        // Ensure optional fields are passed
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
    }, [id, router, type]);

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

    // 2. Fetch Chat History
    useEffect(() => {
        const fetchHistory = async () => {
            const token = Cookies.get("token");
            if (!token) return;

            try {
                const url = new URL(`${API_URL}/chat/history`);
                url.searchParams.append("webinar_id", id);
                url.searchParams.append("agent_id", "mentor");

                const res = await fetch(url.toString(), {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const hist = await res.json();
                    if (hist && hist.length > 0) {
                        const uiMsgs = hist.map((m: any) => ({
                            role: m.role,
                            text: m.content
                        }));
                        setMessages(uiMsgs);
                    } else {
                        setMessages([
                            { role: 'assistant', text: `Привет! Я ваш AI-тьютор по этому вебинару. Спрашивайте что угодно по теме!` }
                        ]);
                    }
                }
            } catch (e) {
                console.error("History error", e);
            }
        };

        if (id) fetchHistory();
    }, [id]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isTyping]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const token = Cookies.get("token");
        const userText = input;

        setMessages(prev => [...prev, { role: 'user', text: userText }]);
        setInput("");
        setIsTyping(true);

        try {
            const res = await fetch(`${API_URL}/chat/completions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    messages: [...messages, { role: 'user' as const, text: userText }].map(m => ({ role: m.role, content: m.text })),
                    agent_id: "mentor",
                    webinar_id: parseInt(id)
                })
            });

            if (!res.ok) throw new Error("API Error");
            if (!res.body) throw new Error("No body");

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            setMessages(prev => [...prev, { role: 'assistant', text: "" }]);
            let accumulatedText = "";
            let firstChunk = true;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                // Hide typing indicator when first chunk arrives
                if (firstChunk) {
                    setIsTyping(false);
                    firstChunk = false;
                }

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
            setMessages(prev => [...prev, { role: 'assistant', text: "Ошибка сети. Попробуйте позже." }]);
            setIsTyping(false);
        }
    };

    const [activeTab, setActiveTab] = useState<'info' | 'chat'>('info');

    if (loading) return <div className="p-8 text-center text-gray-500">Загрузка урока...</div>;
    if (!webinar) return <div className="p-8 text-center text-gray-500">Вебинар не найден</div>;

    const chatContent = (
        <div className="flex flex-col h-full w-full bg-white lg:border-l lg:border-gray-100 overflow-hidden">
            {/* Chat Header - Visible only on Desktop (lg) because mobile has Tabs */}
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

                {isTyping && (
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

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 py-6 border-t border-gray-100 border-b mb-8 w-full">
                <div className="min-w-0">
                    <div className="text-xs text-gray-400 uppercase mb-1 font-bold">Спикер</div>
                    <div className="font-medium text-gray-900 break-words">{webinar.speaker}</div>
                </div>
                <div className="min-w-0">
                    <div className="text-xs text-gray-400 uppercase mb-1 font-bold">Дата</div>
                    <div className="font-medium text-gray-900 break-words">{webinar.date}</div>
                </div>
                <div className="min-w-0">
                    <div className="text-xs text-gray-400 uppercase mb-1 font-bold">Длительность</div>
                    <div className="font-medium text-gray-900">{webinar.duration}</div>
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
            {/* Breadcrumbs - Hidden on Mobile/Tablet to save space, visible on Desktop */}
            <div className="hidden lg:flex mb-3 items-center gap-2 text-sm text-gray-500 px-1 w-full min-w-0 shrink-0">
                <Link href="/platform/webinars" className="hover:text-[#206ecf] transition-colors shrink-0">Библиотека</Link>
                <span className="shrink-0">/</span>
                <span className="text-gray-900 font-medium truncate min-w-0">{webinar.title}</span>
            </div>

            {/* Desktop Layout */}
            <div ref={containerRef} className="hidden lg:flex flex-1 overflow-hidden bg-white rounded-2xl shadow-sm border border-gray-100 relative w-full">
                {/* Left: Video & Content */}
                <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                    {/* Desktop: Logic to show Cover for Upcoming, Video for Library */}
                    {webinar.is_upcoming ? (
                        <div className="w-full aspect-video bg-gray-100 relative overflow-hidden flex items-center justify-center">
                            {webinar.thumbnail_url ? (
                                <img
                                    src={webinar.thumbnail_url}
                                    alt={webinar.title}
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                <div className="flex flex-col items-center gap-3 text-gray-400">
                                    <div className="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center">
                                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                    </div>
                                    <span className="font-medium">Вебинар скоро начнется</span>
                                </div>
                            )}
                            {/* Overlay Gradient */}
                            <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent flex items-end p-6">
                                <div className="text-white">
                                    <p className="font-bold text-lg mb-1">Запланировано на {webinar.date}</p>
                                    <p className="text-sm opacity-90">Подключитесь по кнопке ниже перед началом</p>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <VideoPlayer iframe={webinar.iframe} />
                    )}
                    <div className="flex-1 overflow-y-auto custom-scrollbar w-full">
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
                    {webinar.is_upcoming ? (
                        <div className="w-full aspect-video bg-gray-100 relative overflow-hidden flex items-center justify-center">
                            {webinar.thumbnail_url ? (
                                <img
                                    src={webinar.thumbnail_url}
                                    alt={webinar.title}
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                <div className="flex flex-col items-center gap-2 text-gray-500 text-sm">
                                    <span>📅 Вебинар скоро начнется</span>
                                </div>
                            )}
                        </div>
                    ) : (
                        <VideoPlayer iframe={webinar.iframe} />
                    )}
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
