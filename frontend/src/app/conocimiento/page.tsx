"use client";

import React, { useState, useEffect } from "react";
import {
  BookOpen,
  Image as ImageIcon,
  Video,
  FileText,
  UploadCloud,
  X,
  Plus,
  Trash2,
  Search,
  Sparkles,
  Link2,
  Tag,
  Hash,
  Database,
  Check,
} from "lucide-react";
import { KnowledgeSource, getApiBase } from "../../types/radar";
import { useRadar } from "../../context/RadarContext";

export default function ConocimientoPage() {
  const [knowledgeList, setKnowledgeList] = useState<KnowledgeSource[]>([]);
  const [loading, setLoading] = useState(true);

  // Estados de Ingesta
  const [knwInputType, setKnwInputType] = useState<"video" | "image" | "text">("image");
  const [knwMode, setKnwMode] = useState<"completo" | "keywords" | "ganchos">("completo");
  const [knwUrl, setKnwUrl] = useState("");
  const [knwSolicitud, setKnwSolicitud] = useState("");
  const [knwTitulo, setKnwTitulo] = useState("");
  const [knwAutor, setKnwAutor] = useState("");
  const [knwTextContent, setKnwTextContent] = useState("");
  const [knwImagePool, setKnwImagePool] = useState<Array<{ id: string; name: string; base64: string; size: number }>>([]);
  const [knwIsDragging, setKnwIsDragging] = useState(false);
  const [isIngestingKnw, setIsIngestingKnw] = useState(false);

  // Estados de Búsqueda Semántica
  const [knwSearchQuery, setKnwSearchQuery] = useState("");
  const [knwSearchResults, setKnwSearchResults] = useState<any[] | null>(null);
  const [isSearchingKnw, setIsSearchingKnw] = useState(false);
  const [addedFocusTrack, setAddedFocusTrack] = useState<string | null>(null);

  const { setStatusMessage } = useRadar();

  useEffect(() => {
    fetchKnowledge();
  }, []);

  const fetchKnowledge = async () => {
    setLoading(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/knowledge`);
      if (res.ok) {
        const data = await res.json();
        setKnowledgeList(data.sources || []);
      }
    } catch (err) {
      console.warn("Error cargando conocimiento:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilesSelected = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const newItems: Array<{ id: string; name: string; base64: string; size: number }> = [];

    Array.from(files).forEach((file) => {
      if (!file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        const base64 = e.target?.result as string;
        if (base64) {
          setKnwImagePool((prev) => [
            ...prev,
            {
              id: `img-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
              name: file.name,
              base64,
              size: file.size,
            },
          ]);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const handleRemoveImageFromPool = (id: string) => {
    setKnwImagePool((prev) => prev.filter((img) => img.id !== id));
  };

  const handleClearPool = () => {
    setKnwImagePool([]);
  };

  const handleIngestKnowledge = async () => {
    const api = getApiBase();
    setIsIngestingKnw(true);

    let payload: Record<string, any> = {
      tipo: knwInputType,
      modo: knwMode,
      solicitud: knwSolicitud,
      titulo: knwTitulo,
      autor: knwAutor,
    };

    if (knwInputType === "image") {
      if (knwImagePool.length === 0) {
        setStatusMessage("Por favor agrega al menos una imagen al pool antes de procesar.");
        setIsIngestingKnw(false);
        return;
      }
      payload = {
        ...payload,
        tipo: knwImagePool.length > 1 ? "image_pool" : "image",
        imagenes_pool: knwImagePool.map((img) => img.base64),
        nombres_pool: knwImagePool.map((img) => img.name),
        imagen_data: knwImagePool[0].base64,
        nombre_archivo: knwImagePool[0].name,
      };
    } else if (knwInputType === "video") {
      if (!knwUrl.trim()) {
        setStatusMessage("Por favor ingresa una URL de video válida.");
        setIsIngestingKnw(false);
        return;
      }
      payload = { ...payload, url: knwUrl };
    } else {
      if (!knwTextContent.trim() && !knwUrl.trim()) {
        setStatusMessage("Por favor ingresa un texto o enlace de artículo.");
        setIsIngestingKnw(false);
        return;
      }
      payload = { ...payload, url: knwUrl, texto: knwTextContent };
    }

    try {
      const res = await fetch(`${api}/api/knowledge/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMessage(`Recurso indexado exitosamente (${knwMode.toUpperCase()}).`);
        setKnwImagePool([]);
        setKnwUrl("");
        setKnwTitulo("");
        setKnwAutor("");
        setKnwTextContent("");
        setKnwSolicitud("");
        fetchKnowledge();
      } else {
        setStatusMessage(data.error || "Error al procesar el recurso.");
      }
    } catch {
      setStatusMessage("Error conectando con el servidor web.");
    } finally {
      setIsIngestingKnw(false);
    }
  };

  const handleSearchKnowledge = async () => {
    if (!knwSearchQuery.trim()) {
      setKnwSearchResults(null);
      return;
    }
    const api = getApiBase();
    setIsSearchingKnw(true);
    try {
      const res = await fetch(`${api}/api/knowledge/search?q=${encodeURIComponent(knwSearchQuery)}`);
      if (res.ok) {
        const data = await res.json();
        setKnwSearchResults(data.results || []);
      }
    } catch {
      setStatusMessage("Error en búsqueda semántica.");
    } finally {
      setIsSearchingKnw(false);
    }
  };

  const handleDeleteSource = async (id: string) => {
    const api = getApiBase();
    try {
      const res = await fetch(`${api}/api/knowledge/${id}`, { method: "DELETE" });
      if (res.ok) {
        setStatusMessage("Recurso eliminado de la base de conocimiento.");
        setKnowledgeList((prev) => prev.filter((k) => k.id !== id));
      }
    } catch {
      setStatusMessage("Error eliminando recurso.");
    }
  };

  const handleAddKeywordToRadar = async (keyword: string) => {
    const api = getApiBase();
    try {
      const res = await fetch(`${api}/api/focuses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: `Track: ${keyword}`,
          categoria: "radar-sugerido",
          keywords: [keyword],
          descripcion: `Enfoque temático generado automáticamente desde extracción de conocimiento RAG (${keyword}).`,
        }),
      });
      if (res.ok) {
        setAddedFocusTrack(keyword);
        setStatusMessage(`Track de búsqueda creado para '${keyword}'.`);
        setTimeout(() => setAddedFocusTrack(null), 3000);
      }
    } catch {
      setStatusMessage("Error al registrar track en Radar.");
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <section className="text-center max-w-2xl mx-auto space-y-2 pt-2">
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-[4px] bg-[#016a71]/10 border border-[#016a71]/20 text-[#016a71]">
          <BookOpen className="w-3.5 h-3.5 text-[#016a71]" />
          <span className="font-mono text-[10px] tracking-wider font-medium uppercase">
            MULTIMODAL RAG & VISUAL POOL
          </span>
        </div>
        <h1 className="text-3xl text-[#27251e] font-normal tracking-tight">
          Base de Conocimiento <span className="text-[#016a71] font-medium">Multimodal</span>
        </h1>
        <p className="text-[14px] text-[#72706b] font-normal leading-relaxed">
          Ingesta inteligente de lotes de imágenes, transcripción de videos, PDFs y enlaces.
          Extracción estructurada de ganchos psicológicos y palabras clave para alimentar el radar.
        </p>
      </section>

      {/* Ingestion Console */}
      <section data-tour="knowledge-metrics" className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-5 space-y-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#d1d1cd] pb-4">
          <div className="space-y-0.5">
            <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase tracking-wider">
              1. MODALIDAD & EXTRACCIÓN
            </span>
            <h3 className="text-base font-medium text-[#27251e]">Configuración de Entrada</h3>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center p-0.5 rounded-[4px] bg-[#faf8f5] border border-[#d1d1cd]">
            <button
              onClick={() => setKnwMode("completo")}
              className={`px-2.5 py-1 rounded-[3px] text-xs font-normal transition cursor-pointer ${
                knwMode === "completo"
                  ? "bg-[#016a71] text-[#faf8f5] font-medium"
                  : "text-[#72706b] hover:text-[#27251e]"
              }`}
            >
              Completo
            </button>
            <button
              onClick={() => setKnwMode("keywords")}
              className={`px-2.5 py-1 rounded-[3px] text-xs font-normal transition cursor-pointer ${
                knwMode === "keywords"
                  ? "bg-[#016a71] text-[#faf8f5] font-medium"
                  : "text-[#72706b] hover:text-[#27251e]"
              }`}
            >
              Palabras Clave
            </button>
            <button
              onClick={() => setKnwMode("ganchos")}
              className={`px-2.5 py-1 rounded-[3px] text-xs font-normal transition cursor-pointer ${
                knwMode === "ganchos"
                  ? "bg-[#016a71] text-[#faf8f5] font-medium"
                  : "text-[#72706b] hover:text-[#27251e]"
              }`}
            >
              Solo Ganchos
            </button>
          </div>
        </div>

        {/* Format Selector Pills */}
        <div data-tour="knowledge-format-pills" className="flex flex-wrap gap-2">
          <button
            onClick={() => setKnwInputType("image")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] text-xs transition cursor-pointer border ${
              knwInputType === "image"
                ? "bg-[#27251e] text-[#faf8f5] border-[#27251e]"
                : "bg-[#faf8f5] text-[#72706b] border-[#d1d1cd] hover:text-[#27251e]"
            }`}
          >
            <ImageIcon className="w-3.5 h-3.5" />
            <span>Pool de Imágenes / Infografías</span>
          </button>
          <button
            onClick={() => setKnwInputType("video")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] text-xs transition cursor-pointer border ${
              knwInputType === "video"
                ? "bg-[#27251e] text-[#faf8f5] border-[#27251e]"
                : "bg-[#faf8f5] text-[#72706b] border-[#d1d1cd] hover:text-[#27251e]"
            }`}
          >
            <Video className="w-3.5 h-3.5" />
            <span>Video / YouTube</span>
          </button>
          <button
            onClick={() => setKnwInputType("text")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] text-xs transition cursor-pointer border ${
              knwInputType === "text"
                ? "bg-[#27251e] text-[#faf8f5] border-[#27251e]"
                : "bg-[#faf8f5] text-[#72706b] border-[#d1d1cd] hover:text-[#27251e]"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Documento / Texto / Web</span>
          </button>
        </div>

        {/* Image Pool Dropzone */}
        {knwInputType === "image" && (
          <div className="space-y-3">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setKnwIsDragging(true);
              }}
              onDragLeave={() => setKnwIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setKnwIsDragging(false);
                handleFilesSelected(e.dataTransfer.files);
              }}
              className={`p-6 border-2 border-dashed rounded-[6px] text-center transition cursor-pointer ${
                knwIsDragging
                  ? "border-[#016a71] bg-[#016a71]/5"
                  : "border-[#d1d1cd] hover:border-[#72706b] bg-[#faf8f5]"
              }`}
              onClick={() => document.getElementById("pool-file-input")?.click()}
            >
              <input
                id="pool-file-input"
                type="file"
                multiple
                accept="image/*"
                className="hidden"
                onChange={(e) => handleFilesSelected(e.target.files)}
              />
              <UploadCloud className="w-8 h-8 text-[#72706b] mx-auto mb-2" />
              <div className="text-xs text-[#27251e] font-medium">
                Arrastra una o varias imágenes o haz clic para seleccionarlas
              </div>
              <div className="text-[11px] text-[#72706b] mt-1 font-mono">
                PNG, JPG, WEBP — Soporta envío conjunto en lote (Pool)
              </div>
            </div>

            {/* Pool Thumbnails Gallery */}
            {knwImagePool.length > 0 && (
              <div className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-[10px] text-[#016a71] font-medium">
                    POOL PREPARADO ({knwImagePool.length} IMÁGENES)
                  </span>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => document.getElementById("pool-file-input")?.click()}
                      className="font-mono text-[10px] text-[#016a71] hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      <Plus className="w-3 h-3" /> Añadir más
                    </button>
                    <button
                      onClick={handleClearPool}
                      className="font-mono text-[10px] text-[#72706b] hover:text-[#27251e] flex items-center gap-1 cursor-pointer"
                    >
                      <Trash2 className="w-3 h-3" /> Vaciar
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
                  {knwImagePool.map((img, idx) => (
                    <div
                      key={img.id}
                      className="relative group rounded-[4px] overflow-hidden border border-[#d1d1cd] bg-[#fdfbfa] aspect-square flex flex-col justify-between"
                    >
                      <img
                        src={img.base64}
                        alt={img.name}
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveImageFromPool(img.id);
                        }}
                        className="absolute top-1 right-1 p-1 rounded-[2px] bg-black/60 text-white opacity-0 group-hover:opacity-100 transition cursor-pointer"
                        title="Eliminar del pool"
                      >
                        <X className="w-2.5 h-2.5" />
                      </button>
                      <div className="absolute bottom-0 inset-x-0 p-1 bg-black/50 text-[9px] text-white font-mono truncate">
                        #{idx + 1} {img.name}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Video / URL Input */}
        {knwInputType === "video" && (
          <div className="space-y-1">
            <label className="font-mono text-[10px] text-[#72706b] uppercase">URL DEL VIDEO</label>
            <input
              type="text"
              value={knwUrl}
              onChange={(e) => setKnwUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-3 py-2 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71]"
            />
          </div>
        )}

        {/* Text / Article Input */}
        {knwInputType === "text" && (
          <div className="space-y-2">
            <div className="space-y-1">
              <label className="font-mono text-[10px] text-[#72706b] uppercase">URL DEL ARTÍCULO (OPCIONAL)</label>
              <input
                type="text"
                value={knwUrl}
                onChange={(e) => setKnwUrl(e.target.value)}
                placeholder="https://techcrunch.com/..."
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-3 py-2 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71]"
              />
            </div>
            <div className="space-y-1">
              <label className="font-mono text-[10px] text-[#72706b] uppercase">CONTENIDO TEXTUAL</label>
              <textarea
                value={knwTextContent}
                onChange={(e) => setKnwTextContent(e.target.value)}
                rows={4}
                placeholder="Pega aquí el resumen o transcripción..."
                className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-3 py-2 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71]"
              />
            </div>
          </div>
        )}

        {/* Prompt & Optional Metadata */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-3 space-y-1">
            <label className="font-mono text-[10px] text-[#72706b] uppercase">
              SOLICITUD O ENFOQUE ESPECÍFICO (PROMPT)
            </label>
            <input
              type="text"
              value={knwSolicitud}
              onChange={(e) => setKnwSolicitud(e.target.value)}
              placeholder="Ej: Extrae palabras clave de benchmarks, métricas clave y ganchos de retención..."
              className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-3 py-2 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71]"
            />
          </div>
          <div className="space-y-1">
            <label className="font-mono text-[10px] text-[#72706b] uppercase">TÍTULO (OPCIONAL)</label>
            <input
              type="text"
              value={knwTitulo}
              onChange={(e) => setKnwTitulo(e.target.value)}
              placeholder="Nombre del recurso"
              className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-3 py-1.5 text-xs text-[#27251e]"
            />
          </div>
          <div className="space-y-1">
            <label className="font-mono text-[10px] text-[#72706b] uppercase">AUTOR / MEDIO (OPCIONAL)</label>
            <input
              type="text"
              value={knwAutor}
              onChange={(e) => setKnwAutor(e.target.value)}
              placeholder="Canal o publicación"
              className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-3 py-1.5 text-xs text-[#27251e]"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleIngestKnowledge}
              disabled={isIngestingKnw}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 rounded-[4px] bg-[#27251e] hover:bg-black text-[#faf8f5] text-xs font-medium transition disabled:opacity-50 cursor-pointer shadow-xs"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#016a71]" />
              <span>{isIngestingKnw ? "Analizando e indexando..." : "Procesar e Ingestar Recurso"}</span>
            </button>
          </div>
        </div>
      </section>

      {/* Semantic Vector Search Box */}
      <section data-tour="knowledge-search" className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-4 space-y-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="flex items-center space-x-2">
          <Database className="w-3.5 h-3.5 text-[#016a71]" />
          <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase tracking-wider">
            BÚSQUEDA SEMÁNTICA VECTORIAL
          </span>
        </div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-[#72706b] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={knwSearchQuery}
              onChange={(e) => setKnwSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearchKnowledge()}
              placeholder="Consultar en los vectores de conocimiento (ej: sandboxing de agentes, retención SaaS)..."
              className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] pl-9 pr-3 py-1.5 text-xs text-[#27251e] placeholder-[#72706b] focus:outline-none focus:border-[#016a71]"
            />
          </div>
          <button
            onClick={handleSearchKnowledge}
            disabled={isSearchingKnw}
            className="px-3.5 py-1.5 rounded-[4px] border border-[#d1d1cd] text-xs text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer"
          >
            {isSearchingKnw ? "Buscando..." : "Buscar"}
          </button>
        </div>

        {/* Vector Search Results */}
        {knwSearchResults && (
          <div className="pt-2 border-t border-[#d1d1cd] space-y-2">
            <span className="font-mono text-[9px] text-[#72706b]">
              RESULTADOS DE SIMILITUD COSENO ({knwSearchResults.length})
            </span>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {knwSearchResults.map((res, idx) => (
                <div key={idx} className="p-2 rounded-[4px] bg-[#faf8f5] border border-[#d1d1cd] text-xs space-y-0.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="font-mono text-[#016a71] font-medium">{res.titulo || "Recurso"}</span>
                    <span className="font-mono text-[#72706b]">Score: {res.score?.toFixed(2)}</span>
                  </div>
                  <p className="text-[11px] text-[#27251e] leading-snug">{res.texto}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Indexed Sources List */}
      <section data-tour="knowledge-grid" className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
            <h3 className="text-base font-medium text-[#27251e]">
              Fuentes en la Base de Conocimiento ({knowledgeList.length})
            </h3>
          </div>
          <span className="font-mono text-[10px] text-[#72706b]">
            SQLite Vectorial // Memoria 90d
          </span>
        </div>

        {loading ? (
          <div className="text-center py-10 text-xs text-[#72706b]">Cargando recursos indexados...</div>
        ) : knowledgeList.length === 0 ? (
          <div className="text-center py-10 text-xs text-[#72706b] rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd]">
            Aún no hay recursos ingresados. Sube un pool de imágenes o enlace arriba.
          </div>
        ) : (
          <div className="space-y-3">
            {knowledgeList.map((src) => (
              <div
                key={src.id}
                className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20 uppercase">
                        {src.tipo === "image_pool" ? `POOL (${src.total_imagenes || src.imagenes_pool?.length || 2} IMÁGENES)` : src.tipo}
                      </span>
                      {src.modo_extraccion && (
                        <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] bg-[#faf8f5] text-[#72706b] border border-[#d1d1cd] uppercase">
                          Modo: {src.modo_extraccion}
                        </span>
                      )}
                      <span className="font-mono text-[9px] text-[#72706b]">
                        {src.creado_en ? new Date(src.creado_en).toLocaleDateString() : "Reciente"}
                      </span>
                    </div>
                    <h4 className="text-sm font-medium text-[#27251e]">{src.titulo}</h4>
                    {src.autor && (
                      <p className="text-[11px] text-[#72706b]">Por {src.autor}</p>
                    )}
                  </div>

                  <button
                    onClick={() => handleDeleteSource(src.id)}
                    className="p-1 rounded-[3px] text-[#72706b] hover:text-[#27251e] border border-transparent hover:border-[#d1d1cd] transition self-start sm:self-auto cursor-pointer"
                    title="Eliminar recurso"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Pool Images Strip */}
                {src.imagenes_pool && src.imagenes_pool.length > 0 && (
                  <div className="flex items-center space-x-2 overflow-x-auto py-1">
                    {src.imagenes_pool.map((imgB64, idx) => (
                      <div
                        key={idx}
                        className="w-14 h-14 rounded-[3px] overflow-hidden border border-[#d1d1cd] shrink-0 bg-[#faf8f5]"
                      >
                        <img src={imgB64} alt={`Pool item ${idx}`} className="w-full h-full object-cover" />
                      </div>
                    ))}
                  </div>
                )}

                {/* Resumen */}
                <p className="text-xs text-[#27251e] font-normal leading-relaxed">
                  {src.transcripcion_resumen || src.perfil?.resumen_ejecutivo}
                </p>

                {/* Keywords & Radar chips */}
                {src.perfil?.palabras_clave && src.perfil.palabras_clave.length > 0 && (
                  <div className="pt-2 border-t border-[#d1d1cd] space-y-1.5">
                    <span className="font-mono text-[9px] text-[#72706b]">PALABRAS CLAVE DETECTADAS:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {src.perfil.palabras_clave.map((kw, idx) => (
                        <span
                          key={idx}
                          className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] bg-[#faf8f5] text-[#27251e] border border-[#d1d1cd] flex items-center gap-1"
                        >
                          <Hash className="w-2.5 h-2.5 text-[#016a71]" />
                          <span>{kw}</span>
                          <button
                            onClick={() => handleAddKeywordToRadar(kw)}
                            title="Añadir a Enfoques de Búsqueda"
                            className="text-[#016a71] hover:underline cursor-pointer ml-1 text-[8px]"
                          >
                            {addedFocusTrack === kw ? <Check className="w-2.5 h-2.5 inline" /> : "+ Radar"}
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
