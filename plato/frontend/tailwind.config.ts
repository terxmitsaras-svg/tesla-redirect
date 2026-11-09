import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#020306",
        panel: "#070a10",
        line: "rgba(148, 197, 255, 0.10)",
        ice: "#e8f1ff",
        mist: "#8a98ad",
        volt: "#3d8bff",
        cyan: "#5ee7ff",
        ok: "#4ade80",
        warn: "#fbbf24",
        bad: "#f87171",
      },
      fontFamily: {
        sans: ['"Inter"', "ui-sans-serif", "system-ui", "-apple-system", '"Segoe UI"', "Roboto", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(94,231,255,0.18), 0 0 24px -6px rgba(61,139,255,0.45)",
        "glow-sm": "0 0 12px -4px rgba(94,231,255,0.55)",
      },
      keyframes: {
        pulseline: { "0%,100%": { opacity: "0.35" }, "50%": { opacity: "1" } },
      },
      animation: { pulseline: "pulseline 1.6s ease-in-out infinite" },
    },
  },
  plugins: [],
} satisfies Config;
