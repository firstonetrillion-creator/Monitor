import type { Metadata, Viewport } from "next";
import { Fraunces, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const viewport: Viewport = {
  colorScheme: "light dark",
};

export const metadata: Metadata = {
  title: {
    default: "Cerrado Aberto — Transparência Legislativa de Inhumas (GO)",
    template: "%s | Cerrado Aberto",
  },
  description:
    "Plataforma cidadã independente de monitoramento e interpretação dos dados públicos da Câmara Municipal de Inhumas (GO).",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pt-BR"
      className={`${inter.variable} ${fraunces.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <a href="#conteudo-principal" className="skip-link">
          Pular para o conteúdo principal
        </a>
        <SiteHeader />
        <main
          id="conteudo-principal"
          tabIndex={-1}
          className="flex-1 w-full max-w-6xl mx-auto px-4 py-8 outline-none"
        >
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
