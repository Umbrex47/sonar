"use client";

import React, { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { Compass, ArrowRight } from "lucide-react";

interface SonarIntroProps {
  onFinish?: () => void;
  forceShow?: boolean;
}

export function SonarIntro({ onFinish, forceShow = false }: SonarIntroProps) {
  const [isVisible, setIsVisible] = useState(true);
  const overlayRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const txt1Ref = useRef<HTMLSpanElement>(null);
  const txt2Ref = useRef<HTMLSpanElement>(null);
  const barRef = useRef<HTMLDivElement>(null);
  const brandRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<gsap.core.Timeline | null>(null);
  const isFadingRef = useRef<boolean>(false);

  const handleSkip = () => {
    if (isFadingRef.current) return;
    isFadingRef.current = true;

    if (timelineRef.current) {
      timelineRef.current.kill();
    }

    if (!overlayRef.current) {
      setIsVisible(false);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("sonar_intro_viewed", "true");
        (window as any).__sonar_intro_active = false;
        window.dispatchEvent(new CustomEvent("sonar-intro-finished"));
      }
      onFinish?.();
      return;
    }

    gsap.to(overlayRef.current, {
      opacity: 0,
      scale: 1.02,
      duration: 0.6,
      ease: "power2.inOut",
      onComplete: () => {
        setIsVisible(false);
        if (typeof window !== "undefined") {
          sessionStorage.setItem("sonar_intro_viewed", "true");
          (window as any).__sonar_intro_active = false;
          window.dispatchEvent(new CustomEvent("sonar-intro-finished"));
        }
        onFinish?.();
      },
    });
  };

  useEffect(() => {
    // Si ya se vio en esta pestaña y no está forzado, omitir
    if (!forceShow && typeof window !== "undefined") {
      const alreadySeen = sessionStorage.getItem("sonar_intro_viewed");
      if (alreadySeen) {
        setIsVisible(false);
        (window as any).__sonar_intro_active = false;
        onFinish?.();
        return;
      }
    }

    if (typeof window !== "undefined") {
      (window as any).__sonar_intro_active = true;
    }

    const color2 = "#17c0fd";
    const color1 = "#ffffff";

    const moveBar = () => {
      if (txt1Ref.current && barRef.current) {
        const currentW = (gsap.getProperty(txt1Ref.current, "width") as number) || txt1Ref.current.offsetWidth;
        gsap.set(barRef.current, { left: currentW + 1 });
      }
    };

    const t2Chars = txt2Ref.current
      ? txt2Ref.current.querySelectorAll(".sonar-char")
      : [];

    const ctx = gsap.context(() => {
      // 1. Animación de entrada de la marca SONAR y emblema
      gsap.from(brandRef.current, {
        opacity: 0,
        y: -30,
        scale: 0.95,
        duration: 1.4,
        ease: "power3.out",
        delay: 0.2,
      });

      // Calcular el ancho natural de txt1 para posicionar txt2 exactamente después
      const txt1InitialWidth = txt1Ref.current
        ? (gsap.getProperty(txt1Ref.current, "width") as number) || txt1Ref.current.offsetWidth || 340
        : 340;

      // 2. Línea de tiempo principal exacta de GSAP
      const tl = gsap.timeline({ delay: 0.2 });
      timelineRef.current = tl;

      tl.set(txt1Ref.current, { color: color1, fontWeight: "400" })
        .set(txt2Ref.current, {
          color: color2,
          fontWeight: "700",
          opacity: 0,
          x: txt1InitialWidth - 2,
          immediateRender: true,
        })
        .set(barRef.current, {
          left: 1,
          backgroundColor: color1,
          immediateRender: true,
        })

        // Parpadeo del cursor (con mayor presencia)
        .to(
          barRef.current,
          {
            duration: 0.12,
            opacity: 0,
            ease: "expo.in",
            yoyo: true,
            repeat: 5,
            repeatDelay: 0.35,
          },
          0
        )
        // Escritura mecanográfica más pausada y legible de "www.perte.design/"
        .from(
          txt1Ref.current,
          {
            duration: 1.6,
            width: 0,
            ease: "steps(17)",
            onUpdate: moveBar,
          },
          2.6
        )
        // Cambio de color del cursor a cyan #17c0fd
        .to(barRef.current, { duration: 0.08, backgroundColor: color2 }, "+=0.2")
        // Expansión más suave y majestuosa del bloque cursor a 290px
        .to(barRef.current, { duration: 1.3, width: 290, ease: "power4.inOut" }, "+=0.15")
        .from(containerRef.current, { duration: 1.3, x: 135, ease: "power4.inOut" }, "-=1.3")
        // Revelado de la palabra "sonar"
        .to(txt2Ref.current, { duration: 0.01, opacity: 1 }, "-=0.15")
        .to(barRef.current, { duration: 0.5, x: 290, width: 0, ease: "power4.in" })
        // Aparición letra por letra con mayor cadencia y stagger
        .from(t2Chars, { duration: 0.8, opacity: 0, ease: "power3.inOut", stagger: 0.06 }, "-=0.6")
        // Desvanecimiento suave del prefijo URL
        .to(txt1Ref.current, { duration: 1.8, opacity: 0.25, ease: "power3.inOut" }, "-=1.4")
        .timeScale(0.95)

        // 3. Dejar más tiempo para contemplar la animación terminada (2.5s)
        .to({}, { duration: 2.5 })

        // 4. Desvanecimiento cinematográfico suave hacia la plataforma (1.2s)
        .to(overlayRef.current, {
          duration: 1.2,
          opacity: 0,
          scale: 1.02,
          ease: "power2.inOut",
          onComplete: () => {
            isFadingRef.current = true;
            setIsVisible(false);
            if (typeof window !== "undefined") {
              sessionStorage.setItem("sonar_intro_viewed", "true");
              (window as any).__sonar_intro_active = false;
              window.dispatchEvent(new CustomEvent("sonar-intro-finished"));
            }
            onFinish?.();
          },
        });
    });

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleSkip();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      ctx.revert();
      window.removeEventListener("keydown", handleKeyDown);
      if (typeof window !== "undefined") {
        (window as any).__sonar_intro_active = false;
      }
    };
  }, [forceShow]);

  if (!isVisible) return null;

  return (
    <div
      ref={overlayRef}
      className="sonar-intro-overlay select-none"
    >
      {/* 1. Fondo de Agua con Ondas Concéntricas de Radar Sonar */}
      <div className="sonar-water">
        <div className="sonar-wave time1"></div>
        <div className="sonar-wave time2"></div>
        <div className="sonar-wave time3"></div>
        <div className="sonar-wave time4"></div>
      </div>

      {/* Botón flotante para omitir con Esc */}
      <button
        onClick={handleSkip}
        className="fixed top-6 right-6 z-50 px-3.5 py-1.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-[#f1f5f9] text-xs font-mono backdrop-blur-md transition flex items-center space-x-1.5 cursor-pointer shadow-lg"
      >
        <span>Saltar intro [Esc]</span>
        <ArrowRight className="w-3.5 h-3.5 text-[#17c0fd]" />
      </button>

      {/* 2. Contenido Central: Marca SONAR + Tipografía Interactiva GSAP */}
      <div className="sonar-intro-content px-4">
        {/* Cabecera de la Marca Sonar */}
        <div ref={brandRef} className="space-y-2 mb-4 flex flex-col items-center">
          <div className="relative mb-1">
            <div className="w-14 h-14 rounded-full bg-[#1F3A93]/40 border-2 border-[#17c0fd] flex items-center justify-center shadow-[0_0_25px_rgba(23,192,253,0.5)]">
              <Compass className="w-7 h-7 text-[#17c0fd] animate-pulse" />
            </div>
            <div className="absolute inset-0 rounded-full border border-[#7dd3fc]/50 animate-ping opacity-75"></div>
          </div>

          <h1 className="sonar-brand-heading">SONAR</h1>

          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#1F3A93]/30 border border-[#17c0fd]/40 backdrop-blur-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-[#17c0fd] animate-pulse"></span>
            <span className="font-mono text-[10px] tracking-[0.25em] text-[#C5EFF7] font-medium uppercase">
              INTELIGENCIA EDITORIAL & DETECCIÓN DE SEÑALES EN IA
            </span>
          </div>
        </div>

        {/* 3. Contenedor de Texto con la Barra de GSAP */}
        <div className="sonar-typewriter-container" ref={containerRef}>
          <span className="txt1" ref={txt1Ref}>
            www.perte.design/
          </span>
          <span className="txt2" ref={txt2Ref}>
            {"sonar".split("").map((ch, idx) => (
              <span key={idx} className="sonar-char inline-block">
                {ch}
              </span>
            ))}
          </span>
          <div className="sonar-bar bar" ref={barRef}></div>
        </div>

        {/* Indicador sutil de carga al pie */}
        <div className="mt-12 text-[11px] font-mono text-[#7dd3fc]/50 tracking-widest uppercase">
          CARGANDO SEÑALES Y TENDENCIAS // SONAR 2026
        </div>
      </div>
    </div>
  );
}
