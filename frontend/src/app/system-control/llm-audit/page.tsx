"use client";

import { useEffect, useState } from "react";
import Cookies from "js-cookie";

interface LLMAuditLog {
    id: number;
    user_id: number;
    agent_slug: string;
    model: string;
    input_tokens: number;
    cached_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cost_usd: number;
    duration_ms: number;
    request_json: string;
    response_json: string;
    status: string;
    error_message?: string;
    created_at: string;
}

export default function LLMAuditPage() {
    const [logs, setLogs] = useState<LLMAuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [selectedLog, setSelectedLog] = useState<LLMAuditLog | null>(null);

    // Filters
    const [statusFilter, setStatusFilter] = useState<string>("");
    const [agentFilter, setAgentFilter] = useState<string>("");

    const fetchLogs = async (p: number) => {
        setLoading(true);
        const token = Cookies.get("token");
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

        try {
            const queryParams = new URLSearchParams({
                page: p.toString(),
                limit: "20",
            });

            if (statusFilter) queryParams.append("status", statusFilter);
            if (agentFilter) queryParams.append("agent_slug", agentFilter);

            const res = await fetch(`${API_URL}/admin/llm-audit?${queryParams}`, {
                headers: { Authorization: `Bearer ${token}` },
            });

            if (res.ok) {
                const data = await res.json();
                setLogs(data.items);
                setTotalItems(data.total);
                setTotalPages(Math.ceil(data.total / 20));
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs(page);
    }, [page, statusFilter, agentFilter]); // Re-fetch on filter change

    const openLog = (log: LLMAuditLog) => setSelectedLog(log);
    const closeLog = () => setSelectedLog(null);

    return (
        <div className="space-y-6">
            {/* Header with Breadcrumbs */}
            <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <span className="text-gray-400 cursor-pointer hover:text-black" onClick={() => window.location.href = "/system-control"}>
                    System Control
                </span>
                <span className="text-gray-300">/</span>
                <span>LLM Audit</span>
                <span className="ml-auto text-sm font-normal text-gray-500">Total: {totalItems}</span>
            </h1>

            {/* Filters */}
            <div className="flex gap-4 p-4 bg-white rounded-lg shadow-sm border border-gray-100">
                <select
                    value={statusFilter}
                    onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                    className="border p-2 rounded text-sm text-gray-700 bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                    <option value="">All Statuses</option>
                    <option value="success">Success</option>
                    <option value="error">Error</option>
                </select>

                <input
                    type="text"
                    placeholder="Filter by Agent Slug..."
                    value={agentFilter}
                    onChange={(e) => { setAgentFilter(e.target.value); }}
                    onBlur={() => setPage(1)} // Trigger fetch on blur to avoid too many requests
                    className="border p-2 rounded text-sm text-gray-700 bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none"
                />
                <button onClick={() => fetchLogs(1)} className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                    Refresh
                </button>
            </div>

            {/* Table */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-gray-500">
                        <thead className="text-xs text-gray-700 uppercase bg-gray-50 border-b">
                            <tr>
                                <th className="px-6 py-3">ID</th>
                                <th className="px-6 py-3">Agent</th>
                                <th className="px-6 py-3">Model</th>
                                <th className="px-6 py-3">Tokens (In/Out)</th>
                                <th className="px-6 py-3">Cost ($)</th>
                                <th className="px-6 py-3">Duration</th>
                                <th className="px-6 py-3">Status</th>
                                <th className="px-6 py-3">Time</th>
                                <th className="px-6 py-3">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan={9} className="px-6 py-8 text-center">Loading...</td>
                                </tr>
                            ) : logs.length === 0 ? (
                                <tr>
                                    <td colSpan={9} className="px-6 py-8 text-center">No logs found</td>
                                </tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.id} className="bg-white border-b hover:bg-gray-50">
                                        <td className="px-6 py-4 font-medium text-gray-900">{log.id}</td>
                                        <td className="px-6 py-4">{log.agent_slug}</td>
                                        <td className="px-6 py-4">
                                            <span className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600">{log.model}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col">
                                                <span className="text-xs text-gray-400">In: {log.input_tokens}</span>
                                                {log.cached_tokens > 0 && (
                                                    <span className="text-xs text-blue-600">Cached: {log.cached_tokens}</span>
                                                )}
                                                <span className="text-xs text-green-600">Out: {log.output_tokens}</span>
                                                <span className="font-medium">Total: {log.total_tokens}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 font-mono text-gray-900">${log.cost_usd.toFixed(6)}</td>
                                        <td className="px-6 py-4">{log.duration_ms}ms</td>
                                        <td className="px-6 py-4">
                                            {log.status === "success" ? (
                                                <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">Success</span>
                                            ) : (
                                                <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs">Error</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-gray-400 text-xs">
                                            {new Date(log.created_at).toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4">
                                            <button
                                                onClick={() => openLog(log)}
                                                className="font-medium text-blue-600 hover:underline"
                                            >
                                                View JSON
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between p-4 border-t">
                    <button
                        disabled={page <= 1}
                        onClick={() => setPage(page - 1)}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                        Previous
                    </button>
                    <span className="text-sm text-gray-600">
                        Page {page} of {totalPages}
                    </span>
                    <button
                        disabled={page >= totalPages}
                        onClick={() => setPage(page + 1)}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                        Next
                    </button>
                </div>
            </div>

            {/* JSON Viewer Modal */}
            {selectedLog && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
                        <div className="flex justify-between items-center p-6 border-b">
                            <h3 className="text-lg font-bold text-gray-900">
                                Log Details #{selectedLog.id}
                            </h3>
                            <button
                                onClick={closeLog}
                                className="text-gray-400 hover:text-gray-600 p-1"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto flex-1 space-y-6">

                            {selectedLog.error_message && (
                                <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 font-mono text-sm break-all">
                                    <strong>Error:</strong> {selectedLog.error_message}
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <h4 className="font-medium text-gray-700 mb-2">Request JSON</h4>
                                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-xs h-96">
                                        {(() => {
                                            try {
                                                return JSON.stringify(JSON.parse(selectedLog.request_json), null, 2);
                                            } catch {
                                                return selectedLog.request_json;
                                            }
                                        })()}
                                    </pre>
                                </div>
                                <div>
                                    <h4 className="font-medium text-gray-700 mb-2">Response JSON</h4>
                                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-xs h-96">
                                        {(() => {
                                            try {
                                                return JSON.stringify(JSON.parse(selectedLog.response_json), null, 2);
                                            } catch {
                                                return selectedLog.response_json;
                                            }
                                        })()}
                                    </pre>
                                </div>
                            </div>
                        </div>

                        <div className="p-6 border-t bg-gray-50 rounded-b-xl flex justify-end">
                            <button
                                onClick={closeLog}
                                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
