"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Plan } from "@/lib/types";

type Summary = {
  plan: Plan | null;
  subscription_status: string;
  credits_usd: number;
  entitlements: Record<string, number | boolean | null>;
  month_start: string;
  usage_by_model: {
    provider: string;
    model: string;
    billed_to: string;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    calls: number;
    price_is_fallback_estimate: boolean;
  }[];
  total_cost_usd: number;
  stripe_enabled: boolean;
  pricing_note: string;
};

const FEATURES: [string, string][] = [
  ["max_models", "AI models"],
  ["max_agents", "Configured agents"],
  ["max_concurrent_agents", "Concurrently executing agents"],
  ["max_projects", "Projects"],
  ["max_parallel_runs", "Parallel runs"],
  ["max_subagents_per_agent", "Subagents per agent"],
  ["monthly_credit_usd", "Platform credits / month"],
  ["max_turns_per_agent", "Turns per agent per run"],
];

function fmt(k: string, v: number | boolean | null | undefined) {
  if (v === null) return k === "max_agents" || k === "max_projects" ? "Unlimited*" : "All supported";
  if (typeof v === "boolean") return v ? "✓" : "—";
  if (k === "monthly_credit_usd") return `$${v}`;
  return String(v ?? "—");
}

export default function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [s, setS] = useState<Summary | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api<Plan[]>("/api/billing/plans").then(setPlans);
    api<Summary>("/api/billing/summary").then(setS);
    const q = new URLSearchParams(window.location.search).get("checkout");
    if (q === "success") setMsg("Thanks! Your subscription will update as soon as Stripe confirms the payment.");
  }, []);

  async function go(path: string, json?: unknown) {
    setMsg("");
    try {
      const r = await api<{ url: string }>(path, { method: "POST", json });
      window.location.href = r.url;
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-light tracking-wide">Billing &amp; usage</h1>
      {msg && <p className="mt-3 text-sm text-warn" role="status">{msg}</p>}

      {s && (
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <Stat label="Current plan" value={s.plan?.name || "—"} sub={`Status: ${s.subscription_status}`} />
          <Stat label="Platform credits" value={`$${s.credits_usd.toFixed(2)}`} sub="Used only when an agent has no BYOK key" />
          <Stat label="Estimated spend this month" value={`$${s.total_cost_usd.toFixed(4)}`} sub="BYOK + platform + simulated" />
        </div>
      )}
      {s?.stripe_enabled && s.plan && s.plan.code !== "free" && (
        <button className="btn mt-4" onClick={() => go("/api/billing/portal")}>Manage subscription (upgrade, downgrade, cancel)</button>
      )}

      <h2 className="panel-title mt-10">Plans</h2>
      <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((p) => {
          const current = s?.plan?.code === p.code;
          return (
            <div key={p.code} className={`panel flex flex-col p-5 ${current ? "shadow-glow" : ""}`}>
              <div className="flex items-baseline justify-between">
                <h3 className="text-lg font-light tracking-wider">{p.name.toUpperCase()}</h3>
                {current && <span className="chip border-cyan/40 text-cyan">Current</span>}
              </div>
              <p className="mt-2 text-3xl font-extralight">
                ${p.price_usd_month}
                <span className="text-sm text-mist">/mo</span>
              </p>
              <ul className="mt-4 flex-1 space-y-1.5 text-sm">
                {FEATURES.map(([k, label]) => (
                  <li key={k} className="flex justify-between gap-2">
                    <span className="text-mist">{label}</span>
                    <span>{fmt(k, p.entitlements[k])}</span>
                  </li>
                ))}
                <li className="flex justify-between gap-2"><span className="text-mist">Agent hierarchies</span><span>{fmt("", p.entitlements.hierarchies)}</span></li>
                <li className="flex justify-between gap-2"><span className="text-mist">External agents</span><span>{fmt("", p.entitlements.external_agents)}</span></li>
                <li className="flex justify-between gap-2"><span className="text-mist">Audit logs</span><span>{fmt("", p.entitlements.audit_log_access)}</span></li>
              </ul>
              {!current && p.price_usd_month > 0 && (
                <button className="btn-primary mt-5" onClick={() => go("/api/billing/checkout", { plan_code: p.code })}>
                  Choose {p.name}
                </button>
              )}
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-mist">
        * &quot;Unlimited&quot; applies to configured agents/projects only. Every run is bounded by concurrency, turn, message, time and budget
        limits. Prices are proposed USD list prices and may be changed by administrators.
      </p>

      <h2 className="panel-title mt-10">Usage by model this month</h2>
      <div className="panel mt-3 overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="text-left text-xs text-mist">
            <tr className="border-b border-line">
              <th className="p-3 font-normal">Provider / model</th>
              <th className="p-3 font-normal">Billed to</th>
              <th className="p-3 text-right font-normal">Calls</th>
              <th className="p-3 text-right font-normal">Input tok</th>
              <th className="p-3 text-right font-normal">Output tok</th>
              <th className="p-3 text-right font-normal">Est. cost</th>
            </tr>
          </thead>
          <tbody>
            {s?.usage_by_model.length ? (
              s.usage_by_model.map((u) => (
                <tr key={`${u.provider}${u.model}${u.billed_to}`} className="border-b border-line/50">
                  <td className="p-3">{u.provider}/<span className="font-mono">{u.model}</span></td>
                  <td className="p-3 text-mist">{u.billed_to}</td>
                  <td className="p-3 text-right">{u.calls}</td>
                  <td className="p-3 text-right">{u.input_tokens.toLocaleString()}</td>
                  <td className="p-3 text-right">{u.output_tokens.toLocaleString()}</td>
                  <td className="p-3 text-right">
                    ${u.cost_usd.toFixed(4)}
                    {u.price_is_fallback_estimate && <span title="No list price configured for this model; fallback estimate used" className="ml-1 text-warn">*</span>}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td className="p-3 text-mist" colSpan={6}>No usage yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {s && <p className="mt-2 text-xs text-mist">{s.pricing_note}</p>}
    </AppShell>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="panel p-5">
      <p className="panel-title">{label}</p>
      <p className="mt-2 text-2xl font-extralight">{value}</p>
      <p className="mt-1 text-xs text-mist">{sub}</p>
    </div>
  );
}
