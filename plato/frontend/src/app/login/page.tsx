"use client";
/* eslint-disable @next/next/no-img-element */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Wordmark } from "@/components/Brand";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api<{ token: string }>(`/api/auth/${mode}`, { method: "POST", json: { email, password } });
      setToken(r.token);
      router.replace("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden items-center justify-center overflow-hidden lg:flex">
        <img src="/plato-logo.png" alt="PLATO" className="h-full max-h-[900px] w-auto object-contain opacity-95" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-void" />
      </div>
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <img src="/plato-logo.png" alt="" className="mx-auto mb-6 h-40 w-40 rounded-full object-cover lg:hidden" />
          <Wordmark className="block text-center text-3xl" />
          <p className="mt-3 text-center text-sm text-mist">Multiple Minds. One Intelligence.</p>
          <div className="laser my-8" />
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label" htmlFor="email">Email</label>
              <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="password">Password</label>
              <input
                id="password"
                className="input"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={mode === "register" ? 10 : undefined}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {mode === "register" && <p className="mt-1 text-xs text-mist">At least 10 characters.</p>}
            </div>
            {error && <p className="text-sm text-bad" role="alert">{error}</p>}
            <button className="btn-primary w-full py-2" disabled={busy}>
              {busy ? "…" : mode === "login" ? "Enter the command room" : "Create account"}
            </button>
          </form>
          <button className="mt-4 w-full text-center text-sm text-mist hover:text-ice" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "New to PLATO? Create an account" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
