"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";

interface Webinar {
    id: number;
    title: string;
    description: string;
    scheduled_at: string;
    is_upcoming: boolean;
    is_published: boolean;
    speaker_name?: string;
}

export default function WebinarsAdminPage() {
    const router = useRouter();
    const [webinars, setWebinars] = useState<Webinar[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchWebinars();
    }, []);

    const fetchWebinars = async () => {
        const token = Cookies.get("token");
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
        try {
            const res = await fetch(`${API_URL}/webinars?filter_type=all`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                setWebinars(await res.json());
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto">
            {/* Header with Breadcrumbs */}
            <h1 className="text-2xl font-bold mb-6 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => router.push("/system-control")}>
                        System Control
                    </span>
                    <span className="text-gray-300">/</span>
                    <span>Вебинары</span>
                </div>

                <button
                    onClick={() => router.push("/system-control/webinars/new")}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors"
                >
                    + Создать вебинар
                </button>
            </h1>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-gray-50 text-gray-500 text-xs uppercase font-semibold">
                        <tr>
                            <th className="p-4">ID</th>
                            <th className="p-4">Название</th>
                            <th className="p-4">Спикер</th>
                            <th className="p-4">Дата (UTC)</th>
                            <th className="p-4">Статус</th>
                            <th className="p-4">Действия</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {loading ? (
                            <tr><td colSpan={6} className="p-8 text-center text-gray-400">Loading...</td></tr>
                        ) : webinars.map(w => (
                            <tr key={w.id} className="hover:bg-blue-50/30 transition-colors">
                                <td className="p-4 text-gray-400 font-mono text-xs">{w.id}</td>
                                <td className="p-4 font-medium text-gray-900">{w.title}</td>
                                <td className="p-4 text-gray-600">{w.speaker_name || "-"}</td>
                                <td className="p-4 text-gray-600 text-sm">
                                    {w.scheduled_at ? new Date(w.scheduled_at).toLocaleString() : "Без даты"}
                                </td>
                                <td className="p-4">
                                    <div className="flex gap-2">
                                        <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${w.is_published ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                                            }`}>
                                            {w.is_published ? "PUBLISHED" : "DRAFT"}
                                        </span>
                                        {w.is_upcoming && (
                                            <span className="px-2 py-1 rounded text-xs font-bold uppercase bg-purple-100 text-purple-700">
                                                UPCOMING
                                            </span>
                                        )}
                                    </div>
                                </td>
                                <td className="p-4">
                                    <button
                                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                        onClick={() => router.push(`/system-control/webinars/${w.id}`)}
                                    >
                                        Edit
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {!loading && webinars.length === 0 && (
                    <div className="p-10 text-center text-gray-400">Нет вебинаров. Создайте первый!</div>
                )}
            </div>
        </div>
    );
}
