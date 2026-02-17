"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { NewsService, NewsItem } from "../../services/news";
import NewsCard from "../../components/news/NewsCard";

export default function NewsPage() {
    const [news, setNews] = useState<NewsItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    const [isLoadMore, setIsLoadMore] = useState(false);

    // Fetch News
    const fetchNews = useCallback(async (pageNum: number, isInitial = false) => {
        if (isInitial) setLoading(true);
        else setIsLoadMore(true);

        try {
            const newItems = await NewsService.getNews(pageNum);

            if (isInitial) {
                setNews(newItems);
            } else {
                setNews(prev => [...prev, ...newItems]);
            }

            // If we got fewer items than requested (20 default), no more items
            if (newItems.length < 20) {
                setHasMore(false);
            }
        } catch (error) {
            console.error("Failed to fetch news:", error);
        } finally {
            setLoading(false);
            setIsLoadMore(false);
        }
    }, []);

    // Initial Load
    useEffect(() => {
        fetchNews(1, true);
    }, [fetchNews]);

    // Load More Handler
    const handleLoadMore = () => {
        const nextPage = page + 1;
        setPage(nextPage);
        fetchNews(nextPage);
    };

    return (
        <div className="w-full max-w-7xl mx-auto px-4 py-8">
            {/* Header */}
            <div className="flex items-end justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-light text-[#474648] dark:text-gray-100 mb-2">AI News Feed</h1>
                    <p className="text-[#7e95b1] dark:text-gray-400">
                        Top AI news curated and summarized by our agents.
                    </p>
                </div>

                {/* Optional: Refresh Button or Last Updated */}
            </div>

            {/* Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {news.map((item) => (
                    <NewsCard key={item.id} news={item} />
                ))}
            </div>

            {/* Loading State (Initial) */}
            {loading && (
                <div className="flex justify-center py-20">
                    <div className="w-10 h-10 border-4 border-gray-200 border-t-[#206ecf] rounded-full animate-spin"></div>
                </div>
            )}

            {/* Load More / End of List */}
            {!loading && (
                <div className="mt-12 text-center">
                    {hasMore ? (
                        <button
                            onClick={handleLoadMore}
                            disabled={isLoadMore}
                            className="px-6 py-3 bg-white dark:bg-[#1c1c1e] border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 hover:border-[#206ecf] hover:text-[#206ecf] transition-colors disabled:opacity-50"
                        >
                            {isLoadMore ? "Loading..." : "Load More News"}
                        </button>
                    ) : (
                        news.length > 0 && <p className="text-gray-400 text-sm">No more news for now.</p>
                    )}
                </div>
            )}

            {/* Empty State */}
            {!loading && news.length === 0 && (
                <div className="text-center py-20">
                    <p className="text-gray-500">No news found. Check back later!</p>
                </div>
            )}
        </div>
    );
}
