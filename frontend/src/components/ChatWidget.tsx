"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  X,
  Send,
  Sparkles,
  Maximize2,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { getApiBase } from "../types/radar";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  nivel?: string;
  intencion?: string;
  fuentes?: string[];
  latencia_ms?: number;
  timestamp: string;
}

const QUICK_CHIPS = [
  "¿Cuáles son los temas en tendencia?",
  "¿Qué temas están saturados?",
  "¿Qué novedades salieron en HackerNews?",
  "¿Qué ganchos se usan en video corto?",
];

export function ChatWidget() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "widget-welcome",
      sender: "assistant",
      content:
        "👋 **Sonar Chatbot RAG (T0):** Cero alucinación y latencia < 20ms. Pregúntame sobre tendencias, ganchos o fases de saturación.",
      nivel: "T0",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // No mostrar widget flotante si ya estamos en la página /chat
  const isChatPage = pathname === "/chat";

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen, loading]);

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: `w-user-${Date.now()}`,
      sender: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/chat/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pregunta: text,
          show_sources: true,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const assistantMsg: ChatMessage = {
        id: `w-asst-${Date.now()}`,
        sender: "assistant",
        content: data.respuesta || "Sin respuesta.",
        nivel: data.nivel || "T0",
        intencion: data.intencion,
        fuentes: data.fuentes || [],
        latencia_ms: data.latencia_ms ?? 0,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `w-err-${Date.now()}`,
          sender: "assistant",
          content: `⚠️ Error conectando con el backend: ${err.message}`,
          nivel: "ERROR",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (isChatPage) return null;

  return (
    <>
      {/* Botón flotante en la esquina inferior derecha */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-40 bg-[#27251e] hover:bg-black text-[#faf8f5] px-4 py-2.5 rounded-full shadow-lg border border-[#d1d1cd]/50 flex items-center space-x-2.5 text-xs font-medium cursor-pointer transition-transform hover:scale-105 group"
        >
          <div className="relative">
            <MessageSquare className="w-4 h-4 text-[#016a71]" />
            <span className="w-2 h-2 rounded-full bg-[#016a71] absolute -top-1 -right-1 animate-pulse"></span>
          </div>
          <span>Chat IA</span>
          <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-full bg-[#016a71]/30 text-[#016a71] border border-[#016a71]/40 font-semibold">
            Gemini
          </span>
        </button>
      )}

      {/* Panel flotante lateral (Slide-over drawer) */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-full sm:w-[420px] h-[580px] bg-[#faf8f5] border border-[#d1d1cd] rounded-[10px] shadow-2xl flex flex-col justify-between overflow-hidden animate-in slide-in-from-bottom-5 duration-200">
          {/* Header del Widget */}
          <div className="p-3.5 bg-[#fdfbfa] border-b border-[#d1d1cd] flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-[4px] bg-[#27251e] flex items-center justify-center text-[#faf8f5]">
                <MessageSquare className="w-3.5 h-3.5 text-[#016a71]" />
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs font-medium text-[#27251e]">Sonar Chat IA</span>
                  <span className="font-mono text-[9px] px-1 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20 font-medium">
                    Gemini Flash
                  </span>
                </div>
                <span className="text-[10px] text-[#72706b] block">RAG Ground Truth // Multifuente</span>
              </div>
            </div>

            <div className="flex items-center space-x-1">
              <Link
                href="/chat"
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-[#72706b] hover:text-[#27251e] rounded hover:bg-[#d1d1cd]/30"
                title="Expandir a pantalla completa"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </Link>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-[#72706b] hover:text-[#27251e] rounded hover:bg-[#d1d1cd]/30"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Quick chips en widget */}
          <div className="px-3 py-2 bg-[#fdfbfa] border-b border-[#d1d1cd]/60 flex items-center space-x-1.5 overflow-x-auto text-[10px]">
            {QUICK_CHIPS.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(chip)}
                disabled={loading}
                className="whitespace-nowrap px-2 py-0.5 rounded-[4px] bg-[#faf8f5] hover:bg-[#016a71]/10 border border-[#d1d1cd] text-[#27251e] shrink-0 cursor-pointer disabled:opacity-50"
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Lista de Mensajes */}
          <div className="flex-1 p-3.5 space-y-3 overflow-y-auto text-xs bg-[#faf8f5]">
            {messages.map((m) => {
              const isUser = m.sender === "user";
              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${isUser ? "items-end" : "items-start"} space-y-0.5`}
                >
                  <div className="flex items-center space-x-1 text-[9px] font-mono text-[#72706b] px-1">
                    <span>{isUser ? "TÚ" : "SONAR IA"}</span>
                    {m.latencia_ms !== undefined && m.latencia_ms > 0 && (
                      <span>• {m.latencia_ms}ms</span>
                    )}
                  </div>
                  <div
                    className={`p-3 rounded-[6px] max-w-[90%] text-xs leading-relaxed select-text ${
                      isUser
                        ? "bg-[#27251e] text-[#faf8f5]"
                        : "bg-[#fdfbfa] text-[#27251e] border border-[#d1d1cd] shadow-xs"
                    }`}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    ) : (
                      <div className="space-y-2">
                        <MarkdownRenderer content={m.content} />
                        {m.fuentes && m.fuentes.length > 0 && (
                          <div className="pt-1.5 border-t border-[#d1d1cd]/50 text-[10px] font-mono text-[#72706b]">
                            <span>{m.fuentes.length} fuentes verificadas</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex items-center space-x-2 text-[#72706b] text-[11px] font-mono p-2 rounded bg-[#fdfbfa] border border-[#d1d1cd] w-fit">
                <RefreshCw className="w-3 h-3 animate-spin text-[#016a71]" />
                <span>Consultando motor T0...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-2.5 bg-[#fdfbfa] border-t border-[#d1d1cd]">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center space-x-1.5"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Preguntar sobre tendencias o ganchos..."
                disabled={loading}
                className="flex-1 bg-[#faf8f5] border border-[#d1d1cd] rounded-[4px] px-3 py-1.5 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71]"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="p-2 rounded-[4px] bg-[#27251e] hover:bg-black text-[#faf8f5] transition disabled:opacity-40 cursor-pointer"
              >
                <Send className="w-3.5 h-3.5 text-[#016a71]" />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
