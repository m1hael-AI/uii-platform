"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import Cookies from "js-cookie";

interface Webinar {
  id: number;
  title: string;
  description?: string;
  is_upcoming: boolean;
  date?: string; // Formatted
  scheduled_at?: string; // ISO String
  connection_link?: string;
  speaker?: string;
  duration?: string;
}

const ITEMS_PER_PAGE = 10;

import WebinarAction from "@/components/WebinarAction";

export default function SchedulePage() {
  const [upcomingData, setUpcomingData] = useState<Webinar[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const observerTarget = useRef<HTMLDivElement>(null);

  const fetchWebinars = useCallback(async (pageNum: number, isInitial = false) => {
    if (isInitial) {
      setLoading(true);
    } else {
      setIsLoadingMore(true);
    }

    const token = Cookies.get("token");
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    try {
      const offset = (pageNum - 1) * ITEMS_PER_PAGE;
      const res = await fetch(`${API_URL}/webinars?filter_type=upcoming&limit=${ITEMS_PER_PAGE}&offset=${offset}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        const enhancedData = data.map((w: any) => ({
          ...w,
          speaker: w.speaker_name || "М. Овсянников",
          duration: w.duration_minutes ? `${w.duration_minutes} мин` : "1:30:00",
          date: new Date(w.scheduled_at || w.created_at).toLocaleDateString("ru-RU", { day: 'numeric', month: 'long', year: 'numeric' })
        }));

        if (isInitial) {
          setUpcomingData(enhancedData);
        } else {
          setUpcomingData(prev => [...prev, ...enhancedData]);
        }

        setHasMore(data.length === ITEMS_PER_PAGE);
      }
    } catch (e) {
      console.error("Schedule fetch error", e);
    } finally {
      setLoading(false);
      setIsLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    fetchWebinars(1, true);
  }, [fetchWebinars]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore && !loading) {
          setPage(prev => prev + 1);
        }
      },
      { threshold: 0.1 }
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => {
      if (observerTarget.current) {
        observer.unobserve(observerTarget.current);
      }
    };
  }, [hasMore, isLoadingMore, loading]);

  useEffect(() => {
    if (page > 1) {
      fetchWebinars(page);
    }
  }, [page, fetchWebinars]);

  if (loading) return <div className="p-8 text-center text-gray-500">Загрузка расписания...</div>;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-light text-[#231f20] mb-2">Расписание вебинаров</h1>
        <p className="text-[#7e95b1]">Ближайшие мероприятия университета</p>
      </div>

      <div className="space-y-4">
        {upcomingData.map((webinar) => (
          <div
            key={webinar.id}
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row items-start md:items-center gap-4 md:gap-6"
          >
            {/* Date Block */}
            <div className="flex flex-col items-center justify-center w-24 shrink-0 text-center border-r border-gray-100 pr-6 gap-1 md:block hidden">
              <div className="text-3xl font-light text-black">
                {webinar.date?.split(' ')[0] || "15"}
              </div>
              <div className="text-xs font-bold text-[#206ecf] uppercase tracking-wider">
                {webinar.date?.split(' ')[1] || "ЯНВ"}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {webinar.date?.split(' ')[2] || "2026"}
              </div>
            </div>

            {/* Mobile Date */}
            <div className="md:hidden flex items-center gap-2 text-sm font-medium text-gray-500 w-full mb-2">
              <span className="text-black text-base">{webinar.date}</span>
            </div>

            {/* Content */}
            <div className="flex-1 w-full">
              <Link href={`/platform/schedule/${webinar.id}`} className="group block">
                <h3 className="text-lg font-medium text-[#231f20] group-hover:text-[#206ecf] transition-colors mb-2">
                  {webinar.title}
                </h3>
              </Link>
              <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                {webinar.description}
              </p>

              <div className="flex flex-wrap items-center gap-4 text-xs text-[#7e95b1]">
                <div className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  {webinar.speaker}
                </div>
                <div className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {webinar.duration}
                </div>
              </div>
            </div>

            {/* Action Button */}
            <div className="shrink-0 w-full md:w-auto mt-2 md:mt-0 md:ml-6">
              <WebinarAction webinar={webinar} />
            </div>
          </div>
        ))}

        {/* Loading More Indicator */}
        {isLoadingMore && (
          <div className="text-center py-8">
            <div className="inline-block w-8 h-8 border-4 border-gray-200 border-t-[#206ecf] rounded-full animate-spin"></div>
            <p className="text-gray-500 text-sm mt-3">Загрузка...</p>
          </div>
        )}

        {/* Intersection Observer Target */}
        <div ref={observerTarget} className="h-4"></div>

        {upcomingData.length === 0 && (
          <div className="text-center py-20 text-gray-400">
            Пока нет запланированных вебинаров
          </div>
        )}
      </div>

      <div className="mt-8 p-4 bg-orange-50/50 rounded-xl border border-orange-100 flex items-start gap-3">
        <div className="text-[#206ecf] mt-0.5">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm text-[#314b6b]">
          Напоминание о вебинаре придет в Telegram-бот университета за 1 час до начала. Проверьте, что у вас включены уведомления.
        </p>
      </div>
    </div>
  );
}
