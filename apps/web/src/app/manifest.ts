import type { MetadataRoute } from "next";

/** PWA manifest: Captains install the Ship to their home screen (PRD §4 "PWA support"). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "A-hoy Ship",
    short_name: "A-hoy",
    description: "Approve your posts, see your leads and answer reviews.",
    start_url: "/ship",
    scope: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#0a0a0a",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
