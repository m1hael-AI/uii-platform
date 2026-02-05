"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import Cookies from "js-cookie";

const AGENTS_DATA: Record<string, { name: string; role: string; status: string; color: string; bg: string }> = {
  mentor: { name: "AI Ментор", role: "Куратор", status: "Онлайн", color: "text-orange-600", bg: "bg-orange-50" },
  python: { name: "Python Эксперт", role: "Tutor", status: "Онлайн", color: "text-yellow-600", bg: "bg-yellow-50" },
  analyst: { name: "Аналитик Данных", role: "Expert", status: "Онлайн", color: "text-green-600", bg: "bg-green-50" },
  hr: { name: "HR Консультант", role: "Assistant", status: "Онлайн", color: "text-purple-600", bg: "bg-purple-50" },
};

export default function AgentChatPage() {
  const params = useParams();
  const router = useRouter();
  const agentId = params.agentId as string;
  const agent = AGENTS_DATA[agentId] || { name: "AI Агент", role: "Bot", status: "Онлайн" };

  const [messages, setMessages] = useState<{ role: 'user' | 'assistant', text: string }[]>([]);
  const [streamingMessage, setStreamingMessage] = useState("");
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Fetch History on Mount
  useEffect(() => {
    const fetchHistory = async () => {
      const token = Cookies.get("token");
      if (!token) return;

      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
      try {
        const res = await fetch(`${API_URL}/chat/history?agent_id=${agentId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (res.ok) {
          const history = await res.json();
          // The backend returns an object with a 'messages' array: { messages: [], last_read_at: ... }
          if (history.messages && history.messages.length > 0) {
            setMessages(history.messages.map((h: any) => ({
              role: h.role,
              text: h.content
            })));
          } else {
            // Fallback if no messages yet (safety)
            setMessages([]);
          }

          // Mark as read
          await fetch(`${API_URL}/chat/read?agent_id=${agentId}`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` }
          });
          // 🔔 BROADCAST STATUS UPDATE
          window.dispatchEvent(new Event("chatStatusUpdate"));
        }
      } catch (e) {
        console.error("Failed to load history", e);
      }
    };

    fetchHistory();
  }, [agentId, agent.name]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping, streamingMessage]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const token = Cookies.get("token");
    if (!token) {
      router.push("/login");
      return;
    }

    const userText = input;
    const newMessages = [...messages, { role: 'user' as const, text: userText }];

    setMessages(newMessages);
    setInput("");
    setIsTyping(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
      const res = await fetch(`${API_URL}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          messages: newMessages.map(m => ({ role: m.role, content: m.text })),
          agent_id: agentId
        })
      });

      if (!res.ok) throw new Error("API Error");

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No reader");

      let accumulatedText = "";
      setStreamingMessage("");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        accumulatedText += chunk;
        setStreamingMessage(accumulatedText);
      }

      // DONE
      setMessages(prev => [...prev, { role: 'assistant', text: accumulatedText }]);
      setStreamingMessage("");

    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { role: 'assistant', text: "Извините, произошла ошибка подключения к серверу." }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Header */}
      <div className="h-16 px-4 md:px-6 border-b border-gray-100 flex items-center gap-3 shrink-0 bg-white/80 backdrop-blur md:static">
        {/* Mobile Back Button */}
        <button
          onClick={() => router.push("/platform/chat")}
          className="lg:hidden p-2 -ml-2 text-gray-400 hover:text-gray-900 transition-colors"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold shrink-0 ${agent.bg || 'bg-blue-50'} ${agent.color || 'text-blue-600'}`}>
          {agent.name[0]}
        </div>

        <div className="flex-1">
          <h2 className="font-bold text-gray-900 leading-tight">{agent.name}</h2>
          <div className="text-[10px] md:text-xs text-[#206ecf]">
            {isTyping ? "Печатает..." : agent.status}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 md:p-6 overflow-y-auto bg-gray-50/50 space-y-4 md:space-y-6">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs mr-2 shrink-0 shadow-sm ${agent.bg || 'bg-blue-50'} ${agent.color || 'text-blue-600'}`}>
                {agent.name[0]}
              </div>
            )}
            <div className={`max-w-[85%] md:max-w-[70%] rounded-2xl px-4 py-3 md:px-5 md:py-4 text-base shadow-sm break-words overflow-hidden ${msg.role === 'user'
              ? 'bg-[#206ecf] text-white rounded-tr-none'
              : 'bg-white border border-gray-100 text-gray-800 rounded-tl-none'
              }`}>
              <div className={`prose prose-sm md:prose-base max-w-none ${msg.role === 'user' ? 'text-white' : 'text-gray-800'}`}>
                <ReactMarkdown>{msg.text}</ReactMarkdown>
              </div>
            </div>
          </div>
        ))}

        {isTyping && !streamingMessage && (
          <div className="flex justify-start items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs mr-2 shrink-0 shadow-sm ${agent.bg || 'bg-blue-50'} ${agent.color || 'text-blue-600'}`}>
              {agent.name[0]}
            </div>
            <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none px-5 py-4 shadow-sm">
              <div className="flex gap-1.5 items-center h-6">
                <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce"></div>
              </div>
            </div>
          </div>
        )}

        {streamingMessage && (
          <div className="flex justify-start">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs mr-2 shrink-0 shadow-sm ${agent.bg || 'bg-blue-50'} ${agent.color || 'text-blue-600'}`}>
              {agent.name[0]}
            </div>
            <div className="max-w-[85%] md:max-w-[70%] rounded-2xl px-4 py-3 md:px-5 md:py-4 text-base shadow-sm bg-white border border-gray-100 text-gray-800 rounded-tl-none">
              <div className="prose prose-sm md:prose-base max-w-none text-gray-800">
                <ReactMarkdown>{streamingMessage}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input (Full Width) */}
      <div className="p-4 bg-white border-t border-gray-100">
        <div className="w-full relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isTyping && handleSend()}
            placeholder={isTyping ? "AI отвечает..." : "Напишите сообщение..."}
            disabled={isTyping}
            className={`w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#206ecf]/20 focus:border-[#206ecf] transition-all text-black ${isTyping ? "cursor-not-allowed opacity-70" : ""
              }`}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className={`absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg transition-colors ${!input.trim() || isTyping
              ? "text-gray-300 cursor-not-allowed"
              : "text-[#206ecf] hover:bg-blue-50"
              }`}
          >
            {isTyping ? (
              <div className="w-5 h-5 border-2 border-gray-300 border-t-[#206ecf] rounded-full animate-spin"></div>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
