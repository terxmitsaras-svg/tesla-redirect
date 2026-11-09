"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Agent, PlatoEvent, Project, ProjectFile, ProjectSettings, Run, Task } from "@/lib/types";
import { MODE_LABEL } from "@/lib/types";
import { agentColor, agentName, STATUS_STYLE, time } from "./util";

/* ------------------------------------------------------------------ Hierarchy */
export function HierarchyView({ agents, statuses }: { agents: Agent[]; statuses: Record<string, string> }) {
  const primaries = agents.filter((a) => !a.parent_id);
  const W = Math.max(640, primaries.length * 220);
  const colW = W / Math.max(primaries.length, 1);
  const nodes: { a: Agent; x: number; y: number }[] = [];
  primaries.forEach((p, i) => {
    const x = colW * i + colW / 2;
    nodes.push({ a: p, x, y: 170 });
    const subs = agents.filter((s) => s.parent_id === p.id);
    subs.forEach((s, j) => nodes.push({ a: s, x: x + (j - (subs.length - 1) / 2) * 110, y: 310 }));
  });
  const pos = new Map(nodes.map((n) => [n.a.id, n]));
  const H = agents.some((a) => a.parent_id) ? 380 : 240;

  return (
    <section className="panel overflow-x-auto p-4">
      <h2 className="panel-title mb-2">Hierarchy</h2>
      {agents.length === 0 ? (
        <p className="text-sm text-mist">No agents yet.</p>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full min-w-[560px]" role="img" aria-label="Agent hierarchy">
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="b" />
              <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          {nodes.map(({ a, x, y }) => {
            const parent = a.parent_id ? pos.get(a.parent_id) : { x: W / 2, y: 50 };
            return parent ? <line key={`l${a.id}`} x1={parent.x} y1={parent.y + 18} x2={x} y2={y - 22} stroke="#5ee7ff" strokeOpacity="0.35" strokeWidth="1" /> : null;
          })}
          <g filter="url(#glow)">
            <circle cx={W / 2} cy={50} r={18} fill="#020306" stroke="#e8f1ff" strokeWidth="1" />
          </g>
          <text x={W / 2} y={54} textAnchor="middle" fill="#e8f1ff" fontSize="11">You</text>
          <text x={W / 2} y={86} textAnchor="middle" fill="#8a98ad" fontSize="10" letterSpacing="2">COMMANDER</text>
          {nodes.map(({ a, x, y }) => {
            const c = agentColor(agents, a.id);
            const st = statuses[a.id] || "idle";
            const busy = st === "streaming" || st === "thinking";
            return (
              <g key={a.id}>
                <circle cx={x} cy={y} r={a.parent_id ? 16 : 22} fill="#020306" stroke={c} strokeWidth={busy ? 2 : 1} filter={busy ? "url(#glow)" : undefined}>
                  {busy && <animate attributeName="stroke-opacity" values="0.4;1;0.4" dur="1.6s" repeatCount="indefinite" />}
                </circle>
                <text x={x} y={y + 4} textAnchor="middle" fill={c} fontSize="11">{a.name.slice(0, 2)}</text>
                <text x={x} y={y + (a.parent_id ? 34 : 40)} textAnchor="middle" fill="#e8f1ff" fontSize="11">{a.name}</text>
                <text x={x} y={y + (a.parent_id ? 48 : 54)} textAnchor="middle" fill="#8a98ad" fontSize="9">{a.provider} · {STATUS_STYLE[st]?.label || st}</text>
              </g>
            );
          })}
        </svg>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ Task board */
const COLUMNS: { title: string; statuses: string[] }[] = [
  { title: "Pending", statuses: ["pending", "awaiting_approval"] },
  { title: "Active", statuses: ["running"] },
  { title: "Completed", statuses: ["completed"] },
  { title: "Failed / closed", statuses: ["failed", "rejected", "cancelled", "unfinished"] },
];

export function TaskBoard({ tasks, agents }: { tasks: Task[]; agents: Agent[] }) {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {COLUMNS.map((col) => {
        const items = tasks.filter((t) => col.statuses.includes(t.status));
        return (
          <div key={col.title} className="panel p-3">
            <h3 className="panel-title mb-3">{col.title} · {items.length}</h3>
            <ul className="space-y-2">
              {items.map((t) => (
                <li key={t.id} className="rounded-lg border border-line bg-black/30 p-3 text-sm">
                  <p className="font-medium">{t.title}</p>
                  <p className="mt-1 text-[11px] text-mist">
                    {t.created_by_agent_id ? agentName(agents, t.created_by_agent_id) : "Commander"} →{" "}
                    <span style={{ color: agentColor(agents, t.assignee_agent_id) }}>{agentName(agents, t.assignee_agent_id)}</span>
                    {t.status !== col.statuses[0] && <span> · {t.status.replace("_", " ")}</span>}
                  </p>
                  {t.result && <p className="mt-2 line-clamp-4 text-xs text-ice/80">{t.result}</p>}
                </li>
              ))}
              {items.length === 0 && <li className="text-xs text-mist">—</li>}
            </ul>
          </div>
        );
      })}
    </section>
  );
}

/* ------------------------------------------------------------------ Timeline */
const TL: Record<string, string> = {
  "run.status": "◆", "agent.turn.started": "▸", "agent.turn.completed": "■", "agent.turn.interrupted": "⏸",
  "message.sent": "⟶", "task.created": "＋", "task.updated": "↻", "usage.updated": "$", "limit.reached": "!",
  "directive.rejected": "✕", error: "!", "agent.status": "·",
};

function describe(e: PlatoEvent, agents: Agent[]): string {
  const d = e.data;
  const who = e.agent_id ? agentName(agents, e.agent_id) : "";
  switch (e.type) {
    case "run.status": return d.status === "running" ? (d.reason ? "Run resumed" : "Run started") : `Run ${d.status.replace("_", " ")}`;
    case "agent.turn.started": return `${who} started turn ${d.turn} (${d.inputs.map((i: { from: string }) => i.from).join(", ")})`;
    case "agent.turn.completed": return `${who} replied · ${d.usage?.output_tokens ?? 0} tok`;
    case "agent.turn.interrupted": return `${who} interrupted`;
    case "message.sent": return `${d.from_name} → ${d.to_names.join(", ")}`;
    case "task.created": return `Task “${d.title}” → ${d.assignee_name}`;
    case "task.updated": return `Task “${d.title}” ${d.status}`;
    case "usage.updated": return `Run cost $${Number(d.cost_usd).toFixed(4)}`;
    case "limit.reached": return `Limit ${d.limit}`;
    case "directive.rejected": return `${d.name}: ${d.reason}`;
    case "agent.status": return `${who} ${d.status}`;
    case "error": return `${who}: ${d.message}`;
    default: return e.type;
  }
}

export function Timeline({ events, agents }: { events: PlatoEvent[]; agents: Agent[] }) {
  const shown = events.filter((e) => e.type !== "agent.status").slice(-300).reverse();
  return (
    <section className="panel flex flex-col p-4 lg:h-[calc(100vh-11rem)]">
      <h2 className="panel-title mb-3">Activity timeline</h2>
      <ol className="flex-1 space-y-1.5 overflow-y-auto text-xs">
        {shown.map((e) => (
          <li key={e.seq} className="flex gap-2">
            <span className="w-14 shrink-0 font-mono text-mist/70">{time(e.ts || e.created_at)}</span>
            <span className="w-3 shrink-0 text-center" style={{ color: agentColor(agents, e.agent_id) }}>{TL[e.type] || "·"}</span>
            <span className={e.type === "error" || e.type === "limit.reached" ? "text-warn" : "text-ice/80"}>{describe(e, agents)}</span>
          </li>
        ))}
        {shown.length === 0 && <li className="text-mist">No activity yet.</li>}
      </ol>
    </section>
  );
}

/* ------------------------------------------------------------------ Workspace */
export function Workspace({ project, onProjectChange }: { project: Project; onProjectChange: (p: Project) => void }) {
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [sel, setSel] = useState<ProjectFile | null>(null);
  const [draft, setDraft] = useState({ path: "", content: "", shared_with_agents: true });
  const [context, setContext] = useState(project.shared_context);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api<ProjectFile[]>(`/api/projects/${project.id}/files`).then(setFiles);
  }, [project.id]);

  async function saveFile(e: React.FormEvent) {
    e.preventDefault();
    try {
      const f = await api<ProjectFile>(`/api/projects/${project.id}/files`, { method: "PUT", json: draft });
      setFiles((fs) => [...fs.filter((x) => x.id !== f.id), f].sort((a, b) => a.path.localeCompare(b.path)));
      setSel(f);
      setMsg("Saved.");
    } catch (err) {
      setMsg((err as Error).message);
    }
  }

  async function saveContext() {
    const p = await api<Project>(`/api/projects/${project.id}`, { method: "PATCH", json: { shared_context: context } });
    onProjectChange(p);
    setMsg("Shared context saved.");
  }

  return (
    <section className="grid gap-4 lg:grid-cols-[260px_1fr]">
      <div className="panel p-4">
        <h2 className="panel-title mb-3">Files</h2>
        <button className="btn mb-3 w-full text-xs" onClick={() => { setSel(null); setDraft({ path: "", content: "", shared_with_agents: true }); }}>+ New file</button>
        <ul className="space-y-1 text-sm">
          {files.map((f) => (
            <li key={f.id}>
              <button
                className={`w-full truncate rounded px-2 py-1 text-left font-mono text-xs ${sel?.id === f.id ? "bg-white/5 text-cyan" : "text-ice/80 hover:bg-white/5"}`}
                onClick={() => { setSel(f); setDraft({ path: f.path, content: f.content, shared_with_agents: f.shared_with_agents }); }}
              >
                {f.path}
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="space-y-4">
        <div className="panel p-4">
          <h2 className="panel-title mb-2">Shared project context</h2>
          <p className="mb-2 text-xs text-mist">Visible to every agent in every run (instructions, constraints, definitions).</p>
          <textarea className="input min-h-[100px] font-mono text-xs" value={context} onChange={(e) => setContext(e.target.value)} maxLength={50000} />
          <button className="btn mt-2 text-xs" onClick={saveContext}>Save context</button>
        </div>
        <form onSubmit={saveFile} className="panel space-y-2 p-4">
          <h2 className="panel-title">{sel ? "Edit file" : "New file"}</h2>
          <input className="input font-mono text-xs" placeholder="docs/spec.md" required value={draft.path} onChange={(e) => setDraft({ ...draft, path: e.target.value })} />
          <textarea className="input min-h-[260px] font-mono text-xs" value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} />
          <label className="flex items-center gap-2 text-xs text-mist">
            <input type="checkbox" checked={draft.shared_with_agents} onChange={(e) => setDraft({ ...draft, shared_with_agents: e.target.checked })} />
            Share with agents (read-only, treated as untrusted data in their context)
          </label>
          <div className="flex items-center gap-3">
            <button className="btn-primary text-xs">Save file</button>
            {sel && (
              <button type="button" className="btn-danger text-xs" onClick={async () => {
                await api(`/api/projects/${project.id}/files/${sel.id}`, { method: "DELETE" });
                setFiles((fs) => fs.filter((x) => x.id !== sel.id));
                setSel(null);
              }}>Delete</button>
            )}
            {msg && <span className="text-xs text-mist">{msg}</span>}
          </div>
        </form>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ Controls */
export function Controls({ project, runs, onProjectChange }: { project: Project; runs: Run[]; onProjectChange: (p: Project) => void }) {
  const [s, setS] = useState<ProjectSettings>(project.settings);
  const [msg, setMsg] = useState("");
  const num = (k: keyof ProjectSettings) => (e: React.ChangeEvent<HTMLInputElement>) => setS({ ...s, [k]: Number(e.target.value) });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      const p = await api<Project>(`/api/projects/${project.id}`, { method: "PATCH", json: { settings: s } });
      onProjectChange(p);
      setMsg("Saved. Applies to the next run (values above your plan's limits are clamped).");
    } catch (err) {
      setMsg((err as Error).message);
    }
  }

  const fields: [keyof ProjectSettings, string, number, number, number][] = [
    ["max_turns_per_agent", "Max turns per agent", 1, 100, 1],
    ["max_agent_messages", "Max agent-to-agent messages", 0, 1000, 1],
    ["max_run_seconds", "Max run time (seconds)", 30, 86400, 30],
    ["max_output_tokens", "Max output tokens per turn", 256, 32000, 256],
    ["budget_usd", "Budget per run (USD)", 0, 10000, 0.1],
  ];

  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <form onSubmit={save} className="panel space-y-3 p-4">
        <h2 className="panel-title">Collaboration &amp; safety controls</h2>
        <div>
          <label className="label" htmlFor="c-mode">Default collaboration mode</label>
          <select id="c-mode" className="input" value={s.mode} onChange={(e) => setS({ ...s, mode: e.target.value as ProjectSettings["mode"] })}>
            {Object.entries(MODE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={s.approve_delegations} onChange={(e) => setS({ ...s, approve_delegations: e.target.checked })} />
          Require my approval before an agent delegates a task
        </label>
        <div className="grid grid-cols-2 gap-3">
          {fields.map(([k, label, min, max, step]) => (
            <div key={k}>
              <label className="label" htmlFor={`c-${k}`}>{label}</label>
              <input id={`c-${k}`} className="input" type="number" min={min} max={max} step={step} value={s[k] as number} onChange={num(k)} />
            </div>
          ))}
        </div>
        <button className="btn-primary text-xs">Save controls</button>
        {msg && <p className="text-xs text-mist">{msg}</p>}
      </form>
      <div className="panel p-4">
        <h2 className="panel-title mb-3">Run history</h2>
        <ul className="space-y-2 text-sm">
          {runs.map((r) => (
            <li key={r.id} className="rounded-lg border border-line p-3">
              <div className="flex justify-between gap-2">
                <span className="truncate">{r.objective}</span>
                <span className="chip shrink-0">{r.status.replace("_", " ")}</span>
              </div>
              <p className="mt-1 text-[11px] text-mist">
                {new Date(r.created_at).toLocaleString()} · {r.input_tokens + r.output_tokens} tok · est. ${r.cost_usd.toFixed(4)}
                {r.stop_reason ? ` · ${r.stop_reason}` : ""}
              </p>
            </li>
          ))}
          {runs.length === 0 && <li className="text-mist">No runs yet.</li>}
        </ul>
      </div>
    </section>
  );
}
