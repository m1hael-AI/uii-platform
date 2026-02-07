import React, { useState } from 'react';

interface PromptTooltipProps {
    content: string;
}

export default function PromptTooltip({ content }: PromptTooltipProps) {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <div className="relative inline-block ml-2">
            <span
                className="cursor-help text-gray-400 hover:text-[#FF6B35] transition-colors"
                onMouseEnter={() => setIsVisible(true)}
                onMouseLeave={() => setIsVisible(false)}
            >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                </svg>
            </span>

            {isVisible && (
                <div className="absolute z-10 w-72 p-3 mt-2 text-sm text-gray-700 bg-white border border-gray-200 rounded-lg shadow-lg -left-1/2 transform -translate-x-[40%]">
                    <div className="relative">
                        {/* Triangle pointer */}
                        <div className="absolute -top-4  left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[6px] border-b-white filter drop-shadow-sm"></div>
                        <div className="whitespace-pre-wrap">{content}</div>
                    </div>
                </div>
            )}
        </div>
    );
}
