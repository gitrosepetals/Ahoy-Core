import type { Metadata } from "next";
import { Atkinson_Hyperlegible } from "next/font/google";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemeToggleDock } from "@/components/ThemeToggle";
import "./globals.css";

/**
 * One family only — Fraunces+Atkinson was a double network hit on first paint.
 * Size/weight scale still creates hierarchy.
 */
const ahoySans = Atkinson_Hyperlegible({
  variable: "--font-ahoy-sans",
  subsets: ["latin"],
  weight: ["400", "700"],
  display: "swap",
  preload: true,
  adjustFontFallback: true,
});

export const metadata: Metadata = {
  title: "A-hoy",
  description: "Captain Ship and Crew Deck for A-hoy Marketing",
};

const themeBootScript = `
(function(){
  try {
    var k = "ahoy-theme";
    var t = localStorage.getItem(k);
    if (t !== "light" && t !== "dark") {
      t = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
      </head>
      <body className={`${ahoySans.variable} ${ahoySans.className} antialiased text-ahoy-ink`}>
        <ThemeProvider>
          <ThemeToggleDock />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
