"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Agent, Provider } from "@/lib/types";
import { CATEGORY_LABEL } from "@/lib/types";
import { agentColor, STATUS_STYLE } from "./util";

type Props = {
  projectId: string;
  agents: Agent[];
  statuses: Record<string, string>;
  canInterrupt: boolean;
  onInterrupt: (agentId: string) => void;
  onChanged: () => void;
};

export default function AgentPanel({ projectId, agents, statuses, canInterrupt, onInterrupt, onChanged }: Props) {
  const [adding, setAdding] = useState(false);
  const primaries = agents.filter((a) => !a.parent_id);

  return (
    <section className="panel flex flex-col p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="panel-title">Agents</h2>
        <button className="btn px-2 py-1 text-xs" onClick={() => setAdding((v) => !v)}>{adding ? "Close" : "+ Add agent"}</button>
      </div>
      {adding && <AgentForm projectId={projectId} agents={agents} onDone={() => { setAdding(false); onChanged(); }} />}
      {agents.length === 0 && !adding && <p className="text-sm text-mist">No agents yet. Add at least one to start a run.</p>}
      <ul className="space-y-2">
        {primaries.map((a) => (
          <li key={a.id}>
            <AgentRow agent={a} agents={agents} status={statuses[a.id]} canInterrupt={canInterrupt} onInterrupt={onInterrupt} onChanged={onChanged} />
            <ul className="ml-4 mt-2 space-y-2 border-l border-line pl-3">
              {agents.filter((s) => s.parent_id === a.id).map((s) => (
                <li key={s.id}>
                  <AgentRow agent={s} agents={agents} status={statuses[s.id]} canInterrupt={canInterrupt} onInterrupt={onInterrupt} onChanged={onChanged} sub />
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AgentRow({ agent: a, agents, status, canInterrupt, onInterrupt, onChanged, sub = false }: {
  agent: Agent; agents: Agent[]; status?: string; canInterrupt: boolean; onInterrupt: (id: string) => void; onChanged: () => void; sub?: boolean;
}) {
  const st = STATUS_STYLE[status || "idle"] || STATUS_STYLE.idle;
  const generating = status === "streaming" || status === "thinking";
  return (
    <div className="group rounded-lg border border-line bg-black/30 p-3">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: agentColor(agents, a.id), boxShadow: `0 0 8px ${agentColor(agents, a.id)}` }} />
        <span className="truncate font-medium">{a.name}</span>
        {sub && <span className="chip px-1.5 py-0 text-[10px]">sub</span>}
        <span className="ml-auto flex items-center gap-1.5 text-[11px] text-mist">
          <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`} />
          {st.label}
        </span>
      </div>
      <p className="mt-1 truncate text-xs text-mist">{a.role || "—"}</p>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className="chip">{a.provider}</span>
        <span className="chip font-mono">{a.model}</span>
        {a.provider === "mock" && <span className="chip border-warn/40 text-warn">simulated</span>}
        <div className="ml-auto flex gap-2 opacity-100 sm:opacity-0 sm:transition sm:group-hover:opacity-100">
          {canInterrupt && generating && (
            <button className="text-[11px] text-warn hover:underline" onClick={() => onInterrupt(a.id)}>Interrupt</button>
          )}
          <button
            className="text-[11px] text-bad hover:underline"
            onClick={async () => {
              if (!confirm(`Delete ${a.name}${sub ? "" : " and its subagents"}?`)) return;
              await api(`/api/agents/${a.id}`, { method: "DELETE" });
              onChanged();
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

function AgentForm({ projectId, agents, onDone }: { projectId: string; agents: Agent[]; onDone: () => void }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [f, setF] = useState({ name: "", role: "", provider: "", model: "", instructions: "", parent_id: "", external_url: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Provider[]>("/api/providers").then((ps) => {
      setProviders(ps);
      const first = ps.find((p) => p.connected && p.integration === "hosted") || ps.find((p) => p.connected);
      if (first) setF((x) => ({ ...x, provider: first.id }));
    });
  }, []);

  useEffect(() => {
    if (!f.provider) return;
    setModels([]);
    api<{ models: string[] }>(`/api/providers/${f.provider}/models`)
      .then((r) => {
        setModels(r.models);
        setF((x) => ({ ...x, model: x.model && r.models.includes(x.model) ? x.model : r.models[0] || "" }));
      })
      .catch(() => setModels([]));
  }, [f.provider]);

  const provider = providers.find((p) => p.id === f.provider);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api(`/api/projects/${projectId}/agents`, {
        method: "POST",
        json: {
          name: f.name.trim(), role: f.role, instructions: f.instructions, provider: f.provider, model: f.model.trim(),
          parent_id: f.parent_id || null, kind: provider?.integration === "external" ? "external" : "hosted",
          external_url: provider?.integration === "external" ? f.external_url : null,
        },
      });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  return (
    <form onSubmit={submit} className="mb-4 space-y-3 rounded-lg border border-cyan/20 bg-black/40 p-3">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="label" htmlFor="ag-name">Name</label>
          <input id="ag-name" className="input" required maxLength={64} pattern="[A-Za-z0-9][A-Za-z0-9 _.\-]*" value={f.name} onChange={set("name")} placeholder="Architect" />
        </div>
        <div>
          <label className="label" htmlFor="ag-role">Role</label>
          <input id="ag-role" className="input" maxLength={120} value={f.role} onChange={set("role")} placeholder="Software architect" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="label" htmlFor="ag-prov">Provider</label>
          <select id="ag-prov" className="input" value={f.provider} onChange={set("provider")} required>
            <option value="" disabled>Select…</option>
            {(["frontier", "open", "local", "custom"] as const).map((cat) => (
              <optgroup key={cat} label={CATEGORY_LABEL[cat].title}>
                {providers.filter((p) => p.category === cat).map((p) => {
                  const usable = p.connected || p.platform_managed_available || p.integration !== "hosted";
                  const note = !p.connected && p.integration === "hosted"
                    ? (p.platform_managed_available ? " (platform credits)" : " (connect first)")
                    : "";
                  return <option key={p.id} value={p.id} disabled={!usable}>{p.display_name}{note}</option>;
                })}
              </optgroup>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="ag-model">Model</label>
          <input id="ag-model" className="input font-mono" list="ag-models" required value={f.model} onChange={set("model")} placeholder="model id" />
          <datalist id="ag-models">{models.map((m) => <option key={m} value={m} />)}</datalist>
        </div>
      </div>
      {provider?.integration === "external" && (
        <div>
          <label className="label" htmlFor="ag-url">Agent endpoint (PLATO External Agent Protocol)</label>
          <input id="ag-url" className="input font-mono" type="url" required value={f.external_url} onChange={set("external_url")} placeholder="https://agent.example.com/plato" />
        </div>
      )}
      <div>
        <label className="label" htmlFor="ag-parent">Reports to</label>
        <select id="ag-parent" className="input" value={f.parent_id} onChange={set("parent_id")}>
          <option value="">Commander (primary agent)</option>
          {agents.filter((a) => !a.parent_id).map((a) => <option key={a.id} value={a.id}>{a.name} (as subagent)</option>)}
        </select>
      </div>
      <div>
        <label className="label" htmlFor="ag-instr">Instructions</label>
        <textarea id="ag-instr" className="input min-h-[72px]" maxLength={20000} value={f.instructions} onChange={set("instructions")} placeholder="Behavioural rules, focus areas, output format…" />
      </div>
      {error && <p className="text-xs text-bad" role="alert">{error}</p>}
      <button className="btn-primary w-full" disabled={busy}>{busy ? "Adding…" : "Add agent"}</button>
    </form>
  );
}
