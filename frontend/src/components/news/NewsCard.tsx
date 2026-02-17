
import React from "react";
import Link from "next/link";
import { NewsItem } from "../../services/news";

interface NewsCardProps {
    news: NewsItem;
}

const NewsCard: React.FC<NewsCardProps> = ({ news }) => {
    // Format date
    const formattedDate = new Date(news.published_at).toLocaleDateString("ru-RU", {
        day: 'numeric',
        month: 'long',
        hour: '2-digit',
        minute: '2-digit'
    });

    return (
        <div className="group relative bg-[#1c1c1e]/60 backdrop-blur-xl border border-white/5 rounded-2xl overflow-hidden hover:border-[#206ecf]/50 transition-all duration-300 hover:shadow-lg hover:shadow-[#206ecf]/10 h-full flex flex-col">

            {/* Status Indicator */}
            <div className={`absolute top-0 right-0 w-2 h-2 rounded-full m-4 ${news.status === 'COMPLETED' ? 'bg-green-500' : 'bg-yellow-500'
                }`}></div>

            <div className="p-6 flex-1 flex flex-col">
                <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs text-gray-400 font-mono tracking-wide">
                        {formattedDate}
                    </span>
                    {news.tags && news.tags.slice(0, 1).map(tag => (
                        <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-[#206ecf]/10 text-[#206ecf] border border-[#206ecf]/20 uppercase font-semibold tracking-wider">
                            {tag}
                        </span>
                    ))}
                </div>

                <Link href={`/news/${news.id}`} className="block group-hover:text-[#206ecf] transition-colors">
                    <h3 className="text-lg font-medium text-white mb-3 line-clamp-2 leading-snug">
                        {news.title}
                    </h3>
                </Link>

                <p className="text-sm text-gray-400 line-clamp-3 mb-6 leading-relaxed flex-1">
                    {news.summary}
                </p>

                <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between">
                    <Link
                        href={`/news/${news.id}`}
                        className="text-sm text-[#206ecf] font-medium hover:text-white transition-colors flex items-center gap-1"
                    >
                        Читать далее
                        <svg className="w-4 h-4 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                        </svg>
                    </Link>

                    {/* Source domain if available */}
                    {news.source_urls && news.source_urls.length > 0 && (
                        <span className="text-xs text-gray-600 truncate max-w-[120px]">
                            {new URL(news.source_urls[0]).hostname.replace('www.', '')}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
};

export default NewsCard;
