import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AppShell from "@/components/AppShell";

const inter = Inter({ 
  subsets: ["latin"],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: "AquaForge | Swim Meet Optimizer",
  description: "AI-powered swim meet lineup optimization for competitive advantage",
  keywords: ["swim meet", "lineup optimizer", "swimming", "aquatics", "sports analytics"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <AppShell>
          {children}
        </AppShell>
      </body>
    </html>
  );
}
