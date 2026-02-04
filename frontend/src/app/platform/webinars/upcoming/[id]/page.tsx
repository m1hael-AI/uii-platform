"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import ReactMarkdown from "react-markdown";

import WebinarAction from "@/components/WebinarAction";

interface Webinar {
    id: number;
    title: string;
    description: string;
    video_url?: string;
    thumbnail_url?: string;
    date?: string;
    scheduled_at?: string;
    connection_link?: string;
    is_upcoming: boolean;
    category?: string;
    speaker?: string;
    duration?: string;
}

export default function UpcomingWebinarPage() {
    const params = useParams();
    const router = useRouter();
    const id = params.id as string;

    const [webinar, setWebinar] = useState<Webinar | null>(null);
    const [loading, setLoading] = useState(true);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    // 1. Fetch Upcoming Webinar Data
    useEffect(() => {
        const fetchWebinar = async () => {
            const token = Cookies.get("token");
            if (!token) {
                router.push("/login");
                return;
            }

            try {
                const res = await fetch(`${API_URL}/webinars/upcoming/${id}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const data = await res.json();
                    let cleanDesc = data.description || "";
                    cleanDesc = cleanDesc.replace(/STOP$/i, "").trim();

                    setWebinar({
                        ...data,
                        description: cleanDesc,
                        category: "AI Education",
                        speaker: data.speaker_name || "Дмитрий Романов",
                        duration: data.duration_minutes ? `${data.duration_minutes} мин` : "1:00:00",
                        date: new Date(data.scheduled_at || data.created_at).toLocaleDateString("ru-RU", {
                            day: 'numeric', month: 'long', year: 'numeric'
                        }),
                        is_upcoming: true,
                        scheduled_at: data.scheduled_at,
                        connection_link: data.connection_link
                    });
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };

        fetchWebinar();
    }, [id, router]);

    if (loading) return <div className="p-8 text-center text-gray-500">Загрузка информации...</div>;
    if (!webinar) return <div className="p-8 text-center text-gray-500">Вебинар не найден</div>;

    return (
        <div className="flex flex-col w-full min-h-[calc(100vh-6rem)] bg-white lg:bg-transparent overflow-y-auto">
            {/* Breadcrumbs */}
            <div className="hidden lg:flex mb-3 items-center gap-2 text-sm text-gray-500 px-1 w-full min-w-0 shrink-0 max-w-4xl mx-auto">
                <Link href="/platform/schedule" className="hover:text-[#206ecf] transition-colors shrink-0">Расписание</Link>
                <span className="shrink-0">/</span>
                <span className="text-gray-900 font-medium truncate min-w-0">{webinar.title}</span>
            </div>

            {/* Content Card */}
            <div className="flex-1 bg-white rounded-2xl shadow-sm border border-gray-100 w-full max-w-4xl mx-auto overflow-hidden">
                <div className="p-6 lg:p-10">
                    <div className="flex items-start justify-between gap-6 mb-8 w-full flex-col md:flex-row">
                        <div className="w-full min-w-0 flex-1">
                            <div className="flex items-center gap-3 mb-4">
                                <span className="bg-blue-50 text-[#206ecf] text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wide">Предстоящий</span>
                                <span className="text-gray-400 text-sm">{webinar.date}</span>
                            </div>
                            <h1 className="text-2xl lg:text-4xl font-bold text-[#474648] mb-4 break-words leading-tight">{webinar.title}</h1>

                            <div className="flex flex-wrap gap-4 mb-2">
                                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
                                    <span className="text-gray-400">🎤</span>
                                    <span className="font-medium">{webinar.speaker}</span>
                                </div>
                                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
                                    <span className="text-gray-400">⏱</span>
                                    <span className="font-medium">{webinar.duration}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="mb-10 p-6 bg-gray-50 rounded-xl border border-gray-100 flex flex-col md:flex-row items-center justify-between gap-6">
                        <div className="text-sm text-gray-500 max-w-md">
                            <p>Запишитесь, чтобы получить напоминание за час до начала и ссылку на подключение.</p>
                        </div>
                        <div className="shrink-0 w-full md:w-auto flex justify-center">
                            <WebinarAction webinar={webinar} />
                        </div>
                    </div>

                    <div className="prose prose-gray max-w-none text-gray-600 leading-relaxed whitespace-pre-wrap text-base lg:text-lg">
                        {webinar.description}
                    </div>
                </div>
            </div>
        </div>
    );
}
