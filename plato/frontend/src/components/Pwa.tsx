"use client";

import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };

/** Registers the service worker (production builds, secure contexts: HTTPS or localhost). */
export function PwaRegister() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator) || !window.isSecureContext) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* non-fatal: the app works without offline support */
    });
  }, []);
  return null;
}

function isStandalone() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

function isIOS() {
  const ua = navigator.userAgent;
  // iPadOS 13+ reports itself as Mac; detect touch to tell them apart.
  return /iPhone|iPad|iPod/.test(ua) || (ua.includes("Macintosh") && navigator.maxTouchPoints > 1);
}

/**
 * "Install app" button. Chrome/Edge (Windows, macOS, Linux, ChromeOS, Android) expose a native
 * install prompt; Safari (iOS/iPadOS, macOS) has none, so we show the Share-menu steps instead.
 */
export function InstallButton() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [mode, setMode] = useState<"hidden" | "prompt" | "ios" | "safari-mac">("hidden");
  const [help, setHelp] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setMode("prompt");
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    const installed = () => setMode("hidden");
    window.addEventListener("appinstalled", installed);
    const ua = navigator.userAgent;
    if (isIOS()) setMode("ios");
    else if (/Safari/.test(ua) && !/Chrome|Chromium|Edg|OPR/.test(ua) && /Macintosh/.test(ua)) setMode("safari-mac");
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", installed);
    };
  }, []);

  if (mode === "hidden") return null;

  async function install() {
    if (mode === "prompt" && deferred) {
      await deferred.prompt();
      const choice = await deferred.userChoice;
      if (choice.outcome === "accepted") setMode("hidden");
      setDeferred(null);
    } else {
      setHelp((h) => !h);
    }
  }

  return (
    <div className="relative">
      <button className="btn px-2.5 text-xs" onClick={install} aria-expanded={help}>
        Install app
      </button>
      {help && (
        <div role="dialog" className="panel absolute right-0 top-10 z-40 w-64 p-3 text-xs text-ice/90 shadow-glow">
          {mode === "ios" ? (
            <ol className="list-decimal space-y-1 pl-4">
              <li>Tap the <b>Share</b> button in Safari.</li>
              <li>Choose <b>Add to Home Screen</b>.</li>
              <li>Tap <b>Add</b>. PLATO opens full-screen like an app.</li>
            </ol>
          ) : (
            <ol className="list-decimal space-y-1 pl-4">
              <li>In Safari choose <b>File → Add to Dock…</b></li>
              <li>Or open PLATO in Chrome or Edge and use <b>Install</b>.</li>
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
