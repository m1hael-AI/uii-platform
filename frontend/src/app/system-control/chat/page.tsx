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

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/chat-settings`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.status === 401) {
                router.push('/login');
                return;
            }

            if (!response.ok) {
                throw new Error('Failed to fetch settings');
            }

            const data = await response.json();
            setSettings(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
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

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/chat-settings`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(settings),
            });

            if (response.status === 401) {
                router.push('/login');
                return;
            }

            if (!response.ok) {
                throw new Error('Failed to save settings');
            }

            const updatedSettings = await response.json();
            setSettings(updatedSettings);
            setSuccessMessage('✅ Настройки успешно сохранены');
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-xl">Загрузка...</div>
            </div>
        );
    }

    if (!settings) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-xl text-red-500">Ошибка загрузки настроек</div>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 max-w-4xl">
            <h1 className="text-3xl font-bold mb-6">Настройки Чата</h1>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {successMessage && (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                    {successMessage}
                </div>
            )}

            {/* Блок 1: Общение с пользователями */}
            <div className="bg-white shadow-md rounded-lg p-6 mb-6">
                <h2 className="text-2xl font-semibold mb-4">Общение с пользователями</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Модель
                        </label>
                        <input
                            type="text"
                            value={settings.user_chat_model}
                            onChange={(e) => setSettings({ ...settings, user_chat_model: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

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
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Max Tokens (пусто = без лимита)
                        </label>
                        <input
                            type="number"
                            value={settings.user_chat_max_tokens ?? ''}
                            onChange={(e) => setSettings({ ...settings, user_chat_max_tokens: e.target.value ? parseInt(e.target.value) : null })}
                            placeholder="Без лимита"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Rate Limit (сообщений/минуту)
                        </label>
                        <input
                            type="number"
                            value={settings.rate_limit_per_minute}
                            onChange={(e) => setSettings({ ...settings, rate_limit_per_minute: parseInt(e.target.value) })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                </div>
            </div>

            {/* Блок 2: Вечный диалог (Сжатие контекста) */}
            <div className="bg-white shadow-md rounded-lg p-6 mb-6">
                <h2 className="text-2xl font-semibold mb-4">Вечный диалог (Сжатие контекста)</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Модель для сжатия
                        </label>
                        <input
                            type="text"
                            value={settings.compression_model}
                            onChange={(e) => setSettings({ ...settings, compression_model: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Температура для сжатия
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0"
                            max="2"
                            value={settings.compression_temperature}
                            onChange={(e) => setSettings({ ...settings, compression_temperature: parseFloat(e.target.value) })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Max Tokens для саммари (пусто = без лимита)
                        </label>
                        <input
                            type="number"
                            value={settings.compression_max_tokens ?? ''}
                            onChange={(e) => setSettings({ ...settings, compression_max_tokens: e.target.value ? parseInt(e.target.value) : null })}
                            placeholder="Без лимита"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Порог срабатывания (%)
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0"
                            max="1"
                            value={settings.context_threshold}
                            onChange={(e) => setSettings({ ...settings, context_threshold: parseFloat(e.target.value) })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p className="text-sm text-gray-500 mt-1">
                            0.9 = 90% от лимита
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Сколько последних сообщений оставлять
                        </label>
                        <input
                            type="number"
                            value={settings.context_compression_keep_last}
                            onChange={(e) => setSettings({ ...settings, context_compression_keep_last: parseInt(e.target.value) })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Мягкий лимит контекста (токены)
                        </label>
                        <input
                            type="number"
                            value={settings.context_soft_limit}
                            onChange={(e) => setSettings({ ...settings, context_soft_limit: parseInt(e.target.value) })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                    {saving ? 'Сохранение...' : 'Сохранить настройки'}
                </button>
            </div>

            <div className="mt-4 text-sm text-gray-500">
                Последнее обновление: {new Date(settings.updated_at).toLocaleString('ru-RU')}
            </div>
        </div>
    );
}
