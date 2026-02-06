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
    context_soft_limit: number;
    updated_at: string;
}

// Limits referenced from Backend (context_manager.py)
const MODEL_LIMITS: Record<string, number> = {
    "gpt-4.1": 1000000,
    "gpt-4.1-mini": 1000000,
    "gpt-5": 272000,
    "gpt-5-mini": 400000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
};

export default function ChatSettingsPage() {
    const router = useRouter();
    const [settings, setSettings] = useState<ChatSettings | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

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

            if (!response.ok) {
                throw new Error('Ошибка сохранения настроек');
            }

            const updatedSettings = await response.json();
            setSettings(updatedSettings);
            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
        } finally {
            setSaving(false);
        }
    };

    const getModelMaxTokens = () => {
        if (!settings) return 128000;
        return MODEL_LIMITS[settings.user_chat_model] || 128000;
    };

    // Helper to calc effective limit
    const getEffectiveLimit = () => {
        if (!settings) return 0;
        // If soft_limit is set (>0), use it. Otherwise use Model Max.
        const baseLimit = (settings.context_soft_limit && settings.context_soft_limit > 0)
            ? settings.context_soft_limit
            : getModelMaxTokens();
        return Math.floor(baseLimit * (settings.context_threshold || 0.9));
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
            {success && (
                <div className="mb-6 bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
                    ✅ Настройки успешно сохранены
                </div>
            )}
            {error && (
                <div className="mb-6 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
                    ❌ {error}
                </div>
            )}

            <div className="space-y-6">
                {/* Rate Limit Block */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <h2 className="text-xl font-semibold mb-4">Лимиты сообщений</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Сообщений в минуту (Rate Limit)
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
                                (Model Max: {getModelMaxTokens().toLocaleString()})
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Лимит токенов (Override)
                            </label>
                            <input
                                type="number"
                                min="0"
                                max="1000000"
                                step="1000"
                                placeholder={`Auto (${getModelMaxTokens()})`}
                                value={settings.context_soft_limit || ''}
                                onChange={(e) => setSettings({ ...settings, context_soft_limit: parseInt(e.target.value) || 0 })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Укажите <b>0</b> или пусто, чтобы использовать аппаратный лимит ({getModelMaxTokens().toLocaleString()}).
                            </p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Порог срабатывания (%)
                            </label>
                            <div className="flex items-center gap-2">
                                <input
                                    type="range"
                                    min="0.1"
                                    max="1.0"
                                    step="0.05"
                                    value={settings.context_threshold || 0.9}
                                    onChange={(e) => setSettings({ ...settings, context_threshold: parseFloat(e.target.value) })}
                                    className="flex-1"
                                />
                                <span className="w-12 text-sm font-bold text-gray-700">
                                    {Math.round((settings.context_threshold || 0.9) * 100)}%
                                </span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                                Сжимать, когда занято {Math.round((settings.context_threshold || 0.9) * 100)}% от лимита.
                            </p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Оставлять сообщений (Keep Last)
                            </label>
                            <input
                                type="number"
                                min="5"
                                max="100"
                                value={settings.context_compression_keep_last || 20}
                                onChange={(e) => setSettings({ ...settings, context_compression_keep_last: parseInt(e.target.value) })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">Сколько последних сообщений НЕ сжимать.</p>
                        </div>
                    </div>
                </div>

                {/* Save Button */}
                <div className="flex justify-end gap-4">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-6 py-3 bg-[#FF6B35] text-white font-semibold rounded-lg hover:bg-[#E55A2B] disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                        {saving ? 'Сохранение...' : 'Сохранить настройки'}
                    </button>
                </div>
            </div>
        </div>
    );
}
