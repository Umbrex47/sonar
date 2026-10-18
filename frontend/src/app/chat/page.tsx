"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  MessageSquare,
  Send,
  Sparkles,
  RefreshCw,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  Zap,
  Terminal,
  Clock,
  History,
  X,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  HelpCircle,
} from "lucide-react";
import { getApiBase } from "../../types/radar";
import { MarkdownRenderer } from "../../components/MarkdownRenderer";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  nivel?: string;
  modelo?: string;
  intencion?: string;
  fuentes?: string[];
  confianza?: number;
  latencia_ms?: number;
  desde_cache?: boolean;
  timestamp: string;
}

interface ChatLogItem {
  id: number;
  query_hash: string;
  pregunta: string;
  intencion: string;
  nivel: string;
  latencia_ms: number;
  confianza: number;
  creado_at: string;
}

const SUGGESTIONS = [
  "¿Cuáles son los temas en tendencia y qué ganchos están usando?",
  "¿Cómo implementar agentes de IA en mi empresa con seguridad?",
  "¿Qué temas de IA están saturados esta semana?",
  "Compara modelos de razonamiento (o3 vs DeepSeek) para reducir costos",
  "¿Qué novedades emergentes salieron en HackerNews?",
  "¿Cuál es la evolución histórica de DeepSeek?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      content: `👋 **¡Bienvenido al Asesor de Inteligencia de Sonar!**

Soy el motor conversacional de inteligencia editorial y estratégica en IA para líderes y creadores de contenido en Latinoamérica.

🤖 **Arquitectura Híbrida Gemini Flash + RAG Ground Truth:**
- **Fundamentación Empírica:** Mis análisis se basan en el reporte semanal activo de Sonar, las tarjetas de narrativa del grafo y datos auditados en tiempo real.
- **Trazabilidad 100%:** Cita directa de fuentes públicas (GitHub, YouTube, Google News, HackerNews, Jina Markdown).
- **Cero Humo:** Enfoque prioritario en retorno de inversión (ROI), mitigación de costos de inferencia y viabilidad operativa en LatAm.

Puedes hacer clic en cualquiera de las preguntas sugeridas abajo o escribir tu propia consulta:`,
      nivel: "T1",
      modelo: "gemini-3.6-flash",
      intencion: "bienvenida",
      confianza: 0.98,
      latencia_ms: 0,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedSourcesId, setExpandedSourcesId] = useState<string | null>(null);
  const [showLogsDrawer, setShowLogsDrawer] = useState(false);
  const [chatLogs, setChatLogs] = useState<ChatLogItem[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const fetchChatLogs = async () => {
    setLoadingLogs(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/chat/logs`);
      if (res.ok) {
        const data = await res.json();
        setChatLogs(data.logs || []);
      }
    } catch (err) {
      console.error("Error al obtener logs de chat:", err);
    } finally {
      setLoadingLogs(false);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputValue).trim();
    if (!text || loading) return;

    const userMsgId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
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

      if (!res.ok) {
        throw new Error(`Error en servidor (HTTP ${res.status})`);
      }

      const data = await res.json();
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        content: data.respuesta || "No se obtuvo respuesta estructurada.",
        nivel: data.nivel || "T0",
        modelo: data.modelo,
        intencion: data.intencion || "consulta",
        fuentes: data.fuentes || [],
        confianza: data.confianza ?? 1.0,
        latencia_ms: data.latencia_ms ?? 0,
        desde_cache: data.desde_cache ?? false,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        content: `⚠️ **Error de conexión con el backend local:** ${err.message || err}. Asegúrese de que el servidor web esté corriendo en el puerto 8080.`,
        nivel: "ERROR",
        confianza: 0,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const copyText = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClearChat = () => {
    setMessages([messages[0]]);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header Ejecutivo */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#d1d1cd]/70">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
            <span className="font-mono text-[10px] text-[#016a71] uppercase tracking-wider font-medium">
              RAG INTELIGENTE // GEMINI FLASH + SQL GROUND TRUTH
            </span>
          </div>
          <h1 className="text-2xl text-[#27251e] font-normal tracking-tight">
            Chatbot de Inteligencia Editorial y Estratégica
          </h1>
          <p className="text-xs text-[#72706b] font-normal">
            Asesoría ejecutiva potenciada por Gemini Flash fundamentada en la base de datos verificada y el grafo de señales de Sonar.
          </p>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <button
            onClick={() => {
              setShowLogsDrawer(true);
              fetchChatLogs();
            }}
            className="px-2.5 py-1.5 rounded-[4px] border border-[#d1d1cd] bg-[#fdfbfa] hover:bg-[#faf8f5] text-xs font-normal text-[#72706b] hover:text-[#27251e] flex items-center space-x-1.5 transition cursor-pointer shadow-xs"
            title="Ver auditoría de consultas procesadas"
          >
            <History className="w-3.5 h-3.5 text-[#016a71]" />
            <span>Auditoría de Logs</span>
          </button>
          <button
            onClick={handleClearChat}
            className="px-2.5 py-1.5 rounded-[4px] border border-[#d1d1cd] bg-[#fdfbfa] hover:bg-[#faf8f5] text-xs font-normal text-[#72706b] hover:text-[#27251e] transition cursor-pointer shadow-xs"
            title="Reiniciar conversación"
          >
            Limpiar
          </button>
        </div>
      </section>

      {/* Badges de Garantía Técnica Origin Financial */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        <div className="p-2.5 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-[#016a71] shrink-0" />
          <div className="min-w-0">
            <span className="font-mono text-[9px] text-[#72706b] uppercase block">PREVENCIÓN</span>
            <span className="text-xs font-medium text-[#27251e] truncate block">Cero Alucinación</span>
          </div>
        </div>

        <div className="p-2.5 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] flex items-center space-x-2">
          <Zap className="w-4 h-4 text-[#016a71] shrink-0" />
          <div className="min-w-0">
            <span className="font-mono text-[9px] text-[#72706b] uppercase block">VELOCIDAD</span>
            <span className="text-xs font-medium text-[#27251e] truncate block">Latencia &lt; 20ms</span>
          </div>
        </div>

        <div className="p-2.5 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-[#016a71] shrink-0" />
          <div className="min-w-0">
            <span className="font-mono text-[9px] text-[#72706b] uppercase block">MOTOR SQL</span>
            <span className="text-xs font-medium text-[#27251e] truncate block">T0 Determinista</span>
          </div>
        </div>

        <div className="p-2.5 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] flex items-center space-x-2">
          <Clock className="w-4 h-4 text-[#016a71] shrink-0" />
          <div className="min-w-0">
            <span className="font-mono text-[9px] text-[#72706b] uppercase block">HISTORIAL</span>
            <span className="text-xs font-medium text-[#27251e] truncate block">Memoria 90 Días</span>
          </div>
        </div>
      </div>

      {/* Suggested Prompt Chips */}
      <div data-tour="chat-suggestions" className="space-y-1.5">
        <span className="font-mono text-[10px] text-[#72706b] uppercase tracking-wider block">
          CONSULTAS RÁPIDAS SUGERIDAS:
        </span>
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(s)}
              disabled={loading}
              className="text-left px-2.5 py-1 rounded-[4px] bg-[#fdfbfa] hover:bg-[#016a71]/10 border border-[#d1d1cd] hover:border-[#016a71]/40 text-xs text-[#27251e] transition cursor-pointer disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Message Thread Container */}
      <div data-tour="chat-audit-box" className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] shadow-[0_1px_2px_rgba(0,0,0,0.03)] min-h-[460px] flex flex-col justify-between overflow-hidden">
        {/* Messages List */}
        <div className="p-4 sm:p-6 space-y-5 overflow-y-auto max-h-[580px]">
          {messages.map((m) => {
            const isUser = m.sender === "user";
            return (
              <div
                key={m.id}
                className={`flex flex-col ${isUser ? "items-end" : "items-start"} space-y-1 animate-in fade-in duration-150`}
              >
                {/* Message Header Badge */}
                <div className="flex items-center space-x-2 px-1 text-[10px] font-mono text-[#72706b]">
                  <span>{isUser ? "TÚ" : "RADAR RAG"}</span>
                  {m.nivel && (
                    <span className="px-1.5 py-0.2 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20">
                      {m.nivel}
                    </span>
                  )}
                  {m.modelo && (
                    <span className="font-mono text-[9px] text-[#72706b]">
                      • {m.modelo}
                    </span>
                  )}
                  {m.latencia_ms !== undefined && m.latencia_ms > 0 && (
                    <span>• {m.latencia_ms}ms</span>
                  )}
                  {m.desde_cache && (
                    <span className="text-[#016a71]">⚡ caché</span>
                  )}
                  <span>{m.timestamp}</span>
                </div>

                {/* Message Bubble */}
                <div
                  className={`rounded-[8px] p-4 max-w-[85%] text-xs sm:text-[13px] leading-relaxed select-text ${
                    isUser
                      ? "bg-[#27251e] text-[#faf8f5] shadow-xs"
                      : "bg-[#faf8f5] text-[#27251e] border border-[#d1d1cd] shadow-xs w-full"
                  }`}
                >
                  {isUser ? (
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  ) : (
                    <div className="space-y-3">
                      <MarkdownRenderer content={m.content} />

                      {/* Assistant Actions Bar */}
                      <div className="pt-2 border-t border-[#d1d1cd]/60 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => copyText(m.content, m.id)}
                            className="font-mono text-[10px] text-[#72706b] hover:text-[#27251e] flex items-center space-x-1 cursor-pointer"
                          >
                            {copiedId === m.id ? (
                              <>
                                <Check className="w-3 h-3 text-[#016a71]" />
                                <span className="text-[#016a71]">Copiado</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copiar</span>
                              </>
                            )}
                          </button>

                          {m.confianza !== undefined && (
                            <span className="font-mono text-[10px] text-[#72706b]">
                              Confianza: {(m.confianza * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>

                        {/* Fuentes Verificadas Dropdown */}
                        {m.fuentes && m.fuentes.length > 0 && (
                          <button
                            onClick={() =>
                              setExpandedSourcesId(
                                expandedSourcesId === m.id ? null : m.id
                              )
                            }
                            className="font-mono text-[10px] text-[#016a71] hover:underline flex items-center space-x-1 cursor-pointer"
                          >
                            <span>{m.fuentes.length} fuentes verificadas</span>
                            {expandedSourcesId === m.id ? (
                              <ChevronUp className="w-3 h-3" />
                            ) : (
                              <ChevronDown className="w-3 h-3" />
                            )}
                          </button>
                        )}
                      </div>

                      {/* Fuentes expandidas */}
                      {expandedSourcesId === m.id && m.fuentes && m.fuentes.length > 0 && (
                        <div className="p-2.5 rounded-[4px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-1.5 animate-in fade-in duration-150">
                          <span className="font-mono text-[9px] text-[#72706b] uppercase block">
                            EVIDENCIAS Y FUENTES PRIMARIAS VERIFICADAS:
                          </span>
                          <div className="space-y-1 max-h-36 overflow-y-auto text-[11px] font-mono">
                            {m.fuentes.map((f, fIdx) => (
                              <a
                                key={fIdx}
                                href={f}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[#016a71] hover:underline flex items-center space-x-1 truncate"
                              >
                                <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                                <span className="truncate">{f}</span>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex items-center space-x-2 text-[#72706b] font-mono text-xs p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] w-fit animate-pulse">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#016a71]" />
              <span>Ejecutando resolución SQL determinista en T0...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div data-tour="chat-t0-input" className="p-3 sm:p-4 bg-[#faf8f5] border-t border-[#d1d1cd]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center space-x-2"
          >
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Haz una pregunta sobre tendencias, ganchos o saturación de IA..."
              disabled={loading}
              className="flex-1 bg-[#fdfbfa] border border-[#d1d1cd] rounded-[6px] px-3.5 py-2.5 text-xs sm:text-[13px] text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71] focus:ring-1 focus:ring-[#016a71]/20 transition disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !inputValue.trim()}
              className="px-4 py-2.5 rounded-[6px] bg-[#27251e] hover:bg-black text-[#faf8f5] text-xs font-medium transition disabled:opacity-40 cursor-pointer flex items-center space-x-1.5 shrink-0 shadow-xs"
            >
              <span>Consultar</span>
              <Send className="w-3.5 h-3.5 text-[#016a71]" />
            </button>
          </form>
          <div className="flex items-center justify-between pt-2 px-1 text-[10px] text-[#92918b] font-mono">
            <span>Presiona Enter para enviar consulta</span>
            <span>TypeSafe Jev // Zero Latam Hallucination Policy</span>
          </div>
        </div>
      </div>

      {/* Drawer de Auditoría de Logs (chat_logs) */}
      {showLogsDrawer && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-[#faf8f5] border-l border-[#d1d1cd] h-full flex flex-col justify-between shadow-xl">
            <div className="p-4 border-b border-[#d1d1cd] flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="flex items-center space-x-1.5">
                  <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
                  <span className="font-mono text-[10px] text-[#016a71] uppercase">AUDITORÍA SQL</span>
                </div>
                <h3 className="text-sm font-medium text-[#27251e]">Historial de Consultas RAG</h3>
              </div>
              <button
                onClick={() => setShowLogsDrawer(false)}
                className="p-1 rounded text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/30"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 flex-1 overflow-y-auto space-y-2.5">
              {loadingLogs ? (
                <div className="text-center py-8 text-xs font-mono text-[#72706b]">
                  Cargando logs de SQLite...
                </div>
              ) : chatLogs.length === 0 ? (
                <div className="text-center py-8 text-xs text-[#72706b]">
                  No hay registros de consultas en chat_logs aún.
                </div>
              ) : (
                chatLogs.map((log) => (
                  <div
                    key={log.id}
                    onClick={() => {
                      handleSendMessage(log.pregunta);
                      setShowLogsDrawer(false);
                    }}
                    className="p-3 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] hover:border-[#016a71] transition cursor-pointer space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between text-[10px] font-mono text-[#72706b]">
                      <span className="px-1.5 py-0.2 rounded-[2px] bg-[#016a71]/10 text-[#016a71]">
                        {log.nivel} // {log.intencion}
                      </span>
                      <span>{log.latencia_ms}ms</span>
                    </div>
                    <p className="font-medium text-[#27251e]">{log.pregunta}</p>
                    <span className="text-[9px] font-mono text-[#92918b] block">
                      {log.creado_at}
                    </span>
                  </div>
                ))
              )}
            </div>

            <div className="p-3 border-t border-[#d1d1cd] bg-[#fdfbfa] flex justify-between items-center text-[10px] font-mono text-[#72706b]">
              <span>Tabla SQLite: chat_logs</span>
              <button
                onClick={fetchChatLogs}
                className="hover:text-[#27251e] underline cursor-pointer"
              >
                Recargar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
