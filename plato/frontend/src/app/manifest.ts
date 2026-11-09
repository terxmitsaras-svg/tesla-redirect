import type { MetadataRoute } from "next";

/** Web App Manifest: makes PLATO installable on Windows, macOS, Linux, ChromeOS, Android and iOS. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "PLATO — Multiple Minds. One Intelligence.",
    short_name: "PLATO",
    description: "Command centre where AI agents from different providers work together under your control.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    display_override: ["window-controls-overlay", "standalone"],
    orientation: "any",
    background_color: "#000000",
    theme_color: "#020306",
    categories: ["productivity", "developer tools", "utilities"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Projects", url: "/", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
      { name: "Providers", url: "/providers", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
    ],
  };
}
