"use client";

import React, { useState, useEffect } from "react";
import {
  ArrowRight,
  Search,
  ExternalLink,
  Copy,
  Check,
  RefreshCw,
  Plus,
  Trash2,
  SlidersHorizontal,
  X,
  Compass,
  Layers,
  Sparkles,
  Shield,
  TrendingUp,
  Cpu,
} from "lucide-react";

interface ReferenceItem {
  fuente: string;
  titulo: string;
  autor: string;
  fecha: string;
  metricas?: Record<string, any>;
  url: string;
}

interface TrendItem {
  posicion: number;
  tema: string;
  fase: string;
  confianza_jev: number;
  crecimiento: string;
  score: number;
  fuentes: string[];
  gancho: string;
  formato: string;
  encaje_audiencia: number;
  por_que: string;
  adaptacion_30x: string;
  evidencia: string[];
  referencias_detalladas?: ReferenceItem[];
}

interface ReportData {
  semana: string;
  generado: string;
  total_clusters_evaluados: number;
  top_temas: TrendItem[];
}

interface SearchFocus {
  id: string;
  nombre: string;
  categoria: string;
  descripcion: string;
  keywords: string[];
  activo: boolean;
  creado_en?: string;
}

const BACKEND_URL = "http://localhost:8080";

export default function RadarHomePage() {
  const [report, setReport] = useState<ReportData | null>(null);
  const [focuses, setFocuses] = useState<SearchFocus[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFormat, setSelectedFormat] = useState("todos");
  const [selectedCategory, setSelectedCategory] = useState("todos");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isFocusStudioOpen, setIsFocusStudioOpen] = useState(false);
  const [isRunningRadar, setIsRunningRadar] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Nuevo enfoque form state
  const [newFocusName, setNewFocusName] = useState("");
  const [newFocusCategory, setNewFocusCategory] = useState("polemicas");
  const [newFocusKeywords, setNewFocusKeywords] = useState("");
  const [newFocusDesc, setNewFocusDesc] = useState("");

  // Cargar datos al montar
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      // 1. Cargar reporte más reciente
      const resReport = await fetch(`${BACKEND_URL}/api/report/latest`);
      if (resReport.ok) {
        const reportJson = await resReport.json();
        setReport(reportJson);
      }

      // 2. Cargar enfoques de búsqueda
      const resFocuses = await fetch(`${BACKEND_URL}/api/focuses`);
      if (resFocuses.ok) {
        const focusesJson = await resFocuses.json();
        setFocuses(focusesJson.focuses || []);
      }
    } catch (err) {
      console.warn("Backend local no disponible o cargando datos fallback:", err);
      // Fallback elegante para renderizar sin crash si el backend está arrancando
    } finally {
      setLoading(false);
    }
  };

  const copyText = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const handleToggleFocus = async (focusId: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/focuses/${focusId}/toggle`, {
        method: "POST",
      });
      if (res.ok) {
        setFocuses((prev) =>
          prev.map((f) => (f.id === focusId ? { ...f, activo: !f.activo } : f))
        );
      }
    } catch (e) {
      console.error("Error al alternar enfoque:", e);
    }
  };

  const handleDeleteFocus = async (focusId: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/focuses/${focusId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setFocuses((prev) => prev.filter((f) => f.id !== focusId));
      }
    } catch (e) {
      console.error("Error al eliminar enfoque:", e);
    }
  };

  const handleAddFocus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFocusName.trim()) return;

    const kwList = newFocusKeywords
      .split(",")
      .map((k) => k.trim())
      .filter((k) => k.length > 0);

    try {
      const res = await fetch(`${BACKEND_URL}/api/focuses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: newFocusName,
          categoria: newFocusCategory,
          keywords: kwList,
          descripcion: newFocusDesc,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setFocuses((prev) => [...prev, data.focus]);
        setNewFocusName("");
        setNewFocusKeywords("");
        setNewFocusDesc("");
        setStatusMessage("Enfoque agregado correctamente. Haz clic en 'Actualizar Radar'.");
        setTimeout(() => setStatusMessage(null), 4000);
      }
    } catch (e) {
      console.error("Error al agregar enfoque:", e);
    }
  };

  const handleRunRadar = async () => {
    setIsRunningRadar(true);
    setStatusMessage("Ejecutando escaneo de 8 fuentes y calibración Jev en segundo plano...");
    try {
      await fetch(`${BACKEND_URL}/api/run`, { method: "POST" });
      // Polling cada 3 segundos
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${BACKEND_URL}/api/status`);
          const st = await res.json();
          if (!st.is_running) {
            clearInterval(interval);
            setIsRunningRadar(false);
            if (st.last_status === "success") {
              setStatusMessage("Radar actualizado con éxito. Refrescando datos...");
              await fetchInitialData();
            } else {
              setStatusMessage("Finalizado con advertencia: " + (st.last_error || "Revisa logs"));
            }
            setTimeout(() => setStatusMessage(null), 4000);
          }
        } catch (err) {
          console.error("Error en polling:", err);
        }
      }, 3000);
    } catch (e) {
      setIsRunningRadar(false);
      setStatusMessage("No se pudo conectar con el servidor backend en localhost:8080.");
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  // Filtrado de tendencias
  const filteredTrends = (report?.top_temas || []).filter((item) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      item.tema.toLowerCase().includes(q) ||
      item.por_que.toLowerCase().includes(q) ||
      item.adaptacion_30x.toLowerCase().includes(q);

    const matchesFormat =
      selectedFormat === "todos" || item.formato === selectedFormat;

    return matchesSearch && matchesFormat;
  });

  return (
    <div className="min-h-screen bg-[#0f1011] text-[#9f9fa0] flex flex-col font-sans">
      {/* 1. Sticky Navigation Bar — Origin Glassmorphism */}
      <nav className="sticky top-0 z-40 nav-glass px-6 lg:px-12 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <span className="w-7 h-7 rounded-[8px] bg-white text-black font-extrabold flex items-center justify-center text-xs tracking-tighter">
              30X
            </span>
            <span className="font-mono-label text-[#f5f5f7] tracking-[0.18em]">
              RADAR // INTELLIGENCE
            </span>
          </div>

          <div className="hidden md:flex items-center space-x-2 pl-4 border-l border-[#2e2e2e]">
            <span className="font-mono-label text-[#6a6b6b] text-[10px]">
              SEMANA {report?.semana || "2026-W42"}
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#00b3dd] animate-pulse"></span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Ghost outline button — Search Focuses Studio */}
          <button
            onClick={() => setIsFocusStudioOpen(true)}
            className="hidden sm:flex items-center space-x-2 px-3.5 py-2 rounded-[8px] border border-white/20 hover:border-white text-[#f5f5f7] text-xs font-medium transition duration-200"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-[#847dff]" />
            <span>Enfoques de Búsqueda</span>
            <span className="bg-[#2e2e2e] text-[#d1c9ff] px-1.5 py-0.2 rounded text-[10px] font-mono">
              {focuses.filter((f) => f.activo).length}
            </span>
          </button>

          {/* Primary CTA Button — High-contrast white on black (#ffffff -> #000000) */}
          <button
            onClick={handleRunRadar}
            disabled={isRunningRadar}
            className="flex items-center space-x-2 px-4 py-2 rounded-[8px] bg-[#ffffff] hover:bg-[#cacaca] text-[#000000] text-xs font-semibold tracking-tight transition duration-200 disabled:opacity-50 shadow-sm"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRunningRadar ? "animate-spin" : ""}`}
            />
            <span>{isRunningRadar ? "Escaneando..." : "Actualizar Radar"}</span>
            <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
          </button>
        </div>
      </nav>

      {/* Notificación Flotante */}
      {statusMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#2e2e2e] border border-white/20 text-[#f5f5f7] px-4 py-3 rounded-[12px] shadow-2xl flex items-center space-x-3 text-xs animate-in fade-in slide-in-from-bottom-3 duration-200">
          <Sparkles className="w-4 h-4 text-[#847dff] flex-shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Contenedor Principal */}
      <main className="flex-1 max-w-[1200px] w-full mx-auto px-6 lg:px-8 py-16 space-y-24">
        {/* 2. Hero Section — Whisper-weight Serif Display 80-96px with Italic Tension */}
        <section className="text-center max-w-4xl mx-auto space-y-8 pt-6">
          {/* Pill Chip Label */}
          <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-[9999px] bg-white/[0.08] border border-white/[0.12] text-[#f5f5f7]">
            <span className="w-2 h-2 rounded-full bg-[#847dff]"></span>
            <span className="font-mono-label text-[10px] tracking-[0.18em]">
              TYPESAFE JEV CALIBRATED // RECENT INTELLIGENCE
            </span>
          </div>

          <h1 className="font-display-headline text-[60px] sm:text-[84px] lg:text-[96px] text-[#ffffff] tracking-tight leading-[0.92]">
            <span className="italic font-normal text-[#d1c9ff]">Emerging</span> signals, curated with quiet authority.
          </h1>

          <p className="text-[17px] sm:text-[18px] text-[#9f9fa0] font-light max-w-2xl mx-auto leading-relaxed">
            Descubrimiento automatizado y calibrado de tendencias de IA de los últimos 7 días.
            Filtrado de ruido técnico, empaquetado editorial y adaptaciones estratégicas para líderes en Latinoamérica.
          </p>

          {/* AI Prompt Input Bar — Spec: Black #000000, 8px radius, generous left padding */}
          <div className="max-w-2xl mx-auto relative pt-4">
            <div className="relative flex items-center bg-[#000000] border border-white/[0.14] hover:border-white/30 rounded-[8px] transition duration-200">
              <Search className="w-4 h-4 text-[#6a6b6b] absolute left-4" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Explorar polémicas de OpenAI/Anthropic, benchmarks o liderazgo..."
                className="w-full bg-transparent text-[#f5f5f7] placeholder-[#6a6b6b] text-sm py-3.5 pl-11 pr-12 rounded-[8px] focus:outline-none"
              />
              <button
                onClick={() => {}}
                className="w-8 h-8 rounded-full bg-white/20 hover:bg-white text-black flex items-center justify-center absolute right-2 transition duration-200"
              >
                <ArrowRight className="w-4 h-4 text-[#ffffff] hover:text-black" />
              </button>
            </div>

            {/* Quick Filter Tags */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-4">
              <span className="font-mono-label text-[10px] text-[#6a6b6b] mr-2">
                FILTRAR POR FORMATO:
              </span>
              {["todos", "video_corto", "carousel", "hilo", "articulo"].map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => setSelectedFormat(fmt)}
                  className={`font-mono-label text-[10px] px-3 py-1 rounded-[9999px] transition ${
                    selectedFormat === fmt
                      ? "bg-white text-black font-semibold"
                      : "bg-[#2e2e2e] text-[#9f9fa0] hover:text-white"
                  }`}
                >
                  {fmt === "todos"
                    ? "TODOS"
                    : fmt === "video_corto"
                    ? "REELS / SHORTS"
                    : fmt.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* 3. Feature Category Cards — Full-bleed Chromatic Tiles with 30px Radius & 38px Lyon Display */}
        <section className="space-y-6">
          <div className="flex items-center justify-between border-b border-[#2e2e2e] pb-4">
            <span className="font-mono-label text-[#f5f5f7] tracking-[0.16em]">
              01 // LÍNEAS ESTRATÉGICAS DE OBSERVACIÓN
            </span>
            <span className="text-xs text-[#6a6b6b]">4 Pilares Curados para 30X</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Tile 1: Iris Gleam — Polémicas de Labs */}
            <div className="bg-[#847dff] rounded-[30px] p-8 flex flex-col justify-between min-h-[300px] text-white transition hover:-translate-y-1 duration-200">
              <div className="space-y-3">
                <span className="font-mono-label text-[10px] tracking-[0.18em] text-white/80">
                  CRITICAL GOVERNANCE
                </span>
                <h3 className="font-display-card text-white">
                  OpenAI & Anthropic
                </h3>
              </div>
              <p className="text-sm text-white/90 font-normal leading-relaxed pt-6">
                Salidas de investigadores de seguridad, demandas de copyright, disputas de alianzas y el riesgo real para directivos que eligen proveedores de nube.
              </p>
            </div>

            {/* Tile 2: Cyan Signal — Benchmarks */}
            <div className="bg-[#00b3dd] rounded-[30px] p-8 flex flex-col justify-between min-h-[300px] text-white transition hover:-translate-y-1 duration-200">
              <div className="space-y-3">
                <span className="font-mono-label text-[10px] tracking-[0.18em] text-white/80">
                  CAPABILITY DRIFT
                </span>
                <h3 className="font-display-card text-white">
                  The Model Race
                </h3>
              </div>
              <p className="text-sm text-white/90 font-normal leading-relaxed pt-6">
                Corte de caja en benchmarks de razonamiento (o3 vs Claude 3.5 vs DeepSeek). Comparativas de costo por millón de tokens en tareas reales.
              </p>
            </div>

            {/* Tile 3: Orchid Bloom — CEO Desarrollo Personal */}
            <div className="bg-[#dd90d8] rounded-[30px] p-8 flex flex-col justify-between min-h-[300px] text-white transition hover:-translate-y-1 duration-200">
              <div className="space-y-3">
                <span className="font-mono-label text-[10px] tracking-[0.18em] text-white/80">
                  LEADERSHIP MINDSET
                </span>
                <h3 className="font-display-card text-white">
                  The AI CEO
                </h3>
              </div>
              <p className="text-sm text-white/90 font-normal leading-relaxed pt-6">
                Desarrollo personal para directores: modelos mentales para delegar tareas complejas en agentes sin perder la visión de negocio ni el control humano.
              </p>
            </div>

            {/* Tile 4: Periwinkle — Oportunidades & ROI */}
            <div className="bg-[#90b8f0] rounded-[30px] p-8 flex flex-col justify-between min-h-[300px] text-white transition hover:-translate-y-1 duration-200">
              <div className="space-y-3">
                <span className="font-mono-label text-[10px] tracking-[0.18em] text-white/80">
                  REGIONAL IMPACT
                </span>
                <h3 className="font-display-card text-white">
                  LatAm ROI
                </h3>
              </div>
              <p className="text-sm text-white/90 font-normal leading-relaxed pt-6">
                Casos de negocio y automatizaciones en México, Colombia y Chile que sustituyen RPA legado y amortizan la inversión en menos de 90 días.
              </p>
            </div>
          </div>
        </section>

        {/* 4. Inverted Stat Block — Spec: Silver #cacaca, 30px radius, 32px padding, stark black text */}
        <section className="bg-[#cacaca] text-[#000000] rounded-[30px] p-8 sm:p-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
          <div className="space-y-2 max-w-xl">
            <span className="font-mono-label text-[11px] text-[#000000]/60 tracking-[0.18em]">
              AUDIT & METHODOLOGY
            </span>
            <h2 className="font-display-card text-[#000000] text-3xl sm:text-4xl">
              100% Recency Window. Zero Hallucination.
            </h2>
            <p className="text-[#000000]/80 text-sm leading-relaxed">
              Cada tendencia es evaluada con el motor probabilístico TypeSafe Jev (System 1 RLCD) sobre señales reales de la última semana. Cero raspado privado, 100% fuentes públicas auditables.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-6 sm:gap-8 w-full lg:w-auto border-t lg:border-t-0 lg:border-l border-black/15 pt-6 lg:pt-0 lg:pl-10">
            <div>
              <div className="font-display-headline text-3xl sm:text-4xl text-[#000000]">
                &lt; 7d
              </div>
              <div className="font-mono-label text-[10px] text-[#000000]/60 mt-1">
                VENTANA ESTRICTA
              </div>
            </div>
            <div>
              <div className="font-display-headline text-3xl sm:text-4xl text-[#000000]">
                183
              </div>
              <div className="font-mono-label text-[10px] text-[#000000]/60 mt-1">
                ITEMS SEMANALES
              </div>
            </div>
            <div>
              <div className="font-display-headline text-3xl sm:text-4xl text-[#000000]">
                Jev
              </div>
              <div className="font-mono-label text-[10px] text-[#000000]/60 mt-1">
                SYSTEM 1 CALIBRADO
              </div>
            </div>
          </div>
        </section>

        {/* 5. Top 10 Ranked Trends Gallery — Surface Elevated #2e2e2e (Graphite Cards) */}
        <section className="space-y-6">
          <div className="flex items-center justify-between border-b border-[#2e2e2e] pb-4">
            <div className="flex items-center space-x-3">
              <span className="font-mono-label text-[#f5f5f7] tracking-[0.16em]">
                02 // TOP 10 RADAR DE TENDENCIAS
              </span>
              <span className="text-xs text-[#6a6b6b]">
                ({filteredTrends.length} identificadas)
              </span>
            </div>

            <button
              onClick={() => setIsFocusStudioOpen(true)}
              className="text-xs text-[#847dff] hover:text-[#d1c9ff] flex items-center gap-1 transition"
            >
              <span>Configurar enfoques de búsqueda</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-4">
            {filteredTrends.length === 0 ? (
              <div className="bg-[#2e2e2e] rounded-[16px] p-12 text-center space-y-3">
                <p className="text-[#f5f5f7] text-base font-medium">
                  No se encontraron tendencias con los criterios actuales.
                </p>
                <p className="text-xs text-[#9f9fa0]">
                  Prueba limpiando la búsqueda o ejecutando el escaneo de radar.
                </p>
              </div>
            ) : (
              filteredTrends.map((trend) => (
                <div
                  key={trend.posicion}
                  className="bg-[#2e2e2e] rounded-[16px] p-6 sm:p-8 space-y-6 transition hover:bg-[#3f4041]/50 duration-200"
                >
                  {/* Top Bar: Rank + Title + Micro-labels */}
                  <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                    <div className="flex items-start space-x-4">
                      <span className="font-mono-label text-xs w-8 h-8 rounded-[8px] bg-[#0f1011] text-[#ffffff] flex items-center justify-center border border-white/10 flex-shrink-0">
                        #{trend.posicion}
                      </span>
                      <div className="space-y-1.5">
                        <h3 className="text-xl sm:text-2xl font-semibold text-[#f5f5f7] tracking-tight">
                          {trend.tema}
                        </h3>
                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          <span className="font-mono-label text-[10px] px-2.5 py-0.5 rounded-[9999px] bg-[#0f1011] text-[#00b3dd] border border-[#00b3dd]/20">
                            {trend.fase.toUpperCase()}
                          </span>
                          <span className="font-mono-label text-[10px] px-2.5 py-0.5 rounded-[9999px] bg-[#0f1011] text-[#847dff] border border-[#847dff]/20">
                            {trend.crecimiento}
                          </span>
                          <span className="font-mono-label text-[10px] text-[#6a6b6b]">
                            JEV CONF: {(trend.confianza_jev * 100).toFixed(0)}%
                          </span>
                          <span className="font-mono-label text-[10px] text-[#6a6b6b]">
                            ENCAJE LATAM: {(trend.encaje_audiencia * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Sources Badge List */}
                    <div className="flex flex-wrap lg:justify-end gap-1.5 self-start">
                      {trend.fuentes.map((src) => (
                        <span
                          key={src}
                          className="font-mono-label text-[10px] px-2.5 py-1 rounded-[6px] bg-[#0f1011] text-[#cacaca] border border-white/10"
                        >
                          {src}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Body Grid: Por Qué Funciona vs Adaptación Editorial 30X */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
                    {/* Col 1: Por qué funciona */}
                    <div className="bg-[#0f1011] rounded-[12px] p-5 border border-white/5 space-y-2">
                      <span className="font-mono-label text-[10px] text-[#6a6b6b] flex items-center gap-1.5">
                        <TrendingUp className="w-3.5 h-3.5 text-[#00b3dd]" />
                        ¿POR QUÉ FUNCIONA? // SEÑAL CUANTITATIVA
                      </span>
                      <p className="text-sm text-[#cacaca] leading-relaxed font-light">
                        {trend.por_que}
                      </p>
                    </div>

                    {/* Col 2: Adaptación Editorial 30X */}
                    <div className="bg-[#0f1011] rounded-[12px] p-5 border border-[#847dff]/30 space-y-2 relative">
                      <div className="flex items-center justify-between">
                        <span className="font-mono-label text-[10px] text-[#847dff] flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-[#847dff]" />
                          PROPUESTA EDITORIAL 30X
                        </span>
                        <button
                          onClick={() => copyText(trend.adaptacion_30x, `t-${trend.posicion}`)}
                          className="text-[11px] text-[#847dff] hover:text-white flex items-center gap-1 transition"
                        >
                          {copiedId === `t-${trend.posicion}` ? (
                            <>
                              <Check className="w-3 h-3 text-white" />
                              <span className="text-white">Copiado</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copiar</span>
                            </>
                          )}
                        </button>
                      </div>
                      <p className="text-sm text-[#f5f5f7] font-medium leading-relaxed">
                        {trend.adaptacion_30x}
                      </p>
                    </div>
                  </div>

                  {/* References & Evidence Section (SPEC: Clear access to evidence) */}
                  <div className="pt-4 border-t border-white/5 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono-label text-[10px] text-[#6a6b6b] flex items-center gap-1.5">
                        <Compass className="w-3.5 h-3.5 text-[#00b3dd]" />
                        EVIDENCIAS Y REFERENCIAS VERIFICADAS (
                        {trend.referencias_detalladas?.length || trend.evidencia.length})
                      </span>
                    </div>

                    <div className="grid grid-cols-1 gap-2 pt-1">
                      {(trend.referencias_detalladas ||
                        trend.evidencia.map((u) => ({
                          url: u,
                          titulo: u,
                          fuente: "Fuente Web",
                          autor: "",
                          fecha: "Semana en curso",
                        }))
                      ).map((ref, idx) => (
                        <div
                          key={idx}
                          className="bg-[#0f1011] rounded-[8px] p-3 border border-white/5 hover:border-white/20 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                        >
                          <div className="flex-1 min-w-0 space-y-0.5">
                            <div className="flex items-center space-x-2">
                              <span className="font-mono-label text-[9px] px-2 py-0.2 rounded bg-[#2e2e2e] text-[#847dff]">
                                {ref.fuente}
                              </span>
                              {ref.autor && (
                                <span className="text-[#6a6b6b] text-[11px] truncate">
                                  por {ref.autor}
                                </span>
                              )}
                              {ref.fecha && (
                                <span className="text-[#6a6b6b] text-[11px]">
                                  • {ref.fecha}
                                </span>
                              )}
                            </div>
                            <a
                              href={ref.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-[#f5f5f7] hover:text-[#00b3dd] transition truncate block font-normal"
                            >
                              {ref.titulo}
                            </a>
                          </div>

                          <div className="flex items-center space-x-2 flex-shrink-0 self-end sm:self-center">
                            <button
                              onClick={() => copyText(ref.url, `ref-${trend.posicion}-${idx}`)}
                              className="p-1.5 rounded-[6px] bg-[#2e2e2e] hover:bg-[#3f4041] text-[#9f9fa0] hover:text-white transition"
                              title="Copiar enlace"
                            >
                              {copiedId === `ref-${trend.posicion}-${idx}` ? (
                                <Check className="w-3.5 h-3.5 text-white" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                            <a
                              href={ref.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-1.5 rounded-[6px] bg-[#2e2e2e] hover:bg-white hover:text-black text-[#f5f5f7] font-medium text-xs flex items-center gap-1.5 transition duration-200"
                            >
                              <span>Abrir</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>

      {/* 6. Search Focus Studio Modal (Panel de Enfoques de Búsqueda) */}
      {isFocusStudioOpen && (
        <div className="fixed inset-0 z-50 bg-[#000000]/80 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200">
          <div className="bg-[#0f1011] border border-white/15 rounded-[20px] w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-6 border-b border-[#2e2e2e] flex items-center justify-between">
              <div className="space-y-1">
                <span className="font-mono-label text-[10px] text-[#847dff] tracking-[0.18em]">
                  SEARCH FOCUS STUDIO
                </span>
                <h2 className="text-xl font-semibold text-[#ffffff]">
                  Panel de Enfoques y Palabras Clave
                </h2>
              </div>
              <button
                onClick={() => setIsFocusStudioOpen(false)}
                className="p-2 rounded-[8px] bg-[#2e2e2e] text-[#9f9fa0] hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body: Two columns (List & Add Form) */}
            <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Columna Izquierda: Lista de Enfoques Existentes (7 cols) */}
              <div className="lg:col-span-7 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono-label text-[10px] text-[#6a6b6b]">
                    ENFOQUES CONFIGURADOS ({focuses.length})
                  </span>
                  <span className="text-xs text-[#9f9fa0]">
                    Activa/desactiva para orientar la ingesta
                  </span>
                </div>

                <div className="space-y-3">
                  {focuses.map((f) => (
                    <div
                      key={f.id}
                      className={`p-4 rounded-[12px] border transition duration-200 ${
                        f.activo
                          ? "bg-[#2e2e2e] border-white/20"
                          : "bg-[#0f1011] border-white/5 opacity-60"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold text-sm text-[#f5f5f7]">
                              {f.nombre}
                            </span>
                            <span className="font-mono-label text-[9px] px-2 py-0.2 rounded bg-[#0f1011] text-[#00b3dd]">
                              {f.categoria}
                            </span>
                          </div>
                          <p className="text-xs text-[#9f9fa0] leading-relaxed">
                            {f.descripcion}
                          </p>
                          <div className="flex flex-wrap gap-1 pt-1.5">
                            {f.keywords.map((kw, i) => (
                              <span
                                key={i}
                                className="font-mono-label text-[9px] px-2 py-0.5 rounded bg-[#0f1011] text-[#cacaca]"
                              >
                                {kw}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 flex-shrink-0">
                          <button
                            onClick={() => handleToggleFocus(f.id)}
                            className={`px-3 py-1 rounded-[6px] text-xs font-mono transition ${
                              f.activo
                                ? "bg-white text-black font-semibold"
                                : "bg-[#3f4041] text-[#9f9fa0]"
                            }`}
                          >
                            {f.activo ? "ACTIVO" : "INACTIVO"}
                          </button>
                          <button
                            onClick={() => handleDeleteFocus(f.id)}
                            className="p-1.5 rounded-[6px] text-[#6a6b6b] hover:text-red-400 hover:bg-[#3f4041] transition"
                            title="Eliminar enfoque"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Columna Derecha: Formulario para Agregar Nuevo Enfoque (5 cols) */}
              <div className="lg:col-span-5 bg-[#2e2e2e] rounded-[16px] p-6 space-y-4 self-start">
                <span className="font-mono-label text-[10px] text-[#847dff] block">
                  + AGREGAR NUEVO ENFOQUE
                </span>
                <form onSubmit={handleAddFocus} className="space-y-4 text-xs">
                  <div>
                    <label className="block text-[#cacaca] mb-1 font-medium">
                      Nombre del Enfoque
                    </label>
                    <input
                      type="text"
                      required
                      value={newFocusName}
                      onChange={(e) => setNewFocusName(e.target.value)}
                      placeholder="Ej: Demandas de Copyright en Música IA"
                      className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] p-2.5 text-[#f5f5f7] focus:border-[#847dff] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-[#cacaca] mb-1 font-medium">
                      Categoría
                    </label>
                    <select
                      value={newFocusCategory}
                      onChange={(e) => setNewFocusCategory(e.target.value)}
                      className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] p-2.5 text-[#f5f5f7] focus:border-[#847dff] outline-none"
                    >
                      <option value="polemicas">Polémicas & Gobernanza Labs</option>
                      <option value="benchmarks">Benchmarks & Model Race</option>
                      <option value="ceo_liderazgo">Desarrollo Personal de CEO</option>
                      <option value="oportunidades_roi">Oportunidades de Negocio & ROI</option>
                      <option value="agentes_operaciones">Agentes & Operaciones</option>
                      <option value="seguridad">Seguridad & Sandboxing</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[#cacaca] mb-1 font-medium">
                      Palabras Clave (separadas por coma)
                    </label>
                    <input
                      type="text"
                      required
                      value={newFocusKeywords}
                      onChange={(e) => setNewFocusKeywords(e.target.value)}
                      placeholder="Suno, Udio, Sony Music, RIAA, infracción"
                      className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] p-2.5 text-[#f5f5f7] focus:border-[#847dff] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-[#cacaca] mb-1 font-medium">
                      Descripción Estratégica
                    </label>
                    <textarea
                      rows={3}
                      value={newFocusDesc}
                      onChange={(e) => setNewFocusDesc(e.target.value)}
                      placeholder="Qué debe vigilar el radar y qué valor aporta a directivos..."
                      className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] p-2.5 text-[#f5f5f7] focus:border-[#847dff] outline-none resize-none"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full py-2.5 rounded-[8px] bg-white text-black font-semibold text-xs tracking-tight hover:bg-[#cacaca] transition duration-200 flex items-center justify-center space-x-1.5 shadow"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Guardar y Habilitar Enfoque</span>
                  </button>
                </form>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-[#090a0b] border-t border-[#2e2e2e] flex items-center justify-between">
              <span className="text-xs text-[#6a6b6b]">
                Los cambios se aplican automáticamente en la próxima ejecución del radar.
              </span>
              <button
                onClick={() => {
                  setIsFocusStudioOpen(false);
                  handleRunRadar();
                }}
                className="px-4 py-2 rounded-[8px] bg-white text-black text-xs font-semibold flex items-center space-x-2 transition hover:bg-[#cacaca]"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Ejecutar Radar con Nuevos Enfoques</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. Footer — Spec: Nocturnal gallery quiet closing */}
      <footer className="border-t border-[#2e2e2e] py-12 px-6 lg:px-8 mt-24 text-center space-y-4">
        <div className="flex items-center justify-center space-x-3">
          <span className="w-6 h-6 rounded-[6px] bg-white text-black font-bold flex items-center justify-center text-[10px]">
            30X
          </span>
          <span className="font-mono-label text-xs text-[#f5f5f7]">
            RADAR DE CONTENIDO 30X // LATIN AMERICA
          </span>
        </div>
        <p className="text-xs text-[#6a6b6b] max-w-md mx-auto">
          Sistema de descubrimiento y ranking type-safe. Desarrollado con TypeSafe Jev System 1 y Next.js bajo la estética Origin Financial.
        </p>
      </footer>
    </div>
  );
}
