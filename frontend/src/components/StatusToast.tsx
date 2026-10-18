"use client";

import React from "react";
import { Sparkles } from "lucide-react";
import { useRadar } from "../context/RadarContext";

export function StatusToast() {
  const { statusMessage } = useRadar();

  if (!statusMessage) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 bg-[#fdfbfa] border border-[#d1d1cd] text-[#27251e] px-3.5 py-2.5 rounded-[6px] shadow-sm flex items-center space-x-2.5 text-xs animate-in fade-in duration-150">
      <Sparkles className="w-3.5 h-3.5 text-[#016a71] shrink-0" />
      <span className="font-normal">{statusMessage}</span>
    </div>
  );
}
