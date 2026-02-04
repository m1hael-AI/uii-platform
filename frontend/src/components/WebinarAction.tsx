"use client";

import { useState, useEffect } from "react";
import Cookies from "js-cookie";

interface Webinar {
    id: number;
    title: string;
    is_upcoming: boolean;
    scheduled_at?: string;
    connection_link?: string;
}

export default function WebinarAction({ webinar }: { webinar: Webinar }) {
    const [isRegistered, setIsRegistered] = useState(false);
    const [isHovered, setIsHovered] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // Check if live (15 mins before or during presumed 1.5h duration)
    const isLive = (() => {
        if (!webinar.scheduled_at || !webinar.is_upcoming) return false;
        const now = new Date();
        const start = new Date(webinar.scheduled_at);
        // If backend returns string without timezone, assume UTC? Or provided format?
        // Javascript Date(iso_string) works well usually.
        const diffMins = (start.getTime() - now.getTime()) / (1000 * 60);
        // Active if: Starts in <= 15 mins OR started <= 120 mins ago
        return diffMins <= 15 && diffMins > -120;
    })();

    useEffect(() => {
        const checkStatus = async () => {
            const token = Cookies.get("token");
            if (!token) return;
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
            try {
                const res = await fetch(`${API_URL}/webinars/${webinar.id}/signup`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    setIsRegistered(data.is_signed_up);
                }
            } catch (e) {
                console.error("Signup status check failed", e);
            } finally {
                setIsLoading(false);
            }
        };
        checkStatus();
    }, [webinar.id]);

    const toggle = async () => {
        setIsLoading(true);
        const token = Cookies.get("token");
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

        try {
            if (isRegistered) {
                // Cancel logic
                const res = await fetch(`${API_URL}/webinars/${webinar.id}/signup`, {
                    method: "DELETE",
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (res.ok) setIsRegistered(false);
            } else {
                // Signup logic
                const res = await fetch(`${API_URL}/webinars/${webinar.id}/signup`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (res.ok) setIsRegistered(true);
            }
        } catch (e) {
            console.error("Toggle signup failed", e);
            alert("Ошибка при обновлении записи");
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) {
        return <div className="h-10 w-full md:w-40 rounded-lg bg-gray-100 animate-pulse"></div>;
    }

    // --- HIDE BUTTON IF NOT UPCOMING (Library recordings don't need signup) ---
    if (!webinar.is_upcoming) {
        return null;
    }

    // --- SHOW CONNECT BUTTON IF LIVE AND REGISTERED ---
    if (isRegistered && isLive && webinar.connection_link) {
        return (
            <a
                href={webinar.connection_link}
                target="_blank"
                rel="noopener noreferrer"
                className="h-10 w-full md:w-40 rounded-lg text-sm font-bold transition-all duration-200 flex items-center justify-center gap-2 bg-red-600 text-white hover:bg-red-700 shadow-lg shadow-red-200 animate-pulse"
            >
                <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
                </span>
                Подключиться
            </a>
        );
    }

    if (isRegistered) {
        return (
            <button
                onClick={toggle}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
                className={`h-10 w-full md:w-40 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2
          ${isHovered
                        ? "bg-red-50 text-red-600 border border-red-100"
                        : "bg-green-50 text-green-700 border border-green-100"
                    }`}
            >
                {isHovered ? (
                    <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Отменить
                    </>
                ) : (
                    <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Вы записаны
                    </>
                )}
            </button>
        );
    }

    return (
        <button
            onClick={toggle}
            className={`h-10 w-full md:w-40 rounded-lg text-sm font-medium transition-all duration-200 bg-[#ff8a35] text-white hover:bg-[#e67a2e] shadow-sm hover:shadow-md flex items-center justify-center ${isLive ? 'ring-2 ring-red-400 ring-offset-1' : ''}`}
        >
            Записаться{isLive ? " (Live)" : ""}
        </button>
    );
}
