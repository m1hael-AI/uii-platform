"use client";

import { useState, useEffect } from "react";
import Cookies from "js-cookie";

interface SystemConfig {
    key: string;
    value: string;
    description?: string;
}

export default function AdminSettingsPage() {
    const [configs, setConfigs] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Known keys to manage
    const KEYS = [
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

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    useEffect(() => {
        fetchConfigs();
    }, []);

    const fetchConfigs = async () => {
        const token = Cookies.get("token");
        try {
            const res = await fetch(`${API_URL}/admin/configs`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data: SystemConfig[] = await res.json();
                const configMap: Record<string, string> = {};
                data.forEach(c => configMap[c.key] = c.value);
                setConfigs(configMap);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async (key: string, value: string) => {
        const token = Cookies.get("token");
        setSaving(true);
        try {
            const res = await fetch(`${API_URL}/admin/configs/${key}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ value, description: "Webinar Template" })
            });

            if (res.ok) {
                alert("Сохранено!");
                fetchConfigs();
            } else {
                alert("Ошибка сохранения");
            }
        } catch (e) {
            alert("Ошибка сети");
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-8">Загрузка настроек...</div>;

    return (
        <div className="w-full max-w-2xl">
            <h1 className="text-2xl font-bold text-gray-800 mb-8">Настройки системы</h1>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-8">
                <h2 className="text-lg font-bold border-b pb-2 mb-4">Шаблоны уведомлений (Telegram)</h2>

                {KEYS.map(item => (
                    <div key={item.key}>
                        <label className="block text-sm font-bold text-gray-700 mb-1">
                            {item.label}
                        </label>
                        <p className="text-xs text-gray-400 mb-2">{item.desc}</p>

                        <div className="flex gap-2 items-start">
                            <textarea
                                value={configs[item.key] !== undefined ? configs[item.key] : ""}
                                onChange={(e) => setConfigs({ ...configs, [item.key]: e.target.value })}
                                className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-orange-500 outline-none min-h-[100px] text-sm font-medium"
                                placeholder={item.default}
                            />
                        </div>
                        <div className="flex justify-end mt-2">
                            <button
                                onClick={() => handleSave(item.key, configs[item.key] || "")}
                                disabled={saving}
                                className="px-4 py-1.5 bg-gray-900 text-white text-xs rounded hover:bg-black transition-colors"
                            >
                                Сохранить
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <div className="mt-8 p-4 bg-blue-50 text-blue-800 text-sm rounded-lg flex gap-3">
                <span className="text-xl">ℹ️</span>
                <div>
                    <strong>Как тестировать?</strong><br />
                    Чтобы проверить отправку, используйте скрипт на сервере или дождитесь реального вебинара.
                    В будущем здесь появится кнопка "Отправить тест".
                </div>
            </div>
        </div>
    );
}
