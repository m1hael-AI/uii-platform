"use client";
import { useState, useRef, useEffect } from "react";

interface Props {
    onSearch: (query: string) => void;
    isSearching: boolean;
}

export default function FloatingInternetSearch({ onSearch, isSearching }: Props) {
    const [query, setQuery] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSubmit = () => {
        if (!query.trim() || isSearching) return;
        onSearch(query);
        setQuery(""); // Clear input after search
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    // Auto-resize
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
        }
    }, [query]);

    return (
        <div className="fixed bottom-8 left-0 right-0 z-50 px-4 flex justify-center pointer-events-none">
            {/* Wrapper for pointer events */}
            <div className="w-full max-w-4xl pointer-events-auto">
                <div className={`relative bg-white/80 backdrop-blur-xl border border-gray-200/50 shadow-2xl rounded-2xl transition-all duration-300 ${isSearching ? 'ring-2 ring-[#FF6B35]/50' : 'hover:ring-2 hover:ring-gray-200'}`}>
                    <textarea
                        ref={textareaRef}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={isSearching ? "Ищем в интернете..." : "Найти свежие новости..."}
                        className="w-full bg-transparent border-none focus:ring-0 focus:outline-none p-4 pr-14 text-gray-800 placeholder-gray-400 text-lg resize-none max-h-48 overflow-y-auto rounded-2xl outline-none shadow-none ring-0"
                        rows={1}
                        disabled={isSearching}
                        style={{ minHeight: '52px' }}
                    />

                    {/* Search Button */}
                    <button
                        onClick={handleSubmit}
                        disabled={!query.trim() || isSearching}
                        className="absolute right-3 bottom-3 p-2 bg-[#FF6B35] text-white rounded-xl hover:bg-[#ff5722] disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
                    >
                        {isSearching ? (
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        ) : (
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        )}
                    </button>

                    {/* Hint */}
                    {!query && !isSearching && (
                        <div className="absolute -bottom-6 left-0 w-full text-center text-xs text-gray-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                            Shift + Enter for new line • Enter to search
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
