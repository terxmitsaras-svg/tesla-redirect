"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import AgentPanel from "@/components/project/AgentPanel";
import CommandRoom from "@/components/project/CommandRoom";
import { Controls, HierarchyView, TaskBoard, Timeline, Workspace } from "@/components/project/Panels";
import { mergeEvents } from "@/components/project/util";
import { api } from "@/lib/api";
import type { Agent, Mode, PlatoEvent, Project, Run, Task } from "@/lib/types";
import { ACTIVE } from "@/lib/types";
import { useProjectStream } from "@/lib/useProjectStream";

const TABS = ["Command room", "Hierarchy", "Tasks", "Workspace", "Controls"] as const;
type Tab = (typeof TABS)[number];

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [project, setProject] = useState<Project | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [events, setEvents] = useState<PlatoEvent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statuses, setStatuses] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<Tab>("Command room");
  const [mobilePane, setMobilePane] = useState<"main" | "agents" | "timeline">("main");
  const [toast, setToast] = useState("");
  const [loadError, setLoadError] = useState("");

  const runIdRef = useRef<string | null>(null);
  runIdRef.current = runId;
  const lastSeq = useRef(0);
  lastSeq.current = events.length ? events[events.length - 1].seq! : 0;

  const loadAgents = useCallback(() => api<Agent[]>(`/api/projects/${id}/agents`).then(setAgents), [id]);
  const loadTasks = useCallback(
    (rid: string | null) => (rid ? api<Task[]>(`/api/projects/${id}/tasks?run_id=${rid}`).then(setTasks) : Promise.resolve(setTasks([]))),
    [id],
  );
  const loadRuns = useCallback(() => api<Run[]>(`/api/projects/${id}/runs`).then((rs) => { setRuns(rs); return rs; }), [id]);

  const selectRun = useCallback(
    async (rid: string | null) => {
      setRunId(rid);
      runIdRef.current = rid;
      setEvents([]);
      setStatuses({});
      if (!rid) return setTasks([]);
      const evs = await api<PlatoEvent[]>(`/api/runs/${rid}/events`);
      if (runIdRef.current !== rid) return;
      setEvents((prev) => mergeEvents(prev, evs));
      const st: Record<string, string> = {};
      for (const e of evs) if (e.type === "agent.status" && e.agent_id) st[e.agent_id] = e.data.status;
      setStatuses(st);
      loadTasks(rid);
    },
    [loadTasks],
  );

  useEffect(() => {
    (async () => {
      try {
        const [p] = await Promise.all([api<Project>(`/api/projects/${id}`), loadAgents()]);
        setProject(p);
        const rs = await loadRuns();
        if (rs[0]) await selectRun(rs[0].id);
      } catch (e) {
        setLoadError((e as Error).message);
      }
    })();
  }, [id, loadAgents, loadRuns, selectRun]);

  const gapFill = useCallback(async (rid: string) => {
    const evs = await api<PlatoEvent[]>(`/api/runs/${rid}/events?after_seq=${lastSeq.current}`);
    if (runIdRef.current === rid) setEvents((prev) => mergeEvents(prev, evs));
  }, []);

  const onEvent = useCallback(
    (e: PlatoEvent) => {
      if (e.type === "snapshot") {
        if (runIdRef.current) gapFill(runIdRef.current);
        loadRuns();
        return;
      }
      if (e.type === "action.error") {
        setToast(e.data.message);
        return;
      }
      if (!e.run_id) return;
      if (e.run_id !== runIdRef.current) {
        if (e.type === "run.status" && e.data.status === "running") {
          loadRuns();
          selectRun(e.run_id);
        }
        return;
      }
      if (e.seq != null) {
        if (e.seq > lastSeq.current + 1 && lastSeq.current > 0) gapFill(e.run_id);
        setEvents((prev) => mergeEvents(prev, [e]));
      }
      if (e.type === "agent.status" && e.agent_id) setStatuses((s) => ({ ...s, [e.agent_id!]: e.data.status }));
      if (e.type === "task.created" || e.type === "task.updated") loadTasks(e.run_id);
      if (e.type === "usage.updated")
        setRuns((rs) => rs.map((r) => (r.id === e.run_id ? { ...r, cost_usd: e.data.cost_usd, input_tokens: e.data.input_tokens, output_tokens: e.data.output_tokens } : r)));
      if (e.type === "run.status") {
        setRuns((rs) => rs.map((r) => (r.id === e.run_id ? { ...r, status: e.data.status, stop_reason: e.data.reason ?? r.stop_reason } : r)));
        if (!["running", "paused"].includes(e.data.status)) {
          loadRuns();
          loadTasks(e.run_id);
        }
      }
    },
    [gapFill, loadRuns, loadTasks, selectRun],
  );

  const { conn, partials, send } = useProjectStream(id, onEvent);
  const run = runs.find((r) => r.id === runId) || null;
  const isActive = !!run && ACTIVE.includes(run.status);
  const runPartials = Object.fromEntries(Object.entries(partials).filter(([, p]) => agents.some((a) => a.id === p.agent_id)));

  async function startRun(objective: string, mode: Mode) {
    const r = await api<Run>(`/api/projects/${id}/runs`, { method: "POST", json: { objective, mode } });
    setRuns((rs) => [r, ...rs.filter((x) => x.id !== r.id)]);
    if (runIdRef.current !== r.id) await selectRun(r.id);
  }

  async function sendMessage(content: string, to: string[] | null) {
    if (!runId) return;
    if (!send({ action: "user.message", run_id: runId, content, to })) {
      await api(`/api/runs/${runId}/messages`, { method: "POST", json: { content, to } });
    }
  }

  function control(action: "run.pause" | "run.resume" | "run.stop") {
    if (!runId) return;
    if (!send({ action, run_id: runId })) api(`/api/runs/${runId}/${action.split(".")[1]}`, { method: "POST" }).catch((e) => setToast(e.message));
  }

  function interrupt(agentId: string) {
    if (runId && !send({ action: "agent.interrupt", run_id: runId, agent_id: agentId }))
      api(`/api/runs/${runId}/agents/${agentId}/interrupt`, { method: "POST" }).catch((e) => setToast(e.message));
  }

  function decide(taskId: string, approve: boolean) {
    if (runId && !send({ action: approve ? "task.approve" : "task.reject", run_id: runId, task_id: taskId }))
      api(`/api/runs/${runId}/tasks/${taskId}/${approve ? "approve" : "reject"}`, { method: "POST" }).catch((e) => setToast(e.message));
  }

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  if (loadError)
    return (
      <AppShell>
        <p className="text-bad">{loadError}</p>
        <Link href="/" className="mt-4 inline-block text-cyan">← Projects</Link>
      </AppShell>
    );
  if (!project) return <AppShell><p className="text-mist">Loading…</p></AppShell>;

  const agentPanel = (
    <AgentPanel projectId={id} agents={agents} statuses={statuses} canInterrupt={isActive} onInterrupt={interrupt} onChanged={loadAgents} />
  );

  return (
    <AppShell wide>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link href="/" className="text-sm text-mist hover:text-ice">Projects /</Link>
        <h1 className="text-xl font-light tracking-wide">{project.name}</h1>
        <span className={`chip ${conn === "live" ? "border-cyan/40 text-cyan" : "border-warn/40 text-warn"}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${conn === "live" ? "bg-cyan" : "bg-warn animate-pulseline"}`} />
          {conn === "live" ? "Live" : conn === "connecting" ? "Connecting" : "Reconnecting"}
        </span>
        {runs.length > 1 && (
          <select className="input w-full py-1 text-xs sm:ml-auto sm:w-auto sm:max-w-xs" value={runId || ""} onChange={(e) => selectRun(e.target.value)} aria-label="Run">
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {new Date(r.created_at).toLocaleString()} · {r.status} · {r.objective.slice(0, 40)}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="mb-4 flex gap-1 overflow-x-auto border-b border-line" role="tablist">
        {TABS.map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => { setTab(t); setMobilePane("main"); }}
            className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm transition ${tab === t ? "border-cyan text-ice" : "border-transparent text-mist hover:text-ice"}`}
          >
            {t}
          </button>
        ))}
        <span className="flex-1" />
        <button onClick={() => setMobilePane("agents")} className={`whitespace-nowrap px-3 py-2 text-sm lg:hidden ${mobilePane === "agents" ? "text-cyan" : "text-mist"}`}>Agents</button>
        <button onClick={() => setMobilePane("timeline")} className={`whitespace-nowrap px-3 py-2 text-sm xl:hidden ${mobilePane === "timeline" ? "text-cyan" : "text-mist"}`}>Timeline</button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[300px_1fr] xl:grid-cols-[300px_1fr_320px]">
        <aside className={`${mobilePane === "agents" ? "block" : "hidden"} lg:block`}>{agentPanel}</aside>
        <div className={`${mobilePane === "main" ? "block" : "hidden"} min-w-0 lg:block`}>
          {tab === "Command room" && (
            <CommandRoom
              agents={agents}
              run={run}
              events={events}
              partials={isActive ? runPartials : {}}
              tasks={tasks}
              defaultMode={project.settings.mode}
              onStart={startRun}
              onSend={sendMessage}
              onControl={control}
              onDecide={decide}
            />
          )}
          {tab === "Hierarchy" && <HierarchyView agents={agents} statuses={statuses} />}
          {tab === "Tasks" && <TaskBoard tasks={tasks} agents={agents} />}
          {tab === "Workspace" && <Workspace project={project} onProjectChange={setProject} />}
          {tab === "Controls" && <Controls project={project} runs={runs} onProjectChange={setProject} />}
        </div>
        <aside className={`${mobilePane === "timeline" ? "block" : "hidden"} xl:block`}>
          <Timeline events={events} agents={agents} />
        </aside>
      </div>

      {toast && (
        <div role="status" className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-lg border border-warn/40 bg-panel px-4 py-2 text-sm text-warn shadow-glow">
          {toast}
        </div>
      )}
    </AppShell>
  );
}
