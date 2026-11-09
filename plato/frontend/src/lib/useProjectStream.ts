"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, WS_URL } from "./api";
import type { PlatoEvent } from "./types";

export type Partial = { agent_id: string; turn_id: string; text: string };
export type ConnState = "connecting" | "live" | "reconnecting";

type Snapshot = {
  active_runs: { run_id: string; status: string; agents: { id: string; status: string; turn_id: string | null; partial: string }[] }[];
};

/**
 * Live project stream. Persisted events (seq != null) are de-duplicated per run and gap-filled from
 * REST after reconnects, so the feed is always the authoritative, ordered history. Token deltas are
 * merged into in-flight "partials" keyed by turn id.
 */
export function useProjectStream(projectId: string, onEvent: (e: PlatoEvent) => void) {
  const [conn, setConn] = useState<ConnState>("connecting");
  const [partials, setPartials] = useState<Record<string, Partial>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let closed = false;
    let retry = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const connect = async () => {
      try {
        const { ticket } = await api<{ ticket: string }>("/api/auth/ws-ticket", { method: "POST" });
        if (closed) return;
        const ws = new WebSocket(`${WS_URL}/ws/projects/${projectId}?ticket=${encodeURIComponent(ticket)}`);
        wsRef.current = ws;
        ws.onopen = () => {
          retry = 0;
          setConn("live");
        };
        ws.onmessage = (m) => {
          const e = JSON.parse(m.data) as PlatoEvent;
          if (e.type === "snapshot") {
            const snap = e.data as Snapshot;
            const next: Record<string, Partial> = {};
            for (const r of snap.active_runs)
              for (const a of r.agents) if (a.turn_id) next[a.turn_id] = { agent_id: a.id, turn_id: a.turn_id, text: a.partial };
            setPartials(next);
            onEventRef.current(e);
            return;
          }
          if (e.type === "agent.delta") {
            const { turn_id, text } = e.data as { turn_id: string; text: string };
            setPartials((p) => ({ ...p, [turn_id]: { agent_id: e.agent_id!, turn_id, text: (p[turn_id]?.text || "") + text } }));
            return;
          }
          if (e.type === "agent.turn.completed" || e.type === "agent.turn.interrupted") {
            setPartials((p) => {
              const n = { ...p };
              delete n[e.data.turn_id];
              return n;
            });
          }
          if (e.type === "agent.turn.started") {
            setPartials((p) => ({ ...p, [e.data.turn_id]: { agent_id: e.agent_id!, turn_id: e.data.turn_id, text: "" } }));
          }
          if (e.type === "run.status" && !["running", "paused"].includes(e.data.status)) setPartials({});
          if (e.type === "ack") return;
          if (e.type === "error" && !e.project_id) {
            // Response to a Commander action sent over the socket (e.g. "Agent is not generating").
            onEventRef.current({ ...e, type: "action.error", project_id: projectId, run_id: null, agent_id: null, seq: null });
            return;
          }
          onEventRef.current(e);
        };
        ws.onclose = () => {
          wsRef.current = null;
          if (closed) return;
          setConn("reconnecting");
          retry = Math.min(retry + 1, 6);
          timer = setTimeout(connect, 500 * 2 ** retry);
        };
      } catch {
        if (closed) return;
        setConn("reconnecting");
        retry = Math.min(retry + 1, 6);
        timer = setTimeout(connect, 500 * 2 ** retry);
      }
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [projectId]);

  const send = useCallback((msg: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify(msg));
    return true;
  }, []);

  return { conn, partials, send };
}
