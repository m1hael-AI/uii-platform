"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { NewsService, NewsItem } from "@/services/news";

export default function ArticlePage() {
    const { id } = useParams();
    const router = useRouter();
    const [article, setArticle] = useState<NewsItem | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        const loadArticle = async () => {
            try {
                const data = await NewsService.getNewsItem(Number(id));
                setArticle(data);
            } catch (err) {
                console.error("Failed to load article:", err);
                setError("Failed to load article. It might have been deleted or does not exist.");
            } finally {
                setLoading(false);
            }
        };

        loadArticle();
    }, [id]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="w-10 h-10 border-4 border-gray-200 border-t-[#206ecf] rounded-full animate-spin"></div>
            </div>
        );
    }

    if (error || !article) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center">
                <h2 className="text-xl font-medium text-gray-800 dark:text-gray-200 mb-2">Oops!</h2>
                <p className="text-gray-500 mb-6">{error || "Article not found"}</p>
                <Link
                    href="/news"
                    className="px-6 py-2 bg-[#206ecf] text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                    Back to Feed
                </Link>
            </div>
        );
    }

    const formattedDate = new Date(article.published_at).toLocaleDateString("ru-RU", {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });

    return (
        <div className="min-h-screen bg-white dark:bg-[#0a0a0a]">
            {/* Progress Bar (Optional) */}

            <article className="max-w-3xl mx-auto px-4 py-12 md:py-20">
                {/* Back Link */}
                <Link
                    href="/news"
                    className="inline-flex items-center text-sm text-gray-500 hover:text-[#206ecf] transition-colors mb-8 group"
                >
                    <svg className="w-4 h-4 mr-1 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Back to News Feed
                </Link>

                {/* Header */}
                <header className="mb-10">
                    <div className="flex flex-wrap gap-2 mb-6">
                        {article.tags?.map(tag => (
                            <span key={tag} className="px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
                                {tag}
                            </span>
                        ))}
                    </div>

                    <h1 className="text-3xl md:text-5xl font-bold text-gray-900 dark:text-white leading-tight mb-6">
                        {article.title}
                    </h1>

                    <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-6">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                                AI
                            </div>
                            <div>
                                <div className="text-sm font-medium text-gray-900 dark:text-gray-200">AI Reporter</div>
                                <div className="text-xs text-gray-500">{formattedDate}</div>
                            </div>
                        </div>

                        {/* Share / Actions could go here */}
                    </div>
                </header>

                {/* Content */}
                <div className="prose prose-lg dark:prose-invert max-w-none prose-headings:font-bold prose-a:text-[#206ecf] prose-img:rounded-xl">
                    <ReactMarkdown>{article.content || article.summary}</ReactMarkdown>
                </div>

                {/* Footer / Source */}
                {article.source_urls && article.source_urls.length > 0 && (
                    <div className="mt-12 p-6 bg-gray-50 dark:bg-[#1c1c1e] rounded-2xl border border-gray-100 dark:border-gray-800">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-2">
                            Source
                        </h4>
                        <a
                            href={article.source_urls[0]}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#206ecf] hover:underline break-all"
                        >
                            {article.source_urls[0]}
                        </a>
                    </div>
                )}
            </article>
        </div>
    );
}
