"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";
import type { User } from "@/lib/types";
import { Mark, Wordmark } from "./Brand";
import { InstallButton } from "./Pwa";

const NAV = [
  { href: "/", label: "Projects" },
  { href: "/providers", label: "Providers" },
  { href: "/billing", label: "Billing" },
];

export function useUser(enabled = true) {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    if (!enabled) return;
    api<User>("/api/auth/me").then(setUser).catch(() => setUser(null));
  }, [enabled]);
  return user;
}

export default function AppShell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState(false);
  const user = useUser(ready);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
    else setReady(true);
  }, [router]);

  if (!ready) return null;

  const active = (href: string) => (href === "/" ? pathname === "/" || pathname.startsWith("/projects") : pathname.startsWith(href));

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-void/80 pl-[env(safe-area-inset-left)] pr-[env(safe-area-inset-right)] pt-[env(safe-area-inset-top)] backdrop-blur">
        <div className={`mx-auto flex h-14 items-center gap-4 px-4 ${wide ? "max-w-[1600px]" : "max-w-6xl"}`}>
          <Link href="/" className="flex items-center gap-3">
            <Mark size={30} />
            <Wordmark className="text-sm" />
          </Link>
          <nav className="ml-6 hidden gap-1 md:flex">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`rounded-md px-3 py-1.5 text-sm transition ${active(n.href) ? "bg-white/5 text-ice" : "text-mist hover:text-ice"}`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <InstallButton />
            {user && (
              <span className="chip hidden sm:inline-flex">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan" />
                {user.plan_code.toUpperCase()} · {user.email}
              </span>
            )}
            <button
              className="btn hidden md:inline-flex"
              onClick={() => {
                setToken(null);
                router.replace("/login");
              }}
            >
              Sign out
            </button>
            <button className="btn md:hidden" aria-label="Menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
              ☰
            </button>
          </div>
        </div>
        {open && (
          <nav className="flex flex-col gap-1 border-t border-line px-4 py-2 md:hidden">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} onClick={() => setOpen(false)} className="rounded-md px-2 py-2 text-sm text-ice">
                {n.label}
              </Link>
            ))}
            <button
              className="rounded-md px-2 py-2 text-left text-sm text-mist"
              onClick={() => {
                setToken(null);
                router.replace("/login");
              }}
            >
              Sign out
            </button>
          </nav>
        )}
      </header>
      <main
        className={`mx-auto px-4 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] ${wide ? "max-w-[1600px]" : "max-w-6xl"}`}
      >
        {children}
      </main>
    </div>
  );
}
