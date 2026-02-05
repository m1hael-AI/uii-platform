"use client";

import { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { motion } from "framer-motion";

interface SystemConfig {
    key: string;
    value: string;
    description?: string;
}

interface ProactivitySettings {
    id: number;
    enabled: boolean;
    cron_expression: string;
    quiet_hours_start: string;
    quiet_hours_end: string;
    max_messages_per_day_agents: number;
    max_messages_per_day_assistant: number;
    model: string;
    temperature: number;
    max_tokens: number;
    summarizer_check_interval: number;
    summarizer_idle_threshold: number;
    agent_memory_prompt: string;
    assistant_memory_prompt: string;
}

export default function AdminSettingsPage() {
    const [activeTab, setActiveTab] = useState<"templates" | "proactivity">("templates");

    // Templates State
    const [configs, setConfigs] = useState<Record<string, string>>({});

    // Proactivity State
    const [proSettings, setProSettings] = useState<ProactivitySettings | null>(null);

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
    const token = Cookies.get("token");

    // Templates Definitions
    const CONFIG_KEYS = [
        {
            key: "webinar_reminder_1h_template",
            label: "Шаблон уведомления за 1 час",
            desc: "Используйте {webinar_title} и {link} для подстановки.",
            default: "Напоминание: Вебинар '{webinar_title}' начнется через 1 час! Ссылка: {link}"
        },
        {
            key: "webinar_reminder_start_template",
            label: "Шаблон уведомления о начале",
            desc: "Используйте {webinar_title} и {link} для подстановки.",
            default: "Вебинар '{webinar_title}' начинается! Подключайтесь: {link}"
        }
    ];

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Fetch Templates
            const configRes = await fetch(`${API_URL}/admin/configs`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (configRes.ok) {
                const data: SystemConfig[] = await configRes.json();
                const configMap: Record<string, string> = {};
                data.forEach(c => configMap[c.key] = c.value);
                setConfigs(configMap);
            }

            // Fetch Proactivity Settings
            const proRes = await fetch(`${API_URL}/admin/proactivity`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (proRes.ok) {
                const proData = await proRes.json();
                setProSettings(proData);
            } else {
                console.error("Failed to fetch proactivity settings");
            }

        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSaveTemplate = async (key: string, value: string) => {
        setSaving(true);
        try {
            await fetch(`${API_URL}/admin/configs/${key}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ value, description: "Webinar Template" })
            });
            alert("Шаблон сохранен!");
        } catch {
            alert("Ошибка сохранения");
        } finally {
            setSaving(false);
        }
    };

    const handleSaveProactivity = async () => {
        if (!proSettings) return;
        setSaving(true);
        try {
            const res = await fetch(`${API_URL}/admin/proactivity`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify(proSettings)
            });

            if (res.ok) {
                alert("Настройки проактивности сохранены!");
            } else {
                alert("Ошибка сохранения");
            }
        } catch {
            alert("Ошибка сети");
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-8">Загрузка настроек...</div>;

    return (
        <div className="w-full max-w-4xl">
            <h1 className="text-2xl font-bold text-gray-800 mb-6">Настройки системы</h1>

            {/* Tabs */}
            <div className="flex gap-4 border-b border-gray-200 mb-6">
                <button
                    onClick={() => setActiveTab("templates")}
                    className={`pb-2 px-1 text-sm font-medium transition-colors border-b-2 ${activeTab === "templates"
                            ? "border-black text-black"
                            : "border-transparent text-gray-500 hover:text-gray-800"
                        }`}
                >
                    Уведомления
                </button>
                <button
                    onClick={() => setActiveTab("proactivity")}
                    className={`pb-2 px-1 text-sm font-medium transition-colors border-b-2 ${activeTab === "proactivity"
                            ? "border-black text-black"
                            : "border-transparent text-gray-500 hover:text-gray-800"
                        }`}
                >
                    Проактивность (AI)
                </button>
            </div>

            {/* Content */}
            {activeTab === "templates" && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-8">
                    <h2 className="text-lg font-bold border-b pb-2 mb-4">Шаблоны уведомлений (Telegram)</h2>
                    {CONFIG_KEYS.map(item => (
                        <div key={item.key}>
                            <label className="block text-sm font-bold text-gray-700 mb-1">
                                {item.label}
                            </label>
                            <p className="text-xs text-gray-400 mb-2">{item.desc}</p>
                            <textarea
                                value={configs[item.key] !== undefined ? configs[item.key] : ""}
                                onChange={(e) => setConfigs({ ...configs, [item.key]: e.target.value })}
                                className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-orange-500 outline-none min-h-[100px] text-sm font-medium"
                                placeholder={item.default}
                            />
                            <div className="flex justify-end mt-2">
                                <button
                                    onClick={() => handleSaveTemplate(item.key, configs[item.key] || "")}
                                    disabled={saving}
                                    className="px-4 py-1.5 bg-gray-900 text-white text-xs rounded hover:bg-black transition-colors"
                                >
                                    Сохранить
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {activeTab === "proactivity" && proSettings && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-8">
                    <div className="flex justify-between items-center border-b pb-4">
                        <h2 className="text-lg font-bold">Настройки проактивности</h2>
                        <div className="flex items-center gap-3">
                            <span className="text-sm font-medium text-gray-600">Включить сервис</span>
                            <div
                                className={`w-12 h-6 rounded-full p-1 cursor-pointer transition-colors ${proSettings.enabled ? 'bg-green-500' : 'bg-gray-300'}`}
                                onClick={() => setProSettings({ ...proSettings, enabled: !proSettings.enabled })}
                            >
                                <motion.div
                                    className="bg-white w-4 h-4 rounded-full shadow-sm"
                                    animate={{ x: proSettings.enabled ? 24 : 0 }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Scheduler Settings */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Cron Expression</label>
                            <input
                                value={proSettings.cron_expression}
                                onChange={e => setProSettings({ ...proSettings, cron_expression: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg text-sm font-mono"
                                placeholder="0 */1 * * *"
                            />
                            <p className="text-[10px] text-gray-400 mt-1">Обычно "0 */1 * * *" (каждый час).</p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Тихие часы (Начало)</label>
                                <input
                                    type="time"
                                    value={proSettings.quiet_hours_start}
                                    onChange={e => setProSettings({ ...proSettings, quiet_hours_start: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Тихие часы (Конец)</label>
                                <input
                                    type="time"
                                    value={proSettings.quiet_hours_end}
                                    onChange={e => setProSettings({ ...proSettings, quiet_hours_end: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg text-sm"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Limits */}
                    <div className="border-t pt-4">
                        <h3 className="text-sm font-bold text-gray-900 mb-4">Лимиты сообщений (в сутки)</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Обычные агенты (Суммарно)</label>
                                <input
                                    type="number"
                                    value={proSettings.max_messages_per_day_agents}
                                    onChange={e => setProSettings({ ...proSettings, max_messages_per_day_agents: parseInt(e.target.value) })}
                                    className="w-full px-3 py-2 border rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">AI Помощник (Отдельно)</label>
                                <input
                                    type="number"
                                    value={proSettings.max_messages_per_day_assistant}
                                    onChange={e => setProSettings({ ...proSettings, max_messages_per_day_assistant: parseInt(e.target.value) })}
                                    className="w-full px-3 py-2 border rounded-lg text-sm"
                                />
                            </div>
                        </div>
                    </div>

                    {/* AI Model Settings */}
                    <div className="border-t pt-4">
                        <h3 className="text-sm font-bold text-gray-900 mb-4">Настройки OpenAI для генерации</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Model Name</label>
                                <input
                                    value={proSettings.model}
                                    onChange={e => setProSettings({ ...proSettings, model: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Temperature</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={proSettings.temperature}
                                    onChange={e => setProSettings({ ...proSettings, temperature: parseFloat(e.target.value) })}
                                    className="w-full px-3 py-2 border rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Max Tokens</label>
                                <input
                                    type="number"
                                    value={proSettings.max_tokens}
                                    onChange={e => setProSettings({ ...proSettings, max_tokens: parseInt(e.target.value) })}
                                    className="w-full px-3 py-2 border rounded-lg text-sm"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Prompts */}
                    <div className="border-t pt-4 space-y-4">
                        <h3 className="text-sm font-bold text-gray-900">Системные Промпты (Память и Саммаризация)</h3>

                        <div>
                            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Agent Memory Prompt</label>
                            <textarea
                                value={proSettings.agent_memory_prompt}
                                onChange={e => setProSettings({ ...proSettings, agent_memory_prompt: e.target.value })}
                                rows={4}
                                className="w-full px-3 py-2 border rounded-lg text-xs font-mono bg-gray-50"
                            />
                            <p className="text-[10px] text-gray-400 mt-1">Инструкция для создания саммари взаимодействия с пользователем.</p>
                        </div>

                        <div className="flex justify-end pt-4">
                            <button
                                onClick={handleSaveProactivity}
                                disabled={saving}
                                className="px-6 py-2.5 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors font-medium shadow-lg"
                            >
                                {saving ? "Сохранение..." : "Сохранить настройки"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
