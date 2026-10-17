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
  Video,
  Brain,
  BookOpen,
  Play,
  Gauge,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  FileText,
  Link2,
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
  por_que_audiencia?: string;
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

interface HookAnalysis {
  tipo_gancho: string;
  texto_primeros_15s: string;
  analisis_gancho: string;
  plantilla_reutilizable: string;
}

interface KnowledgeProfile {
  source_id: string;
  hook: HookAnalysis;
  estructura_narrativa: Array<{ etapa: string; segundos: string; proposito: string }>;
  tono_y_voz: string;
  conceptos_clave: string[];
  plantillas_30x: string[];
  resumen_ejecutivo: string;
}

interface KnowledgeSource {
  id: string;
  tipo: string;
  url_o_path: string;
  titulo: string;
  autor: string;
  duracion_segundos: number;
  solicitud_usuario: string;
  transcripcion_resumen: string;
  creado_en: string;
  perfil?: KnowledgeProfile;
}

interface PlaygroundResult {
  tema: string;
  fuentes: string[];
  vistas_por_hora: number;
  preguntas_jev: Array<{ id: string; pregunta: string; opciones: string[]; proposito: string }>;
  decision: {
    fase: string;
    gancho: string;
    formato: string;
    novedad: number;
    encaje_audiencia: number;
    confianza: number;
  };
  score_final: number;
  crecimiento_label: string;
  score_breakdown: Record<string, any>;
  latencia_ms: number;
  motor_utilizado: string;
}

const getApiBase = () => {
  if (typeof window !== "undefined") {
    if (window.location.port === "8080" || window.location.port === "") {
      return "";
    }
  }
  return "http://localhost:8080";
};

export default function RadarHomePage() {
  const [activeTab, setActiveTab] = useState<"tendencias" | "conocimiento" | "enfoques" | "playground">("tendencias");
  const [report, setReport] = useState<ReportData | null>(null);
  const [focuses, setFocuses] = useState<SearchFocus[]>([]);
  const [knowledgeList, setKnowledgeList] = useState<KnowledgeSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFormat, setSelectedFormat] = useState("todos");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isRunningRadar, setIsRunningRadar] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Estado para formulario de Base de Conocimiento
  const [knwUrl, setKnwUrl] = useState("");
  const [knwSolicitud, setKnwSolicitud] = useState("");
  const [knwTitulo, setKnwTitulo] = useState("");
  const [knwAutor, setKnwAutor] = useState("");
  const [isIngestingKnw, setIsIngestingKnw] = useState(false);
  const [knwSearchQuery, setKnwSearchQuery] = useState("");
  const [knwSearchResults, setKnwSearchResults] = useState<any[] | null>(null);
  const [isSearchingKnw, setIsSearchingKnw] = useState(false);

  // Estado para Playground de Jev
  const [playgroundHeadline, setPlaygroundHeadline] = useState("Claude 3.5 Sonnet supera a modelos propietarios en benchmarks de razonamiento");
  const [playgroundVph, setPlaygroundVph] = useState(350);
  const [playgroundSources, setPlaygroundSources] = useState<string[]>(["HackerNews", "YouTube", "GitHub"]);
  const [isEvaluatingPlayground, setIsEvaluatingPlayground] = useState(false);
  const [playgroundResult, setPlaygroundResult] = useState<PlaygroundResult | null>(null);

  // Estado para nuevo enfoque
  const [newFocusName, setNewFocusName] = useState("");
  const [newFocusCategory, setNewFocusCategory] = useState("polemicas");
  const [newFocusKeywords, setNewFocusKeywords] = useState("");
  const [newFocusDesc, setNewFocusDesc] = useState("");

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const api = getApiBase();
      // 1. Reporte
      const resReport = await fetch(`${api}/api/report/latest`);
      if (resReport.ok) {
        const reportJson = await resReport.json();
        setReport(reportJson);
      }
      // 2. Enfoques
      const resFocuses = await fetch(`${api}/api/focuses`);
      if (resFocuses.ok) {
        const focusesJson = await resFocuses.json();
        setFocuses(focusesJson.focuses || []);
      }
      // 3. Conocimiento
      const resKnw = await fetch(`${api}/api/knowledge`);
      if (resKnw.ok) {
        const knwJson = await resKnw.json();
        setKnowledgeList(knwJson.sources || []);
      }
    } catch (err) {
      console.warn("Backend local no disponible:", err);
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
      const api = getApiBase();
      const res = await fetch(`${api}/api/focuses/${focusId}/toggle`, { method: "POST" });
      if (res.ok) {
        setFocuses((prev) => prev.map((f) => (f.id === focusId ? { ...f, activo: !f.activo } : f)));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteFocus = async (focusId: string) => {
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/focuses/${focusId}`, { method: "DELETE" });
      if (res.ok) {
        setFocuses((prev) => prev.filter((f) => f.id !== focusId));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddFocus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFocusName.trim()) return;
    const kwList = newFocusKeywords.split(",").map((k) => k.trim()).filter((k) => k.length > 0);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/focuses`, {
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
        setStatusMessage("Enfoque guardado y activado.");
        setTimeout(() => setStatusMessage(null), 3500);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleIngestKnowledge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!knwUrl.trim()) return;
    setIsIngestingKnw(true);
    setStatusMessage("Transcribiendo video y analizando estilo de gancho con Jev...");
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/knowledge/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: knwUrl,
          solicitud: knwSolicitud || "Extraer ganchos contraintuitivos y estructura de retención",
          titulo: knwTitulo || undefined,
          autor: knwAutor || undefined,
          tipo: knwUrl.includes("youtube") || knwUrl.includes("youtu.be") ? "youtube" : "url",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setKnowledgeList((prev) => [data.source, ...prev]);
        setKnwUrl("");
        setKnwSolicitud("");
        setKnwTitulo("");
        setKnwAutor("");
        setStatusMessage("Recurso procesado y vectorizado con éxito.");
        setTimeout(() => setStatusMessage(null), 4000);
      } else {
        const err = await res.json();
        setStatusMessage(`Error: ${err.error || "No se pudo procesar"}`);
      }
    } catch (err) {
      console.error(err);
      setStatusMessage("Error al conectar con el servidor.");
    } finally {
      setIsIngestingKnw(false);
    }
  };

  const handleSearchKnowledge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!knwSearchQuery.trim()) {
      setKnwSearchResults(null);
      return;
    }
    setIsSearchingKnw(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/knowledge/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: knwSearchQuery, top_k: 4 }),
      });
      if (res.ok) {
        const data = await res.json();
        setKnwSearchResults(data.results || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearchingKnw(false);
    }
  };

  const handleDeleteKnowledge = async (id: string) => {
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/knowledge/${id}`, { method: "DELETE" });
      if (res.ok) {
        setKnowledgeList((prev) => prev.filter((k) => k.id !== id));
        setStatusMessage("Recurso eliminado de la base de conocimiento.");
        setTimeout(() => setStatusMessage(null), 3000);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleEvaluatePlayground = async () => {
    if (!playgroundHeadline.trim()) return;
    setIsEvaluatingPlayground(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/playground/eval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tema: playgroundHeadline,
          fuentes: playgroundSources,
          vistas_por_hora: playgroundVph,
          titulos_muestra: [playgroundHeadline],
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPlaygroundResult(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsEvaluatingPlayground(false);
    }
  };

  const handleRunRadar = async () => {
    setIsRunningRadar(true);
    setStatusMessage("Ejecutando escaneo y calibración en segundo plano...");
    try {
      const api = getApiBase();
      await fetch(`${api}/api/run`, { method: "POST" });
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${api}/api/status`);
          const st = await res.json();
          if (!st.is_running) {
            clearInterval(interval);
            setIsRunningRadar(false);
            if (st.last_status === "success") {
              setStatusMessage("Radar actualizado con éxito. Refrescando datos...");
              await fetchInitialData();
            } else {
              setStatusMessage("Finalizado: " + (st.last_error || "Completado"));
            }
            setTimeout(() => setStatusMessage(null), 4000);
          }
        } catch (err) {
          console.error(err);
        }
      }, 3000);
    } catch (e) {
      setIsRunningRadar(false);
      setStatusMessage("Error al comunicar con el motor del radar.");
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const filteredTrends = (report?.top_temas || []).filter((item) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      item.tema.toLowerCase().includes(q) ||
      item.por_que.toLowerCase().includes(q) ||
      item.adaptacion_30x.toLowerCase().includes(q);
    const matchesFormat = selectedFormat === "todos" || item.formato === selectedFormat;
    return matchesSearch && matchesFormat;
  });

  return (
    <div className="min-h-screen bg-[#0f1011] text-[#9f9fa0] flex flex-col font-sans">
      {/* 1. Sticky Navigation Bar — Origin Glassmorphism */}
      <nav className="sticky top-0 z-40 nav-glass px-6 lg:px-12 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab("tendencias")}>
            <span className="w-7 h-7 rounded-[8px] bg-white text-black font-extrabold flex items-center justify-center text-xs tracking-tighter">
              30X
            </span>
            <span className="font-mono-label text-[#f5f5f7] tracking-[0.18em]">
              RADAR // INTELLIGENCE
            </span>
          </div>

          {/* Navigation Tabs */}
          <div className="hidden md:flex items-center space-x-1 pl-4 border-l border-[#2e2e2e]">
            <button
              onClick={() => setActiveTab("tendencias")}
              className={`px-3 py-1.5 rounded-[8px] text-xs font-medium transition ${
                activeTab === "tendencias" ? "bg-white/10 text-white" : "text-[#9f9fa0] hover:text-white"
              }`}
            >
              Tendencias Top 10
            </button>
            <button
              onClick={() => setActiveTab("conocimiento")}
              className={`px-3 py-1.5 rounded-[8px] text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === "conocimiento" ? "bg-white/10 text-white" : "text-[#9f9fa0] hover:text-white"
              }`}
            >
              <Brain className="w-3.5 h-3.5 text-[#847dff]" />
              <span>Base de Conocimiento</span>
              <span className="text-[10px] font-mono bg-[#2e2e2e] text-[#d1c9ff] px-1.5 rounded">
                {knowledgeList.length}
              </span>
            </button>
            <button
              onClick={() => setActiveTab("enfoques")}
              className={`px-3 py-1.5 rounded-[8px] text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === "enfoques" ? "bg-white/10 text-white" : "text-[#9f9fa0] hover:text-white"
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-[#00b3dd]" />
              <span>Enfoques de Búsqueda</span>
              <span className="text-[10px] font-mono bg-[#2e2e2e] text-[#00b3dd] px-1.5 rounded">
                {focuses.filter((f) => f.activo).length}
              </span>
            </button>
            <button
              onClick={() => {
                setActiveTab("playground");
                if (!playgroundResult) handleEvaluatePlayground();
              }}
              className={`px-3 py-1.5 rounded-[8px] text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === "playground" ? "bg-white/10 text-white" : "text-[#9f9fa0] hover:text-white"
              }`}
            >
              <Gauge className="w-3.5 h-3.5 text-[#dd90d8]" />
              <span>Playground JEV</span>
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2">
            <span className="font-mono-label text-[#6a6b6b] text-[10px]">
              SEMANA {report?.semana || "2026-W42"}
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#00b3dd] animate-pulse"></span>
          </div>

          <button
            onClick={handleRunRadar}
            disabled={isRunningRadar}
            className="flex items-center space-x-2 px-4 py-2 rounded-[8px] bg-[#ffffff] hover:bg-[#cacaca] text-[#000000] text-xs font-semibold tracking-tight transition duration-200 disabled:opacity-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRunningRadar ? "animate-spin" : ""}`} />
            <span>{isRunningRadar ? "Escaneando..." : "Actualizar Radar"}</span>
            <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
          </button>
        </div>
      </nav>

      {/* Floating Status Notification */}
      {statusMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#2e2e2e] border border-white/20 text-[#f5f5f7] px-4 py-3 rounded-[12px] shadow-2xl flex items-center space-x-3 text-xs animate-in fade-in duration-200">
          <Sparkles className="w-4 h-4 text-[#847dff] flex-shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-[1200px] w-full mx-auto px-6 lg:px-8 py-12 space-y-16">

        {/* =========================================================================
            TAB 1: TENDENCIAS (TOP 10 + EVIDENCIAS)
           ========================================================================= */}
        {activeTab === "tendencias" && (
          <div className="space-y-16">
            {/* Hero Display Headline */}
            <section className="text-center max-w-4xl mx-auto space-y-6 pt-4">
              <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-[9999px] bg-white/[0.08] border border-white/[0.12] text-[#f5f5f7]">
                <span className="w-2 h-2 rounded-full bg-[#847dff]"></span>
                <span className="font-mono-label text-[10px] tracking-[0.18em]">
                  TYPESAFE JEV CALIBRATED // RECENT INTELLIGENCE
                </span>
              </div>

              <h1 className="font-display-headline text-[54px] sm:text-[76px] lg:text-[88px] text-[#ffffff] tracking-tight leading-[0.92]">
                <span className="italic font-normal text-[#d1c9ff]">Emerging</span> signals, curated with quiet authority.
              </h1>

              <p className="text-[17px] text-[#9f9fa0] font-light max-w-2xl mx-auto leading-relaxed">
                Descubrimiento automatizado y calibrado de tendencias de IA de los últimos 7 días.
                Filtrado de ruido técnico, empaquetado editorial y adaptaciones estratégicas para líderes en Latinoamérica.
              </p>
            </section>

            {/* Feature Category Cards Grid */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-[30px] p-8 bg-[#847dff] text-white flex flex-col justify-between min-h-[220px]">
                <span className="font-mono-label text-white/80 text-[10px]">RELEVANCIA & AUDIENCIA</span>
                <div className="space-y-2 my-auto">
                  <h3 className="font-display-card text-white text-[34px] leading-tight font-light">
                    Impacto Ejecutivo
                  </h3>
                  <p className="text-white/90 text-sm font-light">
                    Penalización estricta a curiosidades técnicas y prioridad a casos de ROI y operaciones corporativas.
                  </p>
                </div>
              </div>

              <div className="rounded-[30px] p-8 bg-[#00b3dd] text-white flex flex-col justify-between min-h-[220px]">
                <span className="font-mono-label text-white/80 text-[10px]">RECENCIA COMPROBADA</span>
                <div className="space-y-2 my-auto">
                  <h3 className="font-display-card text-white text-[34px] leading-tight font-light">
                    Ventana 7 Días
                  </h3>
                  <p className="text-white/90 text-sm font-light">
                    Filtros temporales en YouTube, Google News y Hacker News asegurando frescura de esta semana.
                  </p>
                </div>
              </div>

              <div className="rounded-[30px] p-8 bg-[#dd90d8] text-white flex flex-col justify-between min-h-[220px]">
                <span className="font-mono-label text-white/80 text-[10px]">SINERGIA MULTI-FUENTE</span>
                <div className="space-y-2 my-auto">
                  <h3 className="font-display-card text-white text-[34px] leading-tight font-light">
                    Cross-Validation
                  </h3>
                  <p className="text-white/90 text-sm font-light">
                    Multiplicador del +25% a temas respaldados simultáneamente en video, prensa y redes profesionales.
                  </p>
                </div>
              </div>
            </section>

            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-[16px] bg-[#2e2e2e]">
              <div className="relative w-full sm:w-96">
                <Search className="w-4 h-4 text-[#6a6b6b] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filtrar por término, tecnología o palabra clave..."
                  className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] pl-10 pr-4 py-2 text-xs text-[#f5f5f7] placeholder-[#6a6b6b] focus:outline-none focus:border-[#847dff] transition"
                />
              </div>

              <div className="flex items-center space-x-2 w-full sm:w-auto">
                <select
                  value={selectedFormat}
                  onChange={(e) => setSelectedFormat(e.target.value)}
                  className="bg-[#0f1011] border border-white/10 text-xs text-[#f5f5f7] rounded-[8px] px-3 py-2 focus:outline-none focus:border-[#847dff]"
                >
                  <option value="todos">Todos los Formatos</option>
                  <option value="video_corto">Video Corto / Reel</option>
                  <option value="carousel">Carrusel LinkedIn</option>
                  <option value="hilo">Hilo X / LinkedIn</option>
                  <option value="articulo">Artículo / Newsletter</option>
                </select>
              </div>
            </div>

            {/* Ranked Trends Cards */}
            <div className="space-y-6">
              {filteredTrends.map((t) => (
                <div
                  key={t.posicion}
                  className="rounded-[24px] bg-[#2e2e2e] p-6 lg:p-8 space-y-6 border border-white/5 hover:border-white/15 transition duration-200"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="flex items-start space-x-4">
                      <span className="w-10 h-10 rounded-[10px] bg-[#0f1011] border border-white/15 text-[#f5f5f7] font-mono font-bold flex items-center justify-center text-sm flex-shrink-0">
                        #{t.posicion}
                      </span>
                      <div className="space-y-1.5">
                        <h2 className="text-xl sm:text-2xl font-bold text-[#ffffff] tracking-tight">
                          {t.tema}
                        </h2>
                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          <span className="font-mono-label px-2.5 py-0.5 rounded-[9999px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                            {t.fase}
                          </span>
                          <span className="font-mono-label px-2.5 py-0.5 rounded-[9999px] bg-[#00b3dd]/10 text-[#00b3dd] border border-[#00b3dd]/20 text-[10px]">
                            {t.crecimiento}
                          </span>
                          <span className="font-mono-label px-2.5 py-0.5 rounded-[9999px] bg-[#847dff]/10 text-[#847dff] border border-[#847dff]/20 text-[10px]">
                            Gancho: {t.gancho.replace("_", " ")}
                          </span>
                          <span className="font-mono-label text-[#6a6b6b] text-[10px]">
                            Confianza JEV: {(t.confianza_jev * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-1.5 sm:justify-end">
                      {t.fuentes.map((f, idx) => (
                        <span
                          key={idx}
                          className="font-mono-label px-2 py-0.5 rounded-[6px] bg-[#0f1011] text-[#cacaca] text-[9px] border border-white/10"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                    <div className="rounded-[16px] bg-[#0f1011] p-5 space-y-2 border border-white/5">
                      <span className="font-mono-label text-[#00b3dd] text-[10px] flex items-center gap-1.5">
                        <TrendingUp className="w-3.5 h-3.5" />
                        ¿POR QUÉ FUNCIONA ESTA TENDENCIA?
                      </span>
                      <p className="text-xs text-[#cacaca] leading-relaxed font-light">{t.por_que}</p>
                    </div>

                    <div className="rounded-[16px] bg-gradient-to-br from-[#4b49aa]/20 to-[#0f1011] p-5 space-y-3 border border-[#847dff]/30">
                      <div className="flex items-center justify-between">
                        <span className="font-mono-label text-[#847dff] text-[10px] flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5" />
                          ADAPTACIÓN EDITORIAL 30X
                        </span>
                        <button
                          onClick={() => copyText(t.adaptacion_30x, `t-${t.posicion}`)}
                          className="font-mono-label text-[10px] text-[#f5f5f7] hover:text-[#847dff] flex items-center gap-1 px-2 py-1 rounded-[6px] bg-white/5 hover:bg-white/10 transition"
                        >
                          {copiedId === `t-${t.posicion}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedId === `t-${t.posicion}` ? "Copiado" : "Copiar"}</span>
                        </button>
                      </div>
                      <p className="text-xs text-[#ffffff] font-medium leading-relaxed">{t.adaptacion_30x}</p>
                    </div>
                  </div>

                  {/* References & Evidence Breakdown */}
                  <div className="pt-3 border-t border-white/5 space-y-3">
                    <span className="font-mono-label text-[#6a6b6b] text-[10px] flex items-center gap-1.5">
                      <Link2 className="w-3.5 h-3.5 text-[#847dff]" />
                      EVIDENCIA VERIFICADA & ENLACES DIRECTOS ({t.evidencia?.length || 0})
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                      {(t.referencias_detalladas || t.evidencia.map((u) => ({
                        url: u,
                        titulo: u,
                        fuente: "Fuente Web",
                        autor: "",
                        fecha: "Octubre 2026",
                      }))).map((ref, idx) => (
                        <div
                          key={idx}
                          className="rounded-[12px] bg-[#0f1011] p-3 border border-white/5 hover:border-white/20 transition flex flex-col justify-between space-y-2 group"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono-label text-[9px] text-[#847dff]">{ref.fuente}</span>
                              <span className="font-mono-label text-[9px] text-[#6a6b6b]">{ref.fecha}</span>
                            </div>
                            <h4 className="text-xs text-[#f5f5f7] font-medium line-clamp-2 leading-snug group-hover:text-[#d1c9ff] transition">
                              {ref.titulo}
                            </h4>
                          </div>
                          <div className="flex items-center justify-between pt-1 border-t border-white/5">
                            <span className="text-[10px] text-[#6a6b6b] truncate max-w-[140px]">{ref.autor || "Redacción"}</span>
                            <a
                              href={ref.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[11px] text-[#00b3dd] hover:text-white flex items-center gap-1 transition"
                            >
                              <span>Visitar</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 2: BASE DE CONOCIMIENTO (VECTOR BRAIN & HOOK STUDIO)
           ========================================================================= */}
        {activeTab === "conocimiento" && (
          <div className="space-y-16">
            <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
              <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-[9999px] bg-white/[0.08] border border-white/[0.12] text-[#f5f5f7]">
                <Brain className="w-3.5 h-3.5 text-[#847dff]" />
                <span className="font-mono-label text-[10px] tracking-[0.18em]">
                  VECTOR KNOWLEDGE BASE // HOOK STUDIO
                </span>
              </div>
              <h2 className="font-display-headline text-[48px] sm:text-[68px] text-[#ffffff] tracking-tight leading-[0.94]">
                Cerebro Editorial & <span className="italic font-normal text-[#d1c9ff]">Estilos de Gancho</span>.
              </h2>
              <p className="text-[16px] text-[#9f9fa0] font-light max-w-xl mx-auto leading-relaxed">
                Ingesta de videos y lecciones magistrales con transcripción automática.
                Indexación vectorial semántica en SQLite y extracción de patrones de alta retención guiados por tu solicitud.
              </p>
            </section>

            {/* Ingestion Box */}
            <div className="rounded-[30px] p-8 lg:p-10 bg-[#2e2e2e] space-y-6 border border-white/10 shadow-lg">
              <div className="space-y-1">
                <span className="font-mono-label text-[#847dff] text-[10px]">INGESTAR NUEVO RECURSO DE VIDEO</span>
                <h3 className="text-xl font-bold text-white tracking-tight">
                  Añadir Video o Recurso a la Memoria Vectorial
                </h3>
              </div>

              <form onSubmit={handleIngestKnowledge} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="font-mono-label text-[10px] text-[#cacaca]">URL DE YOUTUBE O RECURSO</label>
                    <input
                      type="text"
                      required
                      value={knwUrl}
                      onChange={(e) => setKnwUrl(e.target.value)}
                      placeholder="https://www.youtube.com/watch?v=..."
                      className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] px-4 py-2.5 text-xs text-white placeholder-[#6a6b6b] focus:outline-none focus:border-[#847dff]"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-mono-label text-[10px] text-[#cacaca]">TÍTULO O REFERENCIA (OPCIONAL)</label>
                    <input
                      type="text"
                      value={knwTitulo}
                      onChange={(e) => setKnwTitulo(e.target.value)}
                      placeholder="Ej: Masterclass de Agentes de IA en Finanzas"
                      className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] px-4 py-2.5 text-xs text-white placeholder-[#6a6b6b] focus:outline-none focus:border-[#847dff]"
                    />
                  </div>
                </div>

                {/* SOLICITUD ESPECÍFICA (Requerimiento central) */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="font-mono-label text-[10px] text-[#847dff] font-semibold">
                      SOLICITUD / INTENCIÓN PARA ESTE ARCHIVO (¿QUÉ DESEAS APRENDER O EXTRAER EXACTAMENTE?)
                    </label>
                    <span className="text-[10px] text-[#6a6b6b]">Guía el análisis del LLM</span>
                  </div>
                  <textarea
                    rows={2}
                    required
                    value={knwSolicitud}
                    onChange={(e) => setKnwSolicitud(e.target.value)}
                    placeholder="Ej: Extraer estilo de gancho contraintuitivo de los primeros 15s y desglosar cómo convence a CEOs de reemplazar RPA sin hablar de tecnicismos..."
                    className="w-full bg-[#0f1011] border border-[#847dff]/40 rounded-[8px] p-3 text-xs text-white placeholder-[#6a6b6b] focus:outline-none focus:border-[#847dff]"
                  />
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={isIngestingKnw}
                    className="px-6 py-2.5 rounded-[8px] bg-[#ffffff] hover:bg-[#cacaca] text-[#000000] text-xs font-semibold tracking-tight flex items-center space-x-2 disabled:opacity-50 transition"
                  >
                    <Video className="w-3.5 h-3.5" />
                    <span>{isIngestingKnw ? "Transcribiendo y Extrayendo..." : "Procesar y Extraer Estilo"}</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </button>
                </div>
              </form>
            </div>

            {/* Semantic Vector Search in Knowledge Base */}
            <div className="rounded-[20px] bg-[#0f1011] p-6 border border-white/10 space-y-4">
              <span className="font-mono-label text-[#00b3dd] text-[10px] flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5" />
                BÚSQUEDA SEMÁNTICA VECTORIAL (SIMILITUD DE COSENO EN RADAR.DB)
              </span>
              <form onSubmit={handleSearchKnowledge} className="flex gap-3">
                <input
                  type="text"
                  value={knwSearchQuery}
                  onChange={(e) => setKnwSearchQuery(e.target.value)}
                  placeholder="Ej: ganchos para directores de operaciones, objeciones de costo, memoria local..."
                  className="flex-1 bg-[#2e2e2e] border border-white/10 rounded-[8px] px-4 py-2 text-xs text-white placeholder-[#6a6b6b] focus:outline-none focus:border-[#00b3dd]"
                />
                <button
                  type="submit"
                  disabled={isSearchingKnw}
                  className="px-4 py-2 rounded-[8px] bg-[#00b3dd] hover:bg-[#00b3dd]/80 text-white text-xs font-semibold tracking-tight transition"
                >
                  {isSearchingKnw ? "Buscando..." : "Buscar en Cerebro"}
                </button>
              </form>

              {knwSearchResults && (
                <div className="space-y-3 pt-3">
                  <span className="font-mono-label text-[10px] text-[#6a6b6b]">
                    COINCIDENCIAS SEMÁNTICAS ENCONTRADAS ({knwSearchResults.length})
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {knwSearchResults.map((res, idx) => (
                      <div key={idx} className="p-4 rounded-[12px] bg-[#2e2e2e] border border-[#00b3dd]/20 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-mono-label text-[10px] text-[#00b3dd]">
                            AFINIDAD: {(res.score * 100).toFixed(1)}%
                          </span>
                          <span className="font-mono-label text-[10px] text-[#6a6b6b]">
                            {res.timestamp_inicio}s - {res.timestamp_fin}s
                          </span>
                        </div>
                        <p className="text-xs text-white font-light leading-relaxed">"{res.texto}"</p>
                        <div className="text-[10px] text-[#847dff] truncate">Fuente: {res.source_titulo}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* List of Knowledge Profiles */}
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <span className="font-mono-label text-[#f5f5f7] text-[11px]">
                  RECURSOS Y ESTILOS DE GANCHO REGISTRADOS ({knowledgeList.length})
                </span>
              </div>

              {knowledgeList.length === 0 ? (
                <div className="p-12 text-center rounded-[24px] bg-[#2e2e2e] border border-white/5 space-y-2">
                  <BookOpen className="w-8 h-8 text-[#6a6b6b] mx-auto" />
                  <p className="text-sm text-white font-medium">Aún no has ingestado videos en el cerebro</p>
                  <p className="text-xs text-[#9f9fa0]">Pega una URL de YouTube arriba para transcribir y extraer su estilo.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-6">
                  {knowledgeList.map((knw) => (
                    <div
                      key={knw.id}
                      className="rounded-[24px] bg-[#2e2e2e] p-6 lg:p-8 space-y-6 border border-white/10"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono-label px-2 py-0.5 rounded-[4px] bg-[#847dff]/10 text-[#847dff] border border-[#847dff]/20 text-[9px]">
                              {knw.tipo.toUpperCase()}
                            </span>
                            <span className="font-mono-label text-[10px] text-[#6a6b6b]">
                              DURACIÓN: {knw.duracion_segundos}s
                            </span>
                          </div>
                          <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight">{knw.titulo}</h3>
                          <p className="text-xs text-[#847dff] font-medium pt-1">
                            🎯 Solicitud: "{knw.solicitud_usuario}"
                          </p>
                        </div>

                        <button
                          onClick={() => handleDeleteKnowledge(knw.id)}
                          className="text-[#6a6b6b] hover:text-red-400 p-2 rounded-[8px] hover:bg-white/5 transition self-start"
                          title="Eliminar recurso"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                      {knw.perfil && (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
                          {/* Hook Analysis */}
                          <div className="p-5 rounded-[16px] bg-[#0f1011] space-y-3 border border-white/5">
                            <div className="flex items-center justify-between">
                              <span className="font-mono-label text-[#847dff] text-[10px] flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5" />
                                ESTILO DE GANCHO (PRIMEROS 15s)
                              </span>
                              <span className="font-mono-label text-[10px] px-2 py-0.5 rounded bg-white/10 text-white">
                                {knw.perfil.hook.tipo_gancho.replace("_", " ")}
                              </span>
                            </div>
                            <blockquote className="text-xs text-white italic border-l-2 border-[#847dff] pl-3 py-1">
                              "{knw.perfil.hook.texto_primeros_15s}"
                            </blockquote>
                            <p className="text-xs text-[#9f9fa0] font-light leading-relaxed">
                              {knw.perfil.hook.analisis_gancho}
                            </p>
                            <div className="pt-2 border-t border-white/5 space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="font-mono-label text-[9px] text-emerald-400">FÓRMULA REUTILIZABLE:</span>
                                <button
                                  onClick={() => copyText(knw.perfil!.hook.plantilla_reutilizable, `hook-${knw.id}`)}
                                  className="text-[10px] text-[#f5f5f7] hover:text-[#847dff] flex items-center gap-1"
                                >
                                  {copiedId === `hook-${knw.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                  <span>{copiedId === `hook-${knw.id}` ? "Copiada" : "Copiar"}</span>
                                </button>
                              </div>
                              <p className="text-xs text-emerald-200 font-mono bg-emerald-950/20 p-2.5 rounded-[6px] border border-emerald-500/20">
                                {knw.perfil.hook.plantilla_reutilizable}
                              </p>
                            </div>
                          </div>

                          {/* Narrative Structure & 30X Templates */}
                          <div className="p-5 rounded-[16px] bg-[#0f1011] space-y-3 border border-white/5">
                            <span className="font-mono-label text-[#00b3dd] text-[10px] flex items-center gap-1.5">
                              <Layers className="w-3.5 h-3.5" />
                              ESTRUCTURA NARRATIVA & TONO
                            </span>
                            <div className="text-xs text-[#cacaca] font-light">
                              Tono: <span className="text-white font-medium">{knw.perfil.tono_y_voz}</span>
                            </div>
                            <div className="space-y-1.5 pt-1">
                              {knw.perfil.estructura_narrativa.map((et, idx) => (
                                <div key={idx} className="flex items-center justify-between text-[11px] p-2 rounded bg-white/[0.02] border border-white/5">
                                  <span className="font-semibold text-white">{et.etapa} ({et.segundos})</span>
                                  <span className="text-[#9f9fa0]">{et.proposito}</span>
                                </div>
                              ))}
                            </div>
                            <div className="pt-2 border-t border-white/5 space-y-1.5">
                              <span className="font-mono-label text-[9px] text-[#dd90d8]">PLANTILLAS LISTAS PARA 30X:</span>
                              {knw.perfil.plantillas_30x.map((pl, idx) => (
                                <p key={idx} className="text-xs text-white font-light bg-[#2e2e2e] p-2 rounded border border-white/5">
                                  {pl}
                                </p>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 3: ENFOQUES DE BÚSQUEDA
           ========================================================================= */}
        {activeTab === "enfoques" && (
          <div className="space-y-12">
            <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
              <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-[9999px] bg-white/[0.08] border border-white/[0.12] text-[#f5f5f7]">
                <SlidersHorizontal className="w-3.5 h-3.5 text-[#00b3dd]" />
                <span className="font-mono-label text-[10px] tracking-[0.18em]">
                  SEARCH FOCUS STUDIO // DYNAMIC TRACKS
                </span>
              </div>
              <h2 className="font-display-headline text-[48px] sm:text-[68px] text-[#ffffff] tracking-tight leading-[0.94]">
                Enfoques de <span className="italic font-normal text-[#00b3dd]">Búsqueda y Monitoreo</span>.
              </h2>
              <p className="text-[16px] text-[#9f9fa0] font-light max-w-xl mx-auto leading-relaxed">
                Configura los tracks temáticos activos: polémicas de OpenAI/Anthropic, benchmarks de razonamiento, desarrollo de CEO y oportunidades de negocio.
              </p>
            </section>

            {/* Create Focus Form */}
            <div className="rounded-[30px] p-8 lg:p-10 bg-[#2e2e2e] space-y-6 border border-white/10 shadow-lg">
              <div className="space-y-1">
                <span className="font-mono-label text-[#00b3dd] text-[10px]">CREAR NUEVO ENFOQUE TEMÁTICO</span>
                <h3 className="text-xl font-bold text-white tracking-tight">
                  Agregar Track de Monitoreo
                </h3>
              </div>

              <form onSubmit={handleAddFocus} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="font-mono-label text-[10px] text-[#cacaca]">NOMBRE DEL ENFOQUE</label>
                    <input
                      type="text"
                      required
                      value={newFocusName}
                      onChange={(e) => setNewFocusName(e.target.value)}
                      placeholder="Ej: Polémicas de OpenAI y Anthropic"
                      className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] px-4 py-2.5 text-xs text-white placeholder-[#6a6b6b] focus:outline-none focus:border-[#00b3dd]"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-mono-label text-[10px] text-[#cacaca]">CATEGORÍA</label>
                    <select
                      value={newFocusCategory}
                      onChange={(e) => setNewFocusCategory(e.target.value)}
                      className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] px-4 py-2.5 text-xs text-white focus:outline-none focus:border-[#00b3dd]"
                    >
                      <option value="polemicas">Polémicas y Gobernanza (Anthropic / OpenAI)</option>
                      <option value="benchmarks">Benchmarks & Carrera de Modelos</option>
                      <option value="ceo_liderazgo">Desarrollo de CEO & Liderazgo en IA</option>
                      <option value="oportunidades_roi">Oportunidades de Negocio & ROI</option>
                      <option value="agentes_operaciones">Agentes Autónomos y RPA</option>
                      <option value="seguridad">Seguridad y Sandboxing</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="font-mono-label text-[10px] text-[#cacaca]">PALABRAS CLAVE (SEPARADAS POR COMA)</label>
                  <input
                    type="text"
                    required
                    value={newFocusKeywords}
                    onChange={(e) => setNewFocusKeywords(e.target.value)}
                    placeholder="OpenAI, Anthropic, Sam Altman, Dario Amodei, safety, copyright, departures"
                    className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] px-4 py-2.5 text-xs text-white placeholder-[#6a6b6b] focus:outline-none focus:border-[#00b3dd]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-mono-label text-[10px] text-[#cacaca]">DESCRIPCIÓN OPERATIVA</label>
                  <input
                    type="text"
                    value={newFocusDesc}
                    onChange={(e) => setNewFocusDesc(e.target.value)}
                    placeholder="Monitorear tensiones entre fundadores, demandas y renuncias de investigadores de seguridad..."
                    className="w-full bg-[#0f1011] border border-white/10 rounded-[8px] px-4 py-2.5 text-xs text-white placeholder-[#6a6b6b] focus:outline-none focus:border-[#00b3dd]"
                  />
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    className="px-6 py-2.5 rounded-[8px] bg-[#ffffff] hover:bg-[#cacaca] text-[#000000] text-xs font-semibold tracking-tight flex items-center space-x-2 transition"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Guardar y Activar Enfoque</span>
                  </button>
                </div>
              </form>
            </div>

            {/* List of Focus Tracks */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {focuses.map((f) => (
                <div
                  key={f.id}
                  className={`rounded-[24px] p-6 lg:p-7 space-y-4 border transition duration-200 ${
                    f.activo
                      ? "bg-[#2e2e2e] border-white/15"
                      : "bg-[#0f1011] border-white/5 opacity-60"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <span className="font-mono-label text-[10px] text-[#00b3dd]">{f.categoria.toUpperCase()}</span>
                      <h3 className="text-lg font-bold text-white tracking-tight">{f.nombre}</h3>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleToggleFocus(f.id)}
                        className={`px-3 py-1 rounded-[9999px] font-mono-label text-[9px] transition ${
                          f.activo ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40" : "bg-white/10 text-[#6a6b6b]"
                        }`}
                      >
                        {f.activo ? "ACTIVO" : "INACTIVO"}
                      </button>
                      <button
                        onClick={() => handleDeleteFocus(f.id)}
                        className="text-[#6a6b6b] hover:text-red-400 p-1"
                        title="Eliminar enfoque"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-[#cacaca] font-light leading-relaxed">{f.descripcion}</p>

                  <div className="flex flex-wrap gap-1.5 pt-2 border-t border-white/5">
                    {f.keywords.map((kw, idx) => (
                      <span
                        key={idx}
                        className="font-mono-label text-[9px] px-2 py-0.5 rounded-[4px] bg-[#0f1011] text-[#9f9fa0] border border-white/10"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 4: PLAYGROUND INTERACTIVO DE JEV (TELEMETRÍA EN TIEMPO REAL)
           ========================================================================= */}
        {activeTab === "playground" && (
          <div className="space-y-16">
            <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
              <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-[9999px] bg-white/[0.08] border border-white/[0.12] text-[#f5f5f7]">
                <Gauge className="w-3.5 h-3.5 text-[#dd90d8]" />
                <span className="font-mono-label text-[10px] tracking-[0.18em]">
                  TYPESAFE SYSTEM 1 // DECISION PLAYGROUND
                </span>
              </div>
              <h2 className="font-display-headline text-[48px] sm:text-[68px] text-[#ffffff] tracking-tight leading-[0.94]">
                Laboratorio de <span className="italic font-normal text-[#dd90d8]">Decisiones JEV</span>.
              </h2>
              <p className="text-[16px] text-[#9f9fa0] font-light max-w-xl mx-auto leading-relaxed">
                Chequeo de noticias en tiempo real. Inspecciona las 5 preguntas que se le hacen a Jev y observa cómo calibra fase, gancho y certidumbre matemática.
              </p>
            </section>

            {/* Playground Input Card */}
            <div className="rounded-[30px] p-8 lg:p-10 bg-[#2e2e2e] space-y-6 border border-white/10 shadow-lg">
              <div className="space-y-1.5">
                <label className="font-mono-label text-[10px] text-[#dd90d8]">ESCRIBE O PEGA CUALQUIER NOTICIA / TITULAR DE IA</label>
                <div className="flex flex-col sm:flex-row gap-3">
                  <input
                    type="text"
                    value={playgroundHeadline}
                    onChange={(e) => setPlaygroundHeadline(e.target.value)}
                    placeholder="Ej: OpenAI lanza modelo o3 superando a Claude 3.5 en programación..."
                    className="flex-1 bg-[#0f1011] border border-white/10 rounded-[8px] px-4 py-3 text-sm text-white placeholder-[#6a6b6b] focus:outline-none focus:border-[#dd90d8]"
                  />
                  <button
                    onClick={handleEvaluatePlayground}
                    disabled={isEvaluatingPlayground}
                    className="px-6 py-3 rounded-[8px] bg-[#ffffff] hover:bg-[#cacaca] text-[#000000] text-xs font-semibold tracking-tight flex items-center justify-center space-x-2 transition disabled:opacity-50"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>{isEvaluatingPlayground ? "Calibrando..." : "Evaluar con JEV"}</span>
                  </button>
                </div>
              </div>

              {/* Quick Preset Buttons */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="font-mono-label text-[9px] text-[#6a6b6b]">EJEMPLOS RÁPIDOS:</span>
                {[
                  "Ruptura Replit y Anthropic: CEO anuncia futuro de empresas auto-conducidas",
                  "Claude 3.5 Sonnet supera a modelos propietarios en benchmarks de razonamiento",
                  "Bancos en Colombia reemplazan RPA por agentes con memoria persistente",
                  "El CEO aumentado: 5 rutinas para delegar análisis estratégico en IA",
                ].map((preset, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setPlaygroundHeadline(preset);
                      setTimeout(handleEvaluatePlayground, 50);
                    }}
                    className="font-mono-label text-[9px] px-2.5 py-1 rounded-[6px] bg-[#0f1011] text-[#cacaca] hover:text-white border border-white/10 hover:border-white/30 transition truncate max-w-[260px]"
                  >
                    {preset}
                  </button>
                ))}
              </div>

              {/* Signal Simulator Sliders */}
              <div className="pt-4 border-t border-white/5 grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono-label text-[10px] text-[#cacaca]">VELOCIDAD DE TRACCIÓN (VISTAS/HORA)</span>
                    <span className="font-mono text-white font-bold">{playgroundVph} v/h</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1000"
                    step="25"
                    value={playgroundVph}
                    onChange={(e) => setPlaygroundVph(parseInt(e.target.value))}
                    className="w-full accent-[#dd90d8]"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono-label text-[10px] text-[#cacaca]">FUENTES CONFIRMADAS</span>
                    <span className="font-mono text-white font-bold">{playgroundSources.length} plataformas</span>
                  </div>
                  <div className="flex gap-2">
                    {["YouTube", "HackerNews", "LinkedIn", "GitHub"].map((src) => {
                      const active = playgroundSources.includes(src);
                      return (
                        <button
                          key={src}
                          onClick={() => {
                            if (active) setPlaygroundSources(playgroundSources.filter((s) => s !== src));
                            else setPlaygroundSources([...playgroundSources, src]);
                          }}
                          className={`font-mono-label text-[9px] px-2.5 py-1 rounded-[6px] border transition ${
                            active ? "bg-[#847dff]/20 text-[#847dff] border-[#847dff]/40" : "bg-[#0f1011] text-[#6a6b6b] border-white/10"
                          }`}
                        >
                          {src}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Playground Results Split View */}
            {playgroundResult && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Column 1: Preguntas a Jev */}
                <div className="rounded-[24px] bg-[#2e2e2e] p-6 lg:p-8 space-y-6 border border-white/10">
                  <div className="flex items-center justify-between">
                    <span className="font-mono-label text-[#847dff] text-[10px] flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5" />
                      ¿QUÉ LE PREGUNTAMOS A JEV? (5 PREGUNTAS CLAVE)
                    </span>
                    <span className="font-mono text-[10px] text-[#6a6b6b]">{playgroundResult.latencia_ms}ms</span>
                  </div>

                  <div className="space-y-3">
                    {playgroundResult.preguntas_jev.map((q, idx) => (
                      <div key={q.id} className="p-3.5 rounded-[12px] bg-[#0f1011] border border-white/5 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-[#847dff]/20 text-[#847dff] font-mono font-bold flex items-center justify-center text-[10px]">
                            {idx + 1}
                          </span>
                          <h4 className="text-xs font-semibold text-white">{q.pregunta}</h4>
                        </div>
                        <p className="text-[11px] text-[#9f9fa0] pl-7 font-light">{q.proposito}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Column 2: Decisiones y Calibración RLCD */}
                <div className="rounded-[24px] bg-[#2e2e2e] p-6 lg:p-8 space-y-6 border border-white/10">
                  <div className="flex items-center justify-between">
                    <span className="font-mono-label text-[#dd90d8] text-[10px] flex items-center gap-1.5">
                      <Gauge className="w-3.5 h-3.5" />
                      DECISIONES & CALIBRACIÓN EN TIEMPO REAL
                    </span>
                    <span className="font-mono-label text-[9px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      {playgroundResult.motor_utilizado}
                    </span>
                  </div>

                  {/* Decision Chips */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-4 rounded-[12px] bg-[#0f1011] space-y-1 border border-white/5">
                      <span className="font-mono-label text-[9px] text-[#6a6b6b]">FASE CALIBRADA</span>
                      <div className="text-base font-bold text-white capitalize">{playgroundResult.decision.fase}</div>
                    </div>
                    <div className="p-4 rounded-[12px] bg-[#0f1011] space-y-1 border border-white/5">
                      <span className="font-mono-label text-[9px] text-[#6a6b6b]">GANCHO ÓPTIMO</span>
                      <div className="text-base font-bold text-[#847dff] capitalize">
                        {playgroundResult.decision.gancho.replace("_", " ")}
                      </div>
                    </div>
                    <div className="p-4 rounded-[12px] bg-[#0f1011] space-y-1 border border-white/5">
                      <span className="font-mono-label text-[9px] text-[#6a6b6b]">FORMATO SUGERIDO</span>
                      <div className="text-base font-bold text-[#00b3dd] capitalize">
                        {playgroundResult.decision.formato.replace("_", " ")}
                      </div>
                    </div>
                    <div className="p-4 rounded-[12px] bg-[#0f1011] space-y-1 border border-white/5">
                      <span className="font-mono-label text-[9px] text-[#6a6b6b]">ENCAJE AUDIENCIA LATAM</span>
                      <div className="text-base font-bold text-emerald-400">
                        {(playgroundResult.decision.encaje_audiencia * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  {/* Confidence Gauge */}
                  <div className="p-5 rounded-[16px] bg-[#0f1011] space-y-3 border border-white/5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono-label text-[10px] text-white">CONFIANZA CALIBRADA DE JEV (RLCD)</span>
                      <span className="font-mono text-sm font-bold text-[#dd90d8]">
                        {(playgroundResult.decision.confianza * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-[#2e2e2e] h-2.5 rounded-full overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-[#847dff] to-[#dd90d8] h-full transition-all duration-300"
                        style={{ width: `${playgroundResult.decision.confianza * 100}%` }}
                      ></div>
                    </div>
                    <p className="text-[11px] text-[#9f9fa0] font-light">
                      La certidumbre pondera cada señal matemática. Si hay pocas fuentes o métricas dudosas, la confianza desciende automáticamente sin adivinar.
                    </p>
                  </div>

                  {/* Final Score Breakdown */}
                  <div className="p-5 rounded-[16px] bg-gradient-to-br from-[#847dff]/20 to-[#0f1011] space-y-2 border border-[#847dff]/30">
                    <div className="flex items-center justify-between">
                      <span className="font-mono-label text-[10px] text-[#d1c9ff]">RADAR 30X SCORE FINAL</span>
                      <span className="text-2xl font-extrabold text-white font-mono">{playgroundResult.score_final}</span>
                    </div>
                    <div className="text-[11px] text-[#cacaca] font-light">
                      Crecimiento estimado: <span className="text-emerald-400 font-semibold">{playgroundResult.crecimiento_label}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer — Quiet Luxury */}
      <footer className="border-t border-white/5 py-12 px-6 lg:px-12 bg-[#090a0b] mt-24">
        <div className="max-w-[1200px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#6a6b6b]">
          <div className="flex items-center space-x-3">
            <span className="font-mono-label text-white">30X RADAR</span>
            <span>—</span>
            <span>Cerebro de Inteligencia Editorial & Base Vectorial</span>
          </div>
          <div className="font-mono-label text-[10px]">
            100% PUBLIC COMPLIANT // TYPESAFE AI CALIBRATED // 2026
          </div>
        </div>
      </footer>
    </div>
  );
}
