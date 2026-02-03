"use client";

import { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";

interface Webinar {
    id: number;
    title: string;
    description: string;
    video_url: string;
    connection_link?: string;
    thumbnail_url?: string;
    is_upcoming: boolean;
    is_published: boolean;
    transcript_context?: string; // Транскрипция для AI
    date?: string; // Frontend formatted date
}

export default function AdminWebinarsPage() {
    const router = useRouter();
    const [webinars, setWebinars] = useState<Webinar[]>([]);
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);

    // Form State
    const [selectedWebinar, setSelectedWebinar] = useState<Webinar | null>(null); // If null, mode is CREATE
    const [formData, setFormData] = useState({
        title: "",
        description: "",
        video_url: "",
        connection_link: "",
        thumbnail_url: "",
        transcript_context: "",
        is_upcoming: false,
        is_published: true
    });

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    useEffect(() => {
        fetchWebinars();
    }, []);

    const fetchWebinars = async () => {
        const token = Cookies.get("token");
        try {
            const res = await fetch(`${API_URL}/webinars?filter_type=all`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setWebinars(data);
            }
        } catch (e) {
            console.error("Failed to fetch webinars", e);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateNew = () => {
        setSelectedWebinar(null);
        setFormData({
            title: "",
            description: "",
            video_url: "",
            connection_link: "",
            thumbnail_url: "",
            transcript_context: "",
            is_upcoming: false,
            is_published: true
        });
        setIsEditing(true);
    };

    const handleEdit = (webinar: Webinar) => {
        setSelectedWebinar(webinar);
        setFormData({
            title: webinar.title,
            description: webinar.description || "",
            video_url: webinar.video_url || "",
            connection_link: webinar.connection_link || "",
            thumbnail_url: webinar.thumbnail_url || "",
            transcript_context: webinar.transcript_context || "",
            is_upcoming: webinar.is_upcoming,
            is_published: webinar.is_published
        });
        setIsEditing(true);
    };

    const handleSave = async () => {
        const token = Cookies.get("token");
        const method = selectedWebinar ? "PATCH" : "POST";
        const url = selectedWebinar
            ? `${API_URL}/webinars/${selectedWebinar.id}`
            : `${API_URL}/webinars`;

        try {
            const res = await fetch(url, {
                method,
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify(formData)
            });

            if (res.ok) {
                setIsEditing(false);
                fetchWebinars(); // Refresh list
            } else {
                alert("Ошибка сохранения");
            }
        } catch (e) {
            alert("Ошибка сети");
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Вы уверены, что хотите удалить этот вебинар?")) return;

        const token = Cookies.get("token");
        try {
            await fetch(`${API_URL}/webinars/${id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchWebinars();
        } catch (e) {
            alert("Ошибка удаления");
        }
    };

    if (loading) return <div className="p-8">Загрузка...</div>;

    return (
        <div className="w-full">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-2xl font-bold text-gray-800">Управление Вебинарами</h1>
                <button
                    onClick={handleCreateNew}
                    className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium"
                >
                    + Добавить вебинар
                </button>
            </div>

            <div className="flex gap-8 items-start">

                {/* List Column */}
                <div className={`flex-1 transition-all ${isEditing ? "w-1/3 hidden md:block opacity-50 pointer-events-none" : "w-full"}`}>
                    <div className="grid gap-4">
                        {webinars.map(w => (
                            <div key={w.id} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex justify-between items-center group">
                                <div>
                                    <h3 className="font-medium text-gray-900">{w.title}</h3>
                                    <div className="text-xs text-gray-500 mt-1 flex gap-2">
                                        <span className={w.is_published ? "text-green-600" : "text-gray-400"}>
                                            {w.is_published ? "Опубликован" : "Черновик"}
                                        </span>
                                        <span>•</span>
                                        <span className={w.is_upcoming ? "text-orange-500" : "text-orange-500"}>
                                            {w.is_upcoming ? "Предстоящий" : "В библиотеке"}
                                        </span>
                                    </div>
                                </div>
                                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => handleEdit(w)}
                                        className="p-2 text-orange-600 hover:bg-orange-50 rounded-lg"
                                    >
                                        ✏️
                                    </button>
                                    <button
                                        onClick={() => handleDelete(w.id)}
                                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                                    >
                                        🗑️
                                    </button>
                                </div>
                            </div>
                        ))}

                        {webinars.length === 0 && (
                            <div className="text-center py-10 text-gray-500">
                                Список пуст. Создайте первый вебинар.
                            </div>
                        )}
                    </div>
                </div>

                {/* Editor Column (Slide Over) */}
                <AnimatePresence>
                    {isEditing && (
                        <motion.div
                            initial={{ x: 50, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: 50, opacity: 0 }}
                            className="w-full md:w-2/3 bg-white border border-gray-200 rounded-xl shadow-xl p-6 sticky top-6"
                        >
                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-xl font-bold">
                                    {selectedWebinar ? "Редактирование вебинара" : "Новый вебинар"}
                                </h2>
                                <button onClick={() => setIsEditing(false)} className="text-gray-400 hover:text-black">
                                    ✕
                                </button>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Название</label>
                                    <input
                                        value={formData.title}
                                        onChange={e => setFormData({ ...formData, title: e.target.value })}
                                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 outline-none"
                                        placeholder="Например: Введение в AI агентов"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Ссылка на видео (VK/YouTube)</label>
                                        <input
                                            value={formData.video_url}
                                            onChange={e => setFormData({ ...formData, video_url: e.target.value })}
                                            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 outline-none text-sm font-mono"
                                            placeholder="https://vk.com/video_ext.php?..."
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Ссылка подключения (Zoom/Meet)</label>
                                        <input
                                            value={formData.connection_link}
                                            onChange={e => setFormData({ ...formData, connection_link: e.target.value })}
                                            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm font-mono"
                                            placeholder="https://zoom.us/j/..."
                                        />
                                    </div>
                                    <div className="col-span-2">
                                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Превью (URL картинки)</label>
                                        <input
                                            value={formData.thumbnail_url}
                                            onChange={e => setFormData({ ...formData, thumbnail_url: e.target.value })}
                                            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 outline-none text-sm font-mono"
                                            placeholder="https://..."
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Описание</label>
                                    <textarea
                                        value={formData.description}
                                        onChange={e => setFormData({ ...formData, description: e.target.value })}
                                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 outline-none h-24 resize-none"
                                        placeholder="Краткое описание урока..."
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1 text-purple-600">
                                        ✨ Транскрипция (Для AI Мозга)
                                    </label>
                                    <textarea
                                        value={formData.transcript_context}
                                        onChange={e => setFormData({ ...formData, transcript_context: e.target.value })}
                                        className="w-full px-4 py-2 border-2 border-purple-50 rounded-lg focus:border-purple-500 focus:ring-0 outline-none h-48 resize-none font-mono text-xs leading-relaxed"
                                        placeholder="Вставьте сюда полный текст вебинара. Чат-бот будет использовать этот текст, чтобы отвечать на вопросы студентов."
                                    />
                                    <p className="text-[10px] text-gray-400 mt-1">
                                        Чем точнее транскрипция, тем лучше бот будет отвечать на вопросы по этому уроку.
                                    </p>
                                </div>

                                <div className="flex gap-6 pt-4 border-t border-gray-100">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={formData.is_published}
                                            onChange={e => setFormData({ ...formData, is_published: e.target.checked })}
                                            className="w-4 h-4"
                                        />
                                        <span className="text-sm font-medium">Опубликовать</span>
                                    </label>

                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={formData.is_upcoming}
                                            onChange={e => setFormData({ ...formData, is_upcoming: e.target.checked })}
                                            className="w-4 h-4"
                                        />
                                        <span className="text-sm font-medium">Это анонс (будущий)</span>
                                    </label>
                                </div>

                                <div className="flex justify-end gap-3 pt-4">
                                    <button
                                        onClick={() => setIsEditing(false)}
                                        className="px-4 py-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
                                    >
                                        Отмена
                                    </button>
                                    <button
                                        onClick={handleSave}
                                        className="px-6 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors font-medium shadow-lg shadow-gray-200"
                                    >
                                        {selectedWebinar ? "Сохранить изменения" : "Создать вебинар"}
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
