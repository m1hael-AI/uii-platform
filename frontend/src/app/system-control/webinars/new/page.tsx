"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";

type WebinarMode = "upcoming" | "library";
type EventType = "webinar" | "sprint";

export default function NewWebinarPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState<WebinarMode>("upcoming");
    const [eventType, setEventType] = useState<EventType>("webinar");

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

    // Dynamic Fields for Sprint/Webinar
    const [program, setProgram] = useState<{ date: string, title: string, link: string }[]>([]);
    const [bullets, setBullets] = useState<string[]>([]);
    const [newBullet, setNewBullet] = useState("");

    // --- Helpers for Program ---
    const addProgramItem = () => {
        setProgram([...program, { date: "", title: "", link: "" }]);
    };
    const removeProgramItem = (idx: number) => {
        setProgram(program.filter((_, i) => i !== idx));
    };
    const updateProgramItem = (idx: number, field: string, value: string) => {
        const newProgram = [...program];
        // @ts-ignore
        newProgram[idx][field] = value;
        setProgram(newProgram);
    };

    // --- Helpers for Bullets ---
    const addBullet = () => {
        if (newBullet.trim()) {
            setBullets([...bullets, newBullet.trim()]);
            setNewBullet("");
        }
    };
    const removeBullet = (idx: number) => {
        setBullets(bullets.filter((_, i) => i !== idx));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            const token = Cookies.get("token");
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

            let cleanVideoUrl = formData.video_url || "";
            if (cleanVideoUrl && cleanVideoUrl.includes("<iframe")) {
                const srcMatch = cleanVideoUrl.match(/src=["'](.*?)["']/);
                if (srcMatch && srcMatch[1]) {
                    cleanVideoUrl = srcMatch[1];
                }
            }

            const isUpcoming = mode === "upcoming";
            const isSprint = isUpcoming && eventType === "sprint";

            const payload = {
                title: formData.title,
                description: formData.description || null,
                speaker_name: formData.speaker_name || null,
                is_upcoming: isUpcoming,
                is_published: true,

                // New Fields
                type: isUpcoming ? eventType : "webinar",
                program: isSprint ? program : null,
                landing_bullets: bullets.length > 0 ? bullets : null,

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
        <div className="max-w-4xl mx-auto pb-20">
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
                    className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all text-center ${mode === "upcoming"
                            ? "bg-white shadow-sm text-gray-900"
                            : "text-gray-500 hover:text-gray-700"
                        }`}
                >
                    📅 Предстоящий (Schedule)
                </button>
                <button
                    type="button"
                    onClick={() => setMode("library")}
                    className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all text-center ${mode === "library"
                            ? "bg-white shadow-sm text-gray-900"
                            : "text-gray-500 hover:text-gray-700"
                        }`}
                >
                    🎥 Прошедший (Library)
                </button>
            </div>

            <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 space-y-8">

                {/* 1. Basic Info */}
                <div className="space-y-4">
                    <h3 className="text-lg font-bold text-gray-900 border-b pb-2">1. Основная информация</h3>
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
                </div>

                {/* 2. Type Selector (Only for Upcoming) */}
                {mode === "upcoming" && (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-gray-900 border-b pb-2">2. Тип события</h3>
                        <div className="flex gap-4">
                            <label className={`flex-1 border-2 rounded-xl p-4 cursor-pointer transition-all ${eventType === 'webinar' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                                <input type="radio" name="type" className="hidden" checked={eventType === 'webinar'} onChange={() => setEventType('webinar')} />
                                <div className="font-bold text-gray-900">Обычный Вебинар</div>
                                <div className="text-sm text-gray-500">Одно событие, одна дата, одна ссылка.</div>
                            </label>
                            <label className={`flex-1 border-2 rounded-xl p-4 cursor-pointer transition-all ${eventType === 'sprint' ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-gray-300'}`}>
                                <input type="radio" name="type" className="hidden" checked={eventType === 'sprint'} onChange={() => setEventType('sprint')} />
                                <div className="font-bold text-gray-900">Спринт / Курс</div>
                                <div className="text-sm text-gray-500">Серия уроков, программа по дням.</div>
                            </label>
                        </div>
                    </div>
                )}

                {/* 3. Schedule Logic */}
                {mode === "upcoming" && (
                    <div className="p-4 bg-gray-50 border border-gray-100 rounded-lg space-y-4">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-xl">📅</span>
                            <h3 className="font-medium text-gray-900">
                                {eventType === 'sprint' ? 'Настройки старта спринта' : 'Дата проведения'}
                            </h3>
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
                                <label className="block text-sm font-medium text-gray-700 mb-1">Длительность (общая, мин)</label>
                                <input
                                    type="number"
                                    min="15"
                                    value={formData.duration_minutes}
                                    onChange={e => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                            </div>
                        </div>
                        {eventType === 'webinar' && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Ссылка на подключение</label>
                                <input
                                    type="text"
                                    value={formData.connection_link}
                                    onChange={e => setFormData({ ...formData, connection_link: e.target.value })}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                    placeholder="https://zoom.us/..."
                                />
                            </div>
                        )}
                    </div>
                )}

                {/* 4. Sprint Program (Only for Sprints) */}
                {mode === "upcoming" && eventType === "sprint" && (
                    <div className="space-y-4">
                        <div className="flex items-center justify-between border-b pb-2">
                            <h3 className="text-lg font-bold text-gray-900">3. Программа Спринта</h3>
                            <button type="button" onClick={addProgramItem} className="text-sm text-blue-600 hover:text-blue-800 font-medium">+ Добавить урок</button>
                        </div>
                        <div className="space-y-3">
                            {program.length === 0 && <div className="text-gray-400 text-sm italic">Программа пуста. Добавьте первый урок.</div>}
                            {program.map((item, idx) => (
                                <div key={idx} className="flex gap-2 items-start bg-gray-50 p-3 rounded-lg border border-gray-100">
                                    <div className="w-8 pt-2 text-center font-bold text-gray-400">{idx + 1}</div>
                                    <div className="flex-1 space-y-2">
                                        <input
                                            type="datetime-local"
                                            value={item.date}
                                            onChange={e => updateProgramItem(idx, "date", e.target.value)}
                                            className="w-full px-3 py-1.5 border rounded text-sm"
                                            placeholder="Дата урока"
                                        />
                                        <input
                                            type="text"
                                            value={item.title}
                                            onChange={e => updateProgramItem(idx, "title", e.target.value)}
                                            className="w-full px-3 py-1.5 border rounded text-sm"
                                            placeholder="Тема урока (Например: День 1. Введение)"
                                        />
                                        <input
                                            type="text"
                                            value={item.link}
                                            onChange={e => updateProgramItem(idx, "link", e.target.value)}
                                            className="w-full px-3 py-1.5 border rounded text-sm"
                                            placeholder="Ссылка на урок (Zoom)"
                                        />
                                    </div>
                                    <button type="button" onClick={() => removeProgramItem(idx)} className="text-red-400 hover:text-red-600 p-1">✕</button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 5. Landing Bullets */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between border-b pb-2">
                        <h3 className="text-lg font-bold text-gray-900">
                            {eventType === 'sprint' ? '4. Программа / Чему научитесь' : '4. Что будет на вебинаре'}
                        </h3>
                    </div>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={newBullet}
                            onChange={e => setNewBullet(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addBullet())}
                            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            placeholder="Например: Разберем 5 кейсов..."
                        />
                        <button type="button" onClick={addBullet} className="bg-gray-100 hover:bg-gray-200 px-4 rounded-lg font-medium text-gray-700">Добавить</button>
                    </div>
                    <ul className="space-y-2">
                        {bullets.map((b, idx) => (
                            <li key={idx} className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg border border-gray-100">
                                <span className="text-green-500">✓</span>
                                <span className="flex-1 text-gray-700">{b}</span>
                                <button type="button" onClick={() => removeBullet(idx)} className="text-gray-400 hover:text-red-500">удалить</button>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* 6. Library Mode Logic (Unchanged but wrapped) */}
                {mode === "library" && (
                    <div className="p-4 bg-purple-50 border border-purple-100 rounded-lg space-y-4">
                        {/* ... Library fields logic kept same ... */}
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
                            <label className="block text-sm font-medium text-gray-700 mb-1">Транскрибация (Context)</label>
                            <textarea
                                rows={6}
                                value={formData.transcript_context}
                                onChange={e => setFormData({ ...formData, transcript_context: e.target.value })}
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none font-mono text-sm"
                                placeholder="Текст для RAG..."
                            />
                        </div>
                    </div>
                )}

                {/* Description */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                    <textarea
                        rows={4}
                        value={formData.description}
                        onChange={e => setFormData({ ...formData, description: e.target.value })}
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                        placeholder="О чем будет этот вебинар..."
                    />
                </div>

                {/* Sticky Footer */}
                <div className="sticky bottom-0 bg-white border-t border-gray-100 p-4 -mx-8 -mb-8 flex justify-end gap-3 rounded-b-xl z-10">
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
                        className={`px-6 py-2 text-white font-medium rounded-lg transition-colors shadow-sm disabled:opacity-50 ${mode === "upcoming"
                                ? "bg-blue-600 hover:bg-blue-700"
                                // @ts-ignore
                                : "bg-purple-600 hover:bg-purple-700"
                            }`}
                    >
                        {loading ? "Сохранение..." : "Создать"}
                    </button>
                </div>
            </form>
        </div>
    );
}
