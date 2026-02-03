"use client";

import { useState } from "react";

export default function AIWidget() {
    const [isOpen, setIsOpen] = useState(false);
    const [isHovered, setIsHovered] = useState(false);

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end pointer-events-none">
            {/* Chat Window */}
            <div
                className={`
          mb-4 w-[350px] bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-100
          transition-all duration-300 ease-in-out origin-bottom-right pointer-events-auto
          ${isOpen ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-4 pointer-events-none"}
        `}
                style={{ height: isOpen ? "500px" : "0px" }}
            >
                {/* Header */}
                <div className="bg-black text-white p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <div>
                            <h3 className="font-medium text-sm">AI University Assistant</h3>
                            <p className="text-xs text-gray-400">Всегда на связи</p>
                        </div>
                    </div>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="p-1 hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Body */}
                <div className="p-4 h-[calc(100%-130px)] overflow-y-auto bg-gray-50 flex flex-col gap-3">
                    {/* System Msg */}
                    <div className="flex justify-start">
                        <div className="bg-white p-3 rounded-2xl rounded-tl-none shadow-sm max-w-[85%] border border-gray-100">
                            <p className="text-sm text-gray-800">Привет! Я могу помочь вам с навигацией по платформе или ответить на вопросы по материалам. Чем помочь?</p>
                        </div>
                    </div>
                </div>

                {/* Input */}
                <div className="p-3 border-t border-gray-100 bg-white absolute bottom-0 w-full">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Задайте вопрос..."
                            className="w-full pl-4 pr-10 py-2.5 bg-gray-100 rounded-xl text-sm focus:outline-none focus:ring-1 focus:ring-black text-black"
                        />
                        <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-black text-white rounded-lg hover:opacity-90 transition-opacity">
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>

            {/* Toggle Button (FAB) */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
                className={`
          flex items-center justify-center w-14 h-14 rounded-full shadow-lg pointer-events-auto
          transition-all duration-300 ease-out
          ${isOpen ? "rotate-90 bg-gray-100 text-black" : "bg-black text-white hover:scale-110"}
        `}
            >
                {isOpen ? (
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                ) : (
                    <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                )}

                {/* Badge / Tooltip hint */}
                {!isOpen && (
                    <span className={`
                absolute right-full mr-4 bg-white px-3 py-1.5 rounded-lg shadow-md text-xs font-medium text-black whitespace-nowrap
                transition-all duration-200
                ${isHovered ? "opacity-100 translate-x-0" : "opacity-0 translate-x-2 pointer-events-none"}
            `}>
                        Есть вопрос?
                    </span>
                )}
            </button>
        </div>
    );
}
