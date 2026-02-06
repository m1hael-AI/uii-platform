'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';

interface ChatSettings {
    id: number;
    // Блок 1: Общение с пользователями
    user_chat_model: string;
    user_chat_temperature: number;
    user_chat_max_tokens: number | null;
    rate_limit_per_minute: number;
    // Блок 2: Вечный диалог (Сжатие контекста)
    compression_model: string;
    compression_temperature: number;
    compression_max_tokens: number | null;
    context_threshold: number;
    context_compression_keep_last: number;
    compression_prompt: string;
    updated_at: string;
}

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

export default function ChatSettingsPage() {
    const router = useRouter();
    const [settings, setSettings] = useState<ChatSettings | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

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
            const response = await fetch(`${API_URL}/admin/chat-settings`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.status === 403) {
                setError('Доступ запрещён. Требуются права администратора.');
                return;
            }
            if (response.status === 401) {
                router.push('/login');
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
        setSuccessMessage(null);

        try {
            const token = Cookies.get('token');
            if (!token) {
                router.push('/login');
                return;
            }

            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const response = await fetch(`${API_URL}/admin/chat-settings`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(settings),
            });

            if (response.status === 403) {
                setError('Доступ запрещён.');
                return;
            }
            if (response.status === 401) {
                router.push('/login');
                return;
            }

            if (!response.ok) {
                throw new Error('Ошибка сохранения настроек');
            }

            const updatedSettings = await response.json();
            setSettings(updatedSettings);
            setSuccessMessage('✅ Настройки успешно сохранены');
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
        } finally {
            setSaving(false);
        }
    };

    // Лимит модели для сжатия (определяет порог срабатывания вечного диалога)
    const getChatModelMaxTokens = () => {
        if (!settings) return 128000;
        return MODEL_LIMITS[settings.user_chat_model] || 128000;
    };

    // Trigger Point рассчитывается от основной модели общения
    const getEffectiveLimit = () => {
        if (!settings) return 0;
        const maxTokens = getChatModelMaxTokens();
        const threshold = settings.context_threshold || 0.9;
        return Math.floor(maxTokens * threshold);
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
                <div className="text-center text-red-600">
                    <p className="text-xl font-semibold mb-2">Ошибка</p>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    if (!settings) return null;

    return (
        <div className="max-w-6xl mx-auto">
            {/* Header with Breadcrumbs */}
            <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => router.push("/system-control")}>
                    System Control
                </span>
                <span className="text-gray-300">/</span>
                <span>Настройки чата</span>
            </h1>

            {/* Success/Error Messages */}
            {successMessage && (
                <div className="mb-6 bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
                    {successMessage}
                </div>
            )}
            {error && (
                <div className="mb-6 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
                    ❌ {error}
                </div>
            )}

            <div className="space-y-6">

                {/* Block 1: User User Chat Settings */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <h2 className="text-xl font-semibold mb-4">Общение с пользователями</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

                        {/* Model Selector */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Модель
                            </label>
                            <div className="relative">
                                <select
                                    value={settings.user_chat_model}
                                    onChange={(e) => setSettings({ ...settings, user_chat_model: e.target.value })}
                                    className="w-full pl-3 pr-8 py-2 border border-gray-300 rounded-lg appearance-none focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent bg-white"
                                >
                                    {AVAILABLE_MODELS.map(m => (
                                        <option key={m} value={m}>{m}</option>
                                    ))}
                                    {!AVAILABLE_MODELS.includes(settings.user_chat_model) && (
                                        <option value={settings.user_chat_model}>{settings.user_chat_model} (Custom)</option>
                                    )}
                                </select>
                                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                                    <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" /></svg>
                                </div>
                            </div>
                        </div>

                        {/* Temperature */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Температура
                            </label>
                            <input
                                type="number"
                                step="0.1"
                                min="0"
                                max="2"
                                value={settings.user_chat_temperature}
                                onChange={(e) => setSettings({ ...settings, user_chat_temperature: parseFloat(e.target.value) })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                        </div>

                        {/* Max Tokens */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Max Tokens (Ответ)
                            </label>
                            <input
                                type="number"
                                min="1"
                                placeholder="Без лимита"
                                value={settings.user_chat_max_tokens ?? ''}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    setSettings({ ...settings, user_chat_max_tokens: val === '' ? null : parseInt(val) });
                                }}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">Оставьте пустым для безлимита</p>
                        </div>

                        {/* Rate Limit */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Rate Limit (сообщ/мин)
                            </label>
                            <input
                                type="number"
                                min="1"
                                max="1000"
                                value={settings.rate_limit_per_minute || 15}
                                onChange={(e) => setSettings({ ...settings, rate_limit_per_minute: parseInt(e.target.value) })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                        </div>
                    </div>
                </div>

                {/* Context Compression Settings -> Infinite Dialog */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h2 className="text-xl font-semibold">Вечный диалог (Сжатие контекста)</h2>
                            <p className="text-sm text-gray-500">Автоматически сжимает переписку при достижении лимита</p>
                        </div>
                        <div className="text-right bg-blue-50 px-3 py-2 rounded-lg border border-blue-100">
                            <div className="text-xs text-blue-600 font-semibold uppercase">Trigger Point</div>
                            <div className="text-lg font-bold text-blue-800">
                                ~{getEffectiveLimit().toLocaleString()} tokens
                            </div>
                            <div className="text-xs text-blue-500">
                                (Model Max: {getChatModelMaxTokens().toLocaleString()})
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                        {/* Compression Model */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Модель для сжатия
                            </label>
                            <div className="relative">
                                <select
                                    value={settings.compression_model}
                                    onChange={(e) => setSettings({ ...settings, compression_model: e.target.value })}
                                    className="w-full pl-3 pr-8 py-2 border border-gray-300 rounded-lg appearance-none focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent bg-white"
                                >
                                    {AVAILABLE_MODELS.map(m => (
                                        <option key={m} value={m}>{m}</option>
                                    ))}
                                    {!AVAILABLE_MODELS.includes(settings.compression_model) && (
                                        <option value={settings.compression_model}>{settings.compression_model} (Custom)</option>
                                    )}
                                </select>
                                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                                    <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" /></svg>
                                </div>
                            </div>
                        </div>

                        {/* Compression Temp */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Температура сжатия
                            </label>
                            <input
                                type="number"
                                step="0.1"
                                min="0"
                                max="2"
                                value={settings.compression_temperature}
                                onChange={(e) => setSettings({ ...settings, compression_temperature: parseFloat(e.target.value) })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                        </div>

                        {/* Compression Max Tokens */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Max Tokens (Саммари)
                            </label>
                            <input
                                type="number"
                                min="1"
                                placeholder="Без лимита"
                                value={settings.compression_max_tokens ?? ''}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    setSettings({ ...settings, compression_max_tokens: val === '' ? null : parseInt(val) });
                                }}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">Лимит длины самого саммари</p>
                        </div>

                        {/* Keep Last */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Оставлять сообщений (Keep Last)
                            </label>
                            <input
                                type="number"
                                min="1"
                                value={settings.context_compression_keep_last}
                                onChange={(e) => setSettings({ ...settings, context_compression_keep_last: parseInt(e.target.value) })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">Сколько последних оставлять</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Порог срабатывания (%)
                            </label>
                            <div className="flex items-center gap-2">
                                <input
                                    type="range"
                                    min="0.01"
                                    max="1.0"
                                    step="0.01"
                                    value={settings.context_threshold || 0.9}
                                    onChange={(e) => setSettings({ ...settings, context_threshold: parseFloat(e.target.value) })}
                                    className="flex-1"
                                />
                                <span className="w-12 text-sm font-bold text-gray-700">
                                    {Math.round((settings.context_threshold || 0.9) * 100)}%
                                </span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                                Сжимать, когда занято {Math.round((settings.context_threshold || 0.9) * 100)}% от лимита основной модели ({getChatModelMaxTokens().toLocaleString()}).
                            </p>
                        </div>
                    </div>

                    {/* Compression Prompt (Aggregated) */}
                    <div className="mt-6 border-t border-gray-100 pt-6">
                        <label className="block text-lg font-medium text-gray-900 mb-2">
                            Промпт сжатия
                        </label>
                        <p className="text-sm text-gray-500 mb-4">
                            Инструкция для модели, как именно сжимать диалог при достижении лимита.
                        </p>
                        <textarea
                            value={settings.compression_prompt || ""}
                            onChange={(e) => setSettings({ ...settings, compression_prompt: e.target.value })}
                            rows={12}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                            placeholder="Введите промпт для сжатия..."
                        />
                    </div>
                </div>
            </div>

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
