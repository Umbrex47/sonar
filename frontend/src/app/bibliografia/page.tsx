"use client";

import React, { useState, useEffect } from "react";
import {
  Library,
  ExternalLink,
  ShieldCheck,
  Clock,
  Database,
  Radio,
  FileText,
  Video,
  Globe,
  Sparkles,
  ArrowUpRight,
  TrendingUp,
  RefreshCw,
  Search,
  CheckCircle2,
  Code2,
  Cpu,
  Layers,
} from "lucide-react";
import {
  BibliographySource,
  SuggestedSource,
  BibliographyResponse,
  getApiBase,
} from "../../types/radar";

export default function BibliografiaPage() {
  const [data, setData] = useState<BibliographyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState("todas");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchBibliography();
  }, []);

  const fetchBibliography = async () => {
    setLoading(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/bibliography`);
      if (res.ok) {
        const json: BibliographyResponse = await res.json();
        setData(json);
      }
    } catch (err) {
      console.warn("Error cargando bibliografía:", err);
    } finally {
      setLoading(false);
    }
  };

  const categories = [
    "todas",
    "Video & Formatos",
    "Prensa Internacional & LatAm",
    "Modelos Open Source & Research",
    "Comunidad & Desarrolladores",
    "Búsqueda Web Automática",
    "Curaduría & Análisis Ejecutivo",
    "Redes Sociales & Viralidad",
    "Código & Repositorios",
  ];

  const filteredSources = (data?.active_sources || []).filter((s: BibliographySource) => {
    const matchesCategory =
      selectedCategory === "todas" || s.categoria === selectedCategory;
    const matchesSearch =
      searchQuery.trim() === "" ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.descripcion.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.canales_destacados.some((c) =>
        c.toLowerCase().includes(searchQuery.toLowerCase())
      );
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <section className="text-center max-w-2xl mx-auto space-y-3 pt-2">
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-[4px] bg-[#016a71]/10 border border-[#016a71]/20 text-[#016a71]">
          <Library className="w-3.5 h-3.5 text-[#016a71]" />
          <span className="font-mono text-[10px] tracking-wider font-medium uppercase">
            BIBLIOGRAFÍA & TRAZABILIDAD // 100% PUBLIC COMPLIANT
          </span>
        </div>

        <h1 className="text-3xl text-[#27251e] font-normal tracking-tight leading-snug">
          Bibliografía de <span className="text-[#016a71] font-medium">Fuentes & Orígenes</span>
        </h1>

        <p className="text-[14px] text-[#72706b] font-normal leading-relaxed">
          Transparencia metodológica total. Aquí se catalogan todas las fuentes públicas,
          APIs oficiales, canales sindicados y motores de consulta desde los cuales Sonar
          extrae señales objetivas para el radar semanal.
        </p>
      </section>

      {/* KPI Stats Summary Card */}
      <section
        data-tour="biblio-stats"
        className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)] space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
              <span className="font-mono text-[10px] text-[#016a71] uppercase tracking-wider font-medium">
                PANEL DE INGESTA MULTI-CANAL
              </span>
            </div>
            <h3 className="text-base font-medium text-[#27251e]">
              Estado del Ecosistema de Datos
            </h3>
          </div>

          <button
            onClick={fetchBibliography}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] border border-[#d1d1cd] text-xs text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Actualizar Métricas</span>
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 pt-1">
          <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-0.5">
            <span className="font-mono text-[9px] text-[#72706b] uppercase">FUENTES ACTIVAS</span>
            <div className="text-xl font-medium font-mono text-[#016a71]">
              {data?.resumen.total_fuentes_activas || 11}
            </div>
          </div>

          <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-0.5">
            <span className="font-mono text-[9px] text-[#72706b] uppercase">PIEZAS EN SQLITE</span>
            <div className="text-xl font-medium font-mono text-[#27251e]">
              {data?.resumen.total_items_indexados || 600}
            </div>
          </div>

          <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-0.5">
            <span className="font-mono text-[9px] text-[#72706b] uppercase">CATEGORÍAS</span>
            <div className="text-xl font-medium font-mono text-[#27251e]">
              {data?.resumen.categorias_cubiertas?.length || 8}
            </div>
          </div>

          <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-0.5">
            <span className="font-mono text-[9px] text-[#72706b] uppercase">EXPANSIÓN PROPUESTA</span>
            <div className="text-xl font-medium font-mono text-[#016a71]">
              +{data?.resumen.fuentes_sugeridas_expansion || 6}
            </div>
          </div>
        </div>
      </section>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-2.5 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-[#72706b] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por nombre, autor o canal..."
            className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] pl-9 pr-3 py-1.5 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71]"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-[#faf8f5] border border-[#d1d1cd] text-xs text-[#27251e] rounded-[6px] px-2.5 py-1.5 focus:outline-none focus:border-[#016a71]"
          >
            <option value="todas">Todas las categorías</option>
            {categories.filter((c) => c !== "todas").map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Active Sources Grid */}
      <section data-tour="biblio-active-grid" className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
            <h3 className="text-base font-medium text-[#27251e]">
              Directorio de Fuentes Oficiales ({filteredSources.length})
            </h3>
          </div>
          <span className="font-mono text-[10px] text-[#72706b]">
            Monitoreo Continuo
          </span>
        </div>

        {loading ? (
          <div className="text-center py-12 text-[#72706b] text-xs font-mono">
            Cargando bibliografía y metadatos de fuentes...
          </div>
        ) : filteredSources.length === 0 ? (
          <div className="text-center py-10 text-xs text-[#72706b] rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd]">
            No se encontraron fuentes con el criterio de búsqueda seleccionado.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredSources.map((source: BibliographySource) => (
              <div
                key={source.id}
                className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] hover:border-[#016a71]/50 transition duration-150 space-y-3.5 shadow-[0_1px_2px_rgba(0,0,0,0.03)] flex flex-col justify-between"
              >
                <div className="space-y-2.5">
                  {/* Top Bar: Category, Cadence, Status */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[9px] px-1.5 py-0.5 rounded-[3px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20 uppercase">
                      {source.categoria}
                    </span>
                    <div className="flex items-center space-x-1.5">
                      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded-[3px] bg-[#faf8f5] text-[#72706b] border border-[#d1d1cd]">
                        {source.cadencia}
                      </span>
                      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded-[3px] bg-[#016a71] text-[#faf8f5]">
                        Activo
                      </span>
                    </div>
                  </div>

                  {/* Title & Connection type */}
                  <div>
                    <h4 className="text-sm font-medium text-[#27251e] leading-snug">
                      {source.name}
                    </h4>
                    <span className="font-mono text-[10px] text-[#72706b]">
                      Tipo: {source.tipo}
                    </span>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-[#72706b] leading-relaxed font-normal">
                    {source.descripcion}
                  </p>

                  {/* Featured Channels / Queries Chips */}
                  {source.canales_destacados && source.canales_destacados.length > 0 && (
                    <div className="space-y-1">
                      <span className="font-mono text-[9px] text-[#92918b] uppercase tracking-wider block">
                        CANALES & CONSULTAS CLAVE:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {source.canales_destacados.map((ch, idx) => (
                          <span
                            key={idx}
                            className="font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] bg-[#faf8f5] text-[#27251e] border border-[#d1d1cd]"
                          >
                            {ch}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Bottom Footer: Compliance & Link */}
                <div className="pt-2 border-t border-[#d1d1cd]/70 flex items-center justify-between text-[10px] text-[#72706b]">
                  <div className="flex items-center space-x-1 truncate max-w-[210px]">
                    <ShieldCheck className="w-3 h-3 text-[#016a71] shrink-0" />
                    <span className="truncate">{source.compliance}</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    {source.total_items !== undefined && source.total_items > 0 && (
                      <span className="font-mono text-[9px] text-[#016a71] font-medium">
                        {source.total_items} ítems
                      </span>
                    )}
                    <a
                      href={source.url_oficial}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#016a71] hover:underline flex items-center space-x-0.5"
                    >
                      <span>Web</span>
                      <ArrowUpRight className="w-2.5 h-2.5" />
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Suggested Sources for Expansion Section */}
      <section data-tour="biblio-suggested-grid" className="space-y-4 pt-4 border-t border-[#d1d1cd]">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-[#016a71]" />
            <h3 className="text-base font-medium text-[#27251e]">
              Otras Fuentes Recomendadas para Expansión del Radar
            </h3>
          </div>
          <p className="text-xs text-[#72706b] font-normal leading-relaxed">
            Evaluación técnica de fuentes externas de alto impacto para incorporar al pipeline de recolección continua:
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {(data?.suggested_sources || []).map((s: SuggestedSource) => (
            <div
              key={s.id}
              className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] hover:border-[#016a71]/60 transition duration-150 space-y-3 flex flex-col justify-between shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-1">
                  <span className="font-mono text-[9px] px-1.5 py-0.5 rounded-[3px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20 uppercase">
                    {s.categoria}
                  </span>
                  <span
                    className={`font-mono text-[9px] px-1.5 py-0.5 rounded-[3px] border ${
                      s.impacto.includes("Muy Alto")
                        ? "bg-[#27251e] text-[#faf8f5] border-[#27251e]"
                        : "bg-[#faf8f5] text-[#72706b] border-[#d1d1cd]"
                    }`}
                  >
                    {s.impacto}
                  </span>
                </div>

                <h4 className="text-[13px] font-medium text-[#27251e] leading-snug">
                  {s.name}
                </h4>

                <p className="text-xs text-[#72706b] leading-relaxed font-normal">
                  {s.beneficio}
                </p>
              </div>

              <div className="pt-2 border-t border-[#d1d1cd]/70 flex items-center justify-between text-[10px]">
                <span className="font-mono text-[#92918b]">
                  Dificultad: {s.dificultad}
                </span>

                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#016a71] hover:underline flex items-center space-x-0.5"
                >
                  <span>Doc API</span>
                  <ArrowUpRight className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
