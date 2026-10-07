"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, Bell, Bot, CalendarClock, Check, ChevronRight, CircleHelp,
  Cloud, Database, ExternalLink, FileText, Gauge, Layers3, LineChart,
  ListFilter, Loader2, Menu, MessageSquare, Network, Play, Plus, Search,
  Send, Settings, ShieldCheck, SlidersHorizontal, Sparkles, Users, X, Zap,
} from "lucide-react";
import {
  rivalScopeApi,
  type ApiCompany,
  type ApiMcpServer,
  type ApiReport,
  type ApiRun,
  type ApiSignal,
} from "../lib/api";

type Signal = {
  title: string;
  company: string;
  category: string;
  score: number;
  time: string;
  summary: string;
  sources: string[];
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  competitor?: string;
};

const navigation = [
  ["dashboard", "Dashboard", Gauge],
  ["competitors", "Competitors", Users],
  ["signals", "Signals", Activity],
  ["compare", "Compare", LineChart],
  ["reports", "Reports", FileText],
  ["runs", "Agent runs", Bot],
  ["schedules", "Schedules", CalendarClock],
  ["integrations", "Integrations", Cloud],
  ["mcp", "MCP gateway", Network],
  ["memory", "Memory explorer", Database],
  ["settings", "Settings", Settings],
] as const;

const initialSignals: Signal[] = [
  {
    title: "Stripe launches usage-based pricing for embedded finance",
    company: "Stripe",
    category: "Pricing",
    score: 94,
    time: "18m ago",
    summary: "New pricing model lowers entry cost for marketplace platforms and adds volume commitments for enterprise customers.",
    sources: ["stripe.com/newsroom", "Finextra", "TechCrunch"],
  },
  {
    title: "Adyen expands issuer processing across India",
    company: "Adyen",
    category: "Product",
    score: 88,
    time: "2h ago",
    summary: "The rollout adds local payment rails and a new risk console for regional card issuers.",
    sources: ["adyen.com", "Economic Times"],
  },
  {
    title: "Block reports 21% growth in gross profit",
    company: "Block",
    category: "Financial",
    score: 81,
    time: "5h ago",
    summary: "Results point to renewed Cash App engagement and higher seller ecosystem monetisation.",
    sources: ["sec.gov", "Block investor relations"],
  },
  {
    title: "Plaid opens 34 platform engineering roles",
    company: "Plaid",
    category: "Talent",
    score: 72,
    time: "Yesterday",
    summary: "Hiring is concentrated in data infrastructure and enterprise identity products.",
    sources: ["plaid.com/careers"],
  },
];

const pageTitles: Record<string, [string, string]> = {
  dashboard: ["Good morning, Priya", "Here is the competitive picture across your watchlist."],
  competitors: ["Competitors", "Track the companies that shape your market."],
  signals: ["Signals", "Evidence-backed moves ranked by strategic importance."],
  compare: ["Compare rivals", "Line up product, commercial, and momentum signals."],
  reports: ["Reports", "Cited intelligence briefs ready to share."],
  runs: ["Agent runs", "Monitor collection, verification, and delivery in real time."],
  schedules: ["Schedules", "Control when intelligence reaches your team."],
  integrations: ["Integrations", "Connect delivery channels and provider credentials."],
  mcp: ["MCP gateway", "Safely give agents access to tenant-approved tools."],
  memory: ["Memory explorer", "Inspect durable preferences, retrieved knowledge, and events."],
  settings: ["Settings", "Manage workspace security, data retention, and models."],
  onboarding: ["Welcome to RivalScope", "Set up your first competitive intelligence workflow."],
};

function Score({ score }: { score: number }) {
  const color =
    score >= 90
      ? "bg-rose-100 text-rose-700"
      : score >= 80
      ? "bg-amber-100 text-amber-700"
      : "bg-sky-100 text-sky-700";
  return <span className={`chip ${color}`}>{score} impact</span>;
}

function SignalFeed({
  items = initialSignals,
  compact = false,
  onSelect,
}: {
  items?: Signal[];
  compact?: boolean;
  onSelect: (signal: Signal) => void;
}) {
  return (
    <div className="divide-y divide-slate-100">
      {items.slice(0, compact ? 3 : 8).map((signal) => (
        <button
          key={signal.title}
          onClick={() => onSelect(signal)}
          className="w-full px-5 py-4 text-left transition hover:bg-slate-50"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="mb-1 flex items-center gap-2">
                <span className="text-xs font-bold text-mint">{signal.company}</span>
                <span className="text-xs text-slate-400">{signal.time}</span>
              </div>
              <h3 className="font-semibold text-slate-800">{signal.title}</h3>
              {!compact && (
                <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-500">
                  {signal.summary}
                </p>
              )}
            </div>
            <Score score={signal.score} />
          </div>
        </button>
      ))}
    </div>
  );
}

function Dashboard({
  items,
  onSelect,
  onTriggerRun,
  running,
}: {
  items: Signal[];
  onSelect: (signal: Signal) => void;
  onTriggerRun: () => void;
  running: boolean;
}) {
  const metrics: { value: string; label: string; detail: string; Icon: typeof Activity }[] = [
    { value: `${items.length}`, label: "Live signals", detail: "Active watchlist", Icon: Activity },
    { value: `${items.filter((s) => s.score >= 85).length}`, label: "High-impact moves", detail: "Prioritized", Icon: Zap },
    { value: "98.2%", label: "Citation coverage", detail: "Postgres + pgvector", Icon: ShieldCheck },
    { value: "$0.00", label: "Zero-token cost", detail: "Deterministic MockModel", Icon: Gauge },
  ];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ value, label, detail, Icon }) => (
          <div className="panel p-5" key={label}>
            <div className="mb-4 flex items-center justify-between">
              <span className="eyebrow">{label}</span>
              <Icon className="h-4 w-4 text-slate-400" />
            </div>
            <div className="metric">{value}</div>
            <p className="mt-1 text-sm text-emerald-600">{detail}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.55fr_.9fr]">
        <div className="panel overflow-hidden">
          <div className="flex items-center justify-between px-5 py-5">
            <div>
              <p className="eyebrow">Priority feed</p>
              <h2 className="mt-1 text-lg font-bold">Signals worth your attention</h2>
            </div>
            <Link href="/signals" className="text-sm font-semibold text-indigo-600">
              View all
            </Link>
          </div>
          <SignalFeed items={items} onSelect={onSelect} />
        </div>

        <div className="panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="eyebrow">Autonomous Agent Run</p>
              <h2 className="mt-1 text-lg font-bold">Monitor Pipeline</h2>
            </div>
            <button
              onClick={onTriggerRun}
              disabled={running}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow transition hover:bg-indigo-700 disabled:opacity-60"
            >
              {running ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> In Progress
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" /> Trigger Run
                </>
              )}
            </button>
          </div>

          <div className="mt-7 flex h-36 items-end gap-3">
            {[46, 70, 34, 91, 61, 75, 58].map((height, i) => (
              <div className="flex flex-1 flex-col items-center gap-2" key={height}>
                <div
                  className="w-full rounded-t-md bg-gradient-to-t from-indigo-500 to-cyan-400 transition-all duration-500"
                  style={{ height: `${height}%` }}
                />
                <span className="text-[10px] text-slate-400">
                  {["M", "T", "W", "T", "F", "S", "S"][i]}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-7 rounded-xl bg-slate-50 p-4">
            <p className="text-sm font-semibold">Latest Market Trend</p>
            <p className="mt-1 text-sm leading-5 text-slate-500">
              Multi-agent pipeline running across Stripe, Adyen, and Revolut with 6-stage deduplication.
            </p>
            <Link
              href="/reports"
              className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-indigo-600"
            >
              Read executive brief <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function Competitors({
  companies,
  onAddCompany,
}: {
  companies: ApiCompany[];
  onAddCompany: (name: string, domain: string, tag: string) => void;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [tag, setTag] = useState("payments");

  const fallback = [
    ["Stripe", "Payments infrastructure", "12", "18m ago", "High"],
    ["Adyen", "Enterprise payments", "9", "2h ago", "High"],
    ["Revolut", "Retail & business neobanking", "8", "4h ago", "High"],
    ["Block", "Consumer & seller", "7", "5h ago", "Watch"],
    ["Plaid", "Open banking", "4", "Yesterday", "Watch"],
  ];

  const rows = companies.length
    ? companies
        .filter((company) => !company.is_self)
        .map((company) => [
          company.name,
          company.tags[0] || company.domain,
          "Live",
          "Connected",
          "Tracked",
        ])
    : fallback;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !domain.trim()) return;
    onAddCompany(name.trim(), domain.trim(), tag.trim());
    setName("");
    setDomain("");
    setShowAdd(false);
  };

  return (
    <div className="panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 p-5">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
          <input
            className="rounded-xl border border-slate-200 py-2.5 pl-9 pr-4 text-sm outline-none focus:border-indigo-500"
            placeholder="Search competitors"
          />
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700"
        >
          <Plus className="mr-1 inline h-4 w-4" /> Add competitor
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleSubmit} className="border-y bg-slate-50 p-5">
          <h4 className="text-sm font-bold text-slate-800">Add Monitored Competitor</h4>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Company name (e.g. Klarna)"
              className="rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <input
              required
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="Domain (e.g. klarna.com)"
              className="rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <input
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              placeholder="Tag (e.g. bnpl, banking)"
              className="rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="submit"
              className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white"
            >
              Save Competitor
            </button>
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="rounded-lg border px-3 py-1.5 text-xs text-slate-600"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <table className="w-full text-left text-sm">
        <thead className="border-y bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th className="px-5 py-3">Company</th>
            <th>Focus</th>
            <th>Activity</th>
            <th>Last signal</th>
            <th className="px-5">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr className="table-row" key={row[0]}>
              <td className="px-5 py-4 font-semibold">{row[0]}</td>
              <td className="text-slate-500">{row[1]}</td>
              <td>{row[2]} signals</td>
              <td className="text-slate-500">{row[3]}</td>
              <td className="px-5">
                <span className="chip bg-indigo-50 text-indigo-700">{row[4]}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Reports({
  reports,
  onGenerateReport,
  generating,
}: {
  reports: ApiReport[];
  onGenerateReport: (prompt: string) => void;
  generating: boolean;
}) {
  const [prompt, setPrompt] = useState("");

  const handleGenerate = () => {
    if (!prompt.trim() || generating) return;
    onGenerateReport(prompt);
    setPrompt("");
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
      <div className="panel divide-y">
        <div className="p-5">
          <p className="eyebrow">Latest Synthesized Brief</p>
          <h2 className="mt-1 text-xl font-bold">Weekly fintech competitor brief</h2>
          <p className="mt-2 text-sm text-slate-500">
            Automated multi-agent synthesis across Stripe, Adyen, and Revolut
          </p>
        </div>

        {reports.length > 0 ? (
          reports.map((rep) => (
            <div className="flex items-center justify-between p-5" key={rep.id}>
              <div>
                <p className="font-semibold">{rep.title}</p>
                <p className="mt-1 text-sm text-slate-500">
                  {rep.summary ? rep.summary.slice(0, 100) + "..." : "Cited intelligence brief"} ·{" "}
                  {rep.status}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-400" />
            </div>
          ))
        ) : (
          [
            "Daily priority alert — October 6",
            "Product and pricing changes — September",
            "Q3 financial signals review",
          ].map((title, i) => (
            <div className="flex items-center justify-between p-5" key={title}>
              <div>
                <p className="font-semibold">{title}</p>
                <p className="mt-1 text-sm text-slate-500">
                  {12 - i * 2} cited signals · Delivered
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-400" />
            </div>
          ))
        )}
      </div>

      <div className="panel p-6">
        <div className="flex items-center gap-2 text-indigo-600">
          <Sparkles className="h-5 w-5" />
          <span className="text-sm font-bold">Generate a focused report</span>
        </div>
        <h3 className="mt-5 text-xl font-bold">Ask the research team</h3>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Generate an executive cited brief for a competitor, theme, or time window.
        </p>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          className="mt-5 h-28 w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:border-indigo-500"
          placeholder="Example: Compare Stripe and Adyen's enterprise expansion this quarter"
        />
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
        >
          {generating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Synthesizing brief...
            </>
          ) : (
            "Generate report"
          )}
        </button>
      </div>
    </div>
  );
}

function Runs({
  runs,
  onTriggerRun,
  running,
}: {
  runs: ApiRun[];
  onTriggerRun: () => void;
  running: boolean;
}) {
  const latestRun = runs[0];

  return (
    <div className="grid gap-5 xl:grid-cols-[1.45fr_.75fr]">
      <div className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b p-5">
          <div>
            <p className="eyebrow">Pipeline Execution</p>
            <h2 className="mt-1 font-bold">
              {latestRun ? `Run · ${latestRun.id.slice(0, 8)}` : "Daily monitor · run_0d8f"}
            </h2>
          </div>
          <span
            className={`chip ${
              running || latestRun?.status === "running"
                ? "bg-amber-100 text-amber-700"
                : "bg-emerald-100 text-emerald-700"
            }`}
          >
            {running || latestRun?.status === "running" ? "In progress" : "Completed"}
          </span>
        </div>
        <div className="space-y-5 p-5">
          {[
            ["Collectors", "5 sources queried, 16 documents found", true],
            ["Deduplication", "12 unique documents after six stages", true],
            ["Verifier", "Checking evidence and confidence", true],
            ["Analyst", "Strategic impact & threat scoring", !running],
            ["Reporter", "Executive brief markdown synthesis", !running],
          ].map(([name, text, active], i) => (
            <div className="flex gap-4" key={String(name)}>
              <div
                className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                  active ? "bg-emerald-500 text-white" : "bg-slate-100 text-slate-400"
                }`}
              >
                {active ? <Check className="h-4 w-4" /> : i + 1}
              </div>
              <div>
                <p className="font-semibold">{name}</p>
                <p className="mt-0.5 text-sm text-slate-500">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel p-5">
        <p className="eyebrow">Run controls</p>
        <button
          onClick={onTriggerRun}
          disabled={running}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
        >
          {running ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Running pipeline...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 fill-current" /> Trigger pipeline now
            </>
          )}
        </button>
        <div className="mt-6 space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Duration</span>
            <b>{latestRun ? `${latestRun.duration_seconds}s` : "01:42"}</b>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Tokens</span>
            <b>{latestRun ? latestRun.tokens.toLocaleString() : "18,492"}</b>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Estimated cost</span>
            <b>$0.00 (MockModel)</b>
          </div>
        </div>
      </div>
    </div>
  );
}

function Mcp({
  servers,
  onTogglePolicy,
}: {
  servers: ApiMcpServer[];
  onTogglePolicy: (serverId: string, toolName: string, enabled: boolean, approval: boolean) => void;
}) {
  const [localEnabled, setLocalEnabled] = useState<Record<string, boolean>>({
    "search_knowledge_base": true,
    "get_competitor_timeline": true,
    "get_company_signals": true,
  });

  const server = servers[0];

  const handleToggle = (tool: string) => {
    const nextVal = !localEnabled[tool];
    setLocalEnabled((cur) => ({ ...cur, [tool]: nextVal }));
    if (server) {
      onTogglePolicy(server.id, tool, nextVal, false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="panel flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="eyebrow">Connector registry</p>
          <h2 className="mt-1 text-lg font-bold">Tenant MCP servers</h2>
          <p className="mt-1 text-sm text-slate-500">
            SSRF Firewall & Dynamic Policy validation protecting agent tool use.
          </p>
        </div>
        <button className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">
          <Plus className="mr-1 inline h-4 w-4" /> Add server
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
        <div className="panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-bold">{server ? server.name : "PayPulse Intelligence Hub"}</p>
              <p className="mt-1 text-sm text-slate-500">
                {server ? server.transport : "streamable-http"} · healthy
              </p>
            </div>
            <span className="chip bg-emerald-100 text-emerald-700">Healthy</span>
          </div>
          <div className="mt-5 rounded-xl bg-slate-50 p-3 text-sm">
            <ShieldCheck className="mr-2 inline h-4 w-4 text-emerald-600" /> AES-256 envelope
            encryption active
          </div>
        </div>

        <div className="panel overflow-hidden">
          <div className="border-b p-5">
            <p className="font-bold">Tool policy</p>
            <p className="mt-1 text-sm text-slate-500">
              Mutating tools require HITL approval; query tools run autonomously.
            </p>
          </div>
          {Object.entries(localEnabled).map(([tool, value]) => (
            <div
              className="flex items-center justify-between border-b p-5 last:border-0"
              key={tool}
            >
              <div>
                <p className="font-semibold">{tool}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {tool.includes("mutate") ? "Write · approval required" : "Read-only · analyst team"}
                </p>
              </div>
              <button
                onClick={() => handleToggle(tool)}
                className={`h-7 w-12 rounded-full p-1 transition ${
                  value ? "bg-indigo-600" : "bg-slate-200"
                }`}
              >
                <span
                  className={`block h-5 w-5 rounded-full bg-white transition ${
                    value ? "translate-x-5" : ""
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Generic({ section }: { section: string }) {
  const content: Record<string, [string, string, string[]]> = {
    schedules: [
      "Your reporting cadence",
      "Daily monitor is active at 09:00 Asia/Kolkata. High-impact alerts bypass digest quiet hours.",
      ["Daily competitive digest", "High impact alert monitor", "Weekly executive brief"],
    ],
    integrations: [
      "Delivery channels",
      "Connect a channel and test the exact message format your team will receive.",
      ["Slack · #competitive-intel", "Telegram · Product strategy", "Generic webhook · Connected"],
    ],
    memory: [
      "A durable intelligence layer",
      "Search hybrid keyword + vector knowledge, edit organization preferences, and review the event timeline.",
      ["Organization memory", "Knowledge search", "Stripe event timeline"],
    ],
    settings: [
      "Workspace controls",
      "Manage roles, provider availability, budgets, data retention, and security policies.",
      ["Roles & access", "Models & provider keys", "Cost controls"],
    ],
    compare: [
      "Stripe vs. Adyen vs. Revolut",
      "A focused comparison assembled from verified evidence across all monitored competitors.",
      ["Product velocity: Stripe +12%", "Pricing pressure: High", "Financial momentum: Adyen +8%"],
    ],
    onboarding: [
      "Build your first watchlist",
      "In a few steps, RivalScope will begin producing cited competitive reports.",
      ["Company profile", "Add competitors", "Delivery and schedule"],
    ],
  };

  const [heading, intro, rows] = content[section] ?? content.settings;

  return (
    <div className="grid gap-5 lg:grid-cols-[1.1fr_.9fr]">
      <div className="panel p-6">
        <p className="eyebrow">Configuration</p>
        <h2 className="mt-2 text-2xl font-bold">{heading}</h2>
        <p className="mt-3 max-w-xl leading-6 text-slate-500">{intro}</p>
        <div className="mt-7 space-y-3">
          {rows.map((row) => (
            <button
              className="flex w-full items-center justify-between rounded-xl border border-slate-200 p-4 text-left transition hover:border-indigo-300 hover:bg-indigo-50/30"
              key={row}
            >
              <span className="font-semibold">{row}</span>
              <ChevronRight className="h-5 w-5 text-slate-400" />
            </button>
          ))}
        </div>
      </div>
      <div className="panel p-6">
        <div className="flex h-full min-h-64 flex-col items-start justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-sky-500 p-6 text-white">
          <Layers3 className="h-8 w-8" />
          <h3 className="mt-5 text-xl font-bold">Built for an informed next move.</h3>
          <p className="mt-2 text-sm leading-6 text-indigo-100">
            Every screen keeps sources, confidence, tenant controls, and delivery decisions visible.
          </p>
          <button className="mt-6 rounded-lg bg-white px-4 py-2 text-sm font-bold text-indigo-700">
            Configure now
          </button>
        </div>
      </div>
    </div>
  );
}

export function RivalScopeApp({ section }: { section: string }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selected, setSelected] = useState<Signal | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatQuery, setChatQuery] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "initial",
      role: "assistant",
      text: "Hello! I am your competitive intelligence assistant. Ask me anything about your monitored rivals like Stripe, Adyen, or Revolut.",
    },
  ]);
  const [chatLoading, setChatLoading] = useState(false);

  const [liveSignals, setLiveSignals] = useState<Signal[]>(initialSignals);
  const [companies, setCompanies] = useState<ApiCompany[]>([]);
  const [reports, setReports] = useState<ApiReport[]>([]);
  const [runs, setRuns] = useState<ApiRun[]>([]);
  const [mcpServers, setMcpServers] = useState<ApiMcpServer[]>([]);
  const [apiStatus, setApiStatus] = useState<"demo" | "connected">("demo");
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [reportGenerating, setReportGenerating] = useState(false);

  const resolvedSection = pageTitles[section] ? section : "dashboard";
  const [title, subtitle] = pageTitles[resolvedSection];

  const refreshData = useCallback(() => {
    Promise.all([
      rivalScopeApi.companies(),
      rivalScopeApi.signals(),
      rivalScopeApi.reports().catch(() => [] as ApiReport[]),
      rivalScopeApi.runs().catch(() => [] as ApiRun[]),
      rivalScopeApi.mcpServers().catch(() => [] as ApiMcpServer[]),
    ])
      .then(([apiCompanies, apiSignals, apiReports, apiRuns, apiMcp]) => {
        const names = new Map(apiCompanies.map((c) => [c.id, c.name]));
        if (apiSignals.length) {
          setLiveSignals(
            apiSignals.map((signal) => ({
              title: signal.title,
              company: names.get(signal.company_id) ?? "Tracked rival",
              category: signal.category,
              score: signal.importance_score,
              time: new Date(signal.event_date).toLocaleDateString(),
              summary: signal.summary,
              sources: signal.evidence_ids.length
                ? signal.evidence_ids
                : ["Retrieved pgvector evidence"],
            }))
          );
        }
        setCompanies(apiCompanies);
        setReports(apiReports);
        setRuns(apiRuns);
        setMcpServers(apiMcp);
        setApiStatus("connected");
      })
      .catch(() => {
        setApiStatus("demo");
      });
  }, []);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  const handleTriggerRun = useCallback(async () => {
    setPipelineRunning(true);
    try {
      await rivalScopeApi.triggerRun();
      refreshData();
    } catch {
      // Fallback
    } finally {
      setPipelineRunning(false);
    }
  }, [refreshData]);

  const handleGenerateReport = useCallback(async (reportPrompt: string) => {
    setReportGenerating(true);
    try {
      const rep = await rivalScopeApi.generateReport(reportPrompt);
      setReports((cur) => [rep, ...cur]);
    } catch {
      // Fallback
    } finally {
      setReportGenerating(false);
    }
  }, []);

  const handleAddCompany = useCallback(async (name: string, domain: string, tag: string) => {
    try {
      const added = await rivalScopeApi.addCompany({
        name,
        domain,
        region: "Global",
        tags: [tag],
      });
      setCompanies((cur) => [...cur, added]);
    } catch {
      // Fallback
    }
  }, []);

  const handleTogglePolicy = useCallback(
    async (
      serverId: string,
      toolName: string,
      enabled: boolean,
      approval: boolean
    ) => {
      try {
        await rivalScopeApi.updateMcpPolicy(serverId, toolName, enabled, approval);
      } catch {
        // Fallback
      }
    },
    []
  );

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = chatQuery.trim();
    if (!query || chatLoading) return;

    const userMsg: ChatMessage = { id: String(Date.now()), role: "user", text: query };
    const assistantId = String(Date.now() + 1);
    setChatMessages((cur) => [...cur, userMsg]);
    setChatQuery("");
    setChatLoading(true);

    let streamActive = false;
    let accumulatedText = "";

    try {
      for await (const token of rivalScopeApi.chatStream(query)) {
        if (!streamActive) {
          streamActive = true;
          accumulatedText = token;
          setChatMessages((cur) => [
            ...cur,
            { id: assistantId, role: "assistant", text: token },
          ]);
        } else {
          accumulatedText += token;
          setChatMessages((cur) =>
            cur.map((msg) =>
              msg.id === assistantId ? { ...msg, text: msg.text + token } : msg
            )
          );
        }
      }

      if (!streamActive) {
        const res = await rivalScopeApi.chat(query);
        setChatMessages((cur) => [
          ...cur,
          {
            id: assistantId,
            role: "assistant",
            text: res.answer,
            competitor: res.competitor ?? undefined,
          },
        ]);
      }
    } catch {
      if (!streamActive) {
        const fallbackMsg: ChatMessage = {
          id: assistantId,
          role: "assistant",
          text: "Based on stored intelligence, Stripe recently rolled out usage-based pricing for embedded finance, while Adyen expanded issuer processing with localized rails. Verified citations are linked in the Evidence drawer.",
        };
        setChatMessages((cur) => [...cur, fallbackMsg]);
      }
    } finally {
      setChatLoading(false);
    }
  };

  const view = useMemo(() => {
    if (resolvedSection === "dashboard") {
      return (
        <Dashboard
          items={liveSignals}
          onSelect={setSelected}
          onTriggerRun={handleTriggerRun}
          running={pipelineRunning}
        />
      );
    }
    if (resolvedSection === "competitors") {
      return <Competitors companies={companies} onAddCompany={handleAddCompany} />;
    }
    if (resolvedSection === "signals") {
      return (
        <div className="panel overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b p-5">
            <div className="flex items-center gap-2">
              <ListFilter className="h-4 w-4 text-slate-400" />
              <span className="text-sm font-semibold">All competitors · Last 7 days</span>
            </div>
            <button className="rounded-lg border px-3 py-2 text-sm">Filters</button>
          </div>
          <SignalFeed items={liveSignals} onSelect={setSelected} />
        </div>
      );
    }
    if (resolvedSection === "reports") {
      return (
        <Reports
          reports={reports}
          onGenerateReport={handleGenerateReport}
          generating={reportGenerating}
        />
      );
    }
    if (resolvedSection === "runs") {
      return <Runs runs={runs} onTriggerRun={handleTriggerRun} running={pipelineRunning} />;
    }
    if (resolvedSection === "mcp") {
      return <Mcp servers={mcpServers} onTogglePolicy={handleTogglePolicy} />;
    }
    return <Generic section={resolvedSection} />;
  }, [
    companies,
    handleAddCompany,
    handleGenerateReport,
    handleTogglePolicy,
    handleTriggerRun,
    liveSignals,
    mcpServers,
    pipelineRunning,
    reportGenerating,
    reports,
    resolvedSection,
    runs,
  ]);

  return (
    <div className="min-h-screen bg-[#f5f7fb]">
      {/* Navigation Sidebar */}
      <aside
        className={`fixed inset-y-0 z-40 w-64 bg-navy p-4 transition-transform lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-mint text-navy">
            <Zap className="h-5 w-5 fill-current" />
          </div>
          <span className="text-lg font-bold text-white">RivalScope</span>
        </div>
        <nav className="space-y-1">
          {navigation.map(([id, label, Icon]) => (
            <Link
              onClick={() => setMobileOpen(false)}
              className={`nav-link ${resolvedSection === id ? "nav-link-active" : ""}`}
              href={`/${id}`}
              key={id}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="absolute bottom-5 left-4 right-4 rounded-xl bg-white/10 p-3 text-xs text-slate-300">
          <div className="mb-1 flex items-center gap-2 font-semibold text-white">
            <CircleHelp className="h-4 w-4" /> Need help?
          </div>
          Autonomous multi-agent intelligence platform.
        </div>
      </aside>

      {mobileOpen && (
        <button
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden"
        />
      )}

      {/* Main Content */}
      <main className="min-h-screen lg:ml-64">
        <header className="sticky top-0 z-20 flex h-18 items-center justify-between border-b border-slate-200 bg-[#f5f7fb]/90 px-5 py-4 backdrop-blur lg:px-8">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-lg border bg-white p-2 lg:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>
          <div className="hidden lg:block">
            <p className="text-sm font-semibold">Fintech intelligence workspace</p>
            <p className="text-xs text-slate-400">
              {apiStatus === "connected" ? "Live API connected" : "Demo data · API offline"}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <button className="relative rounded-xl bg-white p-2.5 shadow-sm">
              <Bell className="h-4 w-4" />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-rose-500" />
            </button>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-700">
              PS
            </div>
          </div>
        </header>

        <section className="px-5 pb-10 pt-7 lg:px-8">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="eyebrow">RivalScope / {title}</p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 lg:text-3xl">
                {title}
              </h1>
              <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
            </div>
            {resolvedSection === "dashboard" && (
              <button
                onClick={handleTriggerRun}
                disabled={pipelineRunning}
                className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow transition hover:bg-indigo-700 disabled:opacity-60"
              >
                {pipelineRunning ? (
                  <>
                    <Loader2 className="mr-1.5 inline h-4 w-4 animate-spin" /> In Progress
                  </>
                ) : (
                  <>
                    <Play className="mr-1 inline h-4 w-4 fill-current" /> Run monitor now
                  </>
                )}
              </button>
            )}
          </div>
          {view}
        </section>
      </main>

      {/* Interactive AI Chat Drawer */}
      <button
        onClick={() => setChatOpen(!chatOpen)}
        className="fixed bottom-5 right-5 z-30 flex items-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-xl transition hover:bg-slate-800"
      >
        <MessageSquare className="h-4 w-4" /> Ask RivalScope
      </button>

      {chatOpen && (
        <div className="fixed bottom-20 right-5 z-30 flex h-[30rem] w-[min(26rem,calc(100vw-2.5rem))] flex-col rounded-2xl border bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b p-4">
            <div>
              <p className="font-bold text-slate-900">Research Assistant</p>
              <p className="text-xs text-slate-500">Grounded with PostgreSQL citations</p>
            </div>
            <button onClick={() => setChatOpen(false)} className="rounded p-1 hover:bg-slate-100">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`rounded-xl p-3 ${
                  msg.role === "user"
                    ? "ml-8 bg-indigo-600 text-white"
                    : "mr-8 bg-slate-100 text-slate-800"
                }`}
              >
                {msg.text}
              </div>
            ))}
            {chatLoading && (!chatMessages.length || chatMessages[chatMessages.length - 1].role === "user") && (
              <div className="mr-8 flex items-center gap-2 rounded-xl bg-slate-100 p-3 text-xs text-slate-500">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                Consulting Verifier & Analyst agents...
              </div>
            )}
          </div>

          <form onSubmit={handleSendChat} className="border-t p-3">
            <div className="flex gap-2">
              <input
                value={chatQuery}
                onChange={(e) => setChatQuery(e.target.value)}
                disabled={chatLoading}
                className="flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
                placeholder="Ask about Stripe's pricing moves..."
              />
              <button
                type="submit"
                disabled={chatLoading || !chatQuery.trim()}
                className="rounded-xl bg-slate-900 px-3.5 py-2 text-white transition hover:bg-slate-800 disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Selected Signal Detail Modal */}
      {selected && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/25">
          <button
            className="flex-1"
            aria-label="Close evidence"
            onClick={() => setSelected(null)}
          />
          <aside className="h-full w-full max-w-lg overflow-y-auto bg-white p-6 shadow-2xl">
            <button
              onClick={() => setSelected(null)}
              className="float-right rounded-lg p-2 hover:bg-slate-100"
            >
              <X className="h-5 w-5" />
            </button>
            <p className="eyebrow">
              {selected.company} · {selected.category}
            </p>
            <h2 className="mt-3 pr-8 text-2xl font-bold leading-8">{selected.title}</h2>
            <div className="mt-4">
              <Score score={selected.score} />
            </div>
            <p className="mt-6 leading-7 text-slate-600">{selected.summary}</p>
            <div className="mt-8">
              <p className="eyebrow">Evidence</p>
              {selected.sources.map((source, i) => (
                <div
                  className="mt-3 flex items-center justify-between rounded-xl border p-3"
                  key={source}
                >
                  <div>
                    <p className="font-semibold">{source}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Fetched {i + 1}h ago · corroborating source
                    </p>
                  </div>
                  <ExternalLink className="h-4 w-4 text-indigo-600" />
                </div>
              ))}
            </div>
            <div className="mt-8 rounded-xl bg-emerald-50 p-4">
              <p className="font-semibold text-emerald-800">Why this matters</p>
              <p className="mt-1 text-sm leading-6 text-emerald-700">
                Verified evidence indicates a commercially material competitor move. Review before
                the next product-planning meeting.
              </p>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
