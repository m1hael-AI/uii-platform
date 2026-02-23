"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { NewsService, NewsItem } from "@/services/news";
import FloatingInternetSearch from "@/components/news/FloatingInternetSearch";

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
    const [activeTab, setActiveTab] = useState<'all' | 'foryou'>((searchParams.get("tab") as 'all' | 'foryou') || 'all');
    const [searchResults, setSearchResults] = useState<NewsItem[] | null>(null);
    const observerTarget = useRef(null);

    // Sync activeTab to URL
    useEffect(() => {
        const params = new URLSearchParams(searchParams.toString());
        if (activeTab === 'all') {
            params.delete("tab");
        } else {
            params.set("tab", activeTab);
        }
        router.replace(`/platform/news?${params.toString()}`, { scroll: false });
    }, [activeTab, router, searchParams]);

    // Fetch all news from database
    const fetchNews = useCallback(async (pageNum: number, isInitial = false, tabType: 'all' | 'foryou' = 'all') => {
        if (isInitial) setLoading(true);

        try {
            const newItems = await NewsService.getNews(pageNum, 50, tabType);

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

    // Initial load & Tab Change
    useEffect(() => {
        setPage(1);
        setHasMore(true);
        setAllNews([]); // Clear current list on tab switch
        fetchNews(1, true, activeTab);
    }, [activeTab, fetchNews]);

    // Fetch more on page change
    useEffect(() => {
        if (page > 1) {
            fetchNews(page, false, activeTab);
        }
    }, [page, fetchNews, activeTab]);

    // Infinite Scroll Observer (отключается во время AI-поиска)
    useEffect(() => {
        if (searchResults !== null) return;

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
    }, [hasMore, loading, searchResults]);

    // AI-поиск по новостям — запускается по Enter или кнопке
    const runSearch = async (query: string) => {
        const q = query.trim();
        if (!q) {
            setSearchResults(null);
            return;
        }
        setIsSearching(true);
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const newItems = await NewsService.aiSearch(q);
            setSearchResults(newItems);
        } catch (e) {
            console.error("News AI search failed", e);
            setSearchResults([]);
        } finally {
            setIsSearching(false);
        }
    };

    // Search for fresh news via API (Hybrid 2-Step)
    const handleFreshSearch = async (queryOverride?: string) => {
        const queryToUse = queryOverride || searchQuery;
        if (!queryToUse.trim()) return;

        // 1. Clear UI & Filter
        setSearchQuery(""); // Clear top filter
        setAllNews([]);     // Clear current list
        setFilteredNews([]); // Clear filtered list
        setIsSearching(true);
        setLoading(true); // Show loader for initial fetch

        try {
            // 2. Step 1: Instant Context from DB (Vector Search)
            // We use getNews with q param which triggers vector search on backend
            const dbResults = await NewsService.getNews(1, 50, 'all', queryToUse);
            setAllNews(dbResults);
            setFilteredNews(dbResults);

            // Results found? Good. Continue to step 2.
            // If no results, list is empty, user sees loader.
        } catch (error) {
            console.error("Failed to fetch local context:", error);
        } finally {
            setLoading(false); // Stop main loader, but keeps isSearching true for "Searching web..." indicator
        }

        try {
            // 3. Step 2: Perplexity Search (Fresh Content)
            const results = await NewsService.searchNews(queryToUse);
            const newResults = results.map((item: NewsItem) => ({ ...item, isNew: true }));

            // Add to top of news list
            setAllNews(prev => {
                // Filter out duplicates by ID
                const existingIds = new Set(prev.map(n => n.id));
                const uniqueNew = newResults.filter((n: NewsItem) => !existingIds.has(n.id));
                return [...uniqueNew, ...prev];
            });

            // Update visible list
            setFilteredNews(prev => {
                const existingIds = new Set(prev.map(n => n.id));
                const uniqueNew = newResults.filter((n: NewsItem) => !existingIds.has(n.id));
                return [...uniqueNew, ...prev];
            });

        } catch (error) {
            console.error("Failed to search web news:", error);
        } finally {
            setIsSearching(false);
        }
    };

    // Handler for Floating Search (Hybrid)
    const handleFloatingSearch = (query: string) => {
        // Decoupled: Do NOT update setSearchQuery (filter)
        handleFreshSearch(query);  // Trigger hybrid flow
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

    // Активный список: результаты AI-поиска или все новости
    const activeNews = searchResults !== null ? searchResults : allNews;

    return (
        <div className="w-full max-w-full md:max-w-7xl mx-auto px-0 md:px-6 pb-32 relative min-h-screen">

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
                <div>
                    <h1 className="text-3xl font-light text-[#474648] mb-2">Новости</h1>
                    <p className="text-[#7e95b1]">Актуальные новости из мира AI</p>

                    {/* Tabs */}
                    <div className="flex gap-4 mt-6">
                        <button
                            onClick={() => setActiveTab('all')}
                            className={`pb-2 text-sm font-medium transition-colors ${activeTab === 'all'
                                ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                                : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            Все новости
                        </button>
                        <button
                            onClick={() => setActiveTab('foryou')}
                            className={`pb-2 text-sm font-medium transition-colors ${activeTab === 'foryou'
                                ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                                : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            Для Вас
                        </button>
                    </div>
                </div>

                {/* Search Bar — единое поле с кнопкой-иконкой внутри */}
                <div className="flex flex-col md:flex-row gap-3 w-full md:w-auto">
                    <div className="relative flex-1 md:flex-initial">
                        <input
                            placeholder="AI-поиск по новостям..."
                            value={searchQuery}
                            onChange={(e) => {
                                setSearchQuery(e.target.value);
                                if (!e.target.value.trim()) setSearchResults(null);
                            }}
                            onKeyDown={(e) => e.key === "Enter" && runSearch(searchQuery)}
                            className="w-full md:w-96 pl-4 pr-12 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-[#206ecf]/20 focus:border-[#206ecf] outline-none transition-all text-[#474648]"
                        />
                        <button
                            onClick={() => runSearch(searchQuery)}
                            disabled={isSearching || !searchQuery.trim()}
                            className={`absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg transition-colors
                                ${searchQuery.trim()
                                    ? "bg-[#206ecf] hover:bg-[#1a5aad] cursor-pointer"
                                    : "bg-[#206ecf]/30 cursor-not-allowed"
                                } disabled:opacity-70`}
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
                </div>
            </div>

            {/* Search Results Info */}
            {searchResults !== null && (
                <div className="mb-4 text-sm text-gray-600">
                    Найдено {searchResults.length} новостей по запросу "{searchQuery}"
                </div>
            )}

            {/* Loading State */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <div className="w-8 h-8 border-4 border-[#FF6B35] border-t-transparent rounded-full animate-spin"></div>
                </div>
            ) : (
                <div className="space-y-3">
                    {/* Top Loader for Web Search */}
                    {isSearching && (
                        <div className="flex items-center justify-center py-4 bg-gray-50 rounded-xl border border-gray-100 mb-3 animate-pulse">
                            <div className="flex items-center gap-3 text-sm text-gray-500">
                                <div className="w-4 h-4 border-2 border-[#FF6B35] border-t-transparent rounded-full animate-spin"></div>
                                <span>Выполняем поиск...</span>
                            </div>
                        </div>
                    )}

                    {activeNews.length === 0 && !isSearching ? (
                        <div className="text-center py-20 text-gray-500">
                            {searchResults !== null ? "Новости не найдены. Попробуйте другой запрос." : "Новостей пока нет"}
                        </div>
                    ) : activeNews.length > 0 ? (
                        <>
                            {activeNews.map((item: any) => (
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
                        </>
                    ) : null}
                </div>
            )}

            {/* Floating Search Bar */}
            <FloatingInternetSearch
                onSearch={handleFloatingSearch}
                isSearching={isSearching}
            />
        </div>
    );
}
