import type { Agent, PlatoEvent } from "@/lib/types";

const HUES = ["#5ee7ff", "#3d8bff", "#a5b4fc", "#7dd3fc", "#c4b5fd", "#93c5fd", "#67e8f9", "#818cf8"];

export function agentColor(agents: Agent[], id: string | null | undefined): string {
  const i = agents.findIndex((a) => a.id === id);
  return i < 0 ? "#8a98ad" : HUES[i % HUES.length];
}

export function agentName(agents: Agent[], id: string | null | undefined): string {
  return agents.find((a) => a.id === id)?.name || "Agent";
}

/** Merge persisted events by seq (idempotent; tolerant of REST/WS overlap). */
export function mergeEvents(prev: PlatoEvent[], incoming: PlatoEvent[]): PlatoEvent[] {
  const bySeq = new Map<number, PlatoEvent>();
  for (const e of prev) if (e.seq != null) bySeq.set(e.seq, e);
  for (const e of incoming) if (e.seq != null) bySeq.set(e.seq, e);
  return [...bySeq.values()].sort((a, b) => a.seq! - b.seq!);
}

/** Make an in-flight reply readable: render finished directives as markers, hide half-written tags. */
export function cleanLive(text: string): string {
  return text
    .replace(/<message\s+to="([^"]*)"\s*>[\s\S]*?<\/message>/gi, "\n↗ message → $1\n")
    .replace(/<task\s+to="([^"]*)"[^>]*>[\s\S]*?<\/task>/gi, "\n↗ task → $1\n")
    .replace(/<done>[\s\S]*?<\/done>/gi, "\n✓ done\n")
    .replace(/<(message|task)\b[\s\S]*$/i, "\n↗ composing $1…")
    .replace(/<done>[\s\S]*$/i, "\n✓ finishing…");
}

export const STATUS_STYLE: Record<string, { dot: string; label: string }> = {
  idle: { dot: "bg-mist/50", label: "Idle" },
  thinking: { dot: "bg-volt animate-pulseline", label: "Thinking" },
  streaming: { dot: "bg-cyan animate-pulseline", label: "Streaming" },
  done: { dot: "bg-ok", label: "Done" },
  error: { dot: "bg-bad", label: "Error" },
  limit_reached: { dot: "bg-warn", label: "Limit reached" },
  stopped: { dot: "bg-mist/30", label: "Stopped" },
};

export function time(ts?: string) {
  if (!ts) return "";
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}
