"use client";

import React, { useState, useEffect } from "react";
import {
  Gauge,
  Play,
  Cpu,
  Brain,
  Shield,
  TrendingUp,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { PlaygroundResult, getApiBase } from "../../types/radar";
import { useRadar } from "../../context/RadarContext";

export default function PlaygroundPage() {
  const [playgroundHeadline, setPlaygroundHeadline] = useState(
    "Claude 3.5 Sonnet supera a modelos propietarios en benchmarks de razonamiento"
  );
  const [playgroundVph, setPlaygroundVph] = useState(350);
  const [playgroundSources, setPlaygroundSources] = useState<string[]>([
    "HackerNews",
    "YouTube",
    "GitHub",
  ]);
  const [isEvaluatingPlayground, setIsEvaluatingPlayground] = useState(false);
  const [playgroundResult, setPlaygroundResult] = useState<PlaygroundResult | null>(null);

  const { setStatusMessage } = useRadar();

  const presets = [
    {
      label: "Claude 3.5 Benchmarks",
      headline: "Claude 3.5 Sonnet supera a modelos propietarios en benchmarks de razonamiento",
      vph: 450,
      sources: ["HackerNews", "YouTube", "GitHub"],
    },
    {
      label: "Seguridad & Sandboxing",
      headline: "Falla crítica en sandboxing de agentes autónomos permite ejecución remota",
      vph: 320,
      sources: ["HackerNews", "Twitter", "GitHub"],
    },
    {
      label: "Fintech ROI LatAm",
      headline: "Banco regional en Brasil ahorra 40% operativo implementando agentes de conciliación",
      vph: 180,
      sources: ["LinkedIn", "GoogleNews"],
    },
  ];

  useEffect(() => {
    // Evaluar automáticamente el preset por defecto al cargar la página
    handleEvaluatePlayground();
  }, []);

  const handleEvaluatePlayground = async (headlineOverride?: string, vphOverride?: number, sourcesOverride?: string[]) => {
    const headline = headlineOverride || playgroundHeadline;
    const vph = vphOverride || playgroundVph;
    const sources = sourcesOverride || playgroundSources;

    if (!headline.trim()) {
      setStatusMessage("Por favor ingresa un titular para evaluar.");
      return;
    }

    const api = getApiBase();
    setIsEvaluatingPlayground(true);
    try {
      const res = await fetch(`${api}/api/playground/eval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tema: headline.trim(),
          headline: headline.trim(),
          vistas_por_hora: vph,
          fuentes: sources,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPlaygroundResult(data);
      } else {
        const err = await res.json();
        setStatusMessage(err.error || "Error al evaluar con TypeSafe Jev.");
      }
    } catch {
      setStatusMessage("Error conectando con el evaluador de Jev.");
    } finally {
      setIsEvaluatingPlayground(false);
    }
  };

  const toggleSource = (source: string) => {
    setPlaygroundSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source]
    );
  };

  const applyPreset = (preset: (typeof presets)[0]) => {
    setPlaygroundHeadline(preset.headline);
    setPlaygroundVph(preset.vph);
    setPlaygroundSources(preset.sources);
    handleEvaluatePlayground(preset.headline, preset.vph, preset.sources);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <section className="text-center max-w-2xl mx-auto space-y-2 pt-2">
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-[4px] bg-[#016a71]/10 border border-[#016a71]/20 text-[#016a71]">
          <Gauge className="w-3.5 h-3.5 text-[#016a71]" />
          <span className="font-mono text-[10px] tracking-wider font-medium uppercase">
            TYPESAFE JEV REAL-TIME CALIBRATOR
          </span>
        </div>
        <h1 className="text-3xl text-[#27251e] font-normal tracking-tight">
          Playground de Evaluación <span className="text-[#016a71] font-medium">JEV</span>
        </h1>
        <p className="text-[14px] text-[#72706b] font-normal leading-relaxed">
          Simulación probabilística de señales emergentes. Prueba titulares hipotéticos o señales
          detectadas para observar la toma de decisiones algorítmica de TypeSafe Jev.
        </p>
      </section>

      {/* Preset Selector */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] text-[#72706b] uppercase mr-1">PRESETS RÁPIDOS:</span>
        {presets.map((p, idx) => (
          <button
            key={idx}
            onClick={() => applyPreset(p)}
            className="font-mono text-[10px] px-2.5 py-1 rounded-[4px] bg-[#fdfbfa] hover:bg-[#faf8f5] text-[#27251e] border border-[#d1d1cd] transition cursor-pointer"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Simulator Inputs Console */}
      <section data-tour="playground-input" className="rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] p-5 space-y-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="space-y-1">
          <label className="font-mono text-[10px] text-[#72706b] uppercase">
            TITULAR O TEMA A CALIBRAR
          </label>
          <input
            type="text"
            value={playgroundHeadline}
            onChange={(e) => setPlaygroundHeadline(e.target.value)}
            placeholder="Ej: OpenAI lanza nuevo framework de orquestación de agentes..."
            className="w-full bg-[#faf8f5] border border-[#d1d1cd] rounded-[6px] px-3 py-2 text-xs text-[#27251e] focus:outline-none focus:border-[#016a71]"
          />
        </div>

        {/* Sliders and Sources */}
        <div data-tour="playground-jev-weights" className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* VPH Slider */}
          <div className="space-y-1.5 p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd]">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-[#72706b] uppercase">
                VELOCIDAD SIMULADA (VPH)
              </span>
              <span className="font-mono text-xs font-medium text-[#016a71]">
                {playgroundVph} vistas/hora
              </span>
            </div>
            <input
              type="range"
              min="10"
              max="1200"
              step="10"
              value={playgroundVph}
              onChange={(e) => setPlaygroundVph(Number(e.target.value))}
              className="w-full accent-[#016a71] cursor-pointer"
            />
            <div className="flex justify-between text-[9px] font-mono text-[#72706b]">
              <span>10 vph (Nicho)</span>
              <span>400 vph (Emergente)</span>
              <span>1200 vph (Viral)</span>
            </div>
          </div>

          {/* Sources Checkboxes */}
          <div className="space-y-1.5 p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd]">
            <span className="font-mono text-[10px] text-[#72706b] uppercase">
              FUENTES DE COBERTURA SIMULADAS
            </span>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {["HackerNews", "YouTube", "GitHub", "Twitter", "GoogleNews", "LinkedIn"].map((src) => {
                const active = playgroundSources.includes(src);
                return (
                  <button
                    key={src}
                    type="button"
                    onClick={() => toggleSource(src)}
                    className={`font-mono text-[10px] px-2 py-1 rounded-[3px] border transition cursor-pointer ${
                      active
                        ? "bg-[#016a71] text-[#faf8f5] border-[#016a71]"
                        : "bg-[#fdfbfa] text-[#72706b] border-[#d1d1cd]"
                    }`}
                  >
                    {src}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <button
          onClick={() => handleEvaluatePlayground()}
          disabled={isEvaluatingPlayground}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2 rounded-[4px] bg-[#27251e] hover:bg-black text-[#faf8f5] text-xs font-medium transition cursor-pointer shadow-xs disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5 fill-current text-[#016a71]" />
          <span>{isEvaluatingPlayground ? "Consultando TypeSafe Jev..." : "Evaluar con TypeSafe Jev"}</span>
        </button>
      </section>

      {/* Evaluation Results */}
      {playgroundResult && (
        <section data-tour="playground-output" className="space-y-4 animate-in fade-in duration-150">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71]"></span>
              <h3 className="text-base font-medium text-[#27251e]">
                Resultado de la Calibración JEV
              </h3>
            </div>
            <span className="font-mono text-[10px] text-[#72706b]">
              Latencia: {playgroundResult.latencia_ms}ms // Motor: {playgroundResult.motor_utilizado}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Score Card */}
            <div className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-2 shadow-[0_1px_2px_rgba(0,0,0,0.03)] flex flex-col justify-between">
              <span className="font-mono text-[10px] text-[#72706b] uppercase">SCORE RADAR30X</span>
              <div className="text-3xl font-mono font-medium text-[#016a71]">
                {playgroundResult.score_final}
              </div>
              <div className="text-xs text-[#72706b]">
                Clasificación: <span className="font-medium text-[#27251e]">{playgroundResult.crecimiento_label}</span>
              </div>
            </div>

            {/* Decision Summary */}
            <div className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-2 shadow-[0_1px_2px_rgba(0,0,0,0.03)] md:col-span-2">
              <span className="font-mono text-[10px] text-[#72706b] uppercase">DECISIÓN EDITORIAL</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                <div className="p-2 rounded-[4px] bg-[#faf8f5] border border-[#d1d1cd]">
                  <span className="font-mono text-[9px] text-[#72706b]">FASE</span>
                  <div className="text-xs font-medium text-[#27251e]">{playgroundResult.decision.fase}</div>
                </div>
                <div className="p-2 rounded-[4px] bg-[#faf8f5] border border-[#d1d1cd]">
                  <span className="font-mono text-[9px] text-[#72706b]">GANCHO</span>
                  <div className="text-xs font-medium text-[#27251e]">{playgroundResult.decision.gancho}</div>
                </div>
                <div className="p-2 rounded-[4px] bg-[#faf8f5] border border-[#d1d1cd]">
                  <span className="font-mono text-[9px] text-[#72706b]">FORMATO</span>
                  <div className="text-xs font-medium text-[#27251e]">{playgroundResult.decision.formato}</div>
                </div>
                <div className="p-2 rounded-[4px] bg-[#faf8f5] border border-[#d1d1cd]">
                  <span className="font-mono text-[9px] text-[#72706b]">CONFIANZA</span>
                  <div className="text-xs font-medium text-[#016a71]">
                    {(playgroundResult.decision.confianza * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 5 Questions Breakdown */}
          <div className="p-4 rounded-[8px] bg-[#fdfbfa] border border-[#d1d1cd] space-y-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
            <span className="font-mono text-[10px] text-[#016a71] font-medium uppercase tracking-wider">
              DESGLOSE DE LAS 5 PREGUNTAS CLAVE DE JEV
            </span>
            <div className="space-y-2">
              {playgroundResult.preguntas_jev.map((q, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-[6px] bg-[#faf8f5] border border-[#d1d1cd] space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[9px] text-[#72706b]">PREGUNTA {idx + 1}</span>
                    <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-[2px] bg-[#016a71]/10 text-[#016a71] border border-[#016a71]/20 font-medium">
                      {q.respuesta || "Evaluado"}
                    </span>
                  </div>
                  <h4 className="text-xs font-medium text-[#27251e]">{q.pregunta}</h4>
                  {q.razonamiento && (
                    <p className="text-[11px] text-[#72706b] font-normal leading-relaxed">{q.razonamiento}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
