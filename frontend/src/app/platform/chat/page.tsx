"use client";

import Link from "next/link";

const AGENTS = [
    { id: "mentor", name: "AI Ментор", role: "Куратор", avatar: "A", color: "bg-orange-50 text-orange-600", lastMsg: "Персональный куратор по всем вопросам." },
    { id: "python", name: "Python Эксперт", role: "Tutor", avatar: "P", color: "bg-yellow-50 text-yellow-600", lastMsg: "Помогу с кодом и архитектурой." },
    { id: "analyst", name: "Data Analyst", role: "Expert", avatar: "D", color: "bg-green-50 text-green-600", lastMsg: "Анализ данных и Pandas." },
    { id: "hr", name: "HR Консультант", role: "Assistant", avatar: "H", color: "bg-purple-50 text-purple-600", lastMsg: "Помощь с резюме и карьерой." },
];

export default function ChatIndexPage() {
    return (
        <>
            {/* Desktop: Empty state */}
            <div className="hidden lg:flex flex-1 flex-col items-center justify-center p-8 text-center text-gray-500 bg-gray-50/30">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-gray-400">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-1">Выберите собеседника</h3>
                <p className="text-sm max-w-xs mx-auto">
                    Выберите одного из AI-агентов в списке слева, чтобы начать диалог.
                </p>
            </div>

            {/* Mobile/Tablet: Agent list */}
            <div className="lg:hidden flex-1 flex flex-col bg-gray-50 overflow-y-auto">
                <div className="p-4 bg-white border-b border-gray-100">
                    <h2 className="text-lg font-semibold text-gray-900">AI Агенты</h2>
                    <p className="text-sm text-gray-500 mt-1">Выберите агента для начала диалога</p>
                </div>

                <div className="p-4 space-y-3">
                    {AGENTS.map(agent => (
                        <Link
                            key={agent.id}
                            href={`/platform/chat/${agent.id}`}
                            className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all active:scale-98"
                        >
                            <div className={`w-14 h-14 rounded-full flex items-center justify-center font-bold text-lg shrink-0 ${agent.color}`}>
                                {agent.avatar}
                            </div>
                            <div className="flex-1 min-w-0">
                                <h3 className="font-semibold text-gray-900 mb-1">{agent.name}</h3>
                                <p className="text-xs text-gray-500 line-clamp-1">
                                    {agent.lastMsg}
                                </p>
                            </div>
                            <svg className="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                        </Link>
                    ))}
                </div>
            </div>
        </>
    );
}
