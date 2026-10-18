"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  TrendingUp,
  BookOpen,
  SlidersHorizontal,
  Gauge,
  RefreshCw,
  Activity,
  Database,
  Menu,
  X,
  Sparkles,
  Compass,
  FileText,
  MessageSquare,
  Library,
  HelpCircle,
  Terminal,
} from "lucide-react";
import { useRadar } from "../context/RadarContext";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  tag?: string;
}

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const {
    isRunningRadar,
    reportWeek,
    runState,
    isTerminalOpen,
    setIsTerminalOpen,
    handleRunRadar,
    handleRunAgentCycle,
    handleRunBackfill,
  } = useRadar();

  const navSections: { label: string; items: NavItem[] }[] = [
    {
      label: "EXPLORAR",
      items: [
        {
          name: "Tendencias Top 10",
          href: "/",
          icon: TrendingUp,
          tag: "Top",
        },
      ],
    },
    {
      label: "CREACIÓN EDITORIAL",
      items: [
        {
          name: "Borradores & Guiones",
          href: "/borradores",
          icon: FileText,
          tag: "IA",
        },
      ],
    },
    {
      label: "INTELIGENCIA RAG",
      items: [
        {
          name: "Chatbot RAG",
          href: "/chat",
          icon: MessageSquare,
          tag: "T0",
        },
        {
          name: "Base de Conocimiento",
          href: "/conocimiento",
          icon: BookOpen,
          tag: "Pool",
        },
      ],
    },
    {
      label: "FUENTES & CANALES",
      items: [
        {
          name: "Enfoques & RSS.app",
          href: "/enfoques",
          icon: SlidersHorizontal,
        },
        {
          name: "Bibliografía de Fuentes",
          href: "/bibliografia",
          icon: Library,
          tag: "11",
        },
      ],
    },
    {
      label: "CALIBRACIÓN",
      items: [
        {
          name: "Playground JEV",
          href: "/playground",
          icon: Gauge,
        },
      ],
    },
  ];

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/" || pathname === "";
    }
    return pathname.startsWith(href);
  };

  const navContent = (
    <div className="flex flex-col h-full min-h-0 justify-between p-3.5 sm:p-4 custom-sidebar-scroll">
      <div className="space-y-4 sm:space-y-5">
        {/* Brand Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#d1d1cd]/70 shrink-0">
          <Link
            href="/"
            onClick={() => setMobileOpen(false)}
            className="flex items-center space-x-2.5 group"
          >
            <div className="w-8 h-8 rounded-[6px] bg-[#27251e] flex items-center justify-center text-[#faf8f5] shadow-xs shrink-0">
              <Compass className="w-4 h-4 text-[#016a71] group-hover:rotate-45 transition-transform duration-300" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-1.5">
                <span className="font-medium text-[15px] tracking-tight text-[#27251e] truncate">
                  SONAR
                </span>
                <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71] shrink-0"></span>
              </div>
              <p className="text-[10px] text-[#72706b] font-normal tracking-wide truncate">
                Inteligencia Editorial
              </p>
            </div>
          </Link>

          {/* Close button on mobile */}
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1.5 text-[#72706b] hover:text-[#27251e] rounded-[4px] hover:bg-[#d1d1cd]/30"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Sections */}
        <nav className="space-y-4 sm:space-y-4.5">
          {navSections.map((section) => (
            <div key={section.label} className="space-y-1">
              <div className="px-2.5 py-1 text-[11px] font-mono font-medium text-[#92918b] tracking-wider">
                {section.label}
              </div>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const active = isActive(item.href);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMobileOpen(false)}
                      className={`flex items-center justify-between px-2.5 py-2 rounded-[6px] text-[13px] transition duration-150 ${
                        active
                          ? "bg-[#016a71] text-[#faf8f5] font-medium shadow-xs"
                          : "text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/25 font-normal"
                      }`}
                    >
                      <div className="flex items-center space-x-2.5 min-w-0">
                        <Icon
                          className={`w-4 h-4 shrink-0 ${
                            active ? "text-[#faf8f5]" : "text-[#72706b]"
                          }`}
                        />
                        <span className="truncate">{item.name}</span>
                      </div>
                      {item.tag && (
                        <span
                          className={`text-[9px] font-mono px-1.5 py-0.5 rounded-[3px] shrink-0 ${
                            active
                              ? "bg-white/20 text-[#faf8f5]"
                              : "bg-[#d1d1cd]/50 text-[#72706b]"
                          }`}
                        >
                          {item.tag}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* Bottom Controls & Pipeline Trigger */}
      <div data-tour="tour-radar-action" className="shrink-0 pt-3 border-t border-[#d1d1cd]/70 space-y-2.5 mt-4">
        {/* Status week pill */}
        <div className="flex items-center justify-between px-2 text-[11px] text-[#72706b]">
          <span className="font-mono">SEMANA {reportWeek}</span>
          <span className="flex items-center space-x-1.5">
            <span className="w-1.5 h-1.5 rounded-[2px] bg-[#016a71] animate-pulse"></span>
            <span className="font-normal text-[10px]">Activo</span>
          </span>
        </div>

        {/* Primary Action Button */}
        <button
          onClick={handleRunRadar}
          disabled={isRunningRadar}
          className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-[4px] bg-[#27251e] hover:bg-[#000000] text-[#faf8f5] text-xs font-medium transition duration-150 disabled:opacity-50 shadow-xs cursor-pointer"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${isRunningRadar ? "animate-spin" : ""}`}
          />
          <span>{isRunningRadar ? "Escaneando..." : "Actualizar Sonar"}</span>
        </button>

        {/* Secondary Low-emphasis Actions */}
        <div className="grid grid-cols-2 gap-1.5 pt-0.5">
          <button
            onClick={handleRunAgentCycle}
            disabled={isRunningRadar}
            title="Ciclo multi-agente de 12 horas"
            className="flex items-center justify-center space-x-1 px-2 py-1.5 rounded-[4px] border border-[#d1d1cd] text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 text-[11px] font-normal transition duration-150 disabled:opacity-50 cursor-pointer"
          >
            <Activity className="w-3 h-3 text-[#016a71]" />
            <span className="truncate">Ciclo 12h</span>
          </button>
          <button
            onClick={handleRunBackfill}
            disabled={isRunningRadar}
            title="Backfill histórico de 90 días"
            className="flex items-center justify-center space-x-1 px-2 py-1.5 rounded-[4px] border border-[#d1d1cd] text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20 text-[11px] font-normal transition duration-150 disabled:opacity-50 cursor-pointer"
          >
            <Database className="w-3 h-3 text-[#72706b]" />
            <span className="truncate">Backfill 90d</span>
          </button>
        </div>

        {/* Terminal Live Monitor Button */}
        <button
          onClick={() => setIsTerminalOpen(!isTerminalOpen)}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-[4px] border text-[11px] font-mono transition duration-150 cursor-pointer ${
            runState.is_running
              ? "border-[#17c0fd]/40 bg-[#016a71]/15 text-[#17c0fd]"
              : isTerminalOpen
              ? "border-[#27251e] bg-[#27251e] text-[#faf8f5]"
              : "border-[#d1d1cd] text-[#72706b] hover:text-[#27251e] hover:bg-[#d1d1cd]/20"
          }`}
          title="Abrir consola de terminal en tiempo real"
        >
          <div className="flex items-center space-x-1.5 truncate">
            <Terminal className="w-3 h-3 shrink-0" />
            <span className="truncate">Terminal en Vivo</span>
          </div>
          {runState.is_running ? (
            <span className="flex items-center space-x-1 shrink-0 text-[9px] font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-[#17c0fd] animate-ping" />
              <span>{runState.duration_seconds}s</span>
            </span>
          ) : (
            <span className="text-[9px] text-[#92918b]">
              {isTerminalOpen ? "Abierta" : "Ver"}
            </span>
          )}
        </button>

        {/* Footer info & Actions */}
        <div className="pt-1.5 flex items-center justify-between text-[10px] text-[#92918b] font-mono">
          <button
            onClick={() => {
              if (typeof window !== "undefined") {
                window.dispatchEvent(new CustomEvent("start-radar-tour"));
              }
            }}
            className="hover:text-[#016a71] transition-colors cursor-pointer flex items-center space-x-1 text-[#72706b]"
            title="Ver tutorial interactivo de la sección activa"
          >
            <HelpCircle className="w-3 h-3 text-[#016a71]" />
            <span>Tutorial</span>
          </button>
          <button
            onClick={() => {
              if (typeof window !== "undefined") {
                sessionStorage.removeItem("sonar_intro_viewed");
                window.location.reload();
              }
            }}
            className="hover:text-[#016a71] transition-colors cursor-pointer underline"
            title="Reproducir animación de intro de Sonar"
          >
            Ver Intro
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Top Header */}
      <div className="md:hidden flex items-center justify-between px-4 py-3 bg-[#faf8f5] border-b border-[#d1d1cd] sticky top-0 z-40">
        <Link href="/" className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-[4px] bg-[#27251e] flex items-center justify-center text-[#faf8f5]">
            <Compass className="w-3.5 h-3.5 text-[#016a71]" />
          </div>
          <span className="font-medium text-sm text-[#27251e]">SONAR</span>
        </Link>
        <button
          onClick={() => setMobileOpen(true)}
          className="p-1.5 text-[#72706b] hover:text-[#27251e] border border-[#d1d1cd] rounded-[4px] bg-[#fdfbfa]"
        >
          <Menu className="w-4 h-4" />
        </button>
      </div>

      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 bg-black/20 backdrop-blur-xs z-50 md:hidden"
        />
      )}

      {/* Mobile Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 w-72 max-w-[85vw] bg-[#faf8f5] border-r border-[#d1d1cd] z-50 transition-transform duration-200 ease-in-out md:hidden flex flex-col h-full ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {navContent}
      </aside>

      {/* Desktop Fixed Left-Rail Sidebar */}
      <aside className="hidden md:flex flex-col w-56 lg:w-64 shrink-0 bg-[#faf8f5] border-r border-[#d1d1cd] h-screen sticky top-0 select-none z-30">
        {navContent}
      </aside>
    </>
  );
}
