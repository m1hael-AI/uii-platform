"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import PhoneInput from "react-phone-input-2";
import "react-phone-input-2/lib/style.css";

interface Question {
    id: string;
    text: string;
    options?: string[];
    type: "choice" | "input" | "phone";
    placeholder?: string;
    validation?: (value: string) => boolean;
    maxLength?: number;
}

const QUESTIONS: Question[] = [
    {
        id: "country",
        text: "Из какой вы страны?",
        type: "choice",
        options: ["Россия", "СНГ", "Европа", "Северная Америка", "Израиль", "Другое"],
    },
    {
        id: "age",
        text: "Сколько вам лет?",
        type: "choice",
        options: ["до 18 лет", "18 - 25", "26 - 30", "31 - 40", "41 - 50", "51 - 60", "60 +"],
    },
    {
        id: "job",
        text: "В какой сфере сейчас работаете?",
        type: "choice",
        options: [
            "IT сфера (разработчик, тестировщик...)",
            "Числа (аналитик, бухгалтер, инженер...)",
            "Предприниматель, руководитель",
            "Гуманитарий (общение, медицина...)",
            "Преподаватель, учитель",
            "Школьник, студент",
            "Пенсионер",
            "Декрет",
        ],
    },
    {
        id: "income",
        text: "Ваш средний доход в месяц",
        type: "choice",
        options: ["0 руб.", "до 30 000 руб.", "до 60 000 руб.", "до 100 000 руб.", "более 100 000 руб."],
    },
    {
        id: "goal",
        text: "Рассматриваете ли вы платное обучение профессии AI-разработчик?",
        type: "choice",
        options: [
            "Нет. Хочу только бесплатные материалы.",
            "Да, если поможет в проекте.",
            "Да, если найду работу.",
        ],
    },
    {
        id: "phone",
        text: "Введите ваш номер телефона",
        type: "phone",
        placeholder: "+7 (999) 000-00-00",
        validation: (val) => val.length > 8, // Basic check, library handles mask
    },
    {
        id: "email",
        text: "Введите ваш Email",
        type: "input",
        placeholder: "example@mail.com",
        validation: (val) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val),
    },
    {
        id: "password",
        text: "Придумайте пароль",
        type: "input",
        placeholder: "Минимум 8 символов",
        validation: (val) => val.length >= 8 && val.length <= 128,
        maxLength: 128,
    },
];

export default function OnboardingPage() {
    const router = useRouter();
    const [step, setStep] = useState(0);
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    // Local state for current input value (restored from answers on step change)
    const [currentValue, setCurrentValue] = useState("");

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

    useEffect(() => {
        checkStatus();
    }, []);

    // Effect to restore answer when step changes (or clear if new)
    useEffect(() => {
        const q = QUESTIONS[step];
        setCurrentValue(answers[q.id] || "");
    }, [step]); // Removed 'answers' from deps to avoid loop, we only care when step changes

    // Global Enter key handler for all question types
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            const currentQ = QUESTIONS[step];
            const isValid = !!currentValue && (currentQ.validation ? currentQ.validation(currentValue) : currentValue.length > 0);

            if (e.key === 'Enter' && isValid && !submitting) {
                e.preventDefault();
                handleNext();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [submitting, step, currentValue, answers]); // Dependencies to ensure handleNext has latest state

    const checkStatus = async () => {
        const token = Cookies.get("token");
        if (!token) {
            router.push("/");
            return;
        }

        try {
            const res = await fetch(`${API_URL}/users/me`, {
                headers: { Authorization: `Bearer ${token}` },
            });

            if (res.ok) {
                const user = await res.json();
                if (user.is_onboarded) {
                    router.push("/platform");
                } else {
                    setLoading(false);
                }
            } else {
                Cookies.remove("token"); // Clear invalid token to avoid bounce
                router.push("/login");
            }
        } catch (e) {
            console.error("Auth check failed", e);
            setLoading(false);
        }
    };

    const handleSelect = (val: string) => {
        // Just update local state for UI selection
        setCurrentValue(val);
        // Also update answers immediately? Or only on 'Next'?
        // Let's update answers so we don't lose it if user clicks Back immediately
        setAnswers(prev => ({ ...prev, [QUESTIONS[step].id]: val }));
    };

    const handleNext = async () => {
        // Validate
        const q = QUESTIONS[step];
        if (q.validation && !q.validation(currentValue)) {
            alert("Пожалуйста, заполните поле корректно");
            return;
        }

        // Save current answer finally
        const newAnswers = { ...answers, [q.id]: currentValue };
        setAnswers(newAnswers);

        if (step < QUESTIONS.length - 1) {
            setStep(step + 1);
        } else {
            await finishOnboarding(newAnswers);
        }
    };

    const handleBack = () => {
        if (step > 0) {
            setStep(step - 1);
        }
    };

    const finishOnboarding = async (finalAnswers: Record<string, string>) => {
        setSubmitting(true);
        const token = Cookies.get("token");

        // Convert answers to list for quiz_answers and separate fields
        const quizList = Object.entries(finalAnswers)
            .filter(([k]) => k !== 'phone' && k !== 'email' && k !== 'password')
            .map(([_, v]) => v);

        const payload = {
            phone: finalAnswers.phone,
            email: finalAnswers.email,
            quiz_answers: quizList
        };

        try {
            const res = await fetch(`${API_URL}/users/me`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(payload),
            });

            let success = res.ok;

            // Set Password if provided
            if (success && finalAnswers.password) {
                const pwdRes = await fetch(`${API_URL}/users/me/password`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ new_password: finalAnswers.password }),
                });
                if (!pwdRes.ok) success = false;
            }

            if (success) {
                router.push("/platform");
            } else {
                alert("Ошибка сохранения данных.");
                setSubmitting(false);
            }
        } catch (e) {
            alert("Ошибка сети.");
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-950 flex items-center justify-center text-white">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
            </div>
        );
    }

    const currentQ = QUESTIONS[step];
    const progress = ((step + 1) / QUESTIONS.length) * 100;

    // Check if current value satisfies validation (if exists) or just isn't empty
    const canProceed = !!currentValue && (currentQ.validation ? currentQ.validation(currentValue) : currentValue.length > 0);

    return (
        <div className="min-h-screen bg-white text-black flex flex-col items-center justify-center p-6">
            <div className="w-full max-w-md flex flex-col min-h-[500px]">

                {/* Header */}
                <div className="mb-8 text-center shrink-0">
                    <h1 className="text-xl font-medium mb-2 tracking-wide text-[#474648]">АНКЕТА СТУДЕНТА</h1>
                    <div className="w-full h-1 bg-gray-100 rounded-full mt-4 overflow-hidden">
                        <div
                            className="h-full bg-black transition-all duration-500 ease-out"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <p className="text-xs text-gray-400 mt-2 text-right">
                        Вопрос {step + 1} из {QUESTIONS.length}
                    </p>
                </div>

                {/* Content */}
                <div className="flex-1 flex flex-col">
                    <h2 className="text-2xl font-semibold mb-8 text-center leading-snug text-[#231f20]">
                        {currentQ.text}
                    </h2>

                    <div className="flex-1">
                        {currentQ.type === "choice" && (
                            <div className="space-y-3">
                                {currentQ.options?.map((opt) => (
                                    <button
                                        key={opt}
                                        onClick={() => handleSelect(opt)}
                                        // COLORS: Orange selection
                                        className={`w-full text-left px-6 py-4 border rounded-xl transition-all duration-200 text-sm font-medium active:scale-[0.99] ${currentValue === opt
                                            ? "border-[#ff8a35] bg-orange-50/50 shadow-sm ring-1 ring-[#ff8a35]/20"
                                            : "border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-[#474648]"
                                            }`}
                                    >
                                        {opt}
                                    </button>
                                ))}
                            </div>
                        )}

                        {currentQ.type === "input" && (
                            <div className="space-y-4">
                                <input
                                    type={currentQ.id === "password" ? "password" : (currentQ.id === "email" ? "email" : "text")}
                                    value={currentValue}
                                    onChange={(e) => handleSelect(e.target.value)}
                                    // Removed inline onKeyDown as global listener handles it
                                    placeholder={currentQ.placeholder}
                                    maxLength={currentQ.maxLength}
                                    className="w-full px-6 py-4 border border-gray-200 rounded-xl focus:border-[#FF6B35] focus:ring-1 focus:ring-[#FF6B35]/20 outline-none transition-all text-lg"
                                    autoFocus
                                />
                                {currentQ.id === "password" && currentValue.length > 0 && currentValue.length < 8 && (
                                    <p className="text-xs text-red-500 mt-1 ml-2">Нужно еще {8 - currentValue.length} симв.</p>
                                )}
                            </div>
                        )}

                        {currentQ.type === "phone" && (
                            <div
                                className="space-y-4 flex justify-center"
                            >
                                <PhoneInput
                                    country={'ru'}
                                    value={currentValue}
                                    onChange={(phone) => handleSelect(phone)}
                                    masks={{ ru: '(...) ...-..-..' }}
                                    placeholder="+7 (999) 000-00-00"
                                    inputStyle={{
                                        width: '100%',
                                        height: '60px',
                                        fontSize: '18px',
                                        paddingLeft: '60px',
                                        borderRadius: '0.75rem',
                                        borderColor: '#e5e7eb',
                                    }}
                                    buttonStyle={{
                                        borderRadius: '0.75rem 0 0 0.75rem',
                                        borderColor: '#e5e7eb',
                                        backgroundColor: 'white'
                                    }}
                                    dropdownStyle={{
                                        fontFamily: 'inherit'
                                    }}
                                />
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer Navigation */}
                <div className="mt-8 pt-4 border-t border-gray-50 flex items-center justify-between gap-4 shrink-0">
                    <button
                        onClick={handleBack}
                        disabled={step === 0}
                        className={`flex items-center gap-2 text-sm font-medium transition-colors px-4 py-2 rounded-lg 
                        ${step === 0 ? "opacity-0 pointer-events-none" : "text-gray-400 hover:text-black hover:bg-gray-50"}`}
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                        Назад
                    </button>

                    {/* Main Action - Blue */}
                    <button
                        onClick={handleNext}
                        disabled={!canProceed || submitting}
                        className="bg-[#FF6B35] text-white px-8 py-3 rounded-xl font-medium shadow-md shadow-orange-200 hover:bg-[#1a5bb0] hover:shadow-lg transition-all disabled:opacity-50 disabled:shadow-none min-w-[140px]"
                    >
                        {submitting ? "Сохранение..." : "Далее"}
                    </button>
                </div>

            </div>
        </div>
    );
}
