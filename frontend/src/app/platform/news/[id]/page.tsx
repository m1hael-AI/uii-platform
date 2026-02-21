"use client";

import { useState, useEffect, useRef, memo } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { NewsService, NewsItem } from "@/services/news";

// Кастомные компоненты для ReactMarkdown
// [N] цитаты → маленький оранжевый superscript-кружок (стиль Perplexity)
// Обычные ссылки → оранжевый подчёркнутый текст, новая вкладка
const markdownComponents = {
    a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
        const text = String(children ?? "");
        const isCitation = /^\[\d+\]$/.test(text);
        const num = text.replace(/[\[\]]/g, "");
        if (isCitation) {
            return (
                <a href={href} target="_blank" rel="noopener noreferrer" title={href} className="no-underline">
                    <sup className="inline-flex items-center justify-center w-[16px] h-[16px] text-[9px] font-semibold text-[#ff8a35] bg-[#ff8a35]/10 rounded-full hover:bg-[#ff8a35]/20 transition-colors ml-0.5 cursor-pointer">
                        {num}
                    </sup>
                </a>
            );
        }
        return (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#ff8a35] hover:text-[#e67a2e] underline decoration-[#ff8a35]/40 transition-colors">
                {children}
            </a>
        );
    },
};

export default function ArticlePage() {
    const { id } = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();
    const backQuery = searchParams.get("back") || "";
    const newsId = Number(id);

    const [article, setArticle] = useState<NewsItem | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Polling ref — to clear interval on unmount or success
    const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const MAX_POLL_ATTEMPTS = 30; // 30 * 5s = 2.5 min max wait
    const pollAttemptsRef = useRef(0);

    // Resizable logic (Desktop)
    const [chatWidth, setChatWidth] = useState(400); // Default wider for text heavy chat
    const [isDragging, setIsDragging] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    // Polling helper: checks every 5s until article is ready or max attempts exceeded
    const startPolling = (articleId: number) => {
        pollAttemptsRef.current = 0;
        pollingIntervalRef.current = setInterval(async () => {
            pollAttemptsRef.current += 1;

            if (pollAttemptsRef.current > MAX_POLL_ATTEMPTS) {
                // Gave up waiting — show a soft error with reload option
                clearInterval(pollingIntervalRef.current!);
                pollingIntervalRef.current = null;
                setGenerating(false);
                setError("Генерация занимает слишком долго. Пожалуйста, обновите страницу.");
                return;
            }

            try {
                const data = await NewsService.getNewsItem(articleId);
                if (data.status === "completed") {
                    clearInterval(pollingIntervalRef.current!);
                    pollingIntervalRef.current = null;
                    setArticle(data);
                    setGenerating(false);
                } else if (data.status === "failed") {
                    clearInterval(pollingIntervalRef.current!);
                    pollingIntervalRef.current = null;
                    setGenerating(false);
                    setError("Не удалось сгенерировать статью. Попробуйте позже.");
                }
                // If still 'processing' or 'pending' – keep polling silently
            } catch (pollErr) {
                console.warn("Polling request failed, will retry:", pollErr);
                // Network blip — don't stop polling, just skip this attempt
            }
        }, 5000);
    };

    // 1. Fetch Article
    useEffect(() => {
        if (!id) return;

        const loadArticle = async () => {
            try {
                const data = await NewsService.getNewsItem(newsId);

                if (data.status === "pending") {
                    setArticle(data);
                    setLoading(false);
                    setGenerating(true);
                    try {
                        const result = await NewsService.generateArticle(newsId);
                        setArticle(result.article);
                        setGenerating(false);
                    } catch (genError) {
                        // Connection timed out or dropped — backend may still be working.
                        // Switch to polling mode silently instead of showing an error.
                        console.warn("Generation request ended early, switching to polling:", genError);
                        startPolling(newsId);
                    }
                } else if (data.status === "processing") {
                    // Article is already being generated (opened from another tab / refresh)
                    setArticle(data);
                    setLoading(false);
                    setGenerating(true);
                    startPolling(newsId);
                } else {
                    setArticle(data);
                    setLoading(false);
                }
            } catch (err) {
                console.error("Failed to load article:", err);
                setError("Не удалось загрузить статью. Возможно, она была удалена.");
                setLoading(false);
            }
        };

        loadArticle();

        // Cleanup polling on unmount or id change
        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
        };
    }, [id]);

    // Resize Logic
    const startResizing = () => setIsDragging(true);
    const stopResizing = () => setIsDragging(false);

    const resize = (e: MouseEvent) => {
        if (isDragging && containerRef.current) {
            const containerRect = containerRef.current.getBoundingClientRect();
            const newWidth = containerRect.right - e.clientX;
            if (newWidth > 300 && newWidth < 800) {
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


    // --- CHAT LOGIC ---
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', text: string }[]>([]);
    const [input, setInput] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const streamResponse = async (currentMessages: { role: 'user' | 'assistant', text: string }[], saveUserMessage: boolean = true) => {
        const token = Cookies.get("token");
        if (!token) return;

        setIsTyping(true);
        if (saveUserMessage) {
            setMessages(prev => [...prev, { role: 'assistant', text: "" }]);
        } else {
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
                    agent_id: "news_analyst", // NEW AGENT
                    news_id: newsId,          // NEW CONTEXT
                    save_user_message: saveUserMessage,
                    page_context: {
                        url: window.location.pathname,
                        title: article?.title || document.title
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

    // Load History & Smart Resume
    useEffect(() => {
        if (!id) return;
        // Only fetch history (which triggers greeting) if article is ready
        if (article?.status !== 'completed') return;

        const fetchHistory = async () => {
            const token = Cookies.get("token");
            if (!token) return;

            try {
                const url = new URL(`${API_URL}/chat/history`);
                url.searchParams.append("news_id", id.toString());
                url.searchParams.append("agent_id", "news_analyst");

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

                        // Smart Resume
                        const lastMsg = uiMsgs[uiMsgs.length - 1];
                        if (lastMsg.role === 'user') {
                            console.log("🚀 [Smart Resume] Last message was User. Resuming...");
                            streamResponse(uiMsgs, false);
                        }
                    }
                }
            } catch (e) {
                console.error("History error", e);
            }
        };

        fetchHistory();
    }, [id, article?.status]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isTyping]);


    const handleSend = async () => {
        if (!input.trim() || isTyping) return;
        const userText = input;
        const newMessages = [...messages, { role: 'user' as const, text: userText }];
        setMessages(newMessages);
        setInput("");
        await streamResponse(newMessages, true);
    };

    const [activeTab, setActiveTab] = useState<'article' | 'chat'>('article');


    // --- RENDERING ---

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-[#FF6B35] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-600">Загрузка статьи...</p>
                </div>
            </div>
        );
    }

    if (error || !article) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-red-600 mb-4">{error || "Статья не найдена"}</p>
                    <Link
                        href={`/platform/news${backQuery ? `?q=${encodeURIComponent(backQuery)}` : ''}`}
                        className="text-[#FF6B35] hover:underline"
                    >
                        ← Вернуться к новостям
                    </Link>
                </div>
            </div>
        );
    }

    // Chat Component
    const chatContent = (
        <div className="flex flex-col h-full w-full bg-white lg:border-l lg:border-gray-100 overflow-hidden">
            <div className="hidden lg:flex p-4 bg-white border-b border-gray-100 items-center justify-between shadow-sm z-10 shrink-0 w-full">
                <div className="flex items-center gap-2 min-w-0">
                    <div className={`w-2 h-2 rounded-full shrink-0 ${isTyping ? 'bg-orange-400 animate-pulse' : 'bg-green-500'}`}></div>
                    <h3 className="font-bold text-gray-900 truncate">
                        {isTyping ? "AI пишет..." : "AI Новостной Аналитик"}
                    </h3>
                </div>
            </div>

            {/* Chat Messages Area */}
            <div className="flex-1 p-4 space-y-4 overflow-y-auto bg-gray-50/50 custom-scrollbar w-full min-h-0 relative">
                {(generating || article?.status === 'processing') && (
                    <div className="absolute inset-0 z-20 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center text-center p-6">
                        <div className="w-10 h-10 border-4 border-[#FF6B35] border-t-transparent rounded-full animate-spin mb-3"></div>
                        <h4 className="font-semibold text-gray-900">Анализирую новость...</h4>
                        <p className="text-sm text-gray-500 mt-1 max-w-xs">
                            Чат станет доступен после завершения генерации статьи.
                        </p>
                    </div>
                )}

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
                                    <div className="prose prose-sm max-w-none text-inherit prose-strong:text-gray-900 prose-strong:font-bold break-words">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{msg.text}</ReactMarkdown>
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

            <div className="p-4 bg-white border-t border-gray-100 shrink-0 w-full z-10">
                <div className="relative w-full">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !isTyping && !generating && article?.status !== 'processing' && handleSend()}
                        placeholder={generating || article?.status === 'processing' ? "Генерация новости..." : "Обсудить новость..."}
                        disabled={isTyping || generating || article?.status === 'processing'}
                        className={`w-full pl-4 pr-10 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#FF6B35]/20 focus:border-[#FF6B35] transition-all text-black ${isTyping || generating || article?.status === 'processing' ? "cursor-not-allowed opacity-70" : ""}`}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || isTyping || generating || article?.status === 'processing'}
                        className={`absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors ${input.trim() && !isTyping && !generating && article?.status !== 'processing'
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

    // Article Content
    const articleContent = (
        <article className="bg-white p-8 min-h-full">
            {/* Hero Image (only if available) — самый верх, над тегами */}
            {article.image_url && (
                <div className="mb-6 -mx-8 -mt-8 rounded-t-2xl overflow-hidden">
                    <img
                        src={article.image_url}
                        alt={article.title}
                        className="w-full max-h-[400px] object-cover"
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                    />
                </div>
            )}

            {/* Tags */}
            {article.tags && article.tags.length > 0 && (
                <div className="flex gap-2 mb-4">
                    {article.tags.map(tag => (
                        <span key={tag} className="text-xs px-3 py-1 bg-[#FF6B35]/10 text-[#FF6B35] rounded-full font-medium">
                            {tag}
                        </span>
                    ))}
                </div>
            )}

            {/* Title */}
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
                {article.title}
            </h1>

            {/* Meta */}
            <div className="flex items-center gap-4 text-sm text-gray-500 mb-6 pb-6 border-b border-gray-200">
                <span>
                    {new Date(article.published_at).toLocaleDateString("ru-RU", {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    })}
                </span>
                {article.source_urls && article.source_urls.length > 0 && (
                    <>
                        <span>•</span>
                        <span>{article.source_urls.length} источников</span>
                    </>
                )}
            </div>

            {/* Summary */}
            {article.summary && (
                <div className="bg-gray-50 border-l-4 border-[#FF6B35] p-4 mb-6">
                    <p className="text-gray-700 italic">{article.summary}</p>
                </div>
            )}

            {/* Content */}
            {generating ? (
                <div className="py-20 text-center">
                    <div className="w-16 h-16 border-4 border-[#FF6B35] border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
                    <h2 className="text-xl font-semibold text-gray-800 mb-2">📝 Генерирую полную статью...</h2>
                    <p className="text-gray-600 max-w-md mx-auto">
                        Агент анализирует источники и создаёт подробный материал.
                    </p>
                </div>
            ) : article.content ? (
                <div className="prose max-w-none pb-20 prose-h2:text-2xl prose-h2:mt-8 prose-h2:mb-4 prose-h3:text-xl prose-h3:mt-6 prose-h3:mb-3 prose-p:text-gray-700 prose-p:leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{article.content}</ReactMarkdown>
                </div>
            ) : (
                <p className="text-gray-500 italic">Полный текст статьи пока недоступен.</p>
            )}

            {/* Sources */}
            {article.source_urls && article.source_urls.length > 0 && (
                <div className="mt-8 pt-6 border-t border-gray-200">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Источники:</h3>
                    <ul className="space-y-2">
                        {article.source_urls.map((url, index) => (
                            <li key={index}>
                                <a
                                    href={url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-[#FF6B35] hover:underline flex items-center gap-2"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                    </svg>
                                    {new URL(url).hostname}
                                </a>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </article>
    );

    return (
        <div className="flex flex-col w-full h-[calc(100vh-6rem)] md:h-[calc(100vh-7rem)] bg-white lg:bg-transparent overflow-hidden">
            {/* Breadcrumbs (Desktop only) */}
            <div className="hidden lg:flex mb-3 items-center gap-2 text-sm text-gray-500 px-1 w-full min-w-0 shrink-0">
                <Link href="/platform/news" className="hover:text-[#FF6B35] transition-colors shrink-0">Новости</Link>
                <span className="shrink-0">/</span>
                <span className="text-gray-900 font-medium truncate min-w-0">{article.title}</span>
            </div>

            {/* Desktop Layout */}
            <div ref={containerRef} className="hidden lg:flex flex-1 overflow-hidden bg-white rounded-2xl shadow-sm border border-gray-100 relative w-full">
                {/* Left: Article */}
                <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                    <div className="flex-1 overflow-y-auto custom-scrollbar w-full">
                        {articleContent}
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

                {/* Right: AI Chat */}
                <div style={{ width: chatWidth }} className="flex flex-col shrink-0">
                    {chatContent}
                </div>
            </div>

            {/* Mobile Layout */}
            <div className="lg:hidden flex flex-col flex-1 bg-white overflow-hidden w-full">
                {/* Tabs */}
                <div className="flex border-b border-gray-100 bg-white shrink-0 w-full">
                    {/* Back Button (Mobile) */}
                    <Link href="/platform/news" className="flex items-center justify-center px-4 border-r border-gray-100 text-gray-500">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </Link>

                    <button
                        onClick={() => setActiveTab('article')}
                        className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'article'
                            ? "border-[#FF6B35] text-[#FF6B35]"
                            : "border-transparent text-gray-500"
                            }`}
                    >
                        Статья
                    </button>
                    <button
                        onClick={() => setActiveTab('chat')}
                        className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors flex items-center justify-center gap-2 ${activeTab === 'chat'
                            ? "border-[#FF6B35] text-[#FF6B35]"
                            : "border-transparent text-gray-500"
                            }`}
                    >
                        AI Аналитик
                        {messages.length > 1 && (
                            <span className="bg-orange-100 text-orange-600 text-[10px] px-1.5 py-0.5 rounded-full">
                                {messages.length - 1}
                            </span>
                        )}
                    </button>
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-hidden relative w-full">
                    {activeTab === 'article' ? (
                        <div className="h-full overflow-y-auto w-full">
                            {articleContent}
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
