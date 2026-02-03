"use client";

import { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

interface Agent {
    id: number;
    slug: string;
    name: string;
    description: string;
    system_prompt: string;
    is_active: boolean;
}

export default function AdminPromptsPage() {
    const router = useRouter();
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
    const [promptText, setPromptText] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    useEffect(() => {
        fetchAgents();
    }, []);

    const fetchAgents = async () => {
        const token = Cookies.get("token");
        if (!token) {
            router.push("/login");
            return;
        }

        try {
            const res = await fetch(`${API_URL}/admin/agents`, {
                headers: { Authorization: `Bearer ${token}` }
            });

            if (res.status === 403) {
                setError("Доступ запрещен. Требуются права администратора.");
                setLoading(false);
                return;
            }

            if (res.ok) {
                const data = await res.json();
                setAgents(data);
                if (data.length > 0) {
                    selectAgent(data[0]);
                }
            } else {
                setError("Ошибка загрузки агентов");
            }
        } catch (e) {
            console.error(e);
            setError("Ошибка сети");
        } finally {
            setLoading(false);
        }
    };

    const selectAgent = (agent: Agent) => {
        setSelectedAgent(agent);
        setPromptText(agent.system_prompt);
    };

    const handleSave = async () => {
        if (!selectedAgent) return;
        setSaving(true);
        const token = Cookies.get("token");

        try {
            const res = await fetch(`${API_URL}/admin/agents/${selectedAgent.slug}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ system_prompt: promptText })
            });

            if (res.ok) {
                // Update local state
                const updatedAgents = agents.map(a =>
                    a.slug === selectedAgent.slug ? { ...a, system_prompt: promptText } : a
                );
                setAgents(updatedAgents);
                alert("Промпт сохранен!");
            } else {
                alert("Ошибка сохранения");
            }
        } catch (e) {
            alert("Ошибка сети");
        } finally {
            setSaving(false);
        }
    };

    if (loading) return (
        <div className="flex items-center justify-center h-full text-gray-500">
            Загрузка...
        </div>
    );

    if (error) return (
        <div className="flex flex-col items-center justify-center h-full text-red-500">
            <p className="text-xl font-medium">{error}</p>
            <button
                onClick={() => router.push("/platform")}
                className="mt-4 px-4 py-2 bg-gray-100 rounded text-black hover:bg-gray-200"
            >
                Вернуться назад
            </button>
        </div>
    );

    return (
        <div className="flex flex-col md:flex-row gap-6 w-full">
            {/* Sidebar List */}
            <div className="w-full md:w-1/3 flex flex-col gap-4">
                <h1 className="text-2xl font-bold text-gray-800 mb-4">AI Агенты</h1>

                <div className="flex flex-col gap-2">
                    {agents.map((agent) => (
                        <button
                            key={agent.slug}
                            onClick={() => selectAgent(agent)}
                            className={`text-left px-4 py-3 rounded-xl border transition-all duration-200 ${selectedAgent?.slug === agent.slug
                                ? "bg-white border-orange-500 shadow-md ring-1 ring-orange-500"
                                : "bg-white border-gray-200 hover:border-orange-300 hover:bg-gray-50"
                                }`}
                        >
                            <div className="font-medium text-gray-900">{agent.name}</div>
                            <div className="text-xs mt-1 text-gray-500">
                                {agent.slug}
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Editor Area */}
            <div className="w-full md:w-2/3 flex flex-col h-full">
                {selectedAgent && (
                    <motion.div
                        key={selectedAgent.slug}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="bg-white rounded-2xl border border-gray-200 p-6 flex flex-col h-full shadow-sm"
                    >
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h2 className="text-xl font-medium text-gray-800">{selectedAgent.name}</h2>
                                <p className="text-sm text-gray-500">{selectedAgent.description}</p>
                            </div>
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className={`px-6 py-2.5 rounded-lg font-medium transition-all ${saving
                                    ? "bg-gray-100 text-gray-400"
                                    : "bg-black text-white hover:bg-gray-800 active:scale-95"
                                    }`}
                            >
                                {saving ? "Сохранение..." : "Сохранить"}
                            </button>
                        </div>

                        <div className="flex-1 flex flex-col">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                                System Prompt
                            </label>
                            <textarea
                                value={promptText}
                                onChange={(e) => setPromptText(e.target.value)}
                                className="flex-1 w-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:border-black focus:ring-1 focus:ring-black outline-none font-mono text-sm leading-relaxed resize-none text-gray-800"
                                spellCheck={false}
                            />
                            <p className="text-xs text-gray-400 mt-2">
                                Используйте этот промпт для настройки поведения, тона и знаний агента.
                            </p>
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    );
}
