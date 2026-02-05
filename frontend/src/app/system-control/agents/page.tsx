"use client";

import { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

// Types
interface Agent {
    id: number;
    slug: string;
    name: string;
    description?: string;
    system_prompt: string;
    greeting_message?: string; // Added field
    is_active: boolean;
}

export default function AgentsControlPage() {
    const router = useRouter();
    const [agents, setAgents] = useState<Agent[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
    const [isSaving, setIsSaving] = useState(false);

    // Editor state
    const [editPrompt, setEditPrompt] = useState("");
    const [editGreeting, setEditGreeting] = useState(""); // Added state

    // Fetch Agents
    useEffect(() => {
        const fetchAgents = async () => {
            const token = Cookies.get("token");
            if (!token) return;

            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            try {
                const res = await fetch(`${API_URL}/admin/agents`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });

                if (res.status === 403) {
                    alert("Доступ запрещен!");
                    router.push("/platform");
                    return;
                }

                if (res.ok) {
                    const data = await res.json();
                    setAgents(data);
                }
            } catch (e) {
                console.error("Failed to fetch agents", e);
            } finally {
                setIsLoading(false);
            }
        };
        fetchAgents();
    }, []);

    // Handle Selection
    const handleSelectAgent = (agent: Agent) => {
        setSelectedAgent(agent);
        setEditPrompt(agent.system_prompt || "");
        setEditGreeting(agent.greeting_message || "");
    };

    // Save Changes
    const handleSave = async () => {
        if (!selectedAgent) return;
        setIsSaving(true);
        const token = Cookies.get("token");
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

        try {
            const res = await fetch(`${API_URL}/admin/agents/${selectedAgent.slug}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    system_prompt: editPrompt,
                    greeting_message: editGreeting
                })
            });

            if (res.ok) {
                // Update local list
                setAgents(prev => prev.map(a =>
                    a.id === selectedAgent.id ? {
                        ...a,
                        system_prompt: editPrompt,
                        greeting_message: editGreeting
                    } : a
                ));
                alert("Изменения сохранены!");
            } else {
                alert("Ошибка сохранения");
            }
        } catch (e) {
            console.error("Save failed", e);
            alert("Ошибка сети");
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) return <div className="p-10 text-center">Загрузка агентов...</div>;

    return (
        <div className="max-w-6xl mx-auto h-[calc(100vh-100px)] flex flex-col">
            <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => router.push("/system-control")}>
                    System Control
                </span>
                <span className="text-gray-300">/</span>
                <span>Редактор Личностей (Agents)</span>
            </h1>

            <div className="flex-1 flex gap-6 overflow-hidden">
                {/* Left Sidebar: Agent List */}
                <div className="w-1/3 bg-white rounded-2xl border border-gray-200 overflow-y-auto shadow-sm">
                    <div className="p-4 border-b border-gray-100 bg-gray-50">
                        <h2 className="font-semibold text-gray-700">Список Агентов</h2>
                    </div>
                    <div>
                        {agents.map(agent => (
                            <div
                                key={agent.id}
                                onClick={() => handleSelectAgent(agent)}
                                className={`p-4 border-b border-gray-50 cursor-pointer transition-colors hover:bg-blue-50 ${selectedAgent?.id === agent.id ? "bg-blue-50 border-l-4 border-blue-500" : ""
                                    }`}
                            >
                                <div className="font-bold text-gray-800">{agent.name}</div>
                                <div className="text-xs text-gray-400 font-mono mt-1">{agent.slug}</div>
                                {agent.description && (
                                    <div className="text-xs text-gray-500 mt-2 line-clamp-2">{agent.description}</div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Right Area: Editor */}
                <div className="flex-1 bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col overflow-hidden">
                    {selectedAgent ? (
                        <>
                            <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center shrink-0">
                                <div>
                                    <h2 className="font-bold text-lg">{selectedAgent.name}</h2>
                                    <span className="text-xs text-gray-400">Редактирование</span>
                                </div>
                                <button
                                    onClick={handleSave}
                                    disabled={isSaving}
                                    className={`px-4 py-2 rounded-lg font-medium text-white transition-all ${isSaving ? "bg-gray-400 cursor-wait" : "bg-blue-600 hover:bg-blue-700 active:scale-95"
                                        }`}
                                >
                                    {isSaving ? "Сохранение..." : "Сохранить изменения"}
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto p-6 space-y-8">
                                {/* System Prompt Section */}
                                <div className="flex flex-col h-[50%] min-h-[300px]">
                                    <label className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                                        System Prompt
                                    </label>
                                    <textarea
                                        value={editPrompt}
                                        onChange={(e) => setEditPrompt(e.target.value)}
                                        className="w-full h-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none font-mono text-sm leading-relaxed resize-none text-gray-800"
                                        placeholder="Введите системный промпт здесь..."
                                        spellCheck={false}
                                    />
                                    <p className="text-xs text-gray-400 mt-2">
                                        Задает личность, знания и стиль общения агента.
                                    </p>
                                </div>

                                {/* Greeting Message Section */}
                                <div className="flex flex-col">
                                    <label className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                                        Приветственное сообщение
                                    </label>
                                    <textarea
                                        rows={4}
                                        value={editGreeting}
                                        onChange={(e) => setEditGreeting(e.target.value)}
                                        className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-sm leading-relaxed resize-none text-gray-800"
                                        placeholder="Привет! Я... Чем могу помочь?"
                                    />
                                    <p className="text-xs text-gray-400 mt-2">
                                        Отображается при старте нового диалога.
                                    </p>
                                </div>
                            </div>

                            <div className="p-3 bg-gray-50 border-t border-gray-100 text-xs text-gray-500 flex justify-between shrink-0">
                                <span>ID: {selectedAgent.id}</span>
                                <div>
                                    <span className="mr-4">Prompt: {editPrompt.length} chars</span>
                                    <span>Greeting: {editGreeting.length} chars</span>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
                            <svg className="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                            </svg>
                            <p>Выберите агента слева для редактирования</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
