import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PLATO — Multiple Minds. One Intelligence.",
  description: "A real-time command centre where AI agents from different providers work together under human control.",
};

export const viewport: Viewport = { themeColor: "#020306", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
