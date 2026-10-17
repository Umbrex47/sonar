import type { Metadata } from "next";
import { DM_Serif_Display, Inter, Roboto_Mono } from "next/font/google";
import "./globals.css";

const dmSerif = DM_Serif_Display({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-lyon-display",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-suisse-intl",
  display: "swap",
});

const robotoMono = Roboto_Mono({
  subsets: ["latin"],
  variable: "--font-roboto-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Radar de Contenido 30X — Quiet Authority in AI Intelligence",
  description: "Curación ejecutiva de tendencias y señales emergentes en Inteligencia Artificial para líderes de Latinoamérica. Calibración probabilística con TypeSafe Jev.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${dmSerif.variable} ${inter.variable} ${robotoMono.variable} h-full dark`}
    >
      <body className="min-h-full flex flex-col bg-[#0f1011] text-[#9f9fa0] antialiased selection:bg-[#ffffff] selection:text-[#000000]">
        {children}
      </body>
    </html>
  );
}
