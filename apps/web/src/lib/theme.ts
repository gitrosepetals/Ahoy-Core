export type AhoyTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "ahoy-theme";

export function readStoredTheme(): AhoyTheme | null {
  if (typeof window === "undefined") return null;
  const v = window.localStorage.getItem(THEME_STORAGE_KEY);
  return v === "light" || v === "dark" ? v : null;
}

export function systemTheme(): AhoyTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function resolveTheme(stored: AhoyTheme | null): AhoyTheme {
  return stored ?? systemTheme();
}

export function applyTheme(theme: AhoyTheme) {
  document.documentElement.setAttribute("data-theme", theme);
}

export function persistTheme(theme: AhoyTheme) {
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  applyTheme(theme);
}
