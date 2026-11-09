"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Credential, Provider } from "@/lib/types";

const INTEGRATION_COPY: Record<Provider["integration"], { label: string; text: string }> = {
  hosted: { label: "Hosted agent", text: "PLATO runs the agent by calling this provider's API with your key." },
  external: { label: "Connected runtime", text: "You run the agent (e.g. a local coding agent); PLATO talks to it over the PLATO External Agent Protocol." },
  simulated: { label: "Simulated", text: "Offline stand-in for demos and tests. No real AI is called and nothing is billed." },
};

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [creds, setCreds] = useState<Credential[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([api<Provider[]>("/api/providers"), api<Credential[]>("/api/credentials")]);
      setProviders(p);
      setCreds(c);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  return (
    <AppShell>
      <h1 className="text-2xl font-light tracking-wide">AI providers</h1>
      <p className="mt-2 max-w-3xl text-sm text-mist">
        Bring your own API keys (BYOK). Keys are verified with a live call to the provider, encrypted at rest, and never shown again or sent to
        agents. Usage on your key is billed by the provider to you.
      </p>
      {error && <p className="mt-4 text-sm text-bad">{error}</p>}
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {providers.map((p) => (
          <ProviderCard key={p.id} provider={p} creds={creds.filter((c) => c.provider === p.id)} onChange={load} />
        ))}
      </div>
    </AppShell>
  );
}

function ProviderCard({ provider: p, creds, onChange }: { provider: Provider; creds: Credential[]; onChange: () => void }) {
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const copy = INTEGRATION_COPY[p.integration];

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await api("/api/credentials", { method: "POST", json: { provider: p.id, api_key: key } });
      setKey("");
      setMsg({ ok: true, text: "Key verified and saved." });
      onChange();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Remove this key? Agents using it will stop working until a new key is added.")) return;
    await api(`/api/credentials/${id}`, { method: "DELETE" });
    onChange();
  }

  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-light">{p.display_name}</h2>
        <span className={`chip ${p.connected ? "border-cyan/40 text-cyan" : ""}`}>{p.connected ? "Connected" : "Not connected"}</span>
      </div>
      <p className="mt-1 text-xs text-mist">
        <span className="text-ice/80">{copy.label}.</span> {copy.text}
      </p>
      {p.platform_managed_available && (
        <p className="mt-2 text-xs text-mist">Platform-managed usage credits are available for this provider if you don&apos;t add a key.</p>
      )}
      {creds.map((c) => (
        <div key={c.id} className="mt-3 flex items-center justify-between rounded-lg border border-line px-3 py-2 text-sm">
          <span>
            <span className="font-mono text-mist">{c.key_hint}</span> <span className="text-mist">· {c.label}</span>
            {c.verified_at && <span className="ml-2 text-xs text-ok">verified</span>}
          </span>
          <button className="text-xs text-bad hover:underline" onClick={() => remove(c.id)}>Remove</button>
        </div>
      ))}
      {p.integration === "hosted" && (
        <form onSubmit={save} className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input
            className="input font-mono"
            type="password"
            autoComplete="off"
            placeholder={creds.length ? "Replace API key" : "Paste API key"}
            value={key}
            onChange={(e) => setKey(e.target.value)}
            minLength={8}
            required
          />
          <button className="btn-primary shrink-0" disabled={busy}>{busy ? "Verifying…" : "Connect"}</button>
        </form>
      )}
      {p.integration === "external" && (
        <p className="mt-4 text-xs text-mist">Add an external agent from a project&apos;s Agent panel by providing its endpoint URL (Power plan and above).</p>
      )}
      {msg && <p className={`mt-2 text-xs ${msg.ok ? "text-ok" : "text-bad"}`}>{msg.text}</p>}
    </div>
  );
}
