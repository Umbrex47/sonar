"use client";

import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import {
  FileText,
  Sparkles,
  Copy,
  Check,
  CheckCircle2,
  Clock,
  ArrowRight,
  Filter,
  Plus,
  RefreshCw,
  ExternalLink,
  Shield,
  Layers,
  ChevronRight,
  Send,
  X,
  Eye,
  Edit3,
  Save,
  RotateCcw,
} from "lucide-react";
import { DraftItem, getApiBase } from "../../types/radar";

export default function BorradoresPage() {
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedDraft, setSelectedDraft] = useState<DraftItem | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("todos");
  const [copied, setCopied] = useState<boolean>(false);
  const [updatingStatus, setUpdatingStatus] = useState<boolean>(false);
  const [loadingBody, setLoadingBody] = useState<boolean>(false);

  // Estados de modo edición y switch de vista previa
  const [isEditMode, setIsEditMode] = useState<boolean>(false);
  const [editedBody, setEditedBody] = useState<string>("");
  const [isSavingDraft, setIsSavingDraft] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // Modal para redactar nuevo borrador
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [newTitle, setNewTitle] = useState<string>("");
  const [newFormat, setNewFormat] = useState<string>("video_corto");
  const [newHook, setNewHook] = useState<string>("opinion");
  const [newEvidence, setNewEvidence] = useState<string>("");
  const [newAuthor, setNewAuthor] = useState<string>("30X Editorial");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [modalError, setModalError] = useState<string | null>(null);

  useEffect(() => {
    fetchDrafts();
  }, []);

  const handleSelectDraft = async (draft: DraftItem) => {
    setSelectedDraft(draft);
    setEditedBody(draft.body || draft.content || "");
    setIsEditMode(false);
    setSaveSuccess(false);

    if (!draft.body && !draft.content) {
      setLoadingBody(true);
      try {
        const api = getApiBase();
        const res = await fetch(`${api}/api/drafts/${draft.id}`);
        if (res.ok) {
          const full: DraftItem = await res.json();
          setSelectedDraft(full);
          setEditedBody(full.body || full.content || "");
          setDrafts((prev) =>
            prev.map((d) => (d.id === draft.id ? { ...d, ...full } : d))
          );
        }
      } catch (err) {
        console.warn("Error cargando cuerpo del borrador:", err);
      } finally {
        setLoadingBody(false);
      }
    }
  };

  const handleSaveDraft = async () => {
    if (!selectedDraft) return;
    setIsSavingDraft(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/drafts/${selectedDraft.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          body: editedBody,
          titulo: selectedDraft.titulo,
          autor: selectedDraft.autor,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedDraft((prev) =>
          prev ? { ...prev, ...updated, body: editedBody } : null
        );
        setDrafts((prev) =>
          prev.map((d) =>
            d.id === selectedDraft.id
              ? {
                  ...d,
                  ...updated,
                  body: editedBody,
                  version: updated.version || d.version + 1,
                }
              : d
          )
        );
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(`Error al guardar borrador: ${errData.error || res.statusText}`);
      }
    } catch (err) {
      console.error("Error guardando borrador:", err);
      alert("Error de conexión al guardar el borrador");
    } finally {
      setIsSavingDraft(false);
    }
  };

  const fetchDrafts = async () => {
    setLoading(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/drafts`);
      if (res.ok) {
        const data = await res.json();
        const list: DraftItem[] = Array.isArray(data) ? data : data.drafts || [];
        setDrafts(list);
        if (list.length > 0) {
          handleSelectDraft(list[0]);
        }
      }
    } catch (err) {
      console.warn("Error cargando borradores:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (draftId: number, nextStatus: string) => {
    setUpdatingStatus(true);
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/drafts/${draftId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado: nextStatus }),
      });
      if (res.ok) {
        const updated = await res.json();
        setDrafts((prev) =>
          prev.map((d) => (d.id === draftId ? { ...d, estado: nextStatus as any } : d))
        );
        if (selectedDraft && selectedDraft.id === draftId) {
          setSelectedDraft({ ...selectedDraft, estado: nextStatus as any });
        }
      }
    } catch (err) {
      console.error("Error al actualizar estado:", err);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setIsGenerating(true);
    setModalError(null);
    try {
      const api = getApiBase();
      const evidenceList = newEvidence
        .split("\n")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

      const res = await fetch(`${api}/api/drafts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          titulo: newTitle.trim(),
          formato: newFormat,
          gancho: newHook,
          autor: newAuthor.trim() || "30X Editorial",
          evidencia: evidenceList,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || "Error al generar borrador con LLM");
      }

      const created = await res.json();
      const newDraftItem: DraftItem = {
        id: created.id,
        tema_id: created.tema_id,
        narrative_id: created.narrative_id,
        titulo: created.titulo,
        formato: created.formato,
        gancho: created.gancho,
        autor: created.autor,
        estado: created.estado || "borrador",
        version: created.version || 1,
        body: created.body || "",
        file_path: created.file_path,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      setDrafts([newDraftItem, ...drafts]);
      setSelectedDraft(newDraftItem);
      setIsModalOpen(false);
      setNewTitle("");
      setNewEvidence("");
    } catch (err: any) {
      setModalError(err.message || "Error al invocar LLM");
    } finally {
      setIsGenerating(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredDrafts = drafts.filter((d) => {
    if (filterStatus === "todos") return true;
    return d.estado === filterStatus;
  });

  const getStatusBadge = (estado: string) => {
    switch (estado) {
      case "aprobado":
        return {
          label: "Aprobado",
          className: "bg-[#016a71]/15 text-[#016a71] border-[#016a71]/30",
        };
      case "publicado":
        return {
          label: "Publicado",
          className: "bg-[#27251e] text-[#faf8f5] border-[#27251e]",
        };
      case "en_revision":
        return {
          label: "En Revisión",
          className: "bg-[#fdfbfa] text-[#72706b] border-[#d1d1cd]",
        };
      case "borrador":
      default:
        return {
          label: "Borrador",
          className: "bg-[#faf8f5] text-[#72706b] border-[#d1d1cd]",
        };
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header Headline */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#d1d1cd]">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-[4px] bg-[#016a71]/10 border border-[#016a71]/20 text-[#016a71]">
            <Sparkles className="w-3 h-3 text-[#016a71]" />
            <span className="font-mono text-[10px] tracking-wider font-medium uppercase">
              TALLER EDITORIAL // MOTOR LLM CONTEXTUAL
            </span>
          </div>
          <h1 className="text-2xl font-normal text-[#27251e] tracking-tight">
            Guiones & Borradores Estructurados
          </h1>
          <p className="text-xs text-[#72706b] max-w-2xl font-normal leading-relaxed">
            Generación de piezas listas para producción a partir de tendencias de Sonar.
            Cada borrador pasa por LLM integrando ganchos psicológicos, evidencia directa y adaptaciones ejecutivas.
          </p>
        </div>

        <button
          data-tour="drafts-generate"
          onClick={() => setIsModalOpen(true)}
          className="flex items-center space-x-2 px-3 py-2 rounded-[4px] bg-[#27251e] hover:bg-[#000000] text-[#faf8f5] text-xs font-medium transition cursor-pointer self-start sm:self-auto shadow-xs shrink-0"
        >
          <Plus className="w-3.5 h-3.5 text-[#016a71]" />
          <span>Generar Nuevo Borrador IA</span>
        </button>
      </section>

      {/* Filter Chips Bar */}
      <div data-tour="drafts-config" className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1">
          {[
            { id: "todos", label: "Todos", count: drafts.length },
            {
              id: "borrador",
              label: "Borradores",
              count: drafts.filter((d) => d.estado === "borrador").length,
            },
            {
              id: "en_revision",
              label: "En Revisión",
              count: drafts.filter((d) => d.estado === "en_revision").length,
            },
            {
              id: "aprobado",
              label: "Aprobados",
              count: drafts.filter((d) => d.estado === "aprobado").length,
            },
            {
              id: "publicado",
              label: "Publicados",
              count: drafts.filter((d) => d.estado === "publicado").length,
            },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setFilterStatus(pill.id)}
              className={`px-3 py-1 rounded-[4px] text-xs transition font-normal cursor-pointer flex items-center space-x-1.5 border ${
                filterStatus === pill.id
                  ? "bg-[#016a71] text-[#faf8f5] border-[#016a71] font-medium"
                  : "bg-[#fdfbfa] text-[#72706b] border-[#d1d1cd] hover:text-[#27251e] hover:bg-[#d1d1cd]/20"
              }`}
            >
              <span>{pill.label}</span>
              <span
                className={`font-mono text-[10px] px-1 py-0.2 rounded-[2px] ${
                  filterStatus === pill.id ? "bg-white/20 text-white" : "bg-[#d1d1cd]/40 text-[#72706b]"
                }`}
              >
                {pill.count}
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={fetchDrafts}
          disabled={loading}
          className="p-1.5 rounded-[4px] border border-[#d1d1cd] bg-[#fdfbfa] text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer"
          title="Refrescar lista"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Main Split Layout: List on Left, Viewer on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left List of Drafts */}
        <div data-tour="drafts-sidebar" className="lg:col-span-5 space-y-2.5">
          {loading && drafts.length === 0 ? (
            <div className="p-8 text-center text-xs text-[#72706b] bg-[#fdfbfa] rounded-[8px] border border-[#d1d1cd]">
              <RefreshCw className="w-4 h-4 animate-spin text-[#016a71] mx-auto mb-2" />
              Cargando biblioteca de borradores...
            </div>
          ) : filteredDrafts.length === 0 ? (
            <div className="p-8 text-center bg-[#fdfbfa] rounded-[8px] border border-[#d1d1cd] space-y-2">
              <FileText className="w-6 h-6 text-[#92918b] mx-auto" />
              <p className="text-xs text-[#72706b] font-normal">
                No hay borradores en estado &ldquo;{filterStatus}&rdquo;.
              </p>
              <button
                onClick={() => setIsModalOpen(true)}
                className="text-xs text-[#016a71] hover:underline cursor-pointer"
              >
                Generar primer borrador con LLM
              </button>
            </div>
          ) : (
            filteredDrafts.map((draft) => {
              const isSelected = selectedDraft?.id === draft.id;
              const badge = getStatusBadge(draft.estado);

              return (
                <div
                  key={draft.id}
                  onClick={() => handleSelectDraft(draft)}
                  className={`p-3.5 rounded-[8px] border transition cursor-pointer flex flex-col justify-between space-y-2.5 ${
                    isSelected
                      ? "bg-[#fdfbfa] border-[#016a71] shadow-xs ring-1 ring-[#016a71]/20"
                      : "bg-[#fdfbfa] border-[#d1d1cd] hover:border-[#92918b]"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-mono text-[9px] text-[#72706b]">
                          #{draft.id}
                        </span>
                        <span
                          className={`font-mono text-[9px] px-1.5 py-0.2 rounded-[3px] border uppercase ${badge.className}`}
                        >
                          {badge.label}
                        </span>
                      </div>
                      <span className="font-mono text-[9px] text-[#92918b]">
                        v{draft.version}
                      </span>
                    </div>

                    <h3 className="text-sm font-medium text-[#27251e] leading-snug line-clamp-2">
                      {draft.titulo}
                    </h3>
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-[#d1d1cd]/50 text-[10px] text-[#72706b]">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono bg-[#faf8f5] px-1.5 py-0.5 rounded-[3px] border border-[#d1d1cd]">
                        {draft.formato.replace("_", " ")}
                      </span>
                      <span className="font-mono">
                        Gancho: {draft.gancho}
                      </span>
                    </div>
                    <ChevronRight className="w-3 h-3 text-[#92918b]" />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Reader / Editor Pane */}
        <div data-tour="drafts-editor" className="lg:col-span-7">
          {selectedDraft ? (
            <div className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-5 space-y-5 shadow-xs sticky top-20">
              {/* Header of Selected Draft */}
              <div className="space-y-3 pb-4 border-b border-[#d1d1cd]">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[10px] text-[#72706b]">
                      BORRADOR #{selectedDraft.id} // v{selectedDraft.version}
                    </span>
                    <span
                      className={`font-mono text-[9px] px-1.5 py-0.2 rounded-[3px] border uppercase ${
                        getStatusBadge(selectedDraft.estado).className
                      }`}
                    >
                      {getStatusBadge(selectedDraft.estado).label}
                    </span>
                  </div>

                  {/* Actions: Edit Mode Switch & Copy */}
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Switch de Vista Previa vs Modo Editor */}
                    <div className="flex items-center rounded-[6px] bg-[#f0ece1] p-0.5 border border-[#d1d1cd]">
                      <button
                        type="button"
                        onClick={() => setIsEditMode(false)}
                        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-[4px] text-xs font-medium transition cursor-pointer ${
                          !isEditMode
                            ? "bg-[#fdfbfa] text-[#016a71] shadow-2xs"
                            : "text-[#72706b] hover:text-[#27251e]"
                        }`}
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Vista Previa</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditedBody(selectedDraft.body || selectedDraft.content || "");
                          setIsEditMode(true);
                        }}
                        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-[4px] text-xs font-medium transition cursor-pointer ${
                          isEditMode
                            ? "bg-[#fdfbfa] text-[#016a71] shadow-2xs"
                            : "text-[#72706b] hover:text-[#27251e]"
                        }`}
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Modo Editor</span>
                      </button>
                    </div>

                    <button
                      onClick={() => copyToClipboard(isEditMode ? editedBody : (selectedDraft.body || selectedDraft.content || ""))}
                      className="flex items-center space-x-1.5 px-2.5 py-1 rounded-[4px] border border-[#d1d1cd] text-xs text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer"
                    >
                      {copied ? (
                        <Check className="w-3.5 h-3.5 text-[#016a71]" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-[#72706b]" />
                      )}
                      <span>{copied ? "Copiado!" : "Copiar Guión"}</span>
                    </button>
                  </div>
                </div>

                <h2 className="text-lg font-medium text-[#27251e] leading-snug">
                  {selectedDraft.titulo}
                </h2>

                <div className="flex flex-wrap items-center gap-2 text-[11px] text-[#72706b]">
                  <span className="font-mono px-2 py-0.5 rounded-[3px] bg-[#faf8f5] border border-[#d1d1cd]">
                    Formato: {selectedDraft.formato.replace("_", " ")}
                  </span>
                  <span className="font-mono px-2 py-0.5 rounded-[3px] bg-[#faf8f5] border border-[#d1d1cd]">
                    Gancho: {selectedDraft.gancho.replace("_", " ")}
                  </span>
                  <span className="font-mono">
                    Autor: {selectedDraft.autor}
                  </span>
                </div>

                {/* Workflow Transitions */}
                <div className="flex flex-wrap items-center gap-1.5 pt-2">
                  <span className="font-mono text-[10px] text-[#92918b] mr-1">
                    TRANSICIÓN DE ESTADO:
                  </span>
                  {selectedDraft.estado !== "borrador" && (
                    <button
                      disabled={updatingStatus}
                      onClick={() => handleUpdateStatus(selectedDraft.id, "borrador")}
                      className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] border border-[#d1d1cd] text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 cursor-pointer disabled:opacity-50"
                    >
                      Borrador
                    </button>
                  )}
                  {selectedDraft.estado !== "en_revision" && (
                    <button
                      disabled={updatingStatus}
                      onClick={() => handleUpdateStatus(selectedDraft.id, "en_revision")}
                      className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] border border-[#d1d1cd] text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 cursor-pointer disabled:opacity-50"
                    >
                      En Revisión
                    </button>
                  )}
                  {selectedDraft.estado !== "aprobado" && (
                    <button
                      disabled={updatingStatus}
                      onClick={() => handleUpdateStatus(selectedDraft.id, "aprobado")}
                      className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] border border-[#016a71]/40 text-[#016a71] hover:bg-[#016a71]/10 cursor-pointer disabled:opacity-50 font-medium"
                    >
                      Aprobar
                    </button>
                  )}
                  {selectedDraft.estado !== "publicado" && (
                    <button
                      disabled={updatingStatus}
                      onClick={() => handleUpdateStatus(selectedDraft.id, "publicado")}
                      className="font-mono text-[9px] px-2 py-0.5 rounded-[3px] bg-[#27251e] text-[#faf8f5] hover:bg-black cursor-pointer disabled:opacity-50 font-medium"
                    >
                      Publicar
                    </button>
                  )}
                </div>
              </div>

              {/* Script / Body Content: Markdown Viewer vs Editor */}
              {isEditMode ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs pb-1 border-b border-[#d1d1cd]/60">
                    <span className="font-mono text-[10px] text-[#72706b] uppercase tracking-wider flex items-center space-x-1.5">
                      <Edit3 className="w-3 h-3 text-[#016a71]" />
                      <span>Editor Markdown en Vivo</span>
                    </span>
                    <div className="flex items-center space-x-3">
                      {saveSuccess && (
                        <span className="text-[#016a71] font-mono text-xs flex items-center space-x-1 animate-in fade-in">
                          <Check className="w-3.5 h-3.5" />
                          <span>¡Guardado con éxito!</span>
                        </span>
                      )}
                      <span className="font-mono text-[10px] text-[#92918b]">
                        {editedBody.trim() ? editedBody.trim().split(/\s+/).length : 0} palabras • {editedBody.length} caracteres
                      </span>
                    </div>
                  </div>

                  <textarea
                    value={editedBody}
                    onChange={(e) => setEditedBody(e.target.value)}
                    placeholder="Escribe o edita el guión en formato Markdown..."
                    className="w-full h-[480px] bg-[#faf8f5] border border-[#016a71] rounded-[6px] p-4 text-[#27251e] font-mono text-xs sm:text-[13px] leading-relaxed focus:outline-none focus:ring-1 focus:ring-[#016a71] resize-y shadow-inner"
                  />

                  <div className="flex items-center justify-between pt-1">
                    <button
                      type="button"
                      onClick={() => {
                        setEditedBody(selectedDraft.body || selectedDraft.content || "");
                      }}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-[4px] border border-[#d1d1cd] text-xs text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Restaurar texto original</span>
                    </button>

                    <button
                      type="button"
                      disabled={isSavingDraft}
                      onClick={handleSaveDraft}
                      className="flex items-center space-x-1.5 px-4 py-1.5 rounded-[4px] bg-[#016a71] hover:bg-[#025156] text-[#faf8f5] text-xs font-medium shadow-xs transition cursor-pointer disabled:opacity-50"
                    >
                      {isSavingDraft ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Save className="w-3.5 h-3.5" />
                      )}
                      <span>{isSavingDraft ? "Guardando..." : "Guardar Cambios"}</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-[#faf8f5] rounded-[6px] border border-[#d1d1cd] p-5 text-[#27251e] font-sans text-xs sm:text-[13px] leading-relaxed max-h-[600px] overflow-y-auto select-text selection:bg-[#016a71]/20">
                  {loadingBody ? (
                    <div className="flex items-center space-x-2 text-[#72706b] py-8 justify-center font-mono text-xs">
                      <RefreshCw className="w-4 h-4 animate-spin text-[#016a71]" />
                      <span>Cargando guión editorial...</span>
                    </div>
                  ) : (selectedDraft.body || selectedDraft.content) ? (
                    <div className="prose prose-neutral max-w-none space-y-2">
                      <ReactMarkdown
                        components={{
                          h1: ({ children }) => (
                            <h1 className="text-base sm:text-lg font-semibold text-[#27251e] mt-4 mb-2 pb-1 border-b border-[#d1d1cd] first:mt-0">
                              {children}
                            </h1>
                          ),
                          h2: ({ children }) => (
                            <h2 className="text-sm sm:text-base font-semibold text-[#016a71] mt-3.5 mb-1.5 border-b border-[#d1d1cd]/50 pb-0.5 first:mt-0">
                              {children}
                            </h2>
                          ),
                          h3: ({ children }) => (
                            <h3 className="text-xs sm:text-sm font-semibold text-[#27251e] mt-2.5 mb-1">
                              {children}
                            </h3>
                          ),
                          p: ({ children }) => (
                            <p className="mb-2.5 text-[#27251e] leading-relaxed last:mb-0">
                              {children}
                            </p>
                          ),
                          ul: ({ children }) => (
                            <ul className="list-disc pl-5 mb-2.5 space-y-1 text-[#27251e]">
                              {children}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="list-decimal pl-5 mb-2.5 space-y-1 text-[#27251e]">
                              {children}
                            </ol>
                          ),
                          li: ({ children }) => (
                            <li className="leading-relaxed">{children}</li>
                          ),
                          blockquote: ({ children }) => (
                            <blockquote className="border-l-3 border-[#016a71] pl-3 py-1 my-2.5 bg-[#fdfbfa] italic text-[#72706b] rounded-r">
                              {children}
                            </blockquote>
                          ),
                          code: ({ inline, className, children, ...props }: any) => {
                            return inline ? (
                              <code
                                className="bg-[#f0ece1] text-[#016a71] px-1.5 py-0.5 rounded text-[11px] font-mono"
                                {...props}
                              >
                                {children}
                              </code>
                            ) : (
                              <code
                                className="block bg-[#16181d] text-[#e4e4e7] p-3 rounded-[6px] font-mono text-[11px] my-2 overflow-x-auto border border-[#27251e]/30 leading-normal"
                                {...props}
                              >
                                {children}
                              </code>
                            );
                          },
                          hr: () => <hr className="my-4 border-[#d1d1cd]" />,
                          strong: ({ children }) => (
                            <strong className="font-semibold text-[#181816]">{children}</strong>
                          ),
                          a: ({ href, children }) => (
                            <a
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[#016a71] underline hover:text-[#025156] font-medium"
                            >
                              {children}
                            </a>
                          ),
                        }}
                      >
                        {selectedDraft.body || selectedDraft.content || ""}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <span className="text-[#92918b] italic">Sin contenido redactado para este borrador.</span>
                  )}
                </div>
              )}

              {selectedDraft.file_path && (
                <div className="text-[10px] font-mono text-[#92918b] truncate pt-1">
                  Archivo local: {selectedDraft.file_path}
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-12 text-center text-xs text-[#72706b] space-y-2">
              <Eye className="w-6 h-6 text-[#92918b] mx-auto" />
              <p>Selecciona un borrador de la lista para inspeccionar su guión completo.</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal para Crear / Redactar Borrador con LLM */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-[#fdfbfa] border border-[#d1d1cd] rounded-[8px] max-w-lg w-full p-5 space-y-4 shadow-lg text-[#27251e]">
            <div className="flex items-center justify-between pb-3 border-b border-[#d1d1cd]">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-[#016a71]" />
                <h3 className="text-sm font-medium tracking-tight">
                  Generar Nuevo Guión / Borrador con LLM
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-[#72706b] hover:text-[#27251e] p-1 rounded-[4px] hover:bg-[#d1d1cd]/30"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {modalError && (
              <div className="p-2.5 rounded-[4px] bg-red-50 border border-red-200 text-red-700 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateDraft} className="space-y-3.5">
              <div className="space-y-1">
                <label className="font-mono text-[10px] text-[#72706b] uppercase">
                  Título o Tema Central de la Tendencia
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej. DeepSeek-V3 vs Claude 3.7 en Agentes Financieros"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-[6px] border border-[#d1d1cd] bg-[#faf8f5] text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-mono text-[10px] text-[#72706b] uppercase">
                    Formato Nativo
                  </label>
                  <select
                    value={newFormat}
                    onChange={(e) => setNewFormat(e.target.value)}
                    className="w-full px-3 py-2 rounded-[6px] border border-[#d1d1cd] bg-[#faf8f5] text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
                  >
                    <option value="video_corto">Video Corto (Reels / TikTok / Shorts)</option>
                    <option value="carrusel">Carrusel Ejecutivo (LinkedIn / IG)</option>
                    <option value="hilo_x">Hilo de Análisis (Twitter / X)</option>
                    <option value="articulo_opinion">Artículo de Fondo (Newsletter)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="font-mono text-[10px] text-[#72706b] uppercase">
                    Gancho Psicológico
                  </label>
                  <select
                    value={newHook}
                    onChange={(e) => setNewHook(e.target.value)}
                    className="w-full px-3 py-2 rounded-[6px] border border-[#d1d1cd] bg-[#faf8f5] text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
                  >
                    <option value="opinion">Opinión Polarizante / Disruptiva</option>
                    <option value="caso_estudio">Caso de Estudio Real</option>
                    <option value="revelacion">Revelación de Métricas / Benchmark</option>
                    <option value="pregunta_provocativa">Pregunta Provocativa</option>
                    <option value="antitesis">Antítesis / Contra-narrativa</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-mono text-[10px] text-[#72706b] uppercase">
                  Evidencias / Enlaces de Soporte (1 por línea)
                </label>
                <textarea
                  rows={2}
                  placeholder="https://arxiv.org/...&#10;https://github.com/..."
                  value={newEvidence}
                  onChange={(e) => setNewEvidence(e.target.value)}
                  className="w-full px-3 py-2 rounded-[6px] border border-[#d1d1cd] bg-[#faf8f5] text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
                />
              </div>

              <div className="space-y-1">
                <label className="font-mono text-[10px] text-[#72706b] uppercase">
                  Firma / Autor
                </label>
                <input
                  type="text"
                  value={newAuthor}
                  onChange={(e) => setNewAuthor(e.target.value)}
                  className="w-full px-3 py-2 rounded-[6px] border border-[#d1d1cd] bg-[#faf8f5] text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#d1d1cd]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-2 rounded-[4px] border border-[#d1d1cd] text-xs text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 transition cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isGenerating}
                  className="flex items-center space-x-2 px-3.5 py-2 rounded-[4px] bg-[#27251e] hover:bg-[#000000] text-[#faf8f5] text-xs font-medium transition cursor-pointer disabled:opacity-50 shadow-xs"
                >
                  <Sparkles className={`w-3.5 h-3.5 text-[#016a71] ${isGenerating ? "animate-spin" : ""}`} />
                  <span>{isGenerating ? "Redactando con LLM..." : "Generar Borrador"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
