import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Ship shell: loads the Next.js web app.
 * For local dev, point server.url at the Next dev server.
 * For store builds, set server.url to the deployed Ship origin (or use bundled assets).
 */
const config: CapacitorConfig = {
  appId: "com.ahoy.ship",
  appName: "A-hoy Ship",
  webDir: "www",
  server: {
    // Dev: load Next.js. Override with CAP_SERVER_URL if needed.
    url: process.env.CAP_SERVER_URL ?? "http://localhost:3000",
    cleartext: true,
  },
  plugins: {
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"],
    },
  },
};

export default config;
