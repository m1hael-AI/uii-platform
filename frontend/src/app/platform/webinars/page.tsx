"use client";

import Link from "next/link";
import { useState, useEffect, useRef, useCallback } from "react";
import Cookies from "js-cookie";
import { motion, AnimatePresence } from "framer-motion";

interface Webinar {
    id: number;
    title: string;
    description: string;
    video_url: string; // iframe src
    thumbnail_url?: string;
    is_upcoming: boolean;
    is_published: boolean;
    date?: string; // formatted date string
    conducted_at?: string; // ISO date for sorting
    created_at?: string; // ISO date for sorting
    category?: string;
    speaker?: string;
    duration?: string;
}

const ITEMS_PER_PAGE = 20;

export default function WebinarsPage() {
    const [webinars, setWebinars] = useState<Webinar[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);

    // UI State
    const [selectedCategory, setSelectedCategory] = useState("Все");
    const [searchQuery, setSearchQuery] = useState("");
    const [sortOrder, setSortOrder] = useState<"newest" | "oldest">("newest");
    const [isSortOpen, setIsSortOpen] = useState(false);
    const sortRef = useRef<HTMLDivElement>(null);

    // AI Search State
    const [isSearching, setIsSearching] = useState(false);
    const [searchResults, setSearchResults] = useState<Webinar[] | null>(null);

    // Close sort dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (sortRef.current && !sortRef.current.contains(event.target as Node)) {
                setIsSortOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    // Intersection Observer ref
    const observerTarget = useRef<HTMLDivElement>(null);

    // Fetch Data
    const fetchWebinars = useCallback(async (pageNum: number, isInitial = false) => {
        if (isInitial) {
            setLoading(true);
        } else {
            setIsLoadingMore(true);
        }

        const token = Cookies.get("token");
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

        try {
            const offset = (pageNum - 1) * ITEMS_PER_PAGE;
            const res = await fetch(`${API_URL}/webinars?filter_type=library&limit=${ITEMS_PER_PAGE}&offset=${offset}`, {
                headers: { Authorization: `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();

                // Transform API data to UI data (NO hardcoded defaults)
                const enhancedData = data.map((w: any) => ({
                    ...w,
                    category: w.category || "Общее",
                    speaker: w.speaker_name || "Не указан",
                    duration: w.duration || "Не указано",
                    video_url: w.video_url || "",
                    date: new Date(w.conducted_at || w.created_at).toLocaleDateString("ru-RU", {
                        day: 'numeric', month: 'long', year: 'numeric'
                    })
                }));

                if (isInitial) {
                    setWebinars(enhancedData);
                } else {
                    setWebinars(prev => [...prev, ...enhancedData]);
                }

                setHasMore(data.length === ITEMS_PER_PAGE);
            }
        } catch (e) {
            console.error("Failed to fetch webinars", e);
        } finally {
            setLoading(false);
            setIsLoadingMore(false);
        }
    }, []);

    // Initial load
    useEffect(() => {
        fetchWebinars(1, true);
    }, [fetchWebinars]);

    // AI Search — запускается только понажатию Enter или кнопке «Найти»
    const runSearch = async (query: string) => {
        const q = query.trim();
        if (!q) {
            setSearchResults(null);
            return;
        }
        setIsSearching(true);
        try {
            const token = Cookies.get("token");
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const res = await fetch(
                `${API_URL}/webinars/search?q=${encodeURIComponent(q)}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            if (res.ok) {
                const data = await res.json();
                const enhanced = data.map((w: any) => ({
                    ...w,
                    category: w.category || "Общее",
                    speaker: w.speaker_name || "Не указан",
                    duration: w.duration || "Не указано",
                    video_url: w.video_url || "",
                    date: new Date(w.conducted_at || w.created_at).toLocaleDateString("ru-RU", {
                        day: 'numeric', month: 'long', year: 'numeric'
                    })
                }));
                setSearchResults(enhanced);
            } else {
                console.error("Search API error", res.status);
                setSearchResults([]);
            }
        } catch (e) {
            console.error("Search failed", e);
            setSearchResults([]);
        } finally {
            setIsSearching(false);
        }
    };


    // Intersection Observer for infinite scroll
    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                if (entries[0].isIntersecting && hasMore && !isLoadingMore && !loading) {
                    setPage(prev => prev + 1);
                }
            },
            { threshold: 0.1 }
        );

        if (observerTarget.current) {
            observer.observe(observerTarget.current);
        }

        return () => {
            if (observerTarget.current) {
                observer.unobserve(observerTarget.current);
            }
        };
    }, [hasMore, isLoadingMore, loading]);

    // Load more when page changes
    useEffect(() => {
        if (page > 1) {
            fetchWebinars(page);
        }
    }, [page, fetchWebinars]);

    // Derived State
    const categories = ["Все", ...Array.from(new Set(webinars.map(w => w.category || "General")))];

    // Активный источник данных: результаты поиска ИЛИ полный список вебинаров
    const activeWebinars = searchResults !== null ? searchResults : webinars;

    const filteredWebinars = activeWebinars.filter((webinar) => {
        const matchesCategory = selectedCategory === "Все" || webinar.category === selectedCategory;
        return matchesCategory;
    }).sort((a, b) => {
        const dateA = new Date(a.conducted_at || a.created_at || 0).getTime();
        const dateB = new Date(b.conducted_at || b.created_at || 0).getTime();
        return sortOrder === "newest" ? dateB - dateA : dateA - dateB;
    });

    // Helper: Get raw HTML or wrap URL with smart transformation
    const getCardIframe = (iframeHtml?: string) => {
        if (!iframeHtml) return null;

        // 1. If it's already an iframe tag
        if (iframeHtml.includes("<iframe")) {
            if (!iframeHtml.includes('loading="lazy"')) {
                return iframeHtml.replace("<iframe", '<iframe loading="lazy"');
            }
            return iframeHtml;
        }

        // 2. Smart Transformation
        let src = iframeHtml;
        // VK Video Logic
        const vkMatch = iframeHtml.match(/video(-?\d+)_(\d+)/);
        if (vkMatch) {
            src = `https://vk.com/video_ext.php?oid=${vkMatch[1]}&id=${vkMatch[2]}&hd=2`;
        }
        // YouTube Logic
        else if (iframeHtml.includes("youtube.com/watch?v=")) {
            src = iframeHtml.replace("watch?v=", "embed/");
        } else if (iframeHtml.includes("youtu.be/")) {
            src = iframeHtml.replace("youtu.be/", "youtube.com/embed/");
        }

        return `<iframe src="${src}" width="100%" height="100%" frameborder="0" allow="autoplay; encrypted-media; fullscreen; picture-in-picture" loading="lazy" referrerPolicy="no-referrer-when-downgrade"></iframe>`;
    };

    return (
        <div className="w-full max-w-full md:max-w-7xl mx-auto px-0 md:px-6">

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
                <div>
                    <h1 className="text-3xl font-light text-[#474648] mb-2">Библиотека вебинаров</h1>
                    <p className="text-[#7e95b1]">Архив прошедших вебинаров и лекций</p>
                </div>

                <div className="flex flex-col md:flex-row gap-3 w-full md:w-auto">
                    {/* Search row — единое поле с кнопкой-иконкой внутри */}
                    <div className="relative flex-1 md:flex-initial">
                        <input
                            type="text"
                            placeholder="AI-поиск по темам..."
                            value={searchQuery}
                            onChange={(e) => {
                                setSearchQuery(e.target.value);
                                if (!e.target.value.trim()) setSearchResults(null);
                            }}
                            onKeyDown={(e) => e.key === "Enter" && runSearch(searchQuery)}
                            className="w-full md:w-96 pl-4 pr-12 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-[#206ecf]/20 focus:border-[#206ecf] outline-none transition-all text-[#474648]"
                        />
                        {/* Синяя кнопка-иконка внутри поля справа — фиксированный размер, нет дёрганий */}
                        <button
                            onClick={() => runSearch(searchQuery)}
                            disabled={isSearching}
                            className="absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center bg-[#206ecf] hover:bg-[#1a5aad] disabled:opacity-70 rounded-lg transition-colors"
                        >
                            {isSearching ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                            )}
                        </button>
                    </div>

                    {/* Custom Styled Sort */}
                    <div className="relative flex-1 md:flex-initial" ref={sortRef}>
                        <button
                            onClick={() => setIsSortOpen(!isSortOpen)}
                            className="w-full md:w-48 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-[#474648] flex items-center justify-between hover:border-[#206ecf] transition-colors focus:ring-2 focus:ring-[#206ecf]/20 focus:border-[#206ecf] outline-none"
                        >
                            <span>{sortOrder === "newest" ? "Сначала новые" : "Сначала старые"}</span>
                            <svg
                                className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isSortOpen ? 'rotate-180' : ''}`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </button>

                        <AnimatePresence>
                            {isSortOpen && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                    transition={{ duration: 0.2 }}
                                    className="absolute right-0 top-full mt-2 w-full bg-white border border-gray-100 rounded-xl shadow-xl overflow-hidden z-20"
                                >
                                    <button
                                        onClick={() => {
                                            setSortOrder("newest");
                                            setIsSortOpen(false);
                                        }}
                                        className={`w-full text-left px-4 py-2.5 text-sm transition-colors hover:bg-gray-50 flex items-center justify-between ${sortOrder === "newest" ? "text-[#206ecf] bg-blue-50/50" : "text-[#474648]"
                                            }`}
                                    >
                                        <span>Сначала новые</span>
                                        {sortOrder === "newest" && (
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                        )}
                                    </button>
                                    <button
                                        onClick={() => {
                                            setSortOrder("oldest");
                                            setIsSortOpen(false);
                                        }}
                                        className={`w-full text-left px-4 py-2.5 text-sm transition-colors hover:bg-gray-50 flex items-center justify-between ${sortOrder === "oldest" ? "text-[#206ecf] bg-blue-50/50" : "text-[#474648]"
                                            }`}
                                    >
                                        <span>Сначала старые</span>
                                        {sortOrder === "oldest" && (
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                        )}
                                    </button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* Categories */}
            <div className="flex flex-wrap gap-2 mb-8 border-b border-gray-100 pb-4">
                {categories.map((category) => (
                    <button
                        key={category}
                        onClick={() => setSelectedCategory(category)}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${selectedCategory === category
                            ? "bg-[#206ecf] text-white shadow-md shadow-blue-200"
                            : "bg-white text-gray-500 hover:bg-gray-50 hover:text-[#474648] border border-transparent hover:border-gray-200"
                            }`}
                    >
                        {category}
                    </button>
                ))}
            </div>

            {/* Grid */}
            {/* Loader Overlay within Grid */}
            {(loading || isLoadingMore) && !hasMore && (
                <div className="absolute inset-0 bg-white/80 z-50 flex items-start justify-center pt-24 backdrop-blur-sm transition-all duration-300">
                    <div className="flex flex-col items-center">
                        <div className="w-10 h-10 border-4 border-gray-100 border-t-[#206ecf] rounded-full animate-spin"></div>
                        <p className="text-gray-500 text-sm mt-3 font-medium">Загрузка...</p>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-fr">
                <AnimatePresence>
                    {filteredWebinars.map((webinar) => (
                        <motion.div
                            layout
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={{ duration: 0.2 }}
                            key={webinar.id}
                        >
                            <Link
                                href={`/platform/webinars/${webinar.id}`}
                                className="group block bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-lg hover:border-blue-100 transition-all duration-300 flex flex-col h-full relative"
                            >
                                {/* Thumbnail: Real Iframe behind a glass layer or Image */}
                                <div className="aspect-video bg-black relative">
                                    {/* Пытаемся получить картинку превью (Thumbnail) */}
                                    {(() => {
                                        // 1. Если есть явная картинка с бэкенда
                                        if (webinar.thumbnail_url && webinar.thumbnail_url.length > 10) {
                                            return (
                                                <img
                                                    src={webinar.thumbnail_url}
                                                    alt={webinar.title}
                                                    className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                                                />
                                            );
                                        }

                                        // 2. Пытаемся достать картинку из URL видео (YouTube / VK)
                                        // VK Video: https://vk.com/video_ext.php?oid=...&id=...
                                        // VK Thumb format: https://assets.vk.com/images/video/thumbs/default.jpg (Generic) - hard to guess real one without API
                                        // BUT we can use a placeholder for VK to avoid loading heavyweight iframe

                                        // YouTube
                                        if (webinar.video_url?.includes("youtube.com") || webinar.video_url?.includes("youtu.be")) {
                                            let vidId = "";
                                            if (webinar.video_url.includes("v=")) vidId = webinar.video_url.split("v=")[1]?.split("&")[0];
                                            else if (webinar.video_url.includes("embed/")) vidId = webinar.video_url.split("embed/")[1]?.split("?")[0];
                                            else if (webinar.video_url.includes("youtu.be/")) vidId = webinar.video_url.split("youtu.be/")[1]?.split("?")[0];

                                            if (vidId) {
                                                return (
                                                    <img
                                                        src={`https://img.youtube.com/vi/${vidId}/hqdefault.jpg`}
                                                        alt={webinar.title}
                                                        className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                                                    />
                                                );
                                            }
                                        }

                                        // Fallback for VK/Other: Show generic placeholder instead of IFRAME
                                        // Loading 20 iframes kills the page and causes 403.
                                        return (
                                            <div className="w-full h-full flex items-center justify-center text-gray-500 bg-gray-100 flex-col gap-2">
                                                <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-500 flex items-center justify-center">
                                                    <svg className="w-6 h-6 ml-1" fill="currentColor" viewBox="0 0 24 24">
                                                        <path d="M8 5v14l11-7z" />
                                                    </svg>
                                                </div>
                                                <span className="text-xs font-medium text-gray-400">Смотреть запись</span>
                                            </div>
                                        );
                                    })()}

                                    {/* Overlay (Glass) */}
                                    <div className="absolute inset-0 bg-transparent z-10 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                                    </div>
                                </div>

                                <div className="p-6 flex-1 flex flex-col z-20 bg-white">
                                    <div className="flex items-center justify-between mb-3 text-xs text-gray-400">
                                        <span>{webinar.date}</span>
                                        <span className="text-[#206ecf] bg-blue-50 px-2 py-0.5 rounded font-medium">{webinar.category}</span>
                                    </div>

                                    <h3 className="text-lg font-medium text-[#474648] mb-2 line-clamp-2 group-hover:text-[#206ecf] transition-colors leading-snug">
                                        {webinar.title}
                                    </h3>

                                    <p className="text-sm text-gray-500 mb-4 line-clamp-2 flex-1 leading-relaxed">
                                        {webinar.description}
                                    </p>

                                    <div className="flex items-center gap-3 pt-4 border-t border-gray-50 mt-auto">
                                        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500 shrink-0">
                                            {webinar.speaker?.charAt(0)}
                                        </div>
                                        <span className="text-xs text-gray-500 font-medium truncate">{webinar.speaker}</span>
                                    </div>
                                </div>
                            </Link>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            {/* Load More Button or Loading Indicator */}
            {
                hasMore && !loading && (
                    <div className="text-center py-8">
                        <div ref={observerTarget} className="h-4"></div>
                        {isLoadingMore && (
                            <div className="inline-block w-8 h-8 border-4 border-gray-200 border-t-[#206ecf] rounded-full animate-spin"></div>
                        )}
                    </div>
                )
            }

            {
                filteredWebinars.length === 0 && (!loading || webinars.length > 0) && (
                    <div className="text-center py-24">
                        <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
                            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        </div>
                        <h3 className="text-gray-900 font-medium mb-1">Ничего не найдено</h3>
                        <p className="text-gray-500 text-sm">Попробуйте изменить параметры поиска</p>
                    </div>
                )
            }
        </div >
    );
}
