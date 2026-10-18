"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Terminal,
  Play,
  Square,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
  X,
  Activity,
  Clock,
  Sparkles,
} from "lucide-react";
import { useRadar } from "../context/RadarContext";

interface TerminalConsoleProps {
  embedded?: boolean;
}

export function TerminalConsole({ embedded = false }: TerminalConsoleProps) {
  const {
    runState,
    isTerminalOpen,
    setIsTerminalOpen,
    handleRunRadar,
    handleRunAgentCycle,
    handleRunBackfill,
    handleCancelRun,
  } = useRadar();

  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll al final cuando llegan nuevos logs
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [runState.logs, autoScroll]);

  const handleCopyLogs = () => {
    const text = runState.logs.map((l) => `[${l.time}] ${l.text}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Si no está abierto y es modo flotante/modal, no renderizar
  if (!embedded && !isTerminalOpen) {
    return null;
  }

  return (
    <div
      className={`rounded-[10px] overflow-hidden border border-[#27251e]/30 bg-[#0d0e11] text-[#e4e4e7] shadow-xl transition-all duration-200 ${
        embedded
          ? "w-full"
          : "fixed bottom-5 right-5 z-50 w-[95vw] sm:w-[680px] max-h-[85vh] flex flex-col"
      }`}
    >
      {/* Terminal Title Bar */}
      <div className="flex items-center justify-between px-3.5 py-2.5 bg-[#16181d] border-b border-[#27251e]/50 select-none">
        {/* Left: Window Controls & Title */}
        <div className="flex items-center space-x-2.5">
          <div className="flex items-center space-x-1.5">
            <span
              onClick={() => setIsTerminalOpen(false)}
              className="w-2.5 h-2.5 rounded-full bg-[#ef4444] cursor-pointer hover:opacity-80 transition"
              title="Cerrar consola"
            />
            <span
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-2.5 h-2.5 rounded-full bg-[#f59e0b] cursor-pointer hover:opacity-80 transition"
              title="Minimizar / Expandir"
            />
            <span
              onClick={() => setAutoScroll(!autoScroll)}
              className={`w-2.5 h-2.5 rounded-full cursor-pointer transition ${
                autoScroll ? "bg-[#10b981]" : "bg-[#6b7280]"
              }`}
              title={autoScroll ? "Auto-scroll activado" : "Auto-scroll pausado"}
            />
          </div>

          <div className="flex items-center space-x-2 pl-2 border-l border-[#27251e]/60">
            <Terminal className="w-3.5 h-3.5 text-[#17c0fd]" />
            <span className="font-mono text-xs font-medium tracking-wide text-[#faf8f5]">
              SONAR TERMINAL
            </span>
            <span className="font-mono text-[10px] text-[#71717a] hidden sm:inline">
              // TIEMPO REAL
            </span>
          </div>
        </div>

        {/* Right: State Pill & Controls */}
        <div className="flex items-center space-x-2">
          {runState.is_running ? (
            <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded-[3px] bg-[#016a71]/20 border border-[#016a71]/40 text-[#17c0fd] text-[10px] font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-[#17c0fd] animate-pulse" />
              <span className="font-semibold uppercase tracking-wider">EJECUTANDO</span>
              <span className="text-[#a1a1aa]">({runState.duration_seconds}s)</span>
            </div>
          ) : runState.last_status === "success" ? (
            <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded-[3px] bg-[#10b981]/15 border border-[#10b981]/30 text-[#34d399] text-[10px] font-mono">
              <Check className="w-3 h-3" />
              <span>COMPLETADO ({runState.duration_seconds}s)</span>
            </div>
          ) : runState.last_status === "error" ? (
            <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded-[3px] bg-[#ef4444]/15 border border-[#ef4444]/30 text-[#f87171] text-[10px] font-mono">
              <X className="w-3 h-3" />
              <span>ERROR ({runState.duration_seconds}s)</span>
            </div>
          ) : (
            <div className="px-2 py-0.5 rounded-[3px] bg-[#27251e]/40 text-[#71717a] text-[10px] font-mono">
              IDLE
            </div>
          )}

          <button
            onClick={handleCopyLogs}
            title="Copiar salida de terminal"
            className="p-1 rounded-[3px] text-[#a1a1aa] hover:text-[#faf8f5] hover:bg-[#27251e]/40 transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-[#34d399]" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          {!embedded && (
            <button
              onClick={() => setIsTerminalOpen(false)}
              className="p-1 rounded-[3px] text-[#a1a1aa] hover:text-[#faf8f5] hover:bg-[#27251e]/40 transition"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Progress & Current Phase Sub-bar */}
      <div className="px-3.5 py-2 bg-[#121316] border-b border-[#27251e]/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
        <div className="flex items-center space-x-2 truncate">
          <Activity
            className={`w-3.5 h-3.5 shrink-0 ${
              runState.is_running ? "text-[#17c0fd] animate-spin" : "text-[#71717a]"
            }`}
          />
          <span className="font-mono text-[11px] text-[#a1a1aa] shrink-0 font-medium">Fase:</span>
          <span className="font-mono text-[11px] text-[#faf8f5] truncate font-medium">
            {runState.current_step || "Esperando inicio de proceso"}
          </span>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <div className="w-28 sm:w-36 h-1.5 rounded-full bg-[#27251e] overflow-hidden border border-[#27251e]/60">
            <div
              className={`h-full transition-all duration-300 ${
                runState.last_status === "error"
                  ? "bg-[#ef4444]"
                  : "bg-gradient-to-r from-[#016a71] to-[#17c0fd]"
              }`}
              style={{ width: `${runState.progress_percent || (runState.is_running ? 15 : 0)}%` }}
            />
          </div>
          <span className="font-mono text-[10px] text-[#71717a]">
            {runState.progress_percent}%
          </span>
        </div>
      </div>

      {/* Terminal Log Console */}
      <div
        ref={logContainerRef}
        className={`p-3.5 font-mono text-[11px] leading-relaxed overflow-y-auto bg-[#090a0c] select-text transition-all duration-200 ${
          isExpanded ? "h-[500px]" : embedded ? "h-[260px] sm:h-[300px]" : "h-[320px]"
        }`}
      >
        {runState.logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-2 text-[#71717a]">
            <Terminal className="w-8 h-8 text-[#27251e]" />
            <p className="text-xs">Consola de ejecución lista.</p>
            <p className="text-[10px] text-[#52525b]">
              Haz clic en &quot;Actualizar Sonar&quot; para ver la recolección, clustering y evaluación de Jev línea a línea.
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {runState.logs.map((log) => {
              const isStep = log.level === "step";
              const isSuccess = log.level === "success";
              const isWarning = log.level === "warning";
              const isError = log.level === "error";

              return (
                <div
                  key={log.id}
                  className={`flex items-start space-x-2 py-0.5 rounded px-1 -mx-1 transition-colors ${
                    isStep
                      ? "bg-[#016a71]/15 text-[#17c0fd] font-semibold border-l-2 border-[#17c0fd]"
                      : isSuccess
                      ? "text-[#34d399]"
                      : isWarning
                      ? "text-[#fbbf24]"
                      : isError
                      ? "text-[#f87171] bg-[#ef4444]/10 font-medium"
                      : "text-[#d4d4d8] hover:bg-[#16181d]/50"
                  }`}
                >
                  <span className="text-[#52525b] shrink-0 select-none text-[10px]">
                    {log.time}
                  </span>
                  <span className="break-all whitespace-pre-wrap">{log.text}</span>
                </div>
              );
            })}

            {runState.is_running && (
              <div className="flex items-center space-x-1.5 pt-1 text-[#17c0fd] animate-pulse">
                <span>&gt;</span>
                <span className="w-1.5 h-3 bg-[#17c0fd]" />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Command Bar & Action Triggers */}
      <div className="px-3 py-2 bg-[#121316] border-t border-[#27251e]/40 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center space-x-2 truncate text-[#71717a] font-mono text-[10px]">
          <span>CMD:</span>
          <code className="text-[#17c0fd] bg-[#090a0c] px-1.5 py-0.5 rounded border border-[#27251e]/60 truncate">
            {runState.command || "python run.py run-all --top 10"}
          </code>
        </div>

        <div className="flex items-center space-x-1.5">
          {runState.is_running ? (
            <button
              onClick={handleCancelRun}
              className="flex items-center space-x-1 px-2.5 py-1 rounded bg-[#ef4444]/20 hover:bg-[#ef4444]/30 border border-[#ef4444]/40 text-[#f87171] text-[11px] font-mono font-medium transition cursor-pointer"
            >
              <Square className="w-3 h-3 fill-current" />
              <span>Detener</span>
            </button>
          ) : (
            <>
              <button
                onClick={handleRunRadar}
                className="flex items-center space-x-1 px-2.5 py-1 rounded bg-[#016a71] hover:bg-[#025156] text-[#faf8f5] text-[11px] font-mono font-medium transition cursor-pointer"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>Ejecutar Sonar</span>
              </button>
              <button
                onClick={handleRunAgentCycle}
                className="flex items-center space-x-1 px-2 py-1 rounded border border-[#27251e] text-[#a1a1aa] hover:text-[#faf8f5] hover:bg-[#1f2228] text-[10px] font-mono transition cursor-pointer"
                title="Ciclo multi-agente 12h"
              >
                <span>Ciclo 12h</span>
              </button>
              <button
                onClick={handleRunBackfill}
                className="flex items-center space-x-1 px-2 py-1 rounded border border-[#27251e] text-[#a1a1aa] hover:text-[#faf8f5] hover:bg-[#1f2228] text-[10px] font-mono transition cursor-pointer"
                title="Backfill 90 días"
              >
                <span>Backfill 90d</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
