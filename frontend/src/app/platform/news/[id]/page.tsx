"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { NewsService, NewsItem } from "@/services/news";

export default function ArticlePage() {
    const { id } = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();
    const backQuery = searchParams.get("back") || "";

    const [article, setArticle] = useState<NewsItem | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        const loadArticle = async () => {
            try {
                const data = await NewsService.getNewsItem(Number(id));

                // If article is PENDING, trigger generation
                if (data.status === "pending") {
                    setArticle(data);
                    setLoading(false);
                    setGenerating(true);

                    try {
                        const result = await NewsService.generateArticle(Number(id));
                        setArticle(result.article);
                        setGenerating(false);
                    } catch (genError) {
                        console.error("Failed to generate article:", genError);
                        setError("Не удалось сгенерировать статью. Попробуйте позже.");
                        setGenerating(false);
                    }
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
    }, [id]);

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

    if (generating) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center max-w-md">
                    <div className="w-16 h-16 border-4 border-[#FF6B35] border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
                    <h2 className="text-xl font-semibold text-gray-800 mb-2">📝 Генерирую полную статью...</h2>
                    <p className="text-gray-600">Это займёт 10-15 секунд. Агент анализирует источники и создаёт подробный материал.</p>
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

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Back Button */}
            <div className="mb-6">
                <Link
                    href={`/platform/news${backQuery ? `?q=${encodeURIComponent(backQuery)}` : ''}`}
                    className="inline-flex items-center gap-2 text-gray-600 hover:text-[#FF6B35] transition-colors"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Назад к новостям
                </Link>
            </div>

            {/* Article */}
            <article className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
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
                {article.content ? (
                    <div className="prose prose-lg max-w-none">
                        <ReactMarkdown>{article.content}</ReactMarkdown>
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
        </div>
    );
}
