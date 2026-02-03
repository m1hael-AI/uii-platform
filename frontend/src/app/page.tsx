"use client";

import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <Image
          src="/logo.jpg"
          alt="UII Logo"
          width={80}
          height={80}
          className="mx-auto rounded-xl mb-12"
        />
        <h1 className="text-4xl md:text-5xl font-light text-black mb-16 tracking-tight leading-tight">
          Платформа Университета
          <br />
          <span className="font-medium text-[#FF6B35]">искусственного интеллекта</span>
        </h1>

        <a
          href={`https://t.me/${process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME || 'YOUR_BOT_USERNAME'}?start=utm_source_website`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-3 bg-[#0088cc] text-white px-8 py-4 rounded-xl font-medium hover:bg-[#006699] transition-all shadow-lg hover:shadow-xl"
        >
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.18-.357.295-.6.295-.002 0-.003 0-.005 0l.213-3.054 5.56-5.022c.24-.213-.054-.334-.373-.121l-6.869 4.326-2.96-.924c-.64-.203-.658-.64.135-.954l11.566-4.458c.538-.196 1.006.128.832.941z" />
          </svg>
          Начать в Telegram
        </a>

        <p className="mt-6 text-sm text-gray-500">
          Нажмите, чтобы открыть бота и получить доступ к платформе
        </p>
      </div>
    </div>
  );
}
