"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";

type WebinarMode = "upcoming" | "library";

export default function NewWebinarPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState<WebinarMode>("upcoming");
    
    const [formData, setFormData] = useState({
        title: "",
        description: "",
        speaker_name: "",
        // Schedule fields
        scheduled_at: "",
        duration_minutes: 60,
        connection_link: "https://zoom.us/j/...",
        // Library fields
        video_url: "",
        transcript_context: "",
        conducted_at: "",
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            const token = Cookies.get("token");
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            // Clean up video URL (handle raw iframe code)
            let cleanVideoUrl = formData.video_url || "";
            if (cleanVideoUrl && cleanVideoUrl.includes("<iframe")) {
                const srcMatch = cleanVideoUrl.match(/src=["'](.*?)["']/);
                if (srcMatch && srcMatch[1]) {
                    cleanVideoUrl = srcMatch[1];
                }
            }

            // Prepare payload based on mode
            const isUpcoming = mode === "upcoming";
            
            const payload = {
                title: formData.title,
                description: formData.description || null,
                speaker_name: formData.speaker_name || null,
                is_upcoming: isUpcoming,
                is_published: true, // Always publish
                
                // Fields specific to Upcoming
                ...(isUpcoming && {
                    scheduled_at: formData.scheduled_at ? new Date(formData.scheduled_at).toISOString() : new Date().toISOString(),
                    duration_minutes: formData.duration_minutes,
                    connection_link: formData.connection_link
                }),

                // Fields specific to Library
                ...(!isUpcoming && {
                    video_url: cleanVideoUrl,
                    transcript_context: formData.transcript_context || null,
                    conducted_at: formData.conducted_at ? new Date(formData.conducted_at).toISOString() : new Date().toISOString(),
                })
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

            {/* Mode Switcher Tabs */}
            <div className="flex p-1 bg-gray-100 rounded-xl mb-6 select-none">
                <button
                    type="button"
                    onClick={() => setMode("upcoming")}
                    className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all text-center ${
                        mode === "upcoming" 
                            ? "bg-white shadow-sm text-gray-900" 
                            : "text-gray-500 hover:text-gray-700"
                    }`}
                >
                    📅 Предстоящий (Schedule)
                </button>
                <button
                    type="button"
                    onClick={() => setMode("library")}
                    className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all text-center ${
                        mode === "library" 
                            ? "bg-white shadow-sm text-gray-900" 
                            : "text-gray-500 hover:text-gray-700"
                    }`}
                >
                    🎥 Прошедший (Library)
                </button>
            </div>

            <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 space-y-6">
                
                {/* Common Fields */}
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
                </div>

                {/* Conditional Fields: UPCOMING */}
                {mode === "upcoming" && (
                    <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg space-y-4">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-xl">📅</span>
                            <h3 className="font-medium text-blue-900">Настройки расписания</h3>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Дата и время начала</label>
                                <input
                                    required
                                    type="datetime-local"
                                    value={formData.scheduled_at}
                                    onChange={e => setFormData({ ...formData, scheduled_at: e.target.value })}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
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

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Ссылка на подключение (Zoom/Meet)</label>
                            <input
                                type="text"
                                value={formData.connection_link}
                                onChange={e => setFormData({ ...formData, connection_link: e.target.value })}
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                placeholder="https://zoom.us/..."
                            />
                        </div>
                    </div>
                )}

                {/* Conditional Fields: LIBRARY */}
                {mode === "library" && (
                     <div className="p-4 bg-purple-50 border border-purple-100 rounded-lg space-y-4">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-xl">🎥</span>
                            <h3 className="font-medium text-purple-900">Настройки записи</h3>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Дата проведения</label>
                                <input
                                    type="datetime-local"
                                    value={formData.conducted_at}
                                    onChange={e => setFormData({ ...formData, conducted_at: e.target.value })}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Ссылка на видео (YouTube/Embed)</label>
                                <input
                                    required
                                    type="text"
                                    value={formData.video_url}
                                    onChange={e => setFormData({ ...formData, video_url: e.target.value })}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none"
                                    placeholder="https://youtube.com/..."
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Транскрибация (Context)
                                <span className="ml-2 text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded-full">Для RAG поиска</span>
                            </label>
                            <textarea
                                rows={6}
                                value={formData.transcript_context}
                                onChange={e => setFormData({ ...formData, transcript_context: e.target.value })}
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none font-mono text-sm"
                                placeholder="Вставьте полный текст транскрибации вебинара здесь. Это поможет AI отвечать на вопросы по содержанию..."
                            />
                        </div>
                     </div>
                )}

                {/* Common Description */}
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

                {/* Sticky Footer */}
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
                        className={`px-6 py-2 text-white font-medium rounded-lg transition-colors shadow-sm disabled:opacity-50 ${
                            mode === "upcoming" 
                                ? "bg-blue-600 hover:bg-blue-700" 
                                : "bg-purple-600 hover:bg-purple-700"
                        }`}
                    >
                        {loading 
                            ? "Сохранение..." 
                            : mode === "upcoming" ? "Запланировать вебинар" : "Добавить запись"}
                    </button>
                </div>
            </form>
        </div>
    );
}
