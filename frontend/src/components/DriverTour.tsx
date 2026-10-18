"use client";

import React, { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { driver, Driver } from "driver.js";
import "driver.js/dist/driver.css";
import { HelpCircle, Sparkles } from "lucide-react";

interface TourStep {
  element: string;
  popover: {
    title: string;
    description: string;
    side?: "top" | "right" | "bottom" | "left";
    align?: "start" | "center" | "end";
  };
}

const ROUTE_TOURS: Record<
  string,
  { title: string; badge: string; steps: TourStep[] }
> = {
  "/": {
    title: "Tendencias Top 10 & Embudo",
    badge: "Radar Semanal",
    steps: [
      {
        element: '[data-tour="tour-radar-action"]',
        popover: {
          title: "Actualización & Agentes",
          description:
            "Dispara el escaneo en tiempo real de fuentes públicas o activa el ciclo de 12h con los 3 agentes (Explorador, Historiador y Crítico).",
          side: "right",
        },
      },
      {
        element: '[data-tour="tour-hero-stats"]',
        popover: {
          title: "Búsqueda & Filtros de Formato",
          description:
            "Filtra temas por palabras clave o formato nativo (hilo, video corto, carrusel) y revisa el conteo de clusters evaluados.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="tour-top-cards"]',
        popover: {
          title: "Tarjetas de Tendencias Aprobadas",
          description:
            "Cada tarjeta condensa el gancho psicológico, ángulo editorial para líderes LatAm, veredicto JEV y enlaces directos verificados.",
          side: "top",
        },
      },
      {
        element: '[data-tour="tour-observation-funnel"]',
        popover: {
          title: "Embudo de Observación y Descarte",
          description:
            "Monitorea temas nacientes en observación y audita las publicaciones descartadas por clickbait o falta de sustento empírico.",
          side: "top",
        },
      },
    ],
  },
  "/conocimiento": {
    title: "Base de Conocimiento Multimodal",
    badge: "Memoria 90d",
    steps: [
      {
        element: '[data-tour="knowledge-metrics"]',
        popover: {
          title: "Consola de Ingesta & Modalidades",
          description:
            "Elige el modo de extracción: Completo (visión + audio + texto), Palabras Clave o Solo Ganchos psicológicos.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="knowledge-format-pills"]',
        popover: {
          title: "Pool Multimodal de Entrada",
          description:
            "Ingesta lotes de imágenes, infografías, transcripciones de video, documentos PDF o enlaces web directos.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="knowledge-search"]',
        popover: {
          title: "Búsqueda Semántica Vectorial",
          description:
            "Consulta en lenguaje natural sobre la memoria de 90 días con cálculo de similitud coseno sobre los embeddings.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="knowledge-grid"]',
        popover: {
          title: "Catálogo de Recursos Indexados",
          description:
            "Explora todos los ítems almacenados en SQLite con autor, fecha, URL y ganchos estructurados para alimentar el radar.",
          side: "top",
        },
      },
    ],
  },
  "/enfoques": {
    title: "Enfoques & Canales RSS.app",
    badge: "Curaduría",
    steps: [
      {
        element: '[data-tour="focus-tracks"]',
        popover: {
          title: "Tracks Temáticos Prioritarios",
          description:
            "Activa o pausa los ángulos estratégicos de búsqueda (Agentes de Voz, Modelos SLM, SWE-bench, GraphRAG, etc.).",
          side: "top",
        },
      },
      {
        element: '[data-tour="focus-create-btn"]',
        popover: {
          title: "Crear Nuevo Enfoque",
          description:
            "Agrega un nuevo track editorial con palabras clave específicas que orientarán las consultas automáticas de Sonar.",
          side: "left",
        },
      },
      {
        element: '[data-tour="focus-web-search"]',
        popover: {
          title: "Sonda Web en Vivo (DuckDuckGo)",
          description:
            "Prueba consultas directas en tiempo real para verificar qué resultados indexa el motor de búsqueda en la web abierta.",
          side: "top",
        },
      },
      {
        element: '[data-tour="rssapp-feeds"]',
        popover: {
          title: "Hub de Sindicación RSS.app",
          description:
            "Conecta feeds sindicados de Twitter/X, TikTok, LinkedIn y YouTube para capturar señales virales sin APIs propietarias.",
          side: "top",
        },
      },
    ],
  },
  "/borradores": {
    title: "Borradores & Guiones IA",
    badge: "Redacción",
    steps: [
      {
        element: '[data-tour="drafts-sidebar"]',
        popover: {
          title: "Temas Seleccionables",
          description:
            "Elige cualquiera de las tendencias aprobadas del Radar o abre un borrador generado previamente en el historial.",
          side: "right",
        },
      },
      {
        element: '[data-tour="drafts-config"]',
        popover: {
          title: "Parámetros Editoriales",
          description:
            "Configura el formato (post LinkedIn/X, guion video corto, newsletter), la audiencia directiva y el tono.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="drafts-generate"]',
        popover: {
          title: "Generación Asistida por LLM",
          description:
            "El modelo genera la redacción completa integrando ganchos psicológicos, adaptaciones y enlaces de evidencia directa.",
          side: "top",
        },
      },
      {
        element: '[data-tour="drafts-editor"]',
        popover: {
          title: "Editor Markdown & Copia",
          description:
            "Revisa, ajusta el borrador en vivo y cópialo al portapapeles listo para su publicación o distribución en equipo.",
          side: "left",
        },
      },
    ],
  },
  "/chat": {
    title: "Chatbot Determinista RAG T0",
    badge: "Consultas",
    steps: [
      {
        element: '[data-tour="chat-t0-input"]',
        popover: {
          title: "Consulta Determinista T0",
          description:
            "Formula preguntas sobre tendencias o pide comparar temas. Cada respuesta cita obligatoriamente las fuentes primarias del radar.",
          side: "top",
        },
      },
      {
        element: '[data-tour="chat-suggestions"]',
        popover: {
          title: "Preguntas Estratégicas Predefinidas",
          description:
            "Accede con un clic a consultas clave para directores: comparativas de modelos, ROI y mitigación de riesgos de API.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="chat-audit-box"]',
        popover: {
          title: "Auditoría de Citas & Trazabilidad",
          description:
            "Panel donde se muestran las evidencias crudas, autor y métricas exactas que respaldan cada respuesta generada.",
          side: "top",
        },
      },
    ],
  },
  "/playground": {
    title: "Playground de Calibración JEV",
    badge: "Simulador",
    steps: [
      {
        element: '[data-tour="playground-input"]',
        popover: {
          title: "Entrada de Señales Crudas",
          description:
            "Introduce un tema hipotético con métricas de tracción para poner a prueba el algoritmo de puntuación.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="playground-jev-weights"]',
        popover: {
          title: "Calibración de Ponderaciones",
          description:
            "Ajusta los pesos asignados a novedad, velocidad temporal, diversidad multi-fuente y afinidad con líderes LatAm.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="playground-output"]',
        popover: {
          title: "Simulación de Veredicto",
          description:
            "Comprueba el desglose de la fórmula matemática y si el tema clasifica como APROBADO o EN OBSERVACIÓN.",
          side: "top",
        },
      },
    ],
  },
  "/bibliografia": {
    title: "Bibliografía & Directorio de Fuentes",
    badge: "12 Feeds RSS",
    steps: [
      {
        element: '[data-tour="biblio-stats"]',
        popover: {
          title: "Catálogo Multi-Fuente",
          description:
            "Resumen cuantitativo de las 11 fuentes activas monitoreadas y más de 640 piezas indexadas en la base de datos.",
          side: "bottom",
        },
      },
      {
        element: '[data-tour="biblio-active-grid"]',
        popover: {
          title: "Directorio de Canales Oficiales & Feeds",
          description:
            "Revisa los 12 feeds RSS activos (Latent Space, OpenAI, Hugging Face, ArXiv) con sus frecuencias de actualización y compliance legal.",
          side: "top",
        },
      },
      {
        element: '[data-tour="biblio-suggested-grid"]',
        popover: {
          title: "Hoja de Ruta de Nuevas Fuentes",
          description:
            "Evaluación técnica de fuentes adicionales de alto impacto (ArXiv grafos de citas, Substack deep dives, Whisper Podcasts) para expansión.",
          side: "top",
        },
      },
    ],
  },
};

export function DriverTour() {
  const pathname = usePathname();
  const driverInstanceRef = useRef<Driver | null>(null);
  const activePathRef = useRef<string>("");
  const isCancelledRef = useRef<boolean>(false);
  const [currentTourTitle, setCurrentTourTitle] = useState<string>("");

  const getCleanPath = (p: string) => (p === "" ? "/" : p);

  const isTourDismissed = (): boolean => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("sonar_tour_dismissed") === "true";
  };

  const markTourDismissed = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("sonar_tour_dismissed", "true");
    }
  };

  const isIntroActive = (): boolean => {
    if (typeof window === "undefined") return false;
    if (sessionStorage.getItem("sonar_intro_viewed") === "true") return false;
    if ((window as any).__sonar_intro_active === true) return true;
    if (document.querySelector(".sonar-intro-overlay")) return true;
    return false;
  };

  const startTour = (force = false) => {
    const tourKey = getCleanPath(pathname);
    const tourConfig = ROUTE_TOURS[tourKey];

    if (!tourConfig) return;

    // Si no es forzado y el usuario ya cerró el tutorial, nunca auto-abrir
    if (!force && isTourDismissed()) {
      return;
    }

    // Si no es forzado y la intro aún está activa, esperar a que cierre
    if (!force && isIntroActive()) {
      return;
    }

    // Limpiar driver previo si estuviese abierto
    if (driverInstanceRef.current) {
      try {
        driverInstanceRef.current.destroy();
      } catch (_) {}
      driverInstanceRef.current = null;
    }

    isCancelledRef.current = false;
    let attempts = 0;
    const maxAttempts = 20;

    const checkAndDrive = () => {
      if (isCancelledRef.current || getCleanPath(window.location.pathname) !== tourKey) {
        return;
      }

      // Si no es forzado y fue cerrado mientras sondeaba, abortar
      if (!force && isTourDismissed()) {
        return;
      }

      attempts++;
      const availableSteps = tourConfig.steps.filter((s) => {
        return document.querySelector(s.element) !== null;
      });

      if (availableSteps.length > 0) {
        try {
          const driverObj = driver({
            showProgress: true,
            animate: true,
            allowClose: true,
            overlayColor: "#27251e",
            overlayOpacity: 0.45,
            doneBtnText: "Entendido",
            nextBtnText: "Siguiente →",
            prevBtnText: "← Anterior",
            progressText: "{{current}} de {{total}}",
            steps: availableSteps,
            onCloseClick: () => {
              markTourDismissed();
              driverInstanceRef.current?.destroy();
            },
            onDestroyed: () => {
              markTourDismissed();
              driverInstanceRef.current = null;
            },
          });

          driverInstanceRef.current = driverObj;
          driverObj.drive();
        } catch (e) {
          console.warn("DriverTour no pudo inicializar en", tourKey, e);
        }
        return;
      }

      if (attempts < maxAttempts) {
        setTimeout(checkAndDrive, 150);
      }
    };

    // Pequeño retardo inicial para asegurar renderizado en pantalla
    setTimeout(checkAndDrive, 200);
  };

  useEffect(() => {
    const cleanPath = getCleanPath(pathname);
    activePathRef.current = cleanPath;
    const tourConfig = ROUTE_TOURS[cleanPath];
    setCurrentTourTitle(tourConfig ? tourConfig.title : "");

    let autoStartTimer: NodeJS.Timeout | null = null;

    // Escuchar evento manual para forzar la apertura del tour (sidebar o floating)
    const handleManualTrigger = () => startTour(true);
    window.addEventListener("start-radar-tour", handleManualTrigger);

    // Escuchar evento cuando la intro termine o sea omitida
    const handleIntroFinished = () => {
      if (!isTourDismissed()) {
        setTimeout(() => {
          if (!isCancelledRef.current && !isTourDismissed()) {
            startTour(false);
          }
        }, 500);
      }
    };
    window.addEventListener("sonar-intro-finished", handleIntroFinished);

    // Si no ha sido descartado y la intro no está activa, auto-iniciar con retardo
    if (!isTourDismissed() && !isIntroActive()) {
      autoStartTimer = setTimeout(() => {
        if (!isCancelledRef.current && !isTourDismissed()) {
          startTour(false);
        }
      }, 500);
    }

    return () => {
      isCancelledRef.current = true;
      if (autoStartTimer) clearTimeout(autoStartTimer);
      window.removeEventListener("start-radar-tour", handleManualTrigger);
      window.removeEventListener("sonar-intro-finished", handleIntroFinished);
      if (driverInstanceRef.current) {
        try {
          driverInstanceRef.current.destroy();
        } catch (_) {}
        driverInstanceRef.current = null;
      }
    };
  }, [pathname]);

  const cleanPath = getCleanPath(pathname);
  const tourConfig = ROUTE_TOURS[cleanPath];
  if (!tourConfig) return null;

  return (
    <div className="fixed bottom-4 right-4 z-40 hidden sm:block">
      <button
        onClick={() => startTour(true)}
        title={`Ver tutorial interactivo de ${tourConfig.title}`}
        className="group flex items-center space-x-2 px-3 py-1.5 rounded-[6px] bg-[#fdfbfa] hover:bg-[#faf8f5] border border-[#d1d1cd] hover:border-[#016a71] text-[#27251e] shadow-[0_2px_4px_rgba(0,0,0,0.06)] text-xs font-normal transition duration-150 cursor-pointer"
      >
        <span className="flex h-2 w-2 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#016a71] opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-[#016a71]"></span>
        </span>
        <HelpCircle className="w-3.5 h-3.5 text-[#016a71]" />
        <span className="font-mono text-[11px] text-[#72706b] group-hover:text-[#27251e] transition-colors">
          Guía: <strong className="font-medium text-[#27251e]">{tourConfig.badge}</strong>
        </span>
      </button>
    </div>
  );
}
