import type { Metadata, Viewport } from "next";
import { PwaRegister } from "@/components/Pwa";
import "./globals.css";

export const metadata: Metadata = {
  title: "PLATO — Multiple Minds. One Intelligence.",
  description: "A real-time command centre where AI agents from different providers work together under human control.",
  applicationName: "PLATO",
  // iOS / iPadOS home-screen app.
  appleWebApp: { capable: true, title: "PLATO", statusBarStyle: "black-translucent" },
  icons: {
    icon: [{ url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#020306",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover", // draw under the notch / home indicator; padding uses safe-area insets
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">
        <PwaRegister />
        {children}
      </body>
    </html>
  );
}
