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
    type?: string;
    program?: { date: string, title: string, link: string }[];
    landing_bullets?: string[];
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

                    let dateStr = new Date(data.scheduled_at || data.created_at).toLocaleDateString("ru-RU", {
                        day: 'numeric', month: 'long', year: 'numeric'
                    });

                    // Logic for Date Range (Sprints)
                    if (data.type === 'sprint' && data.program && data.program.length > 1) {
                        try {
                            const sortedDates = data.program.map((p: any) => new Date(p.date)).sort((a: any, b: any) => a - b);
                            const start = sortedDates[0];
                            const end = sortedDates[sortedDates.length - 1];
                            const startStr = start.toLocaleDateString("ru-RU", { day: 'numeric', month: 'long' });
                            const endStr = end.toLocaleDateString("ru-RU", { day: 'numeric', month: 'long' });
                            dateStr = `${startStr} — ${endStr}`;
                        } catch (e) {
                            // Fallback to standard date
                        }
                    }

                    setWebinar({
                        ...data,
                        description: cleanDesc,
                        category: "AI Education",
                        speaker: data.speaker_name || "Дмитрий Романов",
                        date: dateStr,
                        is_upcoming: true,
                        scheduled_at: data.scheduled_at,
                        connection_link: data.connection_link,
                        type: data.type,
                        program: data.program,
                        landing_bullets: data.landing_bullets
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
        <div className="flex flex-col w-full h-[calc(100vh-6rem)] md:h-[calc(100vh-7rem)] bg-white lg:bg-transparent overflow-hidden">
            {/* Breadcrumbs */}
            <div className="hidden lg:flex mb-3 items-center gap-2 text-sm text-gray-500 px-1 w-full min-w-0 shrink-0">
                <Link href="/platform/schedule" className="hover:text-[#206ecf] transition-colors shrink-0">Расписание</Link>
                <span className="shrink-0">/</span>
                <span className="text-gray-900 font-medium truncate min-w-0">{webinar.title}</span>
            </div>

            {/* Main Card (Full Width) */}
            <div className="flex-1 bg-white rounded-2xl shadow-sm border border-gray-100 w-full overflow-y-auto custom-scrollbar">

                {/* Hero / Cover Image */}
                {webinar.thumbnail_url ? (
                    <div className="w-full h-48 md:h-64 lg:h-96 relative shrink-0">
                        <img
                            src={webinar.thumbnail_url}
                            alt={webinar.title}
                            className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end">
                            <div className="p-6 lg:p-10 w-full max-w-7xl mx-auto">
                                <div className="flex items-center gap-3 mb-2">
                                    <span className="bg-[#FF6B35] text-white text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wide">Предстоящий</span>
                                </div>
                                <h1 className="text-2xl lg:text-4xl font-bold text-white mb-2 break-words leading-tight shadow-sm">{webinar.title}</h1>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* If no image, show header in content area */
                    null
                )}

                <div className="p-6 lg:p-10 w-full max-w-7xl mx-auto">
                    {!webinar.thumbnail_url && (
                        <div className="mb-8 border-b border-gray-100 pb-8">
                            <div className="flex items-center gap-3 mb-4">
                                <span className="bg-blue-50 text-[#206ecf] text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wide">Предстоящий</span>
                            </div>
                            <h1 className="text-2xl lg:text-4xl font-bold text-[#474648] mb-4 break-words leading-tight">{webinar.title}</h1>
                        </div>
                    )}

                    <div className="flex flex-col lg:flex-row gap-8 lg:gap-16 items-start">
                        {/* Left: Description */}
                        <div className="flex-1 min-w-0">
                            <h2 className="text-lg font-bold text-gray-900 mb-4">О вебинаре</h2>
                            <div className="prose prose-gray max-w-none text-gray-600 leading-relaxed whitespace-pre-wrap text-base lg:text-lg">
                                {webinar.description}
                            </div>
                        </div>

                        {/* Right: Sidebar / Meta Info */}
                        <div className="w-full lg:w-96 shrink-0 bg-gray-50 rounded-2xl p-6 border border-gray-100 sticky top-6">
                            <div className="flex flex-col gap-6">
                                <div className="flex flex-col gap-1">
                                    <span className="text-xs font-bold text-gray-400 uppercase">Дата и время</span>
                                    <span className="text-lg font-medium text-gray-900">{webinar.date}</span>
                                    {webinar.scheduled_at && !webinar.program && <span className="text-sm text-gray-500">{new Date(webinar.scheduled_at).toLocaleTimeString("ru-RU", { hour: '2-digit', minute: '2-digit' })} МСК</span>}
                                </div>

                                <div className="flex flex-col gap-1">
                                    <span className="text-xs font-bold text-gray-400 uppercase">Спикер</span>
                                    <span className="text-lg font-medium text-gray-900">{webinar.speaker}</span>
                                </div>

                                <div className="pt-6 border-t border-gray-200 flex flex-col items-center">
                                    <WebinarAction webinar={webinar} />
                                    <p className="text-xs text-center text-gray-400 mt-3">
                                        {webinar.type === 'sprint' ? "Одна запись на весь спринт" : "Напоминание придет за 1 час до начала"}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Content Section: Program OR Bullets */}
                    <div className="mt-12">
                        {/* Priority: Program (Sprints) > Bullets (Webinars) */}
                        {webinar.program && webinar.program.length > 0 ? (
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 mb-6">Программа</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {webinar.program.map((item, idx) => (
                                        <div key={idx} className="bg-gray-50 rounded-xl p-5 border border-gray-100 hover:border-orange-200 transition-colors">
                                            <div className="text-xs text-[#FF6B35] font-bold uppercase mb-2">
                                                Урок {idx + 1}
                                            </div>
                                            <div className="font-medium text-gray-900 mb-1">{item.title}</div>
                                            <div className="text-sm text-gray-500">
                                                {new Date(item.date).toLocaleDateString("ru-RU", { day: 'numeric', month: 'long' })} в {new Date(item.date).toLocaleTimeString("ru-RU", { hour: '2-digit', minute: '2-digit' })}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : webinar.landing_bullets && webinar.landing_bullets.length > 0 ? (
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 mb-6">Что будет на вебинаре</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                                    {webinar.landing_bullets.map((bullet, idx) => (
                                        <div key={idx} className="flex items-start gap-3 bg-gray-50 p-4 rounded-xl border border-gray-100">
                                            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-sm mt-0.5">✓</span>
                                            <span className="text-gray-700">{bullet}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : null}
                    </div>
                </div>
            </div>
        </div>
    );
}
