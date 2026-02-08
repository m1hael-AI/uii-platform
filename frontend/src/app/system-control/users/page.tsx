"use client";
import { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

interface User {
    id: number;
    tg_id?: number;
    username?: string;
    tg_first_name?: string;
    tg_last_name?: string;
    role: string;
    created_at: string;
    is_onboarded: boolean;
}

export default function UsersAdminPage() {
    const router = useRouter();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            fetchUsers(searchTerm);
        }, 500);
        return () => clearTimeout(timer);
    }, [searchTerm]);

    const fetchUsers = async (query: string) => {
        setLoading(true);
        const token = Cookies.get("token");
        if (!token) return;
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
        try {
            const url = new URL(`${API_URL}/admin/users`);
            if (query) url.searchParams.append("q", query);

            const res = await fetch(url.toString(), {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setUsers(data);
            }
        } catch (e) {
            console.error("Failed to fetch users", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <h1 className="text-2xl font-bold flex items-center gap-2">
                    <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => router.push("/system-control")}>
                        System Control
                    </span>
                    <span className="text-gray-300">/</span>
                    <span>Пользователи</span>
                </h1>

                {/* Search */}
                <div className="relative w-full md:w-64">
                    <input
                        type="text"
                        placeholder="Поиск по username..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-blue-500 transition-colors"
                    />
                    <svg className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                            <th className="p-4 font-semibold">ID</th>
                            <th className="p-4 font-semibold">TG ID</th>
                            <th className="p-4 font-semibold">Username</th>
                            <th className="p-4 font-semibold">Name</th>
                            <th className="p-4 font-semibold">Роль</th>
                            <th className="p-4 font-semibold">Onboarded</th>
                            <th className="p-4 font-semibold">Дата регистрации</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50 text-sm">
                        {loading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <tr key={i} className="animate-pulse">
                                    <td className="p-4"><div className="h-4 bg-gray-100 rounded w-8"></div></td>
                                    <td className="p-4"><div className="h-4 bg-gray-100 rounded w-24"></div></td>
                                    <td className="p-4"><div className="h-4 bg-gray-100 rounded w-32"></div></td>
                                    <td className="p-4"><div className="h-4 bg-gray-100 rounded w-16"></div></td>
                                    <td className="p-4"><div className="h-4 bg-gray-100 rounded w-12"></div></td>
                                    <td className="p-4"><div className="h-4 bg-gray-100 rounded w-20"></div></td>
                                </tr>
                            ))
                        ) : users.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="p-8 text-center text-gray-400">
                                    Пользователи не найдены
                                </td>
                            </tr>
                        ) : (
                            users.map(user => (
                                <tr key={user.id} className="hover:bg-blue-50/50 transition-colors">
                                    <td className="p-4 text-gray-400 font-mono text-xs">{user.id}</td>
                                    <td className="p-4 text-gray-800 font-mono text-sm">{user.tg_id || "-"}</td>
                                    <td className="p-4 font-medium text-gray-800">
                                        {user.username ? (
                                            <span className="text-blue-600">@{user.username}</span>
                                        ) : (
                                            <span className="text-gray-400">-</span>
                                        )}
                                    </td>
                                    <td className="p-4 text-gray-600">
                                        {user.tg_first_name || user.tg_last_name ? (
                                            <span>
                                                {user.tg_first_name} {user.tg_last_name}
                                            </span>
                                        ) : "-"}
                                    </td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${user.role === 'admin' ? 'bg-purple-100 text-purple-600' : 'bg-gray-100 text-gray-500'
                                            }`}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="p-4">
                                        {user.is_onboarded ? (
                                            <span className="text-green-500 text-xs font-bold">YES</span>
                                        ) : (
                                            <span className="text-gray-300 text-xs">NO</span>
                                        )}
                                    </td>
                                    <td className="p-4 text-gray-400 text-xs">
                                        {user.created_at ? new Date(user.created_at).toLocaleDateString() : "-"}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <div className="text-center text-xs text-gray-400">
                Показаны последние 50 пользователей
            </div>
        </div>
    );
}
