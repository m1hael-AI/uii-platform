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
    const [userToDelete, setUserToDelete] = useState<User | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

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

    const handleClearData = async () => {
        if (!userToDelete) return;

        setIsDeleting(true);
        const token = Cookies.get("token");
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

        try {
            const res = await fetch(`${API_URL}/admin/users/${userToDelete.id}/data`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.ok) {
                alert(`✅ Все данные пользователя ${userToDelete.username || userToDelete.tg_first_name} успешно удалены!`);
                setUserToDelete(null);
                fetchUsers(searchTerm); // Refresh list
            } else {
                const error = await res.json();
                alert(`❌ Ошибка: ${error.detail || "Не удалось удалить данные"}`);
            }
        } catch (e) {
            console.error("Failed to clear user data", e);
            alert("❌ Ошибка сети");
        } finally {
            setIsDeleting(false);
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
                            <th className="p-4 font-semibold">Действия</th>
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
                                    <td className="p-4"><div className="h-4 bg-gray-100 rounded w-20"></div></td>
                                </tr>
                            ))
                        ) : users.length === 0 ? (
                            <tr>
                                <td colSpan={8} className="p-8 text-center text-gray-400">
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
                                    <td className="p-4">
                                        <button
                                            onClick={() => setUserToDelete(user)}
                                            className="px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors flex items-center gap-1"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                            Clear Data
                                        </button>
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

            {/* Confirmation Modal */}
            {userToDelete && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
                        <div className="p-6 border-b border-gray-100">
                            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                                Подтверждение удаления
                            </h3>
                        </div>

                        <div className="p-6 space-y-4">
                            <p className="text-gray-700">
                                Вы уверены, что хотите <strong className="text-red-600">удалить ВСЕ данные</strong> пользователя:
                            </p>
                            <div className="bg-gray-50 p-4 rounded-lg">
                                <p className="font-semibold text-gray-900">
                                    {userToDelete.username ? `@${userToDelete.username}` : userToDelete.tg_first_name}
                                </p>
                                <p className="text-sm text-gray-500">ID: {userToDelete.id}</p>
                            </div>
                            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                <p className="text-sm text-red-700 font-medium mb-2">⚠️ Будут удалены:</p>
                                <ul className="text-xs text-red-600 space-y-1 list-disc list-inside">
                                    <li>Все сообщения</li>
                                    <li>Все сессии чатов</li>
                                    <li>Вся память (user_memory)</li>
                                    <li>Все pending actions</li>
                                    <li>Все LLM audit logs</li>
                                </ul>
                                <p className="text-xs text-red-700 font-bold mt-3">
                                    ⚠️ Это действие НЕОБРАТИМО!
                                </p>
                            </div>
                        </div>

                        <div className="p-6 border-t border-gray-100 flex gap-3 justify-end">
                            <button
                                onClick={() => setUserToDelete(null)}
                                disabled={isDeleting}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={handleClearData}
                                disabled={isDeleting}
                                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                            >
                                {isDeleting ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                        Удаление...
                                    </>
                                ) : (
                                    <>
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                        Удалить все данные
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
