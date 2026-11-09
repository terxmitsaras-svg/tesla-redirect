"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Credential, Provider, ProviderCategory } from "@/lib/types";
import { CATEGORY_LABEL } from "@/lib/types";

const INTEGRATION_COPY: Record<Provider["integration"], { label: string; text: string }> = {
  hosted: { label: "Hosted agent", text: "PLATO runs the agent by calling this provider's API." },
  external: { label: "Connected runtime", text: "You run the agent (e.g. a local coding agent); PLATO talks to it over the PLATO External Agent Protocol." },
  simulated: { label: "Simulated", text: "Offline stand-in for demos and tests. No real AI is called and nothing is billed." },
};

const ORDER: ProviderCategory[] = ["frontier", "open", "local", "custom"];

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
        Bring your own API keys (BYOK) or point PLATO at your own model servers. Connections are verified with a live call, keys are encrypted at
        rest and never shown again or sent to agents. Usage on your key is billed by the provider to you.
      </p>
      {error && <p className="mt-4 text-sm text-bad">{error}</p>}
      {ORDER.map((cat) => {
        const items = providers.filter((p) => p.category === cat);
        if (!items.length) return null;
        return (
          <section key={cat} className="mt-10">
            <h2 className="panel-title">{CATEGORY_LABEL[cat].title}</h2>
            <p className="mt-1 text-xs text-mist">{CATEGORY_LABEL[cat].blurb}</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {items.map((p) => (
                <ProviderCard key={p.id} provider={p} creds={creds.filter((c) => c.provider === p.id)} onChange={load} />
              ))}
            </div>
          </section>
        );
      })}
    </AppShell>
  );
}

function ProviderCard({ provider: p, creds, onChange }: { provider: Provider; creds: Credential[]; onChange: () => void }) {
  const [key, setKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const copy = INTEGRATION_COPY[p.integration];
  const configurable = p.integration === "hosted";
  const showUrl = p.base_url_mode !== "fixed";
  const savedConnection = creds.length > 0;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await api("/api/credentials", {
        method: "POST",
        json: { provider: p.id, api_key: key, base_url: showUrl && baseUrl.trim() ? baseUrl.trim() : null },
      });
      setKey("");
      setBaseUrl("");
      setMsg({ ok: true, text: "Connection verified and saved." });
      onChange();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Remove this connection? Agents using it will fall back to the default, or stop until a new one is added.")) return;
    await api(`/api/credentials/${id}`, { method: "DELETE" });
    onChange();
  }

  const status =
    p.integration === "simulated" ? "Built in" : savedConnection ? "Connected" : p.connected ? (p.self_hosted ? "Default host" : "Ready") : "Not connected";

  return (
    <div className="panel flex flex-col p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-light">{p.display_name}</h3>
        <span className={`chip ${p.connected ? "border-cyan/40 text-cyan" : ""}`}>{status}</span>
      </div>
      <p className="mt-1 text-xs text-mist">
        <span className="text-ice/80">{copy.label}.</span> {copy.text}
        {p.self_hosted && p.integration === "hosted" && " Runs on your hardware, so there are no per-token charges."}
      </p>
      {p.default_base_url && showUrl && (
        <p className="mt-2 text-xs text-mist">
          Default: <span className="font-mono text-ice/80">{p.default_base_url}</span>
          {p.id === "ollama" && <> · Ollama Cloud: <span className="font-mono text-ice/80">https://ollama.com/v1</span> (with key)</>}
        </p>
      )}
      {p.base_url_mode === "required" && p.integration === "hosted" && <p className="mt-2 text-xs text-mist">{p.docs_url}</p>}
      {p.platform_managed_available && (
        <p className="mt-2 text-xs text-mist">Platform-managed usage credits are available for this provider if you don&apos;t add a key.</p>
      )}

      {creds.map((c) => (
        <div key={c.id} className="mt-3 flex items-center justify-between gap-2 rounded-lg border border-line px-3 py-2 text-sm">
          <span className="min-w-0 truncate">
            <span className="font-mono text-mist">{c.key_hint}</span>
            {c.base_url && <span className="font-mono text-xs text-mist"> · {c.base_url}</span>}
            {c.verified_at && <span className="ml-2 text-xs text-ok">verified</span>}
          </span>
          <button className="shrink-0 text-xs text-bad hover:underline" onClick={() => remove(c.id)}>Remove</button>
        </div>
      ))}

      {configurable && (
        <form onSubmit={save} className="mt-4 space-y-2">
          {showUrl && (
            <input
              className="input font-mono"
              type="url"
              placeholder={p.default_base_url ? `Base URL (default ${p.default_base_url})` : "Base URL, e.g. https://llm.example.com/v1"}
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              required={p.base_url_mode === "required"}
              aria-label={`${p.display_name} base URL`}
            />
          )}
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              className="input font-mono"
              type="password"
              autoComplete="off"
              placeholder={p.requires_api_key ? (savedConnection ? "Replace API key" : "Paste API key") : "API key (optional)"}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              minLength={p.requires_api_key ? 8 : undefined}
              required={p.requires_api_key}
              aria-label={`${p.display_name} API key`}
            />
            <button className="btn-primary shrink-0" disabled={busy}>{busy ? "Verifying…" : savedConnection ? "Update" : "Connect"}</button>
          </div>
        </form>
      )}
      {p.integration === "external" && (
        <p className="mt-4 text-xs text-mist">Add an external agent from a project&apos;s Agent panel by providing its endpoint URL (Power plan and above).</p>
      )}
      {msg && <p className={`mt-2 text-xs ${msg.ok ? "text-ok" : "text-bad"}`}>{msg.text}</p>}
    </div>
  );
}
