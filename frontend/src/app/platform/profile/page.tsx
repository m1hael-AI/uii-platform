"use client";

import { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

interface UserData {
  id: number;
  email: string | null;
  tg_first_name: string | null;
  tg_last_name: string | null;
  tg_username: string | null;
  tg_photo_url?: string | null;
  phone: string | null;
  role: string | null;
  has_password: boolean;
}

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Avatar State
  const [avatarLoading, setAvatarLoading] = useState(false);

  // Password State
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordStatus, setPasswordStatus] = useState("");

  const fetchUser = async () => {
    const token = Cookies.get("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
      const res = await fetch(`${API_URL}/users/me`, {
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setUser(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];

    if (file.size > 5 * 1024 * 1024) {
      alert("Файл слишком большой (макс 5MB)");
      return;
    }

    setAvatarLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = Cookies.get("token");
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
      const res = await fetch(`${API_URL}/users/me/avatar`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setUser(prev => prev ? { ...prev, tg_photo_url: data.avatar_url } : null);
      } else {
        alert("Ошибка загрузки");
      }
    } catch (err) {
      console.error(err);
      alert("Ошибка сети");
    } finally {
      setAvatarLoading(false);
    }
  };

  const handlePasswordUpdate = async () => {
    if (!newPassword || !confirmPassword) {
      setPasswordStatus("Заполните все поля");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordStatus("Пароли не совпадают");
      return;
    }
    if (newPassword.length < 6) {
      setPasswordStatus("Пароль слишком короткий (минимум 6 символов)");
      return;
    }

    setPasswordStatus("Установка...");

    const token = Cookies.get("token");
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    const payload: any = { new_password: newPassword };
    if (user?.has_password) {
      if (!oldPassword) {
        setPasswordStatus("Введите старый пароль");
        return;
      }
      payload.old_password = oldPassword;
    }

    try {
      const res = await fetch(`${API_URL}/users/me/password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setPasswordStatus("Пароль успешно обновлен!");
        setOldPassword("");
        setNewPassword("");
        setConfirmPassword("");
        fetchUser();
        setTimeout(() => setPasswordStatus(""), 3000);
      } else {
        const err = await res.json();
        setPasswordStatus(err.detail || "Ошибка при установке.");
      }
    } catch (e) {
      setPasswordStatus("Ошибка сети.");
    }
  };

  if (isLoading) {
    return <div className="p-6 text-gray-400">Загрузка профиля...</div>;
  }

  if (!user) {
    return <div className="p-6">Ошибка загрузки. Попробуйте обновить страницу.</div>;
  }

  return (
    <div className="p-6">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-medium text-black mb-6">Личный кабинет</h1>

        {/* Profile Card */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-4">

              {/* Avatar Component */}
              <div className="relative group w-24 h-24 flex-shrink-0">
                <div className="w-full h-full rounded-full overflow-hidden border border-gray-100 bg-gray-50 shadow-sm relative">

                  {/* 1. Image Layer */}
                  {user.tg_photo_url ? (
                    <img
                      src={user.tg_photo_url}
                      alt="Avatar"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-[#FF6B35] flex items-center justify-center text-white text-3xl font-medium uppercase">
                      {user.tg_first_name ? user.tg_first_name[0] : "U"}
                    </div>
                  )}

                  {/* 2. Hover Overlay Layer (Darken + Icon) */}
                  {!avatarLoading && (
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                      <svg className="w-8 h-8 text-white drop-shadow-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </div>
                  )}

                  {/* 3. Input Layer (Invisible & Clickable everywhere) */}
                  {!avatarLoading && (
                    <input
                      type="file"
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                      title="Изменить фото"
                      accept="image/png, image/jpeg, image/jpg, image/webp"
                      onChange={handleAvatarUpload}
                    />
                  )}

                  {/* 4. Loading State */}
                  {avatarLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/30 z-30">
                      <div className="w-6 h-6 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h2 className="text-xl font-bold text-black mt-2">
                  {[user.tg_first_name, user.tg_last_name].filter(Boolean).join(" ") || "Пользователь"}
                </h2>
                <div className="text-sm text-gray-500 space-y-1 mt-1">
                  <p>{user.email || "Email не указан"}</p>
                  <p className="flex items-center gap-1">
                    <span className="text-[#7e95b1]">Telegram:</span>
                    <span className="font-medium text-gray-700">
                      {user.tg_username ? `@${user.tg_username}` : "Не использует"}
                    </span>
                  </p>
                </div>
              </div>
            </div>
          </div>


        </div>

        {/* Security Section */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h3 className="text-lg font-medium text-black mb-4">Безопасность</h3>
          <p className="text-sm text-gray-500 mb-6">
            {user?.has_password
              ? "Для смены пароля введите текущий пароль."
              : "Установите пароль, чтобы входить на сайт по Email (альтернатива Telegram)."}
          </p>

          <form onSubmit={(e) => { e.preventDefault(); handlePasswordUpdate(); }} className="space-y-4 max-w-md">

            {/* Old Password */}
            {user?.has_password && (
              <div>
                <label className="block text-sm font-medium text-black mb-1">Старый пароль</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  autoComplete="current-password"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm outline-none focus:border-[#FF6B35] text-black"
                />
              </div>
            )}

            {/* New Password */}
            <div>
              <label className="block text-sm font-medium text-black mb-1">Новый пароль</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm outline-none focus:border-[#FF6B35] text-black"
                placeholder="Минимум 6 символов"
              />
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-black mb-1">Повторите новый пароль</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onPaste={(e) => e.preventDefault()}
                autoComplete="new-password"
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm outline-none focus:border-[#FF6B35] text-black"
                placeholder="Повторите ввод"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={!newPassword || !confirmPassword || (!!user?.has_password && !oldPassword)}
                className="px-6 py-2.5 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors font-medium text-sm disabled:opacity-50 w-full md:w-auto"
              >
                Сохранить пароль
              </button>
            </div>

          </form>

          {passwordStatus && (
            <p className={`text-sm mt-4 font-medium ${passwordStatus.includes("успешно") ? "text-green-600" : "text-red-500"}`}>
              {passwordStatus}
            </p>
          )}
        </div>

        {/* Logout Section */}
        <div className="flex justify-start">
          <button
            onClick={() => {
              Cookies.remove("token");
              router.push("/login");
            }}
            className="px-6 py-3 border border-red-200 text-red-500 rounded-xl hover:bg-red-50 transition-colors bg-white font-medium shadow-sm hover:shadow"
          >
            Выйти из аккаунта
          </button>
        </div>
      </div>
    </div>
  );
}
