"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";

export default function NewWebinarPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        title: "",
        description: "",
        speaker_name: "",
        scheduled_at: "",
        duration_minutes: 60,
        video_url: "",
        is_published: true,
        is_upcoming: true
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            const token = Cookies.get("token");
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            // Clean up video URL (handle raw iframe code)
            let cleanVideoUrl = formData.video_url || null;
            if (cleanVideoUrl && cleanVideoUrl.includes("<iframe")) {
                const srcMatch = cleanVideoUrl.match(/src=["'](.*?)["']/);
                if (srcMatch && srcMatch[1]) {
                    cleanVideoUrl = srcMatch[1];
                }
            }

            const payload = {
                ...formData,
                scheduled_at: formData.scheduled_at ? new Date(formData.scheduled_at).toISOString() : null,
                description: formData.description || null,
                speaker_name: formData.speaker_name || null,
                video_url: cleanVideoUrl,
                is_published: true // Always publish (removed draft logic)
            };

            const res = await fetch(`${API_URL}/webinars`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                router.push("/system-control/webinars");
            } else {
                alert("Ошибка создания: " + res.statusText);
            }
        } catch (e) {
            console.error(e);
            alert("Ошибка сети");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto">
            <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => router.push("/system-control/webinars")}>
                    Вебинары
                </span>
                <span className="text-gray-300">/</span>
                <span>Новый вебинар</span>
            </h1>

            <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 space-y-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Название вебинара</label>
                    <input
                        required
                        type="text"
                        value={formData.title}
                        onChange={e => setFormData({ ...formData, title: e.target.value })}
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        placeholder="Как стать AI-разработчиком"
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Спикер</label>
                        <input
                            type="text"
                            value={formData.speaker_name}
                            onChange={e => setFormData({ ...formData, speaker_name: e.target.value })}
                            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            placeholder="Иван Иванов"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Длительность (мин)</label>
                        <input
                            type="number"
                            min="15"
                            value={formData.duration_minutes}
                            onChange={e => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
                            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Дата начала</label>
                        <input
                            type="datetime-local"
                            value={formData.scheduled_at}
                            onChange={e => setFormData({ ...formData, scheduled_at: e.target.value })}
                            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Ссылка (Zoom/YouTube)</label>
                        <input
                            type="text"
                            placeholder="https://..."
                            value={formData.video_url}
                            onChange={e => setFormData({ ...formData, video_url: e.target.value })}
                            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Описание / Программа</label>
                    <textarea
                        rows={4}
                        value={formData.description}
                        onChange={e => setFormData({ ...formData, description: e.target.value })}
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                        placeholder="О чем будет этот вебинар..."
                    />
                </div>

                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-sm font-medium text-gray-900">Статус: {formData.is_upcoming ? "Предстоящий" : "Прошедший"}</h3>
                            <p className="text-xs text-gray-500 mt-1">
                                {formData.is_upcoming
                                    ? "Вебинар еще не начался. Ссылка будет вести на трансляцию."
                                    : "Вебинар завершен. Ссылка будет вести на запись."}
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => setFormData({ ...formData, is_upcoming: !formData.is_upcoming })}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 ${formData.is_upcoming ? 'bg-purple-600' : 'bg-gray-300'
                                }`}
                        >
                            <span
                                className={`${formData.is_upcoming ? 'translate-x-6' : 'translate-x-1'
                                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                            />
                        </button>
                    </div>
                </div>

                {/* Sticky Footer for mobile/scroll issues */}
                <div className="sticky bottom-0 bg-white border-t border-gray-100 p-4 -mx-8 -mb-8 mt-4 flex justify-end gap-3 rounded-b-xl z-10 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
                    <button
                        type="button"
                        onClick={() => router.back()}
                        className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        Отмена
                    </button>
                    <button
                        type="submit"
                        disabled={loading}
                        className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
                    >
                        {loading ? "Сохранение..." : "Создать вебинар"}
                    </button>
                </div>
            </form>
        </div>
    );
}
