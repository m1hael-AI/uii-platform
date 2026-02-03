"use client";
import { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

interface User {
    id: number;
    email: string;
    role: string;
    tg_first_name: string;
    tg_last_name: string;
    created_at: string;
}

export default function UsersAdminPage() {
    const router = useRouter();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchUsers = async () => {
            const token = Cookies.get("token");
            if (!token) return;
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            try {
                const res = await fetch(`${API_URL}/admin/users`, {
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
        fetchUsers();
    }, []);

    return (
        <div className="max-w-6xl mx-auto">
            {/* Header */}
            <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => router.push("/system-control")}>
                    System Control
                </span>
                <span className="text-gray-300">/</span>
                <span>Список Пользователей</span>
            </h1>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                            <th className="p-4 font-semibold">ID</th>
                            <th className="p-4 font-semibold">User</th>
                            <th className="p-4 font-semibold">Contact</th>
                            <th className="p-4 font-semibold">Role</th>
                            <th className="p-4 font-semibold">Created</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {loading ? (
                            <tr><td colSpan={5} className="p-8 text-center text-gray-400">Loading users...</td></tr>
                        ) : users.map(user => (
                            <tr key={user.id} className="hover:bg-blue-50/50 transition-colors">
                                <td className="p-4 text-gray-400 font-mono text-xs">{user.id}</td>
                                <td className="p-4 font-medium text-gray-800">
                                    {user.tg_first_name} {user.tg_last_name}
                                </td>
                                <td className="p-4 text-gray-600">
                                    {user.email || "-"}
                                </td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${user.role === 'admin' ? 'bg-purple-100 text-purple-600' : 'bg-gray-100 text-gray-500'
                                        }`}>
                                        {user.role}
                                    </span>
                                </td>
                                <td className="p-4 text-gray-400 text-xs">
                                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : "-"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
