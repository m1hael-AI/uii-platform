'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';

// Limits referenced from Backend (context_manager.py)
const MODEL_LIMITS: Record<string, number> = {
    // GPT-4.1 Family
    "gpt-4.1": 1000000,
    "gpt-4.1-mini": 1000000,

    // GPT-5 Family
    "gpt-5": 272000,
    "gpt-5-mini": 400000,

    // Legacy / Stable
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
};

const AVAILABLE_MODELS = Object.keys(MODEL_LIMITS);

// Cache-buster: 2026-02-06T21:40
interface ProactivitySettings {
    id: number;
    // Memory Update Settings
    memory_model: string;
    memory_temperature: number;
    memory_max_tokens: number | null;

    // Proactivity Trigger Settings
    trigger_model: string;
    trigger_temperature: number;
    trigger_max_tokens: number | null;

    // Scheduler Settings
    enabled: boolean;
    cron_expression: string;
    quiet_hours_start: string;
    quiet_hours_end: string;

    // Limits
    max_messages_per_day_agents: number;
    max_messages_per_day_assistant: number;
    rate_limit_per_minute: number;

    // Architecture v2 Timings
    memory_update_interval: number;
    proactivity_timeout: number;

    // Prompts
    agent_memory_prompt: string;
    assistant_memory_prompt: string;
    proactivity_trigger_prompt: string;
    compression_prompt: string;

    // Anti-Spam
    max_consecutive_messages: number;
}

export default function ProactivityAdminPage() {
    const router = useRouter();
    const [settings, setSettings] = useState<ProactivitySettings | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [activeTab, setActiveTab] = useState<'memory' | 'proactivity' | 'general'>('memory');

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            const token = Cookies.get('token');
            if (!token) {
                router.push('/login');
                return;
            }

            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const response = await fetch(`${API_URL}/admin/proactivity`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.status === 403) {
                setError('Доступ запрещён. Требуются права администратора.');
                return;
            }

            if (!response.ok) {
                throw new Error('Ошибка загрузки настроек');
            }

            const data = await response.json();
            setSettings(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!settings) return;

        setSaving(true);
        setError(null);
        setSuccess(false);

        try {
            const token = Cookies.get('token');
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const response = await fetch(`${API_URL}/admin/proactivity`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings),
            });

            if (!response.ok) {
                throw new Error('Ошибка сохранения настроек');
            }

            const data = await response.json();
            setSettings(data);
            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#FF6B35] mx-auto mb-4"></div>
                    <p className="text-gray-600">Загрузка настроек...</p>
                </div>
            </div>
        );
    }

    if (error && !settings) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
                    <h2 className="text-red-800 font-semibold mb-2">Ошибка</h2>
                    <p className="text-red-600">{error}</p>
                </div>
            </div>
        );
    }

    if (!settings) return null;

    return (
        <div className="max-w-6xl mx-auto">
            {/* Header */}
            <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => router.push("/system-control")}>
                    System Control
                </span>
                <span className="text-gray-300">/</span>
                <span>Настройки проактивности</span>
            </h1>

            {/* Tabs */}
            <div className="flex gap-4 mb-6 border-b border-gray-200">
                <button
                    onClick={() => setActiveTab('memory')}
                    className={`px-4 py-2 font-medium transition-colors focus:outline-none ${activeTab === 'memory'
                        ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                        : 'text-gray-600 hover:text-[#FF6B35]'
                        }`}
                >
                    Память
                </button>
                <button
                    onClick={() => setActiveTab('proactivity')}
                    className={`px-4 py-2 font-medium transition-colors focus:outline-none ${activeTab === 'proactivity'
                        ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                        : 'text-gray-600 hover:text-[#FF6B35]'
                        }`}
                >
                    Проактивность
                </button>
                <button
                    onClick={() => setActiveTab('general')}
                    className={`px-4 py-2 font-medium transition-colors focus:outline-none ${activeTab === 'general'
                        ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                        : 'text-gray-600 hover:text-[#FF6B35]'
                        }`}
                >
                    Общие настройки
                </button>
            </div>

            {/* Success Message */}
            {success && (
                <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
                    <p className="text-green-800 font-medium">✅ Настройки успешно сохранены!</p>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-red-800 font-medium">❌ {error}</p>
                </div>
            )}

            {/* Memory Tab */}
            {activeTab === 'memory' && (
                <div className="space-y-6">
                    {/* Memory LLM Settings */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-4">Настройки LLM для обновления памяти</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Модель</label>
                                <select
                                    value={settings.memory_model}
                                    onChange={(e) => setSettings({ ...settings, memory_model: e.target.value })}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent bg-white"
                                >
                                    {AVAILABLE_MODELS.map(model => (
                                        <option key={model} value={model}>{model}</option>
                                    ))}
                                    {!AVAILABLE_MODELS.includes(settings.memory_model) && (
                                        <option value={settings.memory_model}>{settings.memory_model} (Custom)</option>
                                    )}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Temperature</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    max="2"
                                    value={settings.memory_temperature}
                                    onChange={(e) => setSettings({ ...settings, memory_temperature: parseFloat(e.target.value) })}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Max Tokens</label>
                                <input
                                    type="number"
                                    min="1"
                                    placeholder="Без лимита"
                                    value={settings.memory_max_tokens ?? ''}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        setSettings({ ...settings, memory_max_tokens: val === '' ? null : parseInt(val) });
                                    }}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                                <p className="text-xs text-gray-500 mt-1">Оставьте пустым для безлимита</p>
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Интервал обновления (часы)</label>
                            <input
                                type="number"
                                min="1"
                                max="48"
                                value={settings.memory_update_interval}
                                onChange={(e) => setSettings({ ...settings, memory_update_interval: parseInt(e.target.value) })}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">Как часто обновлять память при молчании</p>
                        </div>
                    </div>


                    {/* Agent Memory Prompt */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Промпт для агентов</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Используется для извлечения памяти обычных агентов (Data Analyst, Career Mentor и т.д.)
                        </p>
                        <textarea
                            value={settings.agent_memory_prompt}
                            onChange={(e) => setSettings({ ...settings, agent_memory_prompt: e.target.value })}
                            rows={15}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                        />
                    </div>

                    {/* Assistant Memory Prompt */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Промпт для ассистента</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Используется для извлечения памяти главного ассистента
                        </p>
                        <textarea
                            value={settings.assistant_memory_prompt}
                            onChange={(e) => setSettings({ ...settings, assistant_memory_prompt: e.target.value })}
                            rows={15}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                        />
                    </div>
                </div>
            )
            }

            {/* Proactivity Tab */}
            {
                activeTab === 'proactivity' && (
                    <div className="space-y-6">
                        {/* Proactivity Trigger LLM Settings */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold mb-4">Настройки LLM для проверки проактивности</h2>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Модель</label>
                                    <select
                                        value={settings.trigger_model}
                                        onChange={(e) => setSettings({ ...settings, trigger_model: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent bg-white"
                                    >
                                        {AVAILABLE_MODELS.map(model => (
                                            <option key={model} value={model}>{model}</option>
                                        ))}
                                        {!AVAILABLE_MODELS.includes(settings.trigger_model) && (
                                            <option value={settings.trigger_model}>{settings.trigger_model} (Custom)</option>
                                        )}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Temperature</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        min="0"
                                        max="2"
                                        value={settings.trigger_temperature}
                                        onChange={(e) => setSettings({ ...settings, trigger_temperature: parseFloat(e.target.value) })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Max Tokens</label>
                                    <input
                                        type="number"
                                        min="1"
                                        placeholder="Без лимита"
                                        value={settings.trigger_max_tokens ?? ''}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            setSettings({ ...settings, trigger_max_tokens: val === '' ? null : parseInt(val) });
                                        }}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                    />
                                    <p className="text-xs text-gray-500 mt-1">Оставьте пустым для безлимита</p>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Тайм-аут проактивности (часы)</label>
                                <input
                                    type="number"
                                    min="1"
                                    max="168"
                                    value={settings.proactivity_timeout}
                                    onChange={(e) => setSettings({ ...settings, proactivity_timeout: parseInt(e.target.value) })}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                                <p className="text-xs text-gray-500 mt-1">Время молчания перед проверкой триггера</p>
                            </div>
                        </div>


                        {/* Proactivity Trigger Prompt */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold mb-2">Промпт для проверки проактивности</h2>
                            <p className="text-sm text-gray-600 mb-4">
                                Используется для принятия решения о необходимости проактивного сообщения
                            </p>
                            <textarea
                                value={settings.proactivity_trigger_prompt}
                                onChange={(e) => setSettings({ ...settings, proactivity_trigger_prompt: e.target.value })}
                                rows={15}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                            />
                        </div>
                    </div >
                )
            }

            {/* General Settings Tab */}
            {
                activeTab === 'general' && (
                    <div className="space-y-6">
                        {/* Enable/Disable */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold mb-4">Основные</h2>
                            <label className="flex items-center gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={settings.enabled}
                                    onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
                                    className="w-5 h-5 text-[#FF6B35] rounded focus:ring-[#FF6B35]"
                                />
                                <span className="font-medium">Включить проактивность</span>
                            </label>
                        </div>

                        {/* Scheduler Settings */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold mb-4">Планировщик</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Тихие часы (начало)
                                    </label>
                                    <input
                                        type="time"
                                        value={settings.quiet_hours_start}
                                        onChange={(e) => setSettings({ ...settings, quiet_hours_start: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Тихие часы (конец)
                                    </label>
                                    <input
                                        type="time"
                                        value={settings.quiet_hours_end}
                                        onChange={(e) => setSettings({ ...settings, quiet_hours_end: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Limits */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold mb-4">Лимиты сообщений</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        В день (Общий лимит агентов)
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="1000"
                                        value={settings.max_messages_per_day_agents}
                                        onChange={(e) => setSettings({ ...settings, max_messages_per_day_agents: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        В день (AI Помощник)
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="1000"
                                        value={settings.max_messages_per_day_assistant}
                                        onChange={(e) => setSettings({ ...settings, max_messages_per_day_assistant: parseInt(e.target.value) })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                    />
                                </div>
                            </div>
                            <div className="mt-4">
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Макс. сообщений подряд от AI (Anti-Spam)
                                </label>
                                <input
                                    type="number"
                                    min="1"
                                    max="10"
                                    value={settings.max_consecutive_messages || 3}
                                    onChange={(e) => setSettings({ ...settings, max_consecutive_messages: parseInt(e.target.value) })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                                <p className="text-xs text-gray-500 mt-1">Если AI написал столько сообщений подряд без ответа юзера — проактивность останавливается.</p>
                            </div>
                        </div>


                    </div>
                )
            }

            {/* Save Button */}
            <div className="mt-8 flex justify-end">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-6 py-3 bg-[#FF6B35] text-white font-medium rounded-lg hover:bg-[#FF5722] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {saving ? 'Сохранение...' : 'Сохранить изменения'}
                </button>
            </div>
        </div >
    );
}
