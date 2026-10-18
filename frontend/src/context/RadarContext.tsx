"use client";

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { getApiBase } from "../types/radar";

export interface TerminalLog {
  id: number;
  time: string;
  text: string;
  level: "info" | "warning" | "error" | "success" | "step";
}

export interface RunState {
  is_running: boolean;
  last_run: string | null;
  last_status: "idle" | "running" | "success" | "error" | "cancelled";
  last_error: string | null;
  command_label: string;
  command: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number;
  current_step: string;
  progress_percent: number;
  logs: TerminalLog[];
  total_logs: number;
}

const initialRunState: RunState = {
  is_running: false,
  last_run: null,
  last_status: "idle",
  last_error: null,
  command_label: "Ninguna",
  command: "",
  started_at: null,
  finished_at: null,
  duration_seconds: 0,
  current_step: "Listo",
  progress_percent: 0,
  logs: [],
  total_logs: 0,
};

interface RadarContextType {
  isRunningRadar: boolean;
  statusMessage: string | null;
  reportWeek: string;
  runState: RunState;
  isTerminalOpen: boolean;
  refreshTrigger: number;
  setReportWeek: (week: string) => void;
  setStatusMessage: (msg: string | null) => void;
  setIsTerminalOpen: (open: boolean) => void;
  handleRunRadar: () => Promise<void>;
  handleRunAgentCycle: () => Promise<void>;
  handleRunBackfill: () => Promise<void>;
  handleCancelRun: () => Promise<void>;
}

const RadarContext = createContext<RadarContextType | undefined>(undefined);

export function RadarProvider({ children }: { children: React.ReactNode }) {
  const [runState, setRunState] = useState<RunState>(initialRunState);
  const [isTerminalOpen, setIsTerminalOpen] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [reportWeek, setReportWeek] = useState<string>("2026-W42");
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);
  const wasRunningRef = useRef<boolean>(false);

  const showStatus = (msg: string) => {
    setStatusMessage(msg);
    setTimeout(() => setStatusMessage(null), 6000);
  };

  const pollStatus = useCallback(async () => {
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/status?_t=${Date.now()}`, {
        cache: "no-store",
        headers: { "Pragma": "no-cache", "Cache-Control": "no-cache" },
      });
      if (res.ok) {
        const data: RunState = await res.json();
        setRunState(data);

        // Detectar transición de ejecución terminada
        if (wasRunningRef.current && !data.is_running) {
          if (data.last_status === "success") {
            showStatus(`✨ Sonar completado con éxito (${data.duration_seconds}s). Reporte actualizado.`);
            setRefreshTrigger((prev) => prev + 1);
            if (typeof window !== "undefined") {
              window.dispatchEvent(new CustomEvent("sonar:report-updated"));
            }
          } else if (data.last_status === "error") {
            showStatus(`❌ Error en ejecución: ${data.last_error || "Revisa la consola de terminal."}`);
          }
        }
        wasRunningRef.current = data.is_running;
      }
    } catch {
      // Ignorar fallos transitorios de red durante polling
    }
  }, []);

  // Polling periódico cuando hay un proceso en curso o al montar
  useEffect(() => {
    pollStatus();
    const interval = setInterval(() => {
      pollStatus();
    }, runState.is_running ? 800 : 3000);

    return () => clearInterval(interval);
  }, [runState.is_running, pollStatus]);

  const handleRunRadar = async () => {
    setIsTerminalOpen(true);
    showStatus("Iniciando escaneo completo del pipeline Sonar...");
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/run`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        showStatus("Proceso iniciado en terminal. Visualizando salida en tiempo real...");
        pollStatus();
      } else {
        showStatus(data.message || data.error || "Aviso en la ejecución.");
      }
    } catch {
      showStatus("Error conectando con el servidor web.");
    }
  };

  const handleRunAgentCycle = async () => {
    setIsTerminalOpen(true);
    showStatus("Disparando ciclo de agentes de 12 horas en terminal...");
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/agents/cycle`, { method: "POST" });
      const data = await res.json();
      showStatus(data.message || "Ciclo de agentes iniciado en tiempo real.");
      pollStatus();
    } catch {
      showStatus("Error al contactar orquestador de agentes.");
    }
  };

  const handleRunBackfill = async () => {
    setIsTerminalOpen(true);
    showStatus("Iniciando backfill histórico de 90 días en terminal...");
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/agents/backfill`, { method: "POST" });
      const data = await res.json();
      showStatus(data.message || "Backfill histórico iniciado en tiempo real.");
      pollStatus();
    } catch {
      showStatus("Error al iniciar backfill histórico.");
    }
  };

  const handleCancelRun = async () => {
    try {
      const api = getApiBase();
      const res = await fetch(`${api}/api/run/cancel`, { method: "POST" });
      const data = await res.json();
      showStatus(data.message || "Solicitud de cancelación enviada.");
      pollStatus();
    } catch {
      showStatus("Error cancelando ejecución.");
    }
  };

  return (
    <RadarContext.Provider
      value={{
        isRunningRadar: runState.is_running,
        statusMessage,
        reportWeek,
        runState,
        isTerminalOpen,
        refreshTrigger,
        setReportWeek,
        setStatusMessage,
        setIsTerminalOpen,
        handleRunRadar,
        handleRunAgentCycle,
        handleRunBackfill,
        handleCancelRun,
      }}
    >
      {children}
    </RadarContext.Provider>
  );
}

export function useRadar() {
  const ctx = useContext(RadarContext);
  if (!ctx) {
    throw new Error("useRadar debe utilizarse dentro de un RadarProvider");
  }
  return ctx;
}
