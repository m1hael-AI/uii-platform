'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';

interface ProactivitySettings {
    id: number;
    // OpenAI Settings
    model: string;
    temperature: number;
    max_tokens: number;

    // Scheduler Settings
    enabled: boolean;
    cron_expression: string;
    quiet_hours_start: string;
    quiet_hours_end: string;

    // Limits
    max_messages_per_day_agents: number;
    max_messages_per_day_assistant: number;
    rate_limit_per_minute: number; // Still in interface for type safety, but UI removed if passed from backend

    // Summarizer Settings
    summarizer_check_interval: number;
    summarizer_idle_threshold: number;

    // Prompts
    agent_memory_prompt: string;
    assistant_memory_prompt: string;
}

export default function ProactivityAdminPage() {
    const router = useRouter();
    const [settings, setSettings] = useState<ProactivitySettings | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [activeTab, setActiveTab] = useState<'general' | 'prompts'>('general');

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
                    onClick={() => setActiveTab('general')}
                    className={`px-4 py-2 font-medium transition-colors ${activeTab === 'general'
                        ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                        : 'text-gray-600 hover:text-gray-900'
                        }`}
                >
                    Общие настройки
                </button>
                <button
                    onClick={() => setActiveTab('prompts')}
                    className={`px-4 py-2 font-medium transition-colors ${activeTab === 'prompts'
                        ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                        : 'text-gray-600 hover:text-gray-900'
                        }`}
                >
                    Промпты
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

            {/* General Settings Tab */}
            {activeTab === 'general' && (
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

                    {/* OpenAI Settings */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-4">Настройки OpenAI (Проактивность)</h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Модель
                                </label>
                                <select
                                    value={settings.model}
                                    onChange={(e) => setSettings({ ...settings, model: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                >
                                    <option value="gpt-4.1-mini">gpt-4.1-mini (1M)</option>
                                    <option value="gpt-4.1">gpt-4.1 (1M)</option>
                                    <option value="gpt-5-mini">gpt-5-mini (400k)</option>
                                    <option value="gpt-5">gpt-5 (272k)</option>
                                    <option value="gpt-4o">gpt-4o (128k)</option>
                                    <option value="gpt-4o-mini">gpt-4o-mini (128k)</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Temperature (0-2)
                                </label>
                                <input
                                    type="number"
                                    min="0"
                                    max="2"
                                    step="0.1"
                                    value={settings.temperature}
                                    onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Generartion Max Tokens
                                </label>
                                <input
                                    type="number"
                                    min="100"
                                    max="10000"
                                    step="100"
                                    value={settings.max_tokens}
                                    onChange={(e) => setSettings({ ...settings, max_tokens: parseInt(e.target.value) })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                            </div>
                        </div>
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
                        <p className="text-xs text-gray-400 mt-2 italic">Настройка "Rate Limit" перенесена в раздел "Настройки чата".</p>
                    </div>

                    {/* Summarizer Settings -> Proactivity Detector */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-4">Проактивность (Детектор завершения диалога)</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Интервал проверки (минуты)
                                </label>
                                <input
                                    type="number"
                                    min="1"
                                    max="60"
                                    value={settings.summarizer_check_interval}
                                    onChange={(e) => setSettings({ ...settings, summarizer_check_interval: parseInt(e.target.value) })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                                <p className="text-xs text-gray-500 mt-1">Как часто система проверяет "зависшие" диалоги.</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Порог молчания (минуты)
                                </label>
                                <input
                                    type="number"
                                    min="1"
                                    max="60"
                                    value={settings.summarizer_idle_threshold}
                                    onChange={(e) => setSettings({ ...settings, summarizer_idle_threshold: parseInt(e.target.value) })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                                <p className="text-xs text-gray-500 mt-1">Сколько минут пользователь должен молчать, чтобы диалог считался завершённым.</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Prompts Tab */}
            {activeTab === 'prompts' && (
                <div className="space-y-6">
                    {/* Agent Memory Prompt */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Промпт для агентов</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Используется для извлечения памяти обычных агентов (Data Analyst, Career Mentor и т.д.)
                        </p>
                        <textarea
                            value={settings.agent_memory_prompt}
                            onChange={(e) => setSettings({ ...settings, agent_memory_prompt: e.target.value })}
                            rows={20}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                            placeholder="Промпт для агентов..."
                        />
                    </div>

                    {/* Assistant Memory Prompt */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Промпт для AI Помощника</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Используется для AI Помощника (обновляет глобальную биографию пользователя)
                        </p>
                        <textarea
                            value={settings.assistant_memory_prompt}
                            onChange={(e) => setSettings({ ...settings, assistant_memory_prompt: e.target.value })}
                            rows={20}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                            placeholder="Промпт для AI Помощника..."
                        />
                    </div>
                </div>
            )}

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
        </div>
    );
}
