"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { MODE_LABEL } from "@/lib/types";

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Project[]>("/api/projects").then(setProjects).catch((e) => setError(e.message));
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setError("");
    try {
      const p = await api<Project>("/api/projects", { method: "POST", json: { name: name.trim() } });
      setProjects((ps) => [p, ...(ps || [])]);
      setName("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <AppShell>
      <div className="mb-8 flex flex-col gap-2">
        <h1 className="text-2xl font-light tracking-wide">Projects</h1>
        <p className="text-sm text-mist">Each project is a shared workspace where your agent team works on objectives you set.</p>
      </div>

      <form onSubmit={create} className="panel mb-8 flex flex-col gap-3 p-4 sm:flex-row">
        <input className="input" placeholder="New project name" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
        <button className="btn-primary shrink-0">Create project</button>
      </form>
      {error && <p className="mb-4 text-sm text-bad" role="alert">{error}</p>}

      {projects === null ? (
        <p className="text-sm text-mist">Loading…</p>
      ) : projects.length === 0 ? (
        <div className="panel p-8 text-center">
          <p className="text-ice">No projects yet.</p>
          <p className="mt-2 text-sm text-mist">
            Create a project, then <Link className="text-cyan underline-offset-4 hover:underline" href="/providers">connect providers</Link> and add agents.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="panel group p-5 transition hover:shadow-glow">
              <div className="flex items-start justify-between gap-2">
                <h2 className="truncate text-lg font-light">{p.name}</h2>
                <span className="text-mist transition group-hover:text-cyan">→</span>
              </div>
              <p className="mt-1 line-clamp-2 min-h-[2.5rem] text-sm text-mist">{p.description || "No description"}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="chip">{MODE_LABEL[p.settings.mode] || p.settings.mode}</span>
                <span className="chip">budget ${p.settings.budget_usd}/run</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </AppShell>
  );
}
