"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import Cookies from "js-cookie";

interface Webinar {
  id: number;
  title: string;
  is_upcoming: boolean;
  video_url: string;
  thumbnail_url?: string;
  description?: string;
  // Fallback fields handled by frontend
  category?: string;
  speaker?: string;
  date?: string;
  time?: string;
}

export default function PlatformPage() {
  const router = useRouter();
  const [recentWebinars, setRecentWebinars] = useState<Webinar[]>([]);
  const [upcomingData, setUpcomingData] = useState<Webinar[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");

  useEffect(() => {
    const fetchWebinars = async () => {
      const token = Cookies.get("token");
      if (!token) {
        // Auth handled by layout mostly, but safe to keep
        router.push("/login");
        return;
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

      try {
        // Fetch All webinars
        const res = await fetch(`${API_URL}/webinars?filter_type=all`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (res.ok) {
          const data = await res.json();

          // Enhanced data processing
          const allWebinars = data.map((w: any) => {
            const d = new Date(w.scheduled_at || w.created_at);
            return {
              ...w,
              category: "AI Education",
              speaker: w.speaker_name || "М. Овсянников",
              date: d.toLocaleDateString("ru-RU", { day: 'numeric', month: 'long' }),
              time: d.toLocaleTimeString("ru-RU", { hour: '2-digit', minute: '2-digit' })
            };
          });

          // Filter Logic
          const pastWebinars = allWebinars.filter((w: any) => !w.is_upcoming);
          const futureWebinars = allWebinars.filter((w: any) => w.is_upcoming);

          // Show last 3 archive items
          setRecentWebinars(pastWebinars.slice(0, 3));

          // Show upcoming items (up to 4)
          setUpcomingData(futureWebinars.slice(0, 4));

        } else {
          if (res.status === 401) {
            Cookies.remove("token");
            router.push("/login");
            return;
          }
          const txt = await res.text();
          setFetchError(`Status: ${res.status}.`);
        }
      } catch (e: any) {
        console.error("Dashboard fetch error", e);
        setFetchError("Ошибка соединения");
      } finally {
        setLoading(false);
      }
    };

    fetchWebinars();
  }, []);

  // Helper from Webinars page
  const getCardIframe = (iframeHtml?: string) => {
    if (!iframeHtml) return null;

    // 1. If it's already an iframe tag
    if (iframeHtml.includes("<iframe")) {
      if (!iframeHtml.includes('loading="lazy"')) {
        return iframeHtml.replace("<iframe", '<iframe loading="lazy"');
      }
      return iframeHtml;
    }

    // 2. Smart Transformation
    let src = iframeHtml;
    // VK Video Logic
    const vkMatch = iframeHtml.match(/video(-?\d+)_(\d+)/);
    if (vkMatch) {
      src = `https://vk.com/video_ext.php?oid=${vkMatch[1]}&id=${vkMatch[2]}&hd=2`;
    }
    // YouTube Logic
    else if (iframeHtml.includes("youtube.com/watch?v=")) {
      src = iframeHtml.replace("watch?v=", "embed/");
    } else if (iframeHtml.includes("youtu.be/")) {
      src = iframeHtml.replace("youtu.be/", "youtube.com/embed/");
    }

    return `<iframe src="${src}" width="100%" height="100%" frameborder="0" allow="autoplay; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>`;
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-400">Загрузка панели...</div>;
  }

  return (
    <div className="p-2 md:p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-light text-[#474648] mb-2 leading-tight">
          Университет
          <br />
          <span className="font-medium text-[#206ecf]">Искусственного Интеллекта</span>
        </h1>
        <p className="text-[#7e95b1] mb-12 max-w-xl">
          Добро пожаловать в вашу персональную панель обучения. Здесь собраны все актуальные материалы и ваше расписание.
        </p>

        {/* --- Recent Webinars (Archive) --- */}
        <section className="mb-14">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-medium text-[#474648]">Последние обновления</h2>
            <Link href="/platform/webinars" className="text-sm font-medium text-[#206ecf] hover:text-[#ff8a35] transition-colors flex items-center gap-1">
              Все вебинары
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </Link>
          </div>

          {fetchError ? (
            <div className="p-4 bg-red-50 text-red-500 rounded-lg border border-red-200">
              Ошибка загрузки: {fetchError}
            </div>
          ) : recentWebinars.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {recentWebinars.map((webinar, idx) => {
                return (
                  <Link
                    key={webinar.id}
                    href={`/platform/webinars/${webinar.id}`}
                    className="group block bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-lg hover:border-blue-100 transition-all duration-300"
                  >
                    {/* Thumbnail / Iframe Preview */}
                    <div className="aspect-video bg-black relative">
                      {webinar.thumbnail_url && webinar.thumbnail_url.length > 10 ? (
                        <img
                          src={webinar.thumbnail_url}
                          alt={webinar.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                      ) : webinar.video_url ? (
                        <div
                          className="w-full h-full pointer-events-none [&>iframe]:!w-full [&>iframe]:!h-full"
                          dangerouslySetInnerHTML={{ __html: getCardIframe(webinar.video_url) || "" }}
                        />
                      ) : (
                        // Fallback
                        <div className="w-full h-full bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
                          <svg className="w-12 h-12 text-[#206ecf] opacity-30" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                        </div>
                      )}

                      {/* Overlay (Just darken on hover, no extra button) */}
                      <div className="absolute inset-0 bg-transparent z-10 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                        {/* Orange button removed to avoid double-play-button effect with existing video UI */}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="p-5 flex items-start gap-4">
                      <span className="text-2xl font-bold text-[#e0e7ff] group-hover:text-[#206ecf] transition-colors">
                        {(idx + 1).toString().padStart(2, '0')}
                      </span>
                      <div>
                        <h3 className="text-sm font-medium text-[#474648] group-hover:text-[#206ecf] transition-colors mb-1 line-clamp-2">
                          {webinar.title}
                        </h3>
                        <p className="text-xs text-[#7e95b1] line-clamp-1">{webinar.category}</p>
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          ) : (
            <div className="p-8 bg-gray-50 rounded-2xl border border-dashed border-gray-200 text-center text-gray-400">
              В библиотеке пока нет записей.
            </div>
          )}
        </section>

        {/* --- Upcoming Webinars --- */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-medium text-[#474648]">Ближайшие вебинары</h2>
            <Link href="/platform/schedule" className="text-sm font-medium text-[#206ecf] hover:text-[#ff8a35] transition-colors flex items-center gap-1">
              Расписание
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {upcomingData.length > 0 ? upcomingData.map((webinar) => (
              <Link
                key={webinar.id}
                href={`/platform/schedule/${webinar.id}`}
                className="flex items-center justify-between p-5 bg-white border border-gray-100 rounded-2xl hover:border-blue-100 hover:shadow-sm transition-all group"
              >
                <div className="flex items-center gap-5">
                  <div className="w-14 h-14 bg-blue-50 rounded-xl flex flex-col items-center justify-center text-[#206ecf]">
                    <span className="font-bold text-lg leading-none">{webinar.date?.split(' ')[0] || "15"}</span>
                    <span className="text-[10px] uppercase font-bold tracking-wider mt-0.5">
                      {webinar.date?.split(' ')[1]?.slice(0, 3) || "YAN"}
                    </span>
                  </div>
                  <div>
                    <h3 className="text-base font-medium text-[#474648] mb-1">{webinar.title}</h3>
                    <div className="flex items-center gap-3 text-xs text-[#7e95b1]">
                      <span className="flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {webinar.time || "19:00"}
                      </span>
                      <span className="flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        {webinar.speaker}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-2 text-gray-300 group-hover:text-[#ff8a35] group-hover:bg-orange-50 rounded-lg transition-all">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </Link>
            )) : (
              <div className="col-span-2 py-8 text-center text-gray-400 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
                На ближайшее время вебинары не запланированы
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
