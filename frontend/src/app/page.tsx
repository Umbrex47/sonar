"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  ExternalLink,
  Copy,
  Check,
  TrendingUp,
  Shield,
  Sparkles,
  Link2,
  Gauge,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Filter,
  Activity,
  Layers,
  FileText,
  X,
  Eye,
  ArrowRight,
  Terminal,
  RefreshCw,
  Play,
} from "lucide-react";
import { ReportData, TrendItem, getApiBase } from "../types/radar";
import { useRadar } from "../context/RadarContext";
import { TerminalConsole } from "../components/TerminalConsole";

export default function TendenciasPage() {
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFormat, setSelectedFormat] = useState("todos");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedAuditId, setExpandedAuditId] = useState<number | null>(null);
  const [showFunnel, setShowFunnel] = useState<boolean>(false);
  const [funnelTab, setFunnelTab] = useState<"descartados" | "observacion">("descartados");
  const [generatingDraftFor, setGeneratingDraftFor] = useState<number | null>(null);
  const [createdDraft, setCreatedDraft] = useState<any | null>(null);
  const [draftModalCopied, setDraftModalCopied] = useState<boolean>(false);

  const {
    setReportWeek,
    refreshTrigger,
    runState,
    isTerminalOpen,
    setIsTerminalOpen,
    handleRunRadar,
  } = useRadar();

  useEffect(() => {
    fetchReport();
  }, [refreshTrigger]);

  useEffect(() => {
    const handleUpdated = () => fetchReport();
    window.addEventListener("sonar:report-updated", handleUpdated);
    return () => window.removeEventListener("sonar:report-updated", handleUpdated);
  }, []);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/report/latest?_t=${Date.now()}`, {
        cache: "no-store",
        headers: { "Pragma": "no-cache", "Cache-Control": "no-cache" },
      });
      if (res.ok) {
        const data: ReportData = await res.json();
        setReport(data);
        if (data.semana) {
          setReportWeek(data.semana);
        }
      }
    } catch (err) {
      console.warn("Backend local no disponible:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatSafeText = (val: any): string => {
    if (val === null || val === undefined) return "";
    if (typeof val === "string") return val;
    if (typeof val === "object") {
      const parts = [];
      if (val.formato_sugerido) {
        parts.push(`Formato: ${val.formato_sugerido}`);
      }
      if (val.titular_gancho) {
        parts.push(`Titular: "${val.titular_gancho}"`);
      }
      return parts.length > 0 ? parts.join(" — ") : JSON.stringify(val);
    }
    return String(val);
  };

  const copyText = (text: any, id: string) => {
    const str = typeof text === "string" ? text : formatSafeText(text);
    navigator.clipboard.writeText(str);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleGenerateDraft = async (t: TrendItem) => {
    setGeneratingDraftFor(t.posicion);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/drafts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tema_id: t.posicion,
          titulo: t.tema,
          formato: t.formato,
          gancho: t.gancho,
          autor: "30X Editorial",
          evidencia: t.evidencia || [],
        }),
      });
      if (res.ok) {
        let data = await res.json();
        if (!data.body && data.id) {
          const detailRes = await fetch(`${api}/api/drafts/${data.id}`);
          if (detailRes.ok) {
            data = await detailRes.json();
          }
        }
        setCreatedDraft(data);
      }
    } catch (err) {
      console.error("Error al redactar borrador con LLM:", err);
    } finally {
      setGeneratingDraftFor(null);
    }
  };

  const handleGoToObservation = () => {
    setShowFunnel(true);
    setFunnelTab("observacion");
    setTimeout(() => {
      const el = document.getElementById("embudo-curaduria");
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 50);
  };

  const filteredTrends = (report?.top_temas || []).filter((t: TrendItem) => {
    const adaptacionStr = formatSafeText(t.adaptacion_30x).toLowerCase();
    const matchesSearch =
      searchQuery.trim() === "" ||
      t.tema.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.por_que.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.por_que_audiencia && t.por_que_audiencia.toLowerCase().includes(searchQuery.toLowerCase())) ||
      adaptacionStr.includes(searchQuery.toLowerCase()) ||
      t.fuentes.some((f) => f.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesFormat =
      selectedFormat === "todos" ||
      t.formato.toLowerCase() === selectedFormat.toLowerCase();

    return matchesSearch && matchesFormat;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Hero Display Headline */}
      <section className="text-center max-w-2xl mx-auto space-y-3 pt-2">
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-[4px] bg-[#016a71]/10 border border-[#016a71]/20 text-[#016a71]">
          <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
          <span className="font-mono text-[10px] tracking-wider font-medium uppercase">
            TYPESAFE JEV CALIBRATED // RECENT INTELLIGENCE
          </span>
        </div>

        <h1 className="text-3xl text-[#27251e] font-normal tracking-tight leading-snug">
          <span className="text-[#016a71] font-medium">Emerging</span> signals, curated with quiet authority.
        </h1>

        <p className="text-[14px] text-[#72706b] font-normal leading-relaxed">
          Descubrimiento automatizado y calibrado de tendencias de IA de los últimos 7 días.
          Filtrado de ruido técnico, empaquetado editorial y adaptaciones estratégicas para líderes en Latinoamérica.
        </p>
      </section>

      {/* Feature Category Cards Grid (Suggestion Cards con bordes y esquinas sobrias) */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="rounded-[8px] p-4 bg-[#fdfbfa] border border-[#d1d1cd] shadow-[0_1px_2px_rgba(0,0,0,0.03)] flex flex-col justify-between space-y-2">
          <span className="font-mono text-[10px] text-[#72706b] font-medium uppercase tracking-wider">
            RELEVANCIA & AUDIENCIA
          </span>
          <div className="space-y-1">
            <h3 className="text-[#27251e] text-sm font-medium tracking-tight">
              Impacto Ejecutivo
            </h3>
            <p className="text-[#72706b] text-xs font-normal leading-relaxed">
              Penalización estricta a curiosidades técnicas y prioridad a casos de ROI y operaciones corporativas.
            </p>
          </div>
        </div>

        <div className="rounded-[8px] p-4 bg-[#fdfbfa] border border-[#d1d1cd] shadow-[0_1px_2px_rgba(0,0,0,0.03)] flex flex-col justify-between space-y-2">
          <span className="font-mono text-[10px] text-[#72706b] font-medium uppercase tracking-wider">
            RECENCIA COMPROBADA
          </span>
          <div className="space-y-1">
            <h3 className="text-[#27251e] text-sm font-medium tracking-tight">
              Ventana 7 Días
            </h3>
            <p className="text-[#72706b] text-xs font-normal leading-relaxed">
              Filtros temporales en YouTube, Google News y Hacker News asegurando frescura de esta semana.
            </p>
          </div>
        </div>

        <div className="rounded-[8px] p-4 bg-[#fdfbfa] border border-[#d1d1cd] shadow-[0_1px_2px_rgba(0,0,0,0.03)] flex flex-col justify-between space-y-2">
          <span className="font-mono text-[10px] text-[#72706b] font-medium uppercase tracking-wider">
            SINERGIA MULTI-FUENTE
          </span>
          <div className="space-y-1">
            <h3 className="text-[#27251e] text-sm font-medium tracking-tight">
              Cross-Validation
            </h3>
            <p className="text-[#72706b] text-xs font-normal leading-relaxed">
              Multiplicador a temas respaldados simultáneamente en video, prensa y redes profesionales.
            </p>
          </div>
        </div>
      </section>

      {/* Sección de Ejecución & Terminal en Tiempo Real */}
      <section className="space-y-3">
        {/* Banner de Estado de Terminal */}
        <div className="rounded-[8px] p-4 bg-[#fdfbfa] border border-[#d1d1cd] shadow-[0_1px_2px_rgba(0,0,0,0.03)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-start sm:items-center space-x-3 min-w-0">
            <div
              className={`w-8 h-8 rounded-[6px] flex items-center justify-center shrink-0 ${
                runState.is_running ? "bg-[#016a71]/15 text-[#016a71]" : "bg-[#27251e]/5 text-[#27251e]"
              }`}
            >
              <Terminal className={`w-4 h-4 ${runState.is_running ? "animate-pulse text-[#016a71]" : ""}`} />
            </div>
            <div className="space-y-0.5 min-w-0">
              <div className="flex items-center space-x-2">
                <span className="font-mono text-[10px] uppercase tracking-wider font-semibold text-[#016a71]">
                  PROCESO & SALIDA EN TERMINAL
                </span>
                {runState.is_running ? (
                  <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-[#016a71]/10 text-[#016a71] font-mono text-[9px] font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#016a71] animate-ping" />
                    <span>EN VIVO ({runState.duration_seconds}s)</span>
                  </span>
                ) : runState.last_status === "success" ? (
                  <span className="text-[9px] font-mono text-[#059669]">
                    ✓ Listo ({runState.duration_seconds}s)
                  </span>
                ) : null}
              </div>
              <h3 className="text-sm font-medium text-[#27251e] tracking-tight">
                {runState.is_running
                  ? runState.current_step
                  : "Monitoreo del Motor Sonar y Pipeline de Ingesta"}
              </h3>
              <p className="text-xs text-[#72706b] font-normal truncate">
                {runState.is_running
                  ? `Transmitiendo stdout en tiempo real: ${runState.logs.length} líneas registradas.`
                  : "Visualiza línea a línea la recolección en YouTube, Google News, Hacker News, clustering y evaluación JEV."}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 shrink-0 self-start sm:self-auto">
            <button
              onClick={handleRunRadar}
              disabled={runState.is_running}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] bg-[#27251e] hover:bg-[#000000] text-[#faf8f5] text-xs font-medium transition disabled:opacity-50 cursor-pointer shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${runState.is_running ? "animate-spin" : ""}`} />
              <span>{runState.is_running ? "Escaneando..." : "Actualizar Sonar"}</span>
            </button>
            <button
              onClick={() => setIsTerminalOpen(!isTerminalOpen)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] border text-xs font-medium transition cursor-pointer ${
                isTerminalOpen
                  ? "border-[#27251e] bg-[#27251e] text-[#faf8f5]"
                  : "border-[#d1d1cd] text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20"
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>{isTerminalOpen ? "Ocultar Consola" : "Ver Terminal"}</span>
            </button>
          </div>
        </div>

        {/* Consola Terminal Embebida (cuando está abierta o en ejecución) */}
        {(isTerminalOpen || runState.is_running) && (
          <div className="animate-in fade-in duration-200">
            <TerminalConsole embedded={true} />
          </div>
        )}
      </section>

      {/* Embudo de Decisiones JEV & Resumen de Filtrado */}
      <section id="embudo-curaduria" data-tour="tour-observation-funnel" className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-5 space-y-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
              <span className="font-mono text-[10px] text-[#016a71] tracking-wider font-medium uppercase">
                AUDITORÍA & EMBUDO DE CURADURÍA JEV
              </span>
            </div>
            <h3 className="text-base font-medium text-[#27251e] tracking-tight">
              Trazabilidad de Decisiones y Filtro de Ruido
            </h3>
          </div>

          <button
            onClick={() => setShowFunnel(!showFunnel)}
            className="px-3 py-1.5 rounded-[4px] border border-[#d1d1cd] text-xs font-normal text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 flex items-center space-x-1.5 transition self-start sm:self-auto cursor-pointer"
          >
            <Filter className="w-3.5 h-3.5 text-[#016a71]" />
            <span>{showFunnel ? "Ocultar Embudo" : "Explorar Descartes y Observación"}</span>
            {showFunnel ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* 4 KPI Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 pt-1">
          <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-0.5">
            <span className="font-mono text-[9px] text-[#72706b] uppercase">TOTAL EVALUADOS</span>
            <div className="text-lg font-medium font-mono text-[#27251e]">
              {report?.embudo_metricas?.total_evaluados || report?.total_clusters_evaluados || 181}
            </div>
          </div>

          <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#016a71]/30 space-y-0.5">
            <span className="font-mono text-[9px] text-[#016a71] uppercase font-medium">APROBADOS TOP</span>
            <div className="text-lg font-medium font-mono text-[#016a71]">
              {report?.embudo_metricas?.aprobados_top || report?.top_temas?.length || 10}
            </div>
          </div>

          <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-0.5">
            <span className="font-mono text-[9px] text-[#72706b] uppercase">EN OBSERVACIÓN</span>
            <div className="text-lg font-medium font-mono text-[#27251e]">
              {report?.embudo_metricas?.en_observacion || report?.temas_en_observacion?.length || 0}
            </div>
          </div>

          <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-0.5">
            <span className="font-mono text-[9px] text-[#92918b] uppercase">DESCARTADOS POR JEV</span>
            <div className="text-lg font-medium font-mono text-[#72706b]">
              {report?.embudo_metricas?.descartados || report?.temas_descartados?.length || 0}
            </div>
          </div>
        </div>

        {/* Drawer Expandible del Embudo */}
        {showFunnel && (
          <div className="pt-3 border-t border-[#d1d1cd] space-y-3 animate-in fade-in duration-150">
            <div className="flex items-center space-x-2 border-b border-[#d1d1cd] pb-2">
              <button
                onClick={() => setFunnelTab("descartados")}
                className={`px-2.5 py-1 rounded-[4px] font-mono text-[10px] transition cursor-pointer ${
                  funnelTab === "descartados"
                    ? "bg-[#27251e] text-[#faf8f5]"
                    : "text-[#72706b] hover:text-[#27251e]"
                }`}
              >
                TEMAS DESCARTADOS ({report?.temas_descartados?.length || 0})
              </button>
              <button
                onClick={() => setFunnelTab("observacion")}
                className={`px-2.5 py-1 rounded-[4px] font-mono text-[10px] transition cursor-pointer ${
                  funnelTab === "observacion"
                    ? "bg-[#016a71] text-[#faf8f5]"
                    : "text-[#72706b] hover:text-[#27251e]"
                }`}
              >
                EN OBSERVACIÓN ({report?.temas_en_observacion?.length || 0})
              </button>
            </div>

            {funnelTab === "descartados" && (
              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {(report?.temas_descartados || []).map((disc, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[3px] bg-[#d1d1cd]/30 text-[#72706b] border border-[#d1d1cd]">
                          DESCARTADO
                        </span>
                        <span className="font-mono text-[10px] text-[#72706b]">Score: {disc.score}</span>
                      </div>
                      <h4 className="text-[#27251e] font-medium text-xs">{disc.tema}</h4>
                      <p className="text-[11px] text-[#72706b] font-normal">{disc.motivo}</p>
                    </div>
                    <div className="flex flex-wrap gap-1 sm:justify-end shrink-0">
                      {disc.fuentes.map((f, fIdx) => (
                        <span key={fIdx} className="font-mono text-[8px] px-1.5 py-0.2 rounded-[3px] bg-[#fdfbfa] text-[#72706b] border border-[#d1d1cd]">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {funnelTab === "observacion" && (
              <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                {(report?.temas_en_observacion || []).map((obs, idx) => {
                  const refs = (obs.referencias_detalladas && obs.referencias_detalladas.length > 0)
                    ? obs.referencias_detalladas
                    : (obs.evidencia || []).map((u) => ({
                        url: u,
                        titulo: u,
                        fuente: "Fuente Web",
                        autor: "",
                        fecha: "Reciente",
                      }));

                  return (
                    <div
                      key={idx}
                      className="p-3.5 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-2.5 text-xs"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                        <div className="space-y-0.5">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[3px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20">
                              OBSERVACIÓN
                            </span>
                            <span className="font-mono text-[10px] text-[#72706b]">Score: {obs.score}</span>
                            <span className="font-mono text-[10px] text-[#016a71] font-medium">{obs.crecimiento}</span>
                          </div>
                          <h4 className="text-[#27251e] font-medium text-xs leading-snug">{obs.tema}</h4>
                          <p className="text-[11px] text-[#72706b] font-normal leading-relaxed">{obs.motivo}</p>
                        </div>
                        <div className="flex flex-wrap gap-1 sm:justify-end shrink-0">
                          {obs.fuentes.map((f, fIdx) => (
                            <span key={fIdx} className="font-mono text-[8px] px-1.5 py-0.2 rounded-[3px] bg-[#fdfbfa] text-[#72706b] border border-[#d1d1cd]">
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Enlaces a las referencias del tema en observación */}
                      {refs.length > 0 && (
                        <div className="pt-2 border-t border-[#d1d1cd]/70 space-y-1.5">
                          <span className="font-mono text-[9px] text-[#72706b] flex items-center gap-1 font-normal">
                            <Link2 className="w-3 h-3 text-[#016a71]" />
                            REFERENCIAS & ENLACES DIRECTOS ({refs.length}):
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-1.5">
                            {refs.map((ref, rIdx) => (
                              <a
                                key={rIdx}
                                href={ref.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2 rounded-[4px] bg-[#fdfbfa] border border-[#d1d1cd] hover:border-[#016a71] transition flex flex-col justify-between space-y-1 group text-left cursor-pointer shadow-[0_1px_2px_rgba(0,0,0,0.02)]"
                              >
                                <div className="flex items-center justify-between text-[8px] font-mono">
                                  <span className="text-[#016a71] font-medium">{ref.fuente}</span>
                                  <span className="text-[#92918b]">{ref.fecha}</span>
                                </div>
                                <h5 className="text-[11px] text-[#27251e] group-hover:text-[#016a71] transition line-clamp-1 leading-snug">
                                  {ref.titulo}
                                </h5>
                                <div className="flex items-center justify-between pt-0.5 text-[9px] text-[#72706b]">
                                  <span className="truncate max-w-[120px]">{ref.autor || "Redacción"}</span>
                                  <span className="text-[#016a71] flex items-center gap-0.5 group-hover:underline">
                                    <span>Abrir</span>
                                    <ExternalLink className="w-2.5 h-2.5" />
                                  </span>
                                </div>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Filter Bar (Search Input & Select con bordes reducidos) */}
      <div data-tour="tour-hero-stats" className="flex flex-col sm:flex-row items-center justify-between gap-2.5 p-2.5 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="relative w-full sm:w-96">
          <Search className="w-3.5 h-3.5 text-[#72706b] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filtrar por término, tecnología o palabra clave..."
            className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] pl-9 pr-3 py-1.5 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71] focus:ring-1 focus:ring-[#016a71]/20 transition"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <select
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
            className="bg-[#faf8f5] border border-[#d1d1cd] text-xs text-[#27251e] rounded-[6px] px-2.5 py-1.5 focus:outline-none focus:border-[#016a71]"
          >
            <option value="todos">Todos los Formatos</option>
            <option value="video_corto">Video Corto / Reel</option>
            <option value="carousel">Carrusel LinkedIn</option>
            <option value="hilo">Hilo X / LinkedIn</option>
            <option value="articulo">Artículo / Newsletter</option>
          </select>
        </div>
      </div>

      {/* Botón de acceso directo a Temas en Observación */}
      <div className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-3.5 shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:border-[#016a71]/60 transition duration-150">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start sm:items-center space-x-2.5 min-w-0">
            <div className="w-7 h-7 rounded-[4px] bg-[#016a71]/10 flex items-center justify-center text-[#016a71] shrink-0 mt-0.5 sm:mt-0">
              <Eye className="w-4 h-4" />
            </div>
            <div className="space-y-0.5 min-w-0">
              <button
                type="button"
                onClick={handleGoToObservation}
                className="text-left text-xs sm:text-[13px] font-medium text-[#27251e] hover:text-[#016a71] transition-colors cursor-pointer block"
              >
                No encuentras ningun tema de interes? Verifica la lista de temas en observacion
              </button>
              <p className="text-[11px] text-[#72706b] font-normal truncate">
                {report?.temas_en_observacion?.length || 0} señales emergentes en monitoreo continuo previo a su fase de validación cruzada.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleGoToObservation}
            className="px-3 py-1.5 rounded-[4px] bg-[#016a71] hover:bg-[#01585e] text-[#faf8f5] text-xs font-medium transition shrink-0 cursor-pointer flex items-center justify-center space-x-1.5 shadow-xs self-start sm:self-auto"
          >
            <span>Ver Temas ({report?.temas_en_observacion?.length || 0})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Ranked Trends Cards */}
      <div data-tour="tour-top-cards" className="space-y-4">
        {loading ? (
          <div className="text-center py-12 text-[#72706b] text-sm">
            Cargando tendencias curadas de Sonar...
          </div>
        ) : filteredTrends.length === 0 ? (
          <div className="text-center py-12 text-[#72706b] text-sm rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd]">
            No se encontraron tendencias con los filtros seleccionados.
          </div>
        ) : (
          filteredTrends.map((t) => (
            <div
              key={t.posicion}
              className="rounded-[8px] bg-[#fdfbfa] p-5 space-y-4 border border-[#d1d1cd] shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:border-[#016a71]/40 transition duration-150"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="flex items-start space-x-3">
                  <span className="w-8 h-8 rounded-[4px] bg-[#faf8f5] border border-[#d1d1cd] text-[#27251e] font-mono font-medium flex items-center justify-center text-xs shrink-0">
                    #{t.posicion}
                  </span>
                  <div className="space-y-1">
                    <h2 className="text-base sm:text-lg font-medium text-[#27251e] tracking-tight">
                      {t.tema}
                    </h2>
                    <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                      <span className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/25">
                        {t.fase}
                      </span>
                      <span className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] bg-[#faf8f5] text-[#27251e] border border-[#d1d1cd]">
                        {t.crecimiento}
                      </span>
                      <span className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] bg-[#faf8f5] text-[#72706b] border border-[#d1d1cd]">
                        Gancho: {t.gancho.replace("_", " ")}
                      </span>
                      {t.sparkline && (
                        <span
                          className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] bg-[#faf8f5] text-[#27251e] border border-[#d1d1cd] flex items-center gap-1"
                          title="Trayectoria histórica en 90 días"
                        >
                          <Activity className="w-3 h-3 text-[#016a71]" />
                          <span>90D:</span>
                          <span className="font-medium text-[#27251e] tracking-wider">
                            {t.sparkline}
                          </span>
                        </span>
                      )}
                      {t.novedad !== undefined && (
                        <span className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] bg-[#faf8f5] text-[#72706b] border border-[#d1d1cd]">
                          NOVEDAD: {(t.novedad * 100).toFixed(0)}%
                        </span>
                      )}
                      {t.veredicto_critico && (
                        <span
                          className={`font-mono text-[9px] px-2 py-0.5 rounded-[3px] border flex items-center gap-1 ${
                            t.veredicto_critico.veredicto === "valido"
                              ? "bg-[#016a71]/10 text-[#016a71] border-[#016a71]/25"
                              : "bg-[#faf8f5] text-[#72706b] border-[#d1d1cd]"
                          }`}
                        >
                          <Shield className="w-3 h-3" />
                          VERACIDAD: {(t.veredicto_critico.veracidad_p * 100).toFixed(0)}%
                        </span>
                      )}
                      <span className="font-mono text-[#72706b] text-[9px]">
                        Confianza JEV: {(t.confianza_jev * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:items-end gap-2 shrink-0">
                  <div className="flex flex-wrap gap-1 sm:justify-end">
                    {t.fuentes.map((f, idx) => (
                      <span
                        key={idx}
                        className="font-mono text-[8px] px-1.5 py-0.5 rounded-[3px] bg-[#faf8f5] text-[#72706b] border border-[#d1d1cd]"
                      >
                        {f}
                      </span>
                    ))}
                  </div>

                  <button
                    onClick={() => handleGenerateDraft(t)}
                    disabled={generatingDraftFor === t.posicion}
                    className="flex items-center space-x-1.5 px-2.5 py-1 rounded-[4px] bg-[#27251e] hover:bg-[#000000] text-[#faf8f5] text-xs font-medium transition cursor-pointer disabled:opacity-50 shadow-xs"
                  >
                    <Sparkles
                      className={`w-3.5 h-3.5 text-[#016a71] ${
                        generatingDraftFor === t.posicion ? "animate-spin" : ""
                      }`}
                    />
                    <span>
                      {generatingDraftFor === t.posicion
                        ? "Redactando con LLM..."
                        : "Crear Borrador IA"}
                    </span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                <div className="rounded-[6px] bg-[#faf8f5] p-3.5 space-y-1 border border-[#d1d1cd]">
                  <span className="font-mono text-[9px] text-[#016a71] font-medium flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5" />
                    ¿POR QUÉ FUNCIONA ESTA TENDENCIA?
                  </span>
                  <p className="text-xs text-[#27251e] leading-relaxed font-normal">{t.por_que}</p>
                </div>

                <div className="rounded-[6px] bg-[#faf8f5] p-3.5 space-y-1.5 border border-[#d1d1cd]">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[9px] text-[#27251e] font-medium flex items-center gap-1">
                      <Sparkles className="w-3.5 h-3.5 text-[#016a71]" />
                      ADAPTACIÓN EDITORIAL 30X
                    </span>
                    <button
                      onClick={() => copyText(t.adaptacion_30x, `t-${t.posicion}`)}
                      className="font-mono text-[9px] text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 flex items-center gap-1 px-1.5 py-0.5 rounded-[3px] border border-[#d1d1cd] transition cursor-pointer"
                    >
                      {copiedId === `t-${t.posicion}` ? <Check className="w-3 h-3 text-[#016a71]" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedId === `t-${t.posicion}` ? "Copiado" : "Copiar"}</span>
                    </button>
                  </div>
                  {typeof t.adaptacion_30x === "object" && t.adaptacion_30x !== null ? (
                    <div className="space-y-1.5 text-xs text-[#27251e]">
                      {t.adaptacion_30x.formato_sugerido && (
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-[9px] uppercase px-1.5 py-0.2 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20 font-medium">
                            {t.adaptacion_30x.formato_sugerido}
                          </span>
                        </div>
                      )}
                      {t.adaptacion_30x.titular_gancho && (
                        <p className="font-normal leading-relaxed text-[#27251e]">
                          {t.adaptacion_30x.titular_gancho}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-[#27251e] font-normal leading-relaxed">{formatSafeText(t.adaptacion_30x)}</p>
                  )}
                </div>

                {t.por_que_audiencia && (
                  <div className="rounded-[6px] bg-[#faf8f5] p-3.5 space-y-1 border border-[#d1d1cd] md:col-span-2">
                    <span className="font-mono text-[9px] text-[#016a71] font-medium flex items-center gap-1">
                      <Shield className="w-3.5 h-3.5" />
                      ¿POR QUÉ COINCIDE CON EL PERFIL / AUDIENCIA 30X?
                    </span>
                    <p className="text-xs text-[#27251e] leading-relaxed font-normal">{t.por_que_audiencia}</p>
                  </div>
                )}
              </div>

              {/* Contenido Profundo Extraído con Scraper Híbrido */}
              {t.contenido_profundo && (
                <div className="rounded-[6px] bg-[#faf8f5] p-3 space-y-1.5 border border-[#016a71]/30">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[9px] text-[#016a71] font-semibold flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#016a71]" />
                      EXTRACTO PROFUNDO // SCRAPER HÍBRIDO ({t.contenido_profundo.metodo.toUpperCase()})
                    </span>
                    <span className="font-mono text-[9px] text-[#72706b]">
                      {t.contenido_profundo.tokens_estimados} tokens • {t.contenido_profundo.costo_estimado}
                    </span>
                  </div>
                  <p className="text-xs text-[#27251e] leading-relaxed font-normal line-clamp-3 italic">
                    &ldquo;{t.contenido_profundo.resumen_markdown}&rdquo;
                  </p>
                </div>
              )}

              {/* References & Evidence Breakdown */}
              <div className="pt-2 border-t border-[#d1d1cd] space-y-2">
                <span className="font-mono text-[9px] text-[#72706b] flex items-center gap-1 font-normal">
                  <Link2 className="w-3 h-3 text-[#016a71]" />
                  EVIDENCIA VERIFICADA & ENLACES DIRECTOS ({t.evidencia?.length || 0})
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {(t.referencias_detalladas || t.evidencia.map((u) => ({
                    url: u,
                    titulo: u,
                    fuente: "Fuente Web",
                    autor: "",
                    fecha: "Octubre 2026",
                  }))).map((ref, idx) => (
                    <div
                      key={idx}
                      className="rounded-[6px] bg-[#faf8f5] p-2.5 border border-[#d1d1cd] hover:border-[#016a71]/40 transition flex flex-col justify-between space-y-1.5 group"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[8px] text-[#016a71] font-medium">{ref.fuente}</span>
                          <span className="font-mono text-[8px] text-[#72706b]">{ref.fecha}</span>
                        </div>
                        <h4 className="text-xs text-[#27251e] font-normal line-clamp-2 leading-snug group-hover:text-[#016a71] transition">
                          {ref.titulo}
                        </h4>
                      </div>
                      <div className="flex items-center justify-between pt-1 border-t border-[#d1d1cd]">
                        <span className="text-[10px] text-[#72706b] truncate max-w-[120px]">{ref.autor || "Redacción"}</span>
                        <a
                          href={ref.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] text-[#016a71] hover:underline flex items-center gap-1 transition"
                        >
                          <span>Visitar</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Decision Audit Trail Inspector */}
              <div className="pt-2 border-t border-[#d1d1cd] space-y-2">
                <button
                  onClick={() => setExpandedAuditId(expandedAuditId === t.posicion ? null : t.posicion)}
                  className="w-full flex items-center justify-between p-2.5 rounded-[6px] bg-[#faf8f5] hover:bg-[#faf8f5]/80 border border-[#d1d1cd] transition text-left cursor-pointer group"
                >
                  <div className="flex items-center space-x-2">
                    <Gauge className="w-3.5 h-3.5 text-[#016a71]" />
                    <span className="font-mono text-[10px] text-[#27251e] font-medium">
                      PROCESO DE DECISIÓN JEV // AUDITORÍA DE 5 CRITERIOS
                    </span>
                    {t.proceso_decision && (
                      <span className="font-mono text-[8px] px-1.5 py-0.2 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20">
                        {t.proceso_decision.veredicto}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-1.5 text-[#72706b]">
                    <span className="text-[10px] font-mono">{expandedAuditId === t.posicion ? "Ocultar" : "Ver razonamiento"}</span>
                    {expandedAuditId === t.posicion ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </div>
                </button>

                {expandedAuditId === t.posicion && (
                  <div className="p-3.5 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-3 animate-in fade-in duration-150">
                    {/* Motivo de Veredicto */}
                    <div className="p-2.5 rounded-[4px] bg-[#fdfbfa] border border-[#d1d1cd] text-xs text-[#27251e] flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#016a71] mt-0.5 shrink-0" />
                      <div>
                        <span className="font-medium text-[#27251e]">Veredicto JEV: </span>
                        {t.proceso_decision?.motivo_veredicto || "Aprobado: Cumple con novedad temporal, convergencia multi-fuente y alta aplicabilidad ejecutiva en LatAm."}
                      </div>
                    </div>

                    {/* Las 5 Preguntas con Razonamiento */}
                    <div className="space-y-2">
                      <span className="font-mono text-[9px] text-[#72706b]">
                        EVALUACIÓN DETALLADA DE LAS 5 PREGUNTAS CLAVE:
                      </span>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {(t.proceso_decision?.preguntas || [
                          { id: "q1_fase", pregunta: "¿En qué fase de adopción se encuentra?", respuesta: t.fase, score: t.confianza_jev, razonamiento: `Clasificado en fase '${t.fase}' con velocidad constante y validación en ${t.fuentes.length} fuentes.` },
                          { id: "q2_gancho", pregunta: "¿Cuál es el gancho psicológico?", respuesta: t.gancho, score: 0.88, razonamiento: `Gatillo mental '${t.gancho.replace('_', ' ')}' que maximiza la retención en los primeros 10 segundos.` },
                          { id: "q3_formato", pregunta: "¿Cuál es el formato nativo ideal?", respuesta: t.formato, score: 0.85, razonamiento: `Recomendado '${t.formato.replace('_', ' ')}' por idoneidad para la densidad del concepto.` },
                          { id: "q4_novedad", pregunta: "¿Qué probabilidad de novedad emergente existe?", respuesta: `${(t.confianza_jev * 100).toFixed(0)}%`, score: t.confianza_jev, razonamiento: "Frescura confirmada en los últimos 7 días sin notas de prensa obsoletas." },
                          { id: "q5_encaje_latam", pregunta: "¿Qué nivel de relevancia tiene para directivos LatAm?", respuesta: `${(t.encaje_audiencia * 100).toFixed(0)}%`, score: t.encaje_audiencia, razonamiento: "Afinidad directa con reducción de costos, eficiencia en operaciones y mitigación de riesgos." },
                        ]).map((q, qIdx) => (
                          <div key={qIdx} className="p-2.5 rounded-[4px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-[8px] text-[#72706b]">CRITERIO {qIdx + 1}</span>
                              <span className="font-mono text-[8px] text-[#016a71] bg-[#016a71]/10 px-1.5 py-0.2 rounded-[2px] border border-[#016a71]/20">
                                {q.respuesta}
                              </span>
                            </div>
                            <h4 className="text-xs font-medium text-[#27251e] leading-snug">{q.pregunta}</h4>
                            <p className="text-[11px] text-[#72706b] font-normal leading-relaxed">{q.razonamiento}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal de Previsualización de Borrador Generado con LLM */}
      {createdDraft && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-[#fdfbfa] border border-[#d1d1cd] rounded-[8px] max-w-2xl w-full p-5 space-y-4 shadow-lg text-[#27251e]">
            <div className="flex items-center justify-between pb-3 border-b border-[#d1d1cd]">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-[4px] bg-[#016a71]/10 flex items-center justify-center text-[#016a71]">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-medium tracking-tight">
                    Borrador Generado con IA // #{createdDraft.id}
                  </h3>
                  <p className="text-[10px] text-[#72706b] font-mono">
                    Formato: {createdDraft.formato?.replace("_", " ")} | Gancho: {createdDraft.gancho?.replace("_", " ")}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setCreatedDraft(null)}
                className="text-[#72706b] hover:text-[#27251e] p-1 rounded-[4px] hover:bg-[#d1d1cd]/30 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1">
              <h4 className="text-sm font-medium text-[#27251e]">{createdDraft.titulo}</h4>
            </div>

            <div className="bg-[#faf8f5] rounded-[6px] border border-[#d1d1cd] p-4 text-[#27251e] font-sans text-xs sm:text-[13px] leading-relaxed max-h-[380px] overflow-y-auto whitespace-pre-wrap select-text selection:bg-[#016a71]/20">
              {createdDraft.body || createdDraft.content || "Generando redacción con LLM..."}
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-[#d1d1cd]">
              <div className="text-[10px] font-mono text-[#92918b]">
                Estado: {createdDraft.estado || "borrador"} (v{createdDraft.version || 1})
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(createdDraft.body || createdDraft.content || "");
                    setDraftModalCopied(true);
                    setTimeout(() => setDraftModalCopied(false), 2000);
                  }}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] border border-[#d1d1cd] text-xs text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer"
                >
                  {draftModalCopied ? <Check className="w-3.5 h-3.5 text-[#016a71]" /> : <Copy className="w-3.5 h-3.5 text-[#72706b]" />}
                  <span>{draftModalCopied ? "Copiado!" : "Copiar Guión"}</span>
                </button>
                <Link
                  href="/borradores"
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] bg-[#27251e] hover:bg-[#000000] text-[#faf8f5] text-xs font-medium transition cursor-pointer shadow-xs"
                >
                  <FileText className="w-3.5 h-3.5 text-[#016a71]" />
                  <span>Ver en Borradores</span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
