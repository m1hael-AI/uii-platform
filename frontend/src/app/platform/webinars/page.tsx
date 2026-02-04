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
    date?: string; // or scheduled_at
    category?: string; // API might not have this yet? Let's check API.
    speaker?: string; // API might not have this.
    duration?: string;
    // For now, if API lacks fields, we might need default values or add them to DB.
    // The current DB model has: title, description, video_url, thumbnail_url, transcript_context, is_upcoming, is_published, scheduled_at.
    // IT DOES NOT HAVE: category, speaker, duration.
    // I will use default values for now to keep the UI working.
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

                // Transform API data to UI data
                const enhancedData = data.map((w: any) => ({
                    ...w,
                    category: "AI Education",
                    speaker: w.speaker_name || "Дмитрий Романов",
                    duration: "1:00:00",
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

    // Reset on search/filter change
    useEffect(() => {
        setPage(1);
        setWebinars([]);
        setHasMore(true);
        fetchWebinars(1, true);
    }, [searchQuery, selectedCategory, fetchWebinars]);

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

    const filteredWebinars = webinars.filter((webinar) => {
        const matchesCategory = selectedCategory === "Все" || webinar.category === selectedCategory;
        const matchesSearch = webinar.title.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesCategory && matchesSearch;
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

        return `<iframe src="${src}" width="100%" height="100%" frameborder="0" allow="autoplay; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>`;
    };

    if (loading) return (
        <div className="flex h-screen items-center justify-center text-gray-400">
            Загрузка библиотеки...
        </div>
    );

    return (
        <div className="w-full max-w-full md:max-w-7xl mx-auto px-0 md:px-6">

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
                <div>
                    <h1 className="text-3xl font-light text-[#474648] mb-2">Библиотека вебинаров</h1>
                    <p className="text-[#7e95b1]">Архив прошедших вебинаров и лекций</p>
                </div>

                <div className="w-full md:w-auto relative">
                    <input
                        type="text"
                        placeholder="Поиск по темам..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full md:w-80 pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-[#206ecf]/20 focus:border-[#206ecf] outline-none transition-all text-[#474648]"
                    />
                    <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
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
            <div className="overflow-hidden p-1 -m-1">
                <motion.div
                    layout
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-fr"
                >
                    <AnimatePresence mode="popLayout">
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
                                        {webinar.thumbnail_url && webinar.thumbnail_url.length > 10 ? (
                                            // If thumbnail exists, use it as cover
                                            <img
                                                src={webinar.thumbnail_url}
                                                alt={webinar.title}
                                                className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                                            />
                                        ) : (
                                            // Fallback to Iframe preview or placeholder
                                            webinar.video_url ? (
                                                <div
                                                    className="w-full h-full pointer-events-none [&>iframe]:!w-full [&>iframe]:!h-full"
                                                    dangerouslySetInnerHTML={{ __html: getCardIframe(webinar.video_url) || "" }}
                                                />
                                            ) : (
                                                <div className="w-full h-full flex items-center justify-center text-gray-500 bg-gray-100">
                                                    🎬
                                                </div>
                                            )
                                        )}

                                        {/* Overlay (Glass) */}
                                        <div className="absolute inset-0 bg-transparent z-10 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                                            {/* Play Icon removed to reduce visual noise */}
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
                </motion.div>
            </div>

            {/* Loading More Indicator */}
            {isLoadingMore && (
                <div className="text-center py-8">
                    <div className="inline-block w-8 h-8 border-4 border-gray-200 border-t-[#206ecf] rounded-full animate-spin"></div>
                    <p className="text-gray-500 text-sm mt-3">Загрузка...</p>
                </div>
            )}

            {/* Intersection Observer Target */}
            <div ref={observerTarget} className="h-4"></div>

            {!loading && filteredWebinars.length === 0 && (
                <div className="text-center py-24">
                    <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                    <h3 className="text-gray-900 font-medium mb-1">Ничего не найдено</h3>
                    <p className="text-gray-500 text-sm">В библиотеке пока нет записей.</p>
                </div>
            )}
        </div>
    );
}
