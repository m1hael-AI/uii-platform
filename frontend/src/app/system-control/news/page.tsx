'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';

interface NewsConfig {
    prompts: {
        harvester: string;
        harvester_nightly_prompt: string;
        harvester_search_prompt: string;
        writer: string;
        allowed_tags: string;
    };
    schedule: {
        harvester_cron: string;
        harvester_enabled: boolean;
        generator_cron: string;
        generator_enabled: boolean;
    };
    settings: {
        dedup_threshold: number;
        generator_batch_size: number;
        generator_delay: number;
    };
    stats: {
        total_news: number;
        status_counts: {
            PENDING: number;
            COMPLETED: number;
            FAILED: number;
        };
    };
    updated_at: string | null;
}

export default function NewsAdminPage() {
    const router = useRouter();
    const [config, setConfig] = useState<NewsConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [activeTab, setActiveTab] = useState<'prompts' | 'schedule' | 'settings'>('prompts');

    useEffect(() => {
        fetchConfig();
    }, []);

    const fetchConfig = async () => {
        try {
            const token = Cookies.get('token');
            if (!token) {
                router.push('/login');
                return;
            }

            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const response = await fetch(`${API_URL}/admin/news/config`, {
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
            setConfig(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!config) return;

        setSaving(true);
        setError(null);
        setSuccess(false);

        try {
            const token = Cookies.get('token');
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            const response = await fetch(`${API_URL}/admin/news/config`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config),
            });

            if (!response.ok) {
                throw new Error('Ошибка сохранения настроек');
            }

            const data = await response.json();
            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
            await fetchConfig(); // Reload to get updated stats
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

    if (error && !config) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
                    <h2 className="text-red-800 font-semibold mb-2">Ошибка</h2>
                    <p className="text-red-600">{error}</p>
                </div>
            </div>
        );
    }

    if (!config) return null;

    return (
        <div className="max-w-6xl mx-auto">
            {/* Header */}
            <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => router.push("/system-control")}>
                    System Control
                </span>
                <span className="text-gray-300">/</span>
                <span>Управление AI News</span>
            </h1>

            {/* Stats Banner */}
            <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg p-4 mb-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                    <div>
                        <div className="text-2xl font-bold text-amber-600">{config.stats.total_news}</div>
                        <div className="text-sm text-gray-600">Всего новостей</div>
                    </div>
                    <div>
                        <div className="text-2xl font-bold text-green-600">{config.stats.status_counts.COMPLETED}</div>
                        <div className="text-sm text-gray-600">Готово</div>
                    </div>
                    <div>
                        <div className="text-2xl font-bold text-yellow-600">{config.stats.status_counts.PENDING}</div>
                        <div className="text-sm text-gray-600">В очереди</div>
                    </div>
                    <div>
                        <div className="text-2xl font-bold text-red-600">{config.stats.status_counts.FAILED}</div>
                        <div className="text-sm text-gray-600">Ошибки</div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-4 mb-6 border-b border-gray-200">
                <button
                    onClick={() => setActiveTab('prompts')}
                    className={`px-4 py-2 font-medium transition-colors focus:outline-none ${activeTab === 'prompts'
                        ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                        : 'text-gray-600 hover:text-[#FF6B35]'
                        }`}
                >
                    Промпты
                </button>
                <button
                    onClick={() => setActiveTab('schedule')}
                    className={`px-4 py-2 font-medium transition-colors focus:outline-none ${activeTab === 'schedule'
                        ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                        : 'text-gray-600 hover:text-[#FF6B35]'
                        }`}
                >
                    Расписание
                </button>
                <button
                    onClick={() => setActiveTab('settings')}
                    className={`px-4 py-2 font-medium transition-colors focus:outline-none ${activeTab === 'settings'
                        ? 'text-[#FF6B35] border-b-2 border-[#FF6B35]'
                        : 'text-gray-600 hover:text-[#FF6B35]'
                        }`}
                >
                    Параметры
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

            {/* Prompts Tab */}
            {activeTab === 'prompts' && (
                <div className="space-y-6">
                    {/* Harvester Prompt */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Промпт для Harvester</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Используется для поиска новостей через Perplexity API
                        </p>
                        <textarea
                            value={config.prompts.harvester}
                            onChange={(e) => setConfig({
                                ...config,
                                prompts: { ...config.prompts, harvester: e.target.value }
                            })}
                            rows={6}
                            placeholder="You are a news aggregator AI..."
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                        />
                    </div>

                    {/* Harvester Nightly Prompt */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Промпт для Harvester (Ночной сбор)</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Используется для автоматического сбора новостей каждую ночь
                        </p>
                        <textarea
                            value={config.prompts.harvester_nightly_prompt}
                            onChange={(e) => setConfig({
                                ...config,
                                prompts: { ...config.prompts, harvester_nightly_prompt: e.target.value }
                            })}
                            rows={6}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                        />
                    </div>

                    {/* Harvester Search Prompt */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Промпт для Harvester (Поиск / Context-Aware)</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Используется для поиска по запросу. Должен содержать placeholder <code>{'{context}'}</code> и <code>{'{query}'}</code>.
                        </p>
                        <textarea
                            value={config.prompts.harvester_search_prompt}
                            onChange={(e) => setConfig({
                                ...config,
                                prompts: { ...config.prompts, harvester_search_prompt: e.target.value }
                            })}
                            rows={6}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                        />
                    </div>

                    {/* Allowed Tags */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Разрешенные теги</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Список тегов через запятую. Harvester будет выбирать только из них.
                        </p>
                        <textarea
                            value={config.prompts.allowed_tags}
                            onChange={(e) => setConfig({
                                ...config,
                                prompts: { ...config.prompts, allowed_tags: e.target.value }
                            })}
                            rows={3}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                        />
                    </div>

                    {/* Writer Prompt */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-2">Промпт для Writer</h2>
                        <p className="text-sm text-gray-600 mb-4">
                            Используется для генерации полных статей
                        </p>
                        <textarea
                            value={config.prompts.writer}
                            onChange={(e) => setConfig({
                                ...config,
                                prompts: { ...config.prompts, writer: e.target.value }
                            })}
                            rows={10}
                            placeholder="You are a professional tech writer..."
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono text-sm"
                        />
                    </div>
                </div>
            )}

            {/* Schedule Tab */}
            {activeTab === 'schedule' && (
                <div className="space-y-6">
                    {/* Harvester Schedule */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-4">Расписание Harvester</h2>
                        <div className="space-y-4">
                            <label className="flex items-center gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={config.schedule.harvester_enabled}
                                    onChange={(e) => setConfig({
                                        ...config,
                                        schedule: { ...config.schedule, harvester_enabled: e.target.checked }
                                    })}
                                    className="w-5 h-5 text-[#FF6B35] rounded focus:ring-[#FF6B35]"
                                />
                                <span className="font-medium">Включить автоматический сбор новостей</span>
                            </label>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Cron выражение</label>
                                <input
                                    type="text"
                                    value={config.schedule.harvester_cron}
                                    onChange={(e) => setConfig({
                                        ...config,
                                        schedule: { ...config.schedule, harvester_cron: e.target.value }
                                    })}
                                    placeholder="0 2 * * *"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono"
                                />
                                <p className="text-xs text-gray-500 mt-1">По умолчанию: 0 2 * * * (каждый день в 2:00)</p>
                            </div>
                        </div>
                    </div>

                    {/* Generator Schedule */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-4">Расписание Generator</h2>
                        <div className="space-y-4">
                            <label className="flex items-center gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={config.schedule.generator_enabled}
                                    onChange={(e) => setConfig({
                                        ...config,
                                        schedule: { ...config.schedule, generator_enabled: e.target.checked }
                                    })}
                                    className="w-5 h-5 text-[#FF6B35] rounded focus:ring-[#FF6B35]"
                                />
                                <span className="font-medium">Включить автоматическую генерацию статей</span>
                            </label>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Cron выражение</label>
                                <input
                                    type="text"
                                    value={config.schedule.generator_cron}
                                    onChange={(e) => setConfig({
                                        ...config,
                                        schedule: { ...config.schedule, generator_cron: e.target.value }
                                    })}
                                    placeholder="*/15 * * * *"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent font-mono"
                                />
                                <p className="text-xs text-gray-500 mt-1">По умолчанию: */15 * * * * (каждые 15 минут)</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Settings Tab */}
            {activeTab === 'settings' && (
                <div className="space-y-6">
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold mb-4">Параметры системы</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Порог дедупликации (Cosine Similarity)
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    max="1"
                                    value={config.settings.dedup_threshold}
                                    onChange={(e) => setConfig({
                                        ...config,
                                        settings: { ...config.settings, dedup_threshold: parseFloat(e.target.value) }
                                    })}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                                <p className="text-xs text-gray-500 mt-1">Значение от 0.0 до 1.0. По умолчанию: 0.84</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Размер пакета генератора
                                </label>
                                <input
                                    type="number"
                                    min="1"
                                    max="20"
                                    value={config.settings.generator_batch_size}
                                    onChange={(e) => setConfig({
                                        ...config,
                                        settings: { ...config.settings, generator_batch_size: parseInt(e.target.value) }
                                    })}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                                <p className="text-xs text-gray-500 mt-1">Максимум новостей для генерации за один запуск. По умолчанию: 5</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Задержка между генерациями (секунды)
                                </label>
                                <input
                                    type="number"
                                    min="0"
                                    max="60"
                                    value={config.settings.generator_delay}
                                    onChange={(e) => setConfig({
                                        ...config,
                                        settings: { ...config.settings, generator_delay: parseInt(e.target.value) }
                                    })}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#FF6B35] focus:border-transparent"
                                />
                                <p className="text-xs text-gray-500 mt-1">Задержка между генерациями для снижения нагрузки на API. По умолчанию: 2</p>
                            </div>
                        </div>
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
