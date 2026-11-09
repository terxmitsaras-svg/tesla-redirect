export type User = {
  id: string;
  email: string;
  name: string;
  is_admin: boolean;
  plan_code: string;
  subscription_status: string;
  credits_usd: number;
};

export type ProjectSettings = {
  mode: Mode;
  approve_delegations: boolean;
  max_turns_per_agent: number;
  max_agent_messages: number;
  max_run_seconds: number;
  max_output_tokens: number;
  budget_usd: number;
};

export type Mode = "open_discussion" | "structured_delegation" | "parallel" | "debate" | "independent_review";

export type Project = {
  id: string;
  name: string;
  description: string;
  shared_context: string;
  settings: ProjectSettings;
  created_at: string;
};

export type Agent = {
  id: string;
  project_id: string;
  parent_id: string | null;
  name: string;
  role: string;
  instructions: string;
  kind: "hosted" | "external";
  provider: string;
  model: string;
  credential_id: string | null;
  external_url: string | null;
  is_active: boolean;
  created_at: string;
};

export type ProviderCategory = "frontier" | "open" | "local" | "custom";

export type Provider = {
  id: string;
  display_name: string;
  integration: "hosted" | "external" | "simulated";
  category: ProviderCategory;
  requires_api_key: boolean;
  suggested_models: string[];
  docs_url: string;
  base_url_mode: "fixed" | "optional" | "required";
  default_base_url: string | null;
  self_hosted: boolean;
  connected: boolean;
  platform_managed_available: boolean;
};

export const CATEGORY_LABEL: Record<ProviderCategory, { title: string; blurb: string }> = {
  frontier: { title: "Frontier model labs", blurb: "Hosted APIs from the major model labs." },
  open: { title: "Open models, clouds & routers", blurb: "Open-weight and multi-model APIs: Hugging Face, Mistral, Groq, DeepSeek, Together, OpenRouter." },
  local: { title: "Local & self-hosted", blurb: "Models on your own machine or server. No per-token charges." },
  custom: { title: "Custom & connected runtimes", blurb: "Any OpenAI-compatible server, external agent runtimes, and the offline simulator." },
};

export type Credential = {
  id: string;
  provider: string;
  label: string;
  key_hint: string;
  base_url: string | null;
  verified_at: string | null;
  created_at: string;
};

export type RunStatus = "pending" | "running" | "paused" | "completed" | "stopped" | "limit_reached" | "interrupted" | "failed";

export type Run = {
  id: string;
  project_id: string;
  objective: string;
  mode: Mode;
  status: RunStatus;
  stop_reason: string | null;
  limits: Record<string, number>;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
  ended_at: string | null;
};

export type PlatoEvent = {
  type: string;
  project_id: string;
  run_id: string | null;
  agent_id: string | null;
  seq: number | null;
  ts?: string;
  created_at?: string;
  data: Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
};

export type Task = {
  id: string;
  run_id: string;
  title: string;
  description: string;
  assignee_agent_id: string;
  created_by_agent_id: string | null;
  status: string;
  result: string;
  created_at: string;
  updated_at: string;
};

export type ProjectFile = {
  id: string;
  path: string;
  content: string;
  shared_with_agents: boolean;
  updated_at: string;
};

export type Plan = {
  code: string;
  name: string;
  price_usd_month: number;
  entitlements: Record<string, number | boolean | null>;
  stripe_price_id: string | null;
};

export const ACTIVE: RunStatus[] = ["pending", "running", "paused"];

export const MODE_LABEL: Record<Mode, string> = {
  open_discussion: "Open discussion",
  structured_delegation: "Structured delegation",
  parallel: "Parallel collaboration",
  debate: "Debate",
  independent_review: "Independent review",
};
