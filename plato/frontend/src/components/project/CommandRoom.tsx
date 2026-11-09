"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Agent, Mode, PlatoEvent, Run, Task } from "@/lib/types";
import { MODE_LABEL } from "@/lib/types";
import type { Partial } from "@/lib/useProjectStream";
import { agentColor, agentName, cleanLive, time } from "./util";

type Props = {
  agents: Agent[];
  run: Run | null;
  events: PlatoEvent[];
  partials: Record<string, Partial>;
  tasks: Task[];
  defaultMode: Mode;
  onStart: (objective: string, mode: Mode) => Promise<void>;
  onSend: (content: string, to: string[] | null) => Promise<void>;
  onControl: (action: "run.pause" | "run.resume" | "run.stop") => void;
  onDecide: (taskId: string, approve: boolean) => void;
};

export default function CommandRoom({ agents, run, events, partials, tasks, defaultMode, onStart, onSend, onControl, onDecide }: Props) {
  const active = !!run && ["pending", "running", "paused"].includes(run.status);
  const scroller = useRef<HTMLDivElement>(null);
  const live = Object.values(partials);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    // Only auto-scroll the feed's own scroller (never the window), and only if the user is near the bottom.
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 240) el.scrollTop = el.scrollHeight;
  }, [events.length, live.map((p) => p.text.length).join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  const awaiting = useMemo(() => new Set(tasks.filter((t) => t.status === "awaiting_approval").map((t) => t.id)), [tasks]);

  return (
    <section className="panel flex h-[calc(100dvh-10rem)] min-h-[480px] flex-col lg:h-[calc(100vh-11rem)]">
      <header className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
        <h2 className="panel-title">Command room</h2>
        {run && (
          <>
            <span className={`chip ${run.status === "running" ? "border-cyan/40 text-cyan" : run.status === "paused" ? "border-warn/40 text-warn" : ""}`}>
              {run.status.replace("_", " ")}
            </span>
            <span className="chip">{MODE_LABEL[run.mode]}</span>
            <span className="chip">est. ${run.cost_usd.toFixed(4)}</span>
          </>
        )}
        {active && (
          <div className="ml-auto flex gap-2">
            {run!.status === "paused" ? (
              <button className="btn text-xs" onClick={() => onControl("run.resume")}>Resume</button>
            ) : (
              <button className="btn text-xs" onClick={() => onControl("run.pause")}>Pause</button>
            )}
            <button className="btn-danger text-xs" onClick={() => onControl("run.stop")}>Stop</button>
          </div>
        )}
      </header>

      <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {!run && (
          <div className="mx-auto mt-10 max-w-md text-center">
            <p className="text-lg font-light">The command room is quiet.</p>
            <p className="mt-2 text-sm text-mist">Give your team an objective below. Every agent starts at once and talks to the others directly.</p>
          </div>
        )}
        {run && (
          <div className="rounded-lg border border-line bg-black/30 p-3 text-sm">
            <span className="panel-title">Objective</span>
            <p className="mt-1 whitespace-pre-wrap">{run.objective}</p>
          </div>
        )}
        {events.map((e) => (
          <FeedItem key={e.seq} e={e} agents={agents} awaiting={awaiting} active={active} onDecide={onDecide} />
        ))}
        {live.map((p) => (
          <Bubble key={p.turn_id} agents={agents} agentId={p.agent_id} text={cleanLive(p.text)} streaming />
        ))}
      </div>

      <Composer agents={agents} active={active} defaultMode={defaultMode} onStart={onStart} onSend={onSend} />
    </section>
  );
}

function Bubble({ agents, agentId, text, streaming = false, done, ts }: {
  agents: Agent[]; agentId: string | null; text: string; streaming?: boolean; done?: string | null; ts?: string;
}) {
  const color = agentColor(agents, agentId);
  return (
    <div className="flex gap-3">
      <div className="mt-1 h-7 w-7 shrink-0 rounded-full border text-center text-xs leading-7" style={{ borderColor: `${color}66`, color }}>
        {agentName(agents, agentId).slice(0, 1)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2 text-xs">
          <span style={{ color }}>{agentName(agents, agentId)}</span>
          <span className="text-mist">{agents.find((a) => a.id === agentId)?.model}</span>
          {streaming && <span className="text-cyan animate-pulseline">● streaming</span>}
          {ts && <span className="ml-auto text-mist/70">{time(ts)}</span>}
        </div>
        <div className="mt-1 whitespace-pre-wrap break-words text-sm leading-relaxed text-ice/90">
          {text || (streaming ? <span className="text-mist">…</span> : <span className="text-mist">(only directives)</span>)}
          {streaming && <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-pulseline bg-cyan" />}
        </div>
        {done && <p className="mt-2 rounded-md border border-ok/30 bg-ok/5 px-2 py-1 text-xs text-ok">✓ {done}</p>}
      </div>
    </div>
  );
}

function FeedItem({ e, agents, awaiting, active, onDecide }: {
  e: PlatoEvent; agents: Agent[]; awaiting: Set<string>; active: boolean; onDecide: (id: string, ok: boolean) => void;
}) {
  const d = e.data;
  const ts = e.ts || e.created_at;
  switch (e.type) {
    case "agent.turn.completed":
      return <Bubble agents={agents} agentId={e.agent_id} text={d.visible_text} done={d.done} ts={ts} />;
    case "agent.turn.interrupted":
      return <System tone="warn">{agentName(agents, e.agent_id)} was interrupted{d.partial ? ` after: “${String(d.partial).slice(0, 140)}…”` : ""}</System>;
    case "message.sent":
      if (d.kind === "commander")
        return (
          <div className="ml-auto max-w-[85%] rounded-lg border border-volt/40 bg-volt/10 px-3 py-2 text-sm">
            <p className="mb-1 text-[11px] text-mist">You → {d.to_names.join(", ")}</p>
            <p className="whitespace-pre-wrap">{d.content}</p>
          </div>
        );
      return (
        <div className="ml-10 rounded-lg border border-line bg-gradient-to-r from-cyan/[0.06] to-transparent px-3 py-2 text-sm">
          <p className="mb-1 text-[11px]">
            <span style={{ color: agentColor(agents, d.from) }}>{d.from_name}</span>
            <span className="text-mist"> ⟶ </span>
            {d.to.map((id: string, i: number) => (
              <span key={id} style={{ color: agentColor(agents, id) }}>{i ? ", " : ""}{agentName(agents, id)}</span>
            ))}
          </p>
          <p className="whitespace-pre-wrap text-ice/90">{d.content}</p>
        </div>
      );
    case "task.created":
      return (
        <div className="ml-10 rounded-lg border border-line px-3 py-2 text-sm">
          <p className="text-[11px] text-mist">
            Task · {d.created_by} → {d.assignee_name} {d.status === "awaiting_approval" && <span className="text-warn">· needs your approval</span>}
          </p>
          <p className="font-medium">{d.title}</p>
          <p className="mt-1 whitespace-pre-wrap text-xs text-mist">{d.description}</p>
          {active && awaiting.has(d.task_id) && (
            <div className="mt-2 flex gap-2">
              <button className="btn-primary text-xs" onClick={() => onDecide(d.task_id, true)}>Approve</button>
              <button className="btn-danger text-xs" onClick={() => onDecide(d.task_id, false)}>Reject</button>
            </div>
          )}
        </div>
      );
    case "run.status":
      if (d.status === "running") return <System>{d.reason ? `Run resumed — ${d.reason}` : "Run started"}</System>;
      return <System>Run {d.status.replace("_", " ")}{d.reason ? ` — ${d.reason}` : ""}</System>;
    case "limit.reached":
      return <System tone="warn">Limit reached: {d.limit}{d.agent ? ` (${d.agent})` : ""} = {d.value}</System>;
    case "directive.rejected":
      return <System tone="warn">{d.name}: {d.reason}</System>;
    case "error":
      return <System tone={d.retrying ? "warn" : "bad"}>{agentName(agents, e.agent_id)}: {d.message}</System>;
    default:
      return null;
  }
}

function System({ children, tone }: { children: React.ReactNode; tone?: "warn" | "bad" }) {
  const c = tone === "bad" ? "text-bad" : tone === "warn" ? "text-warn" : "text-mist";
  return (
    <div className="flex items-center gap-3 py-1">
      <div className="laser flex-1 opacity-40" />
      <p className={`max-w-[80%] text-center text-[11px] ${c}`}>{children}</p>
      <div className="laser flex-1 opacity-40" />
    </div>
  );
}

function Composer({ agents, active, defaultMode, onStart, onSend }: {
  agents: Agent[]; active: boolean; defaultMode: Mode; onStart: Props["onStart"]; onSend: Props["onSend"];
}) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState<Mode>(defaultMode);
  const [to, setTo] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => setMode(defaultMode), [defaultMode]);

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      if (active) await onSend(text.trim(), to.length ? to : null);
      else await onStart(text.trim(), mode);
      setText("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="border-t border-line p-3">
      {active ? (
        <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px]">
          <span className="text-mist">To:</span>
          <button type="button" onClick={() => setTo([])} className={`chip ${to.length === 0 ? "border-cyan/50 text-cyan" : ""}`}>
            All primary agents
          </button>
          {agents.map((a) => (
            <button
              type="button"
              key={a.id}
              onClick={() => setTo((t) => (t.includes(a.id) ? t.filter((x) => x !== a.id) : [...t, a.id]))}
              className={`chip ${to.includes(a.id) ? "border-cyan/50 text-cyan" : ""}`}
            >
              {a.name}
            </button>
          ))}
        </div>
      ) : (
        <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px]">
          <label htmlFor="mode" className="text-mist">Mode</label>
          <select id="mode" className="input w-auto py-1 text-xs" value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
            {Object.entries(MODE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      )}
      <div className="flex gap-2">
        <textarea
          className="input min-h-[44px] flex-1 resize-y"
          rows={2}
          maxLength={20000}
          placeholder={active ? "Message the team…  (Enter to send, Shift+Enter for a new line)" : "Describe the project objective for your agent team…"}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          aria-label={active ? "Message" : "Objective"}
        />
        <button className="btn-primary self-end px-4" disabled={busy || !text.trim() || agents.length === 0}>
          {active ? "Send" : "Start run"}
        </button>
      </div>
      {agents.length === 0 && <p className="mt-2 text-xs text-mist">Add an agent first.</p>}
      {error && <p className="mt-2 text-xs text-bad" role="alert">{error}</p>}
    </form>
  );
}
