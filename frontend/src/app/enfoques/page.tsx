"use client";

import React, { useState, useEffect } from "react";
import {
  SlidersHorizontal,
  Plus,
  Trash2,
  Globe,
  Radio,
  Search,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Tag,
  Hash,
  Rss,
  Copy,
  Check,
  ShieldCheck,
  Cpu,
  Zap,
  FileText,
  Sparkles,
} from "lucide-react";
import { SearchFocus, RSSAppFeedItem, getApiBase } from "../../types/radar";
import { useRadar } from "../../context/RadarContext";

export default function EnfoquesPage() {
  const [focuses, setFocuses] = useState<SearchFocus[]>([]);
  const [loading, setLoading] = useState(true);

  // Nuevo Enfoque Form State
  const [newFocusName, setNewFocusName] = useState("");
  const [newFocusCategory, setNewFocusCategory] = useState("polemicas");
  const [newFocusKeywords, setNewFocusKeywords] = useState("");
  const [newFocusDesc, setNewFocusDesc] = useState("");
  const [isSavingFocus, setIsSavingFocus] = useState(false);

  // WebSearch Live Tester
  const [webSearchQuery, setWebSearchQuery] = useState("OpenAI Anthropic controversia seguridad 2026");
  const [isSearchingWeb, setIsSearchingWeb] = useState(false);
  const [webSearchResults, setWebSearchResults] = useState<any[] | null>(null);

  // RSS.app Hub
  const [rssFeeds, setRssFeeds] = useState<RSSAppFeedItem[]>([]);
  const [newRssUrl, setNewRssUrl] = useState("");
  const [newRssName, setNewRssName] = useState("");
  const [newRssPlataforma, setNewRssPlataforma] = useState<"Twitter/X" | "TikTok" | "LinkedIn" | "YouTube" | "Web" | "General">("General");
  const [newRssEnfoque, setNewRssEnfoque] = useState("polemicas-labs");
  const [isTestingRss, setIsTestingRss] = useState(false);
  const [testRssResult, setTestRssResult] = useState<any | null>(null);
  const [isSavingRss, setIsSavingRss] = useState(false);

  // Scraper Híbrido State
  const [scrapeUrl, setScrapeUrl] = useState("https://techcrunch.com/2026/10/16/anthropic-reasoning-budget");
  const [scrapeMode, setScrapeMode] = useState<"auto" | "jina" | "stealth" | "managed">("auto");
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeResult, setScrapeResult] = useState<any | null>(null);
  const [scrapeCopied, setScrapeCopied] = useState(false);
  const [scraperStatus, setScraperStatus] = useState<any | null>(null);

  const { setStatusMessage } = useRadar();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const api = getApiBase();
      const [resFocuses, resRss, resScraper] = await Promise.all([
        fetch(`${api}/api/focuses`),
        fetch(`${api}/api/rssapp/feeds`),
        fetch(`${api}/api/scraper/status`),
      ]);
      if (resFocuses.ok) {
        const data = await resFocuses.json();
        setFocuses(data.focuses || []);
      }
      if (resRss.ok) {
        const dataRss = await resRss.json();
        setRssFeeds(dataRss.feeds || []);
      }
      if (resScraper.ok) {
        const dataScraper = await resScraper.json();
        setScraperStatus(dataScraper);
      }
    } catch (err) {
      console.warn("Error cargando enfoques/RSS:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFocus = async (id: string) => {
    const api = getApiBase();
    try {
      const res = await fetch(`${api}/api/focuses/${id}/toggle`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setFocuses((prev) =>
          prev.map((f) => (f.id === id ? { ...f, activo: data.focus.activo } : f))
        );
        setStatusMessage(`Enfoque ${data.focus.activo ? "activado" : "pausado"}.`);
      }
    } catch {
      setStatusMessage("Error al alternar estado del enfoque.");
    }
  };

  const handleCreateFocus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFocusName.trim() || !newFocusKeywords.trim()) {
      setStatusMessage("Por favor ingresa nombre y palabras clave.");
      return;
    }
    const api = getApiBase();
    setIsSavingFocus(true);
    try {
      const kwList = newFocusKeywords.split(",").map((k) => k.trim()).filter(Boolean);
      const res = await fetch(`${api}/api/focuses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: newFocusName.trim(),
          categoria: newFocusCategory,
          keywords: kwList,
          descripcion: newFocusDesc.trim(),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setFocuses((prev) => [...prev, data.focus]);
        setNewFocusName("");
        setNewFocusKeywords("");
        setNewFocusDesc("");
        setStatusMessage("Nuevo enfoque de búsqueda registrado.");
      }
    } catch {
      setStatusMessage("Error registrando enfoque.");
    } finally {
      setIsSavingFocus(false);
    }
  };

  const handleDeleteFocus = async (id: string) => {
    const api = getApiBase();
    try {
      const res = await fetch(`${api}/api/focuses/${id}`, { method: "DELETE" });
      if (res.ok) {
        setFocuses((prev) => prev.filter((f) => f.id !== id));
        setStatusMessage("Enfoque eliminado.");
      }
    } catch {
      setStatusMessage("Error eliminando enfoque.");
    }
  };

  const handleTestWebSearch = async () => {
    if (!webSearchQuery.trim()) return;
    const api = getApiBase();
    setIsSearchingWeb(true);
    try {
      const res = await fetch(`${api}/api/websearch/test?q=${encodeURIComponent(webSearchQuery)}`);
      if (res.ok) {
        const data = await res.json();
        setWebSearchResults(data.results || []);
        setStatusMessage(`Búsqueda web completada: ${(data.results || []).length} resultados encontrados.`);
      } else {
        const err = await res.json().catch(() => ({}));
        setStatusMessage(err.error || "Error realizando búsqueda web.");
      }
    } catch {
      setStatusMessage("Error realizando búsqueda web.");
    } finally {
      setIsSearchingWeb(false);
    }
  };

  const handleTestRssFeed = async () => {
    if (!newRssUrl.trim()) {
      setStatusMessage("Ingresa la URL del feed de RSS.app.");
      return;
    }
    const api = getApiBase();
    setIsTestingRss(true);
    setTestRssResult(null);
    try {
      const res = await fetch(`${api}/api/rssapp/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: newRssUrl.trim() }),
      });
      const data = await res.json();
      setTestRssResult(data);
    } catch {
      setStatusMessage("Error al verificar feed.");
    } finally {
      setIsTestingRss(false);
    }
  };

  const handleAddRssFeed = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRssUrl.trim()) return;
    const api = getApiBase();
    setIsSavingRss(true);
    try {
      const res = await fetch(`${api}/api/rssapp/feeds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: newRssUrl.trim(),
          nombre: newRssName.trim() || "Feed RSS.app",
          plataforma: newRssPlataforma,
          enfoque_id: newRssEnfoque,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setRssFeeds((prev) => [...prev, data.feed]);
        setNewRssUrl("");
        setNewRssName("");
        setTestRssResult(null);
        setStatusMessage("Feed de RSS.app registrado con éxito.");
      }
    } catch {
      setStatusMessage("Error registrando feed.");
    } finally {
      setIsSavingRss(false);
    }
  };

  const handleToggleRssFeed = async (id: string) => {
    const api = getApiBase();
    try {
      const res = await fetch(`${api}/api/rssapp/feeds/${id}/toggle`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setRssFeeds((prev) =>
          prev.map((f) => (f.id === id ? { ...f, activo: data.feed.activo } : f))
        );
      }
    } catch {
      setStatusMessage("Error cambiando estado del feed.");
    }
  };

  const handleDeleteRssFeed = async (id: string) => {
    const api = getApiBase();
    try {
      const res = await fetch(`${api}/api/rssapp/feeds/${id}`, { method: "DELETE" });
      if (res.ok) {
        setRssFeeds((prev) => prev.filter((f) => f.id !== id));
        setStatusMessage("Feed eliminado.");
      }
    } catch {
      setStatusMessage("Error eliminando feed.");
    }
  };

  const handleScrape = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scrapeUrl.trim()) return;
    setIsScraping(true);
    setScrapeResult(null);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/scraper/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: scrapeUrl.trim(), mode: scrapeMode }),
      });
      const data = await res.json();
      setScrapeResult(data);
      if (data.status === "success") {
        setStatusMessage(`Extracción exitosa vía ${data.method_used} (Costo: ${data.cost_estimate})`);
      } else {
        setStatusMessage(data.error_message || "Aviso en la extracción web.");
      }
    } catch {
      setStatusMessage("Error al conectar con el servicio de scraping.");
    } finally {
      setIsScraping(false);
    }
  };

  const handleCopyScrapeMarkdown = () => {
    if (!scrapeResult?.content_markdown) return;
    navigator.clipboard.writeText(scrapeResult.content_markdown);
    setScrapeCopied(true);
    setStatusMessage("Markdown copiado al portapapeles.");
    setTimeout(() => setScrapeCopied(false), 2500);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <section className="text-center max-w-2xl mx-auto space-y-2 pt-2">
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-[4px] bg-[#016a71]/10 border border-[#016a71]/20 text-[#016a71]">
          <SlidersHorizontal className="w-3.5 h-3.5 text-[#016a71]" />
          <span className="font-mono text-[10px] tracking-wider font-medium uppercase">
            TARGET TRACKS & INGESTION FEEDS
          </span>
        </div>
        <h1 className="text-3xl text-[#27251e] font-normal tracking-tight">
          Enfoques de Búsqueda & <span className="text-[#016a71] font-medium">RSS.app</span>
        </h1>
        <p className="text-[14px] text-[#72706b] font-normal leading-relaxed">
          Supervisión de pistas temáticas activas para el pipeline de Sonar, búsqueda directa en la web y
          conectores automatizados para redes sociales.
        </p>
      </section>

      {/* Focus Tracks Grid */}
      <section data-tour="focus-tracks" className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
            <h3 className="text-base font-medium text-[#27251e]">
              Tracks Temáticos Activos ({focuses.filter((f) => f.activo).length}/{focuses.length})
            </h3>
          </div>
          <span className="font-mono text-[10px] text-[#72706b]">
            Prioridad de Curaduría
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {focuses.map((f) => (
            <div
              key={f.id}
              className={`p-4 rounded-[8px] bg-[#fdfbfa] border transition space-y-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)] ${
                f.activo ? "border-[#d1d1cd]" : "border-[#d1d1cd]/50 opacity-60"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20 uppercase">
                      {f.categoria}
                    </span>
                    <span className="font-mono text-[9px] text-[#72706b]">
                      {f.keywords.length} keywords
                    </span>
                  </div>
                  <h4 className="text-sm font-medium text-[#27251e]">{f.nombre}</h4>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={() => handleToggleFocus(f.id)}
                    className={`font-mono text-[9px] px-2 py-1 rounded-[3px] border transition cursor-pointer ${
                      f.activo
                        ? "bg-[#016a71] text-[#faf8f5] border-[#016a71]"
                        : "bg-[#faf8f5] text-[#72706b] border-[#d1d1cd]"
                    }`}
                  >
                    {f.activo ? "ACTIVO" : "PAUSADO"}
                  </button>
                  <button
                    onClick={() => handleDeleteFocus(f.id)}
                    className="p-1 rounded-[3px] text-[#72706b] hover:text-[#27251e] cursor-pointer"
                    title="Eliminar enfoque"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {f.descripcion && (
                <p className="text-xs text-[#72706b] font-normal leading-relaxed">{f.descripcion}</p>
              )}

              <div className="flex flex-wrap gap-1 pt-1 border-t border-[#d1d1cd]">
                {f.keywords.map((kw, kwIdx) => (
                  <span
                    key={kwIdx}
                    className="font-mono text-[8px] px-1.5 py-0.2 rounded-[2px] bg-[#faf8f5] text-[#27251e] border border-[#d1d1cd]"
                  >
                    #{kw}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Add Focus Form */}
        <form
          data-tour="focus-create-btn"
          onSubmit={handleCreateFocus}
          className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
        >
          <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase tracking-wider">
            AGREGAR NUEVO TRACK DE BÚSQUEDA
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <div className="space-y-1">
              <label className="font-mono text-[9px] text-[#72706b]">NOMBRE DEL TRACK</label>
              <input
                type="text"
                value={newFocusName}
                onChange={(e) => setNewFocusName(e.target.value)}
                placeholder="Ej: Agentes de IA en Finanzas"
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-2.5 py-1.5 text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
              />
            </div>
            <div className="space-y-1">
              <label className="font-mono text-[9px] text-[#72706b]">CATEGORÍA</label>
              <select
                value={newFocusCategory}
                onChange={(e) => setNewFocusCategory(e.target.value)}
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-2.5 py-1.5 text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
              >
                <option value="polemicas">Polémicas & Labs</option>
                <option value="benchmarks">Benchmarks & Modelos</option>
                <option value="ceo_liderazgo">Liderazgo & CEO</option>
                <option value="liderazgo_gestion">Liderazgo & Gestión de Equipos</option>
                <option value="tech_arquitectura">Tecnología & Arquitectura</option>
                <option value="oportunidades_roi">Oportunidades & ROI</option>
                <option value="seguridad">Seguridad & Sandboxing</option>
                <option value="general">General</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="font-mono text-[9px] text-[#72706b]">KEYWORDS (SEPARADAS POR COMA)</label>
              <input
                type="text"
                value={newFocusKeywords}
                onChange={(e) => setNewFocusKeywords(e.target.value)}
                placeholder="agentes, finanzas, roi"
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-2.5 py-1.5 text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
              />
            </div>
            <div className="sm:col-span-2 space-y-1">
              <label className="font-mono text-[9px] text-[#72706b]">DESCRIPCIÓN OPERATIVA</label>
              <input
                type="text"
                value={newFocusDesc}
                onChange={(e) => setNewFocusDesc(e.target.value)}
                placeholder="Criterio editorial de lo que se busca captar..."
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-2.5 py-1.5 text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={isSavingFocus}
                className="w-full flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-[4px] bg-[#27251e] hover:bg-black text-[#faf8f5] text-xs font-medium transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{isSavingFocus ? "Guardando..." : "Guardar Track"}</span>
              </button>
            </div>
          </div>
        </form>
      </section>

      {/* WebSearch Engine Live Tester */}
      <section data-tour="focus-web-search" className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-4 space-y-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="flex items-center space-x-2">
          <Globe className="w-3.5 h-3.5 text-[#016a71]" />
          <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase tracking-wider">
            WEBSEARCH ENGINE // DUCKDUCKGO LIVE PROBE
          </span>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={webSearchQuery}
            onChange={(e) => setWebSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleTestWebSearch()}
            placeholder="Buscar noticias en vivo o verificar fuentes..."
            className="flex-1 bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-3 py-1.5 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71]"
          />
          <button
            onClick={handleTestWebSearch}
            disabled={isSearchingWeb}
            className="px-3.5 py-1.5 rounded-[4px] border border-[#d1d1cd] text-xs text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer"
          >
            {isSearchingWeb ? "Buscando..." : "Consultar Web"}
          </button>
        </div>

        {webSearchResults && (
          <div className="pt-2 border-t border-[#d1d1cd] space-y-2">
            <span className="font-mono text-[9px] text-[#72706b]">
              RESULTADOS WEB OBTENIDOS ({webSearchResults.length})
            </span>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {webSearchResults.map((res, idx) => (
                <div key={idx} className="p-2.5 rounded-[4px] bg-[#faf8f5] border border-[#d1d1cd] text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <h5 className="font-medium text-[#27251e] text-xs">{res.title}</h5>
                    <a
                      href={res.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-[#016a71] hover:underline flex items-center gap-1"
                    >
                      <span>Abrir</span>
                      <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  </div>
                  <p className="text-[11px] text-[#72706b] line-clamp-2">{res.snippet}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* RSS.app Social Ingestion Hub */}
      <section data-tour="rssapp-feeds" className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Rss className="w-3.5 h-3.5 text-[#016a71]" />
            <h3 className="text-base font-medium text-[#27251e]">
              Hub de Ingesta Social con RSS.app ({rssFeeds.length} feeds)
            </h3>
          </div>
          <span className="font-mono text-[10px] text-[#72706b]">
            Twitter, TikTok, LinkedIn, YouTube
          </span>
        </div>

        {/* Add RSS Feed Form */}
        <form
          onSubmit={handleAddRssFeed}
          className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
        >
          <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase tracking-wider">
            REGISTRAR FEED DE RSS.APP
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
            <div className="sm:col-span-2 space-y-1">
              <label className="font-mono text-[9px] text-[#72706b]">URL DEL FEED RSS.APP</label>
              <input
                type="text"
                value={newRssUrl}
                onChange={(e) => setNewRssUrl(e.target.value)}
                placeholder="https://rss.app/feeds/..."
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-2.5 py-1.5 text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
              />
            </div>
            <div className="space-y-1">
              <label className="font-mono text-[9px] text-[#72706b]">NOMBRE DEL CANAL / CUENTA</label>
              <input
                type="text"
                value={newRssName}
                onChange={(e) => setNewRssName(e.target.value)}
                placeholder="Ej: Twitter AI Researchers"
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-2.5 py-1.5 text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
              />
            </div>
            <div className="space-y-1">
              <label className="font-mono text-[9px] text-[#72706b]">PLATAFORMA</label>
              <select
                value={newRssPlataforma}
                onChange={(e: any) => setNewRssPlataforma(e.target.value)}
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-2.5 py-1.5 text-xs text-[#27251e]"
              >
                <option value="Twitter/X">Twitter/X</option>
                <option value="LinkedIn">LinkedIn</option>
                <option value="TikTok">TikTok</option>
                <option value="YouTube">YouTube</option>
                <option value="Web">Web General</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={handleTestRssFeed}
              disabled={isTestingRss}
              className="px-3 py-1.5 rounded-[4px] border border-[#d1d1cd] text-xs text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer"
            >
              {isTestingRss ? "Probando..." : "Verificar Conexión"}
            </button>
            <button
              type="submit"
              disabled={isSavingRss}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-[4px] bg-[#27251e] hover:bg-black text-[#faf8f5] text-xs font-medium transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{isSavingRss ? "Guardando..." : "Registrar Feed"}</span>
            </button>
          </div>

          {/* Test connection result */}
          {testRssResult && (
            <div className={`p-2.5 rounded-[4px] border text-xs ${
              testRssResult.status === "ok" ? "bg-[#016a71]/10 border-[#016a71]/30 text-[#016a71]" : "bg-red-500/10 border-red-500/30 text-red-700"
            }`}>
              <div className="flex items-center space-x-1.5 font-medium">
                {testRssResult.status === "ok" ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                <span>{testRssResult.status === "ok" ? "Conexión exitosa" : "Fallo en conexión"}</span>
              </div>
              <p className="text-[11px] mt-0.5">{testRssResult.title || testRssResult.message}</p>
            </div>
          )}
        </form>

        {/* Existing Feeds List */}
        <div className="space-y-2">
          {rssFeeds.map((feed) => (
            <div
              key={feed.id}
              className="p-3 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
            >
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20">
                    {feed.plataforma}
                  </span>
                  <h5 className="font-medium text-[#27251e]">{feed.nombre}</h5>
                </div>
                <p className="font-mono text-[10px] text-[#72706b] truncate max-w-md">{feed.url}</p>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <button
                  onClick={() => handleToggleRssFeed(feed.id)}
                  className={`font-mono text-[9px] px-2 py-0.5 rounded-[3px] border cursor-pointer ${
                    feed.activo ? "bg-[#016a71] text-[#faf8f5] border-[#016a71]" : "bg-[#faf8f5] text-[#72706b] border-[#d1d1cd]"
                  }`}
                >
                  {feed.activo ? "ACTIVO" : "PAUSADO"}
                </button>
                <button
                  onClick={() => handleDeleteRssFeed(feed.id)}
                  className="p-1 rounded-[3px] text-[#72706b] hover:text-[#27251e] cursor-pointer"
                  title="Eliminar feed"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Scraper Híbrido & Extractor Seguro */}
      <section className="space-y-4 pt-4 border-t border-[#d1d1cd]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
              <h3 className="text-base font-medium text-[#27251e]">
                Scraper Híbrido & Extractor de Contenido Seguro
              </h3>
            </div>
            <p className="text-xs text-[#72706b] mt-0.5">
              Extracción limpia optimizada para RAG y LLMs con cascada de costo $0: Jina Reader → Direct Stealth → Fallback Managed.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="font-mono text-[10px] px-2 py-0.5 rounded-[3px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20 flex items-center space-x-1">
              <ShieldCheck className="w-3 h-3 text-[#016a71]" />
              <span>SSRF PROTECTED</span>
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded-[3px] bg-[#27251e]/5 text-[#27251e] border border-[#d1d1cd]">
              COSTO $0 PRIMARIO
            </span>
          </div>
        </div>

        {/* Engine Status Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-2.5 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase">Capa 0: Jina Reader</span>
              <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 font-medium">
                $0.00 / ACTIVO
              </span>
            </div>
            <p className="text-[11px] text-[#72706b]">Convierte páginas y blogs a Markdown limpio directamente vía API r.jina.ai.</p>
          </div>

          <div className="p-2.5 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase">Capa 1: Direct Stealth</span>
              <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 font-medium">
                $0.00 / ACTIVO
              </span>
            </div>
            <p className="text-[11px] text-[#72706b]">Rotación de User-Agents reales + BeautifulSoup con parseo semántico local.</p>
          </div>

          <div className="p-2.5 rounded-[6px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase">Capa 2: Anti-Bot Managed</span>
              <span className={`font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] border font-medium ${
                scraperStatus?.motores?.zenrows?.disponible || scraperStatus?.motores?.scraperapi?.disponible
                  ? "bg-blue-500/10 text-blue-700 border-blue-500/20"
                  : "bg-amber-500/10 text-amber-700 border-amber-500/20"
              }`}>
                {scraperStatus?.motores?.zenrows?.disponible || scraperStatus?.motores?.scraperapi?.disponible
                  ? "CONFIGURADO"
                  : "STANDBY / SIN KEY"}
              </span>
            </div>
            <p className="text-[11px] text-[#72706b]">ZenRows / ScraperAPI como fallback automático ante Cloudflare Turnstile o 403.</p>
          </div>
        </div>

        {/* Scraper Input Form */}
        <form onSubmit={handleScrape} className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-3 shadow-xs">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="md:col-span-3 space-y-1">
              <label className="text-[11px] font-mono text-[#72706b] uppercase">URL de Destino para Extracción</label>
              <div className="relative">
                <Globe className="absolute left-2.5 top-2.5 w-4 h-4 text-[#92918b]" />
                <input
                  type="url"
                  required
                  value={scrapeUrl}
                  onChange={(e) => setScrapeUrl(e.target.value)}
                  placeholder="https://techcrunch.com/2026/... o cualquier artículo web"
                  className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] pl-9 pr-3 py-2 text-xs text-[#27251e] placeholder-[#92918b] focus:outline-none focus:border-[#016a71]"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-mono text-[#72706b] uppercase">Modo de Extracción</label>
              <select
                value={scrapeMode}
                onChange={(e: any) => setScrapeMode(e.target.value)}
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-2.5 py-2 text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
              >
                <option value="auto">Auto (Cascada $0 + Fallback)</option>
                <option value="jina">Forzar Jina Reader ($0)</option>
                <option value="stealth">Forzar Direct Stealth ($0)</option>
                <option value="managed">Forzar Managed Proxy</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-[#72706b] font-mono">
              Jitter de cortesía (anti-ban) activado // Aislamiento SSRF activo
            </span>
            <button
              type="submit"
              disabled={isScraping}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-[4px] bg-[#016a71] hover:bg-[#01585e] text-[#faf8f5] text-xs font-medium transition cursor-pointer shadow-xs disabled:opacity-50"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>{isScraping ? "Extrayendo contenido..." : "Extraer con Scraper Híbrido"}</span>
            </button>
          </div>
        </form>

        {/* Scraped Content Preview */}
        {scrapeResult && (
          <div className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-3 animate-in fade-in duration-150">
            {/* Metadata Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#d1d1cd] pb-3">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className={`font-mono text-[9px] px-2 py-0.5 rounded-[2px] font-medium border ${
                    scrapeResult.status === "success"
                      ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/20"
                      : "bg-red-500/10 text-red-700 border-red-500/20"
                  }`}>
                    {scrapeResult.status.toUpperCase()}
                  </span>
                  <span className="font-mono text-[9px] px-2 py-0.5 rounded-[2px] bg-[#27251e]/5 text-[#27251e] border border-[#d1d1cd]">
                    MÉTODO: {scrapeResult.method_used}
                  </span>
                  <span className="font-mono text-[9px] px-2 py-0.5 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20">
                    COSTO: {scrapeResult.cost_estimate}
                  </span>
                  {scrapeResult.latency_ms && (
                    <span className="font-mono text-[9px] text-[#72706b]">
                      {scrapeResult.latency_ms} ms
                    </span>
                  )}
                </div>
                <h4 className="text-sm font-medium text-[#27251e] leading-snug">
                  {scrapeResult.title || scrapeResult.url}
                </h4>
                <div className="flex items-center space-x-3 text-[11px] text-[#72706b]">
                  {scrapeResult.author && <span>Autor: <strong>{scrapeResult.author}</strong></span>}
                  {scrapeResult.published_date && <span>Fecha: <strong>{scrapeResult.published_date}</strong></span>}
                  {scrapeResult.tokens_estimate > 0 && <span>Tokens est.: <strong>{scrapeResult.tokens_estimate}</strong></span>}
                </div>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <button
                  type="button"
                  onClick={handleCopyScrapeMarkdown}
                  className="px-2.5 py-1.5 rounded-[4px] border border-[#d1d1cd] hover:border-[#27251e] text-xs text-[#27251e] font-medium transition cursor-pointer flex items-center space-x-1"
                >
                  {scrapeCopied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{scrapeCopied ? "¡Copiado!" : "Copiar Markdown"}</span>
                </button>
                <a
                  href={scrapeResult.url}
                  target="_blank"
                  rel="noreferrer"
                  className="p-1.5 rounded-[4px] border border-[#d1d1cd] text-[#72706b] hover:text-[#27251e] transition"
                  title="Abrir URL original"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>

            {/* Error or Blocked Diagnostic Message */}
            {scrapeResult.error_message && (
              <div className="p-3 rounded-[6px] bg-amber-500/10 border border-amber-500/20 text-amber-900 text-xs">
                <div className="flex items-center space-x-1.5 font-medium mb-0.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  <span>Diagnóstico del Scraper:</span>
                </div>
                <p>{scrapeResult.error_message}</p>
              </div>
            )}

            {/* Markdown Text Area Preview */}
            {scrapeResult.content_markdown && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-[10px] font-mono text-[#72706b]">
                  <span>VISTA PREVIA DEL CONTENIDO EXTRAÍDO (MARKDOWN ESTRUCTURADO)</span>
                  <span>{scrapeResult.content_markdown.length} caracteres</span>
                </div>
                <pre className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] text-xs text-[#27251e] font-mono leading-relaxed max-h-80 overflow-y-auto whitespace-pre-wrap select-text">
                  {scrapeResult.content_markdown}
                </pre>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
