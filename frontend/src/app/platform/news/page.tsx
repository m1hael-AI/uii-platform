"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { NewsService, NewsItem } from "@/services/news";

export default function NewsPage() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const [allNews, setAllNews] = useState<NewsItem[]>([]);
    const [filteredNews, setFilteredNews] = useState<NewsItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");
    const [isSearching, setIsSearching] = useState(false);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    const observerTarget = useRef(null);

    // Fetch all news from database
    const fetchNews = useCallback(async (pageNum: number, isInitial = false) => {
        if (isInitial) setLoading(true);

        try {
            const newItems = await NewsService.getNews(pageNum, 50);

            if (isInitial) {
                setAllNews(newItems);
                setFilteredNews(newItems);
            } else {
                setAllNews(prev => [...prev, ...newItems]);
                setFilteredNews(prev => [...prev, ...newItems]);
            }

            if (newItems.length < 50) {
                setHasMore(false);
            }
        } catch (error) {
            console.error("Failed to fetch news:", error);
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial load
    useEffect(() => {
        fetchNews(1, true);
    }, [fetchNews]);

    // Fetch more on page change
    useEffect(() => {
        if (page > 1) {
            fetchNews(page, false);
        }
    }, [page, fetchNews]);

    // Infinite Scroll Observer
    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                if (entries[0].isIntersecting && hasMore && !loading) {
                    setPage(prev => prev + 1);
                }
            },
            { threshold: 1.0 }
        );

        if (observerTarget.current) {
            observer.observe(observerTarget.current);
        }

        return () => {
            if (observerTarget.current) {
                observer.unobserve(observerTarget.current);
            }
        };
    }, [hasMore, loading]);

    // Client-side filtering
    useEffect(() => {
        if (!searchQuery.trim()) {
            setFilteredNews(allNews);
            return;
        }

        const query = searchQuery.toLowerCase();
        const filtered = allNews.filter(item =>
            item.title.toLowerCase().includes(query) ||
            (item.tags && item.tags.some(tag => tag.toLowerCase().includes(query)))
        );
        setFilteredNews(filtered);
    }, [searchQuery, allNews]);

    // Update URL when search changes
    const handleSearchChange = (value: string) => {
        setSearchQuery(value);
        if (value.trim()) {
            router.push(`/platform/news?q=${encodeURIComponent(value)}`);
        } else {
            router.push("/platform/news");
        }
    };

    // Search for fresh news via API
    const handleFreshSearch = async () => {
        if (!searchQuery.trim()) return;

        setIsSearching(true);
        try {
            const results = await NewsService.searchNews(searchQuery);
            const newResults = results.map((item: NewsItem) => ({ ...item, isNew: true }));
            setAllNews(prev => [...newResults, ...prev]);
            setFilteredNews(prev => [...newResults, ...prev]);
        } catch (error) {
            console.error("Failed to search news:", error);
        } finally {
            setIsSearching(false);
        }
    };

    // Format date
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString("ru-RU", {
            day: 'numeric',
            month: 'long',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="w-full max-w-full md:max-w-7xl mx-auto px-0 md:px-6">

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
                <div>
                    <h1 className="text-3xl font-light text-[#474648] mb-2">Новости</h1>
                    <p className="text-[#7e95b1]">Актуальные новости из мира AI</p>
                </div>

                {/* Search Bar */}
                <div className="flex flex-col md:flex-row gap-3 w-full md:w-auto">
                    <div className="relative flex-1 md:flex-initial">
                        <input
                            type="text"
                            placeholder="Поиск по темам..."
                            value={searchQuery}
                            onChange={(e) => handleSearchChange(e.target.value)}
                            className="w-full md:w-96 pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-[#206ecf]/20 focus:border-[#206ecf] outline-none transition-all text-[#474648]"
                        />
                        <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                    <button
                        onClick={handleFreshSearch}
                        disabled={!searchQuery.trim() || isSearching}
                        className="px-4 py-2.5 bg-[#FF6B35] text-white rounded-xl hover:bg-[#ff5722] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm whitespace-nowrap"
                    >
                        {isSearching ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                Ищу...
                            </>
                        ) : (
                            <>
                                🔍 Найти свежие
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Search Results Info */}
            {searchQuery && (
                <div className="mb-4 text-sm text-gray-600">
                    Найдено {filteredNews.length} новостей по запросу "{searchQuery}"
                </div>
            )}

            {/* Loading State */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <div className="w-8 h-8 border-4 border-[#FF6B35] border-t-transparent rounded-full animate-spin"></div>
                </div>
            ) : filteredNews.length === 0 ? (
                <div className="text-center py-20 text-gray-500">
                    {searchQuery ? "Новости не найдены. Попробуйте другой запрос." : "Новостей пока нет. Загляните позже!"}
                </div>
            ) : (
                <div className="space-y-3">
                    {filteredNews.map((item: any) => (
                        <Link
                            key={item.id}
                            href={`/platform/news/${item.id}?back=${encodeURIComponent(searchQuery)}`}
                            className="block bg-white border border-gray-200 rounded-xl p-4 hover:border-[#FF6B35] hover:shadow-md transition-all"
                        >
                            <div className="flex items-start gap-3">
                                {/* Status Indicator */}
                                <div className="flex-shrink-0 mt-1">
                                    {item.isNew ? (
                                        <span className="inline-block px-2 py-0.5 text-xs font-semibold text-white bg-green-500 rounded">🆕 Новое</span>
                                    ) : item.status === 'completed' ? (
                                        <span className="w-2 h-2 bg-green-500 rounded-full inline-block"></span>
                                    ) : (
                                        <span className="w-2 h-2 bg-yellow-500 rounded-full inline-block"></span>
                                    )}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                    {/* Tags */}
                                    {item.tags && item.tags.length > 0 && (
                                        <div className="flex gap-2 mb-2">
                                            {item.tags.slice(0, 2).map((tag: string) => (
                                                <span key={tag} className="text-xs px-2 py-0.5 bg-[#FF6B35]/10 text-[#FF6B35] rounded font-medium">
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                    )}

                                    {/* Title */}
                                    <h3 className="text-base font-medium text-gray-900 mb-1 hover:text-[#FF6B35] transition-colors">
                                        {item.title}
                                    </h3>

                                    {/* Summary */}
                                    {item.summary && (
                                        <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                                            {item.summary}
                                        </p>
                                    )}

                                    {/* Meta */}
                                    <div className="flex items-center gap-3 text-xs text-gray-500">
                                        <span>{formatDate(item.published_at)}</span>
                                        <span>•</span>
                                        <span className="capitalize">{item.status === 'completed' ? 'Готово' : 'Генерируется'}</span>
                                        {item.source_urls && item.source_urls.length > 0 && (
                                            <>
                                                <span>•</span>
                                                <span>{item.source_urls.length} источников</span>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* Arrow */}
                                <div className="flex-shrink-0 text-gray-400">
                                    →
                                </div>
                            </div>
                        </Link>
                    ))}

                    {/* Sentinel for Infinite Scroll */}
                    <div ref={observerTarget} className="h-10 w-full flex items-center justify-center">
                        {loading && hasMore && !isSearching && (
                            <div className="w-6 h-6 border-2 border-[#FF6B35] border-t-transparent rounded-full animate-spin"></div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
