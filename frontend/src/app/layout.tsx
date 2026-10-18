import type { Metadata } from "next";
import { Inter, Roboto_Mono } from "next/font/google";
import "./globals.css";
import { RadarProvider } from "../context/RadarContext";
import { Sidebar } from "../components/Sidebar";
import { StatusToast } from "../components/StatusToast";
import { ChatWidget } from "../components/ChatWidget";
import { SonarIntro } from "../components/SonarIntro";
import { DriverTour } from "../components/DriverTour";
import { TerminalConsole } from "../components/TerminalConsole";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const robotoMono = Roboto_Mono({
  subsets: ["latin"],
  variable: "--font-roboto-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sonar — Detección de Señales & Inteligencia Editorial en IA",
  description: "Plataforma Sonar: Curación ejecutiva de tendencias y señales emergentes en Inteligencia Artificial para líderes de Latinoamérica. Calibración probabilística con TypeSafe Jev.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${inter.variable} ${robotoMono.variable} h-full`}
    >
      <body className="min-h-full bg-[#faf8f5] text-[#27251e] antialiased selection:bg-[#016a71] selection:text-[#faf8f5]">
        <SonarIntro />
        <RadarProvider>
          <div className="min-h-screen flex flex-col md:flex-row bg-[#faf8f5]">
            <Sidebar />
            <div className="flex-1 min-w-0 flex flex-col overflow-x-hidden">
              <main className="flex-1 max-w-[900px] w-full mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8 space-y-6 md:space-y-8">
                {children}
              </main>
              <footer className="border-t border-[#d1d1cd] py-6 px-6 bg-[#faf8f5] mt-12">
                <div className="max-w-[900px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#72706b]">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-[#27251e]">SONAR</span>
                    <span>—</span>
                    <span>Cerebro de Inteligencia Editorial & Detección de Señales</span>
                  </div>
                  <div className="font-mono text-[10px] text-[#72706b]">
                    SONAR // 100% PUBLIC COMPLIANT // TYPESAFE AI CALIBRATED // 2026
                  </div>
                </div>
              </footer>
            </div>
          </div>
          <StatusToast />
          <ChatWidget />
          <DriverTour />
          <TerminalConsole />
        </RadarProvider>
      </body>
    </html>
  );
}

