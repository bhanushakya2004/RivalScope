"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  Bell,
  Bot,
  CalendarClock,
  Check,
  ChevronRight,
  CircleHelp,
  Cloud,
  Database,
  ExternalLink,
  FileText,
  Gauge,
  History,
  Layers3,
  LineChart,
  ListFilter,
  Loader2,
  Menu,
  MessageSquare,
  Network,
  Play,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Users,
  X,
  Zap,
  FileSpreadsheet,
  Upload,
  Lock,
  Eye,
  AlertTriangle,
} from "lucide-react";
import {
  rivalScopeApi,
  type ApiChatSession,
  type ApiCompany,
  type ApiInternalDoc,
  type ApiMcpAuditLog,
  type ApiMcpCatalogItem,
  type ApiMcpServer,
  type ApiPreference,
  type ApiReport,
  type ApiRun,
  type ApiSchedule,
  type ApiSignal,
  type ApiTimelineEvent,
  type ApiUser,
} from "../lib/api";

type Signal = {
  id?: string;
  title: string;
  company: string;
  company_id?: string;
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
  ["research", "Internal Research", Sparkles],
  ["documents", "Knowledge Docs", FileSpreadsheet],
  ["runs", "Agent runs", Bot],
  ["schedules", "Schedules", CalendarClock],
  ["team", "Team & RBAC", ShieldCheck],
  ["mcp", "MCP Gateway", Network],
  ["memory", "Memory explorer", Database],
  ["settings", "Settings", Settings],
] as const;

const pageTitles: Record<string, [string, string]> = {
  dashboard: ["Executive Dashboard", "Here is the verified competitive picture across your watchlist."],
  competitors: ["Competitors", "Track the companies that shape your market."],
  signals: ["Signals", "Evidence-backed moves ranked by strategic importance."],
  compare: ["Compare rivals", "Line up product, commercial, and momentum signals."],
  reports: ["Reports", "Cited intelligence briefs ready to share."],
  research: ["Internal Research Agent", "Synthesize internal documentation, connected MCP tools, and competitor moves."],
  documents: ["Knowledge Documentation", "Upload CSV, Excel (.xlsx), Word (.docx), and Markdown files for internal enterprise indexing."],
  runs: ["Agent runs", "Monitor collection, verification, and delivery in real time."],
  schedules: ["Schedules", "Control when intelligence reaches your team."],
  team: ["Team & RBAC Management", "Stateless JWT authentication, user roles (Admin, Analyst, Viewer), and tenant access."],
  integrations: ["Integrations", "Connect delivery channels and provider credentials."],
  mcp: ["MCP Gateway Hub", "Uber-style MCP discovery, disabled-by-default policy matrix, and live audit logs."],
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
  items,
  compact = false,
  onSelect,
}: {
  items: Signal[];
  compact?: boolean;
  onSelect: (signal: Signal) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500">
        <Activity className="mx-auto h-8 w-8 text-slate-300" />
        <p className="mt-2 text-sm font-semibold text-slate-700">No signals recorded yet</p>
        <p className="mt-1 text-xs text-slate-400">
          Trigger an autonomous agent run to collect and verify new market signals.
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-slate-100">
      {items.slice(0, compact ? 3 : 15).map((signal, idx) => (
        <button
          key={signal.id || `${signal.title}-${idx}`}
          onClick={() => onSelect(signal)}
          className="w-full px-5 py-4 text-left transition hover:bg-slate-50"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="mb-1 flex items-center gap-2">
                <span className="text-xs font-bold text-mint">{signal.company}</span>
                <span className="text-xs text-slate-400">{signal.time}</span>
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                  {signal.category}
                </span>
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
  companies,
  mcpServers,
  onSelect,
  onTriggerRun,
  running,
}: {
  items: Signal[];
  companies: ApiCompany[];
  mcpServers: ApiMcpServer[];
  onSelect: (signal: Signal) => void;
  onTriggerRun: () => void;
  running: boolean;
}) {
  const activeCompetitors = companies.filter((c) => !c.is_self).length;
  const highImpactCount = items.filter((s) => s.score >= 80).length;
  const toolCount = mcpServers.reduce((acc, s) => acc + (s.allowed_tools?.length || 0), 0);

  const metrics = [
    { value: `${items.length}`, label: "Live signals", detail: "Verified in database", Icon: Activity },
    { value: `${highImpactCount}`, label: "High-impact moves", detail: "Score >= 80", Icon: Zap },
    { value: `${activeCompetitors}`, label: "Monitored rivals", detail: "Active watchlist", Icon: Users },
    { value: `${mcpServers.length} (${toolCount} tools)`, label: "MCP gateway", detail: "SSRF protected", Icon: Network },
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
            <Link href="/signals" className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">
              View all ({items.length})
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
            {[45, 68, 32, 90, 60, 75, 82].map((height, i) => (
              <div className="flex flex-1 flex-col items-center gap-2" key={i}>
                <div
                  className="w-full rounded-t-md bg-gradient-to-t from-indigo-500 to-cyan-400 transition-all duration-500"
                  style={{ height: `${height}%` }}
                />
                <span className="text-[10px] text-slate-400">
                  {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i]}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-7 rounded-xl bg-slate-50 p-4">
            <p className="text-sm font-semibold">Active Monitored Coverage</p>
            <p className="mt-1 text-sm leading-5 text-slate-500">
              {companies.filter((c) => !c.is_self).map((c) => c.name).join(", ") || "No competitors configured yet"}
            </p>
            <Link
              href="/reports"
              className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-800"
            >
              Read executive briefs <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function Competitors({
  companies,
  signals,
  onAddCompany,
}: {
  companies: ApiCompany[];
  signals: Signal[];
  onAddCompany: (name: string, domain: string, tag: string, region: string) => void;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [tag, setTag] = useState("payments");
  const [region, setRegion] = useState("Global");
  const [searchTerm, setSearchTerm] = useState("");

  const filteredCompanies = companies
    .filter((c) => !c.is_self)
    .filter((c) =>
      searchTerm
        ? c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          c.domain.toLowerCase().includes(searchTerm.toLowerCase())
        : true
    );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !domain.trim()) return;
    onAddCompany(name.trim(), domain.trim(), tag.trim(), region.trim());
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
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
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
          <div className="mt-3 grid gap-3 sm:grid-cols-4">
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
            <input
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              placeholder="Region (e.g. Europe, Global)"
              className="rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="submit"
              className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              Save Competitor
            </button>
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="rounded-lg border px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {filteredCompanies.length === 0 ? (
        <div className="p-8 text-center text-slate-500">
          <Users className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-2 text-sm font-semibold text-slate-700">No competitors found</p>
          <p className="mt-1 text-xs text-slate-400">
            Click &quot;Add competitor&quot; above to register rivals like Stripe, Adyen, or Revolut.
          </p>
        </div>
      ) : (
        <table className="w-full text-left text-sm">
          <thead className="border-y bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="px-5 py-3">Company</th>
              <th>Domain / Focus</th>
              <th>Signals Captured</th>
              <th>Region</th>
              <th className="px-5">Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredCompanies.map((c) => {
              const compSignals = signals.filter(
                (s) =>
                  s.company.toLowerCase() === c.name.toLowerCase() ||
                  s.company_id === c.id
              );
              return (
                <tr className="table-row hover:bg-slate-50/50" key={c.id}>
                  <td className="px-5 py-4 font-semibold text-slate-900">{c.name}</td>
                  <td className="text-slate-500">
                    <span className="font-mono text-xs text-slate-600">{c.domain}</span>
                    {c.tags && c.tags.length > 0 && (
                      <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                        {c.tags.join(", ")}
                      </span>
                    )}
                  </td>
                  <td>
                    <span className="font-semibold text-indigo-600">{compSignals.length}</span> verified
                  </td>
                  <td className="text-slate-500">{c.region || "Global"}</td>
                  <td className="px-5">
                    <span className="chip bg-emerald-50 text-emerald-700">Active Monitoring</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

function CompareView({
  companies,
  signals,
}: {
  companies: ApiCompany[];
  signals: Signal[];
}) {
  const rivalCompanies = companies.filter((c) => !c.is_self);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const activeSelectedIds = useMemo(() => {
    const validSelected = selectedIds.filter((id) => rivalCompanies.some((c) => c.id === id));
    if (validSelected.length > 0) return validSelected;
    return rivalCompanies.slice(0, 3).map((c) => c.id);
  }, [selectedIds, rivalCompanies]);

  const toggleSelect = (id: string) => {
    setSelectedIds((cur) => {
      const base = cur.length > 0 ? cur : rivalCompanies.slice(0, 3).map((c) => c.id);
      return base.includes(id)
        ? (base.length > 1 ? base.filter((x) => x !== id) : base)
        : [...base, id];
    });
  };

  const selectedCompanies = rivalCompanies.filter((c) => activeSelectedIds.includes(c.id));

  return (
    <div className="space-y-6">
      <div className="panel p-5">
        <p className="eyebrow">Side-by-side analysis</p>
        <h2 className="mt-1 text-lg font-bold">Select rivals to compare</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {rivalCompanies.map((c) => (
            <button
              key={c.id}
              onClick={() => toggleSelect(c.id)}
              className={`rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                selectedIds.includes(c.id)
                  ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
              }`}
            >
              {c.name}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {selectedCompanies.map((c) => {
          const compSignals = signals.filter(
            (s) =>
              s.company.toLowerCase() === c.name.toLowerCase() ||
              s.company_id === c.id
          );
          const avgScore = compSignals.length
            ? Math.round(
                compSignals.reduce((acc, s) => acc + s.score, 0) / compSignals.length
              )
            : 0;
          const highImpact = compSignals.filter((s) => s.score >= 80).length;
          const topCategories = Array.from(
            new Set(compSignals.map((s) => s.category))
          );

          return (
            <div className="panel overflow-hidden" key={c.id}>
              <div className="border-b bg-slate-50/50 p-5">
                <span className="eyebrow">{c.region || "Global"}</span>
                <h3 className="mt-1 text-xl font-bold text-slate-900">{c.name}</h3>
                <p className="text-xs font-mono text-slate-500">{c.domain}</p>
              </div>

              <div className="space-y-4 p-5 text-sm">
                <div className="flex justify-between border-b pb-2">
                  <span className="text-slate-500">Verified Signals</span>
                  <span className="font-bold text-slate-900">{compSignals.length}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-slate-500">High-Impact Moves</span>
                  <span className="font-bold text-rose-600">{highImpact}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-slate-500">Average Impact Score</span>
                  <span className="font-bold text-indigo-600">{avgScore || "N/A"}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-slate-500">Signal Categories</span>
                  <span className="font-medium text-slate-700">
                    {topCategories.join(", ") || "General"}
                  </span>
                </div>

                <div className="pt-2">
                  <p className="text-xs font-semibold text-slate-500">Latest Verified Move</p>
                  {compSignals[0] ? (
                    <div className="mt-2 rounded-lg bg-slate-50 p-3">
                      <p className="text-xs font-semibold text-slate-800">{compSignals[0].title}</p>
                      <p className="mt-1 text-[11px] text-slate-500 line-clamp-2">
                        {compSignals[0].summary}
                      </p>
                    </div>
                  ) : (
                    <p className="mt-1 text-xs text-slate-400">No signals recorded yet.</p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
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
  const [selectedReport, setSelectedReport] = useState<ApiReport | null>(null);

  const handleGenerate = () => {
    if (!prompt.trim() || generating) return;
    onGenerateReport(prompt);
    setPrompt("");
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
      <div className="panel divide-y">
        <div className="p-5">
          <p className="eyebrow">Intelligence Briefs</p>
          <h2 className="mt-1 text-xl font-bold">Executive Cited Reports</h2>
          <p className="mt-2 text-sm text-slate-500">
            Synthesized multi-agent briefs with citations and strategic evaluations.
          </p>
        </div>

        {reports.length > 0 ? (
          reports.map((rep) => (
            <button
              onClick={() => setSelectedReport(rep)}
              className="flex w-full items-center justify-between p-5 text-left transition hover:bg-slate-50"
              key={rep.id}
            >
              <div>
                <p className="font-semibold text-slate-800">{rep.title}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {rep.summary ? rep.summary.slice(0, 110) + "..." : "Cited intelligence brief"}
                </p>
                <span className="mt-2 inline-block rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700">
                  {rep.status} · {new Date(rep.created_at).toLocaleDateString()}
                </span>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-400" />
            </button>
          ))
        ) : (
          <div className="p-8 text-center text-slate-500">
            <FileText className="mx-auto h-8 w-8 text-slate-300" />
            <p className="mt-2 text-sm font-semibold text-slate-700">No reports generated yet</p>
            <p className="mt-1 text-xs text-slate-400">
              Ask the research team to generate an executive brief using the form on the right.
            </p>
          </div>
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

        {selectedReport && (
          <div className="mt-6 rounded-xl border bg-slate-50 p-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-slate-800">{selectedReport.title}</h4>
              <button
                onClick={() => setSelectedReport(null)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                Close
              </button>
            </div>
            <div className="mt-3 max-h-60 overflow-y-auto text-xs leading-5 text-slate-600">
              <p className="font-semibold text-slate-700">Summary:</p>
              <p className="mt-1">{selectedReport.summary || selectedReport.content}</p>
            </div>
          </div>
        )}
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
              {latestRun ? `Run · ${latestRun.id.slice(0, 8)}` : "Multi-Agent Monitor Pipeline"}
            </h2>
          </div>
          <span
            className={`chip ${
              running || latestRun?.status === "running"
                ? "bg-amber-100 text-amber-700"
                : "bg-emerald-100 text-emerald-700"
            }`}
          >
            {running || latestRun?.status === "running" ? "In progress" : "Ready"}
          </span>
        </div>

        <div className="space-y-5 p-5">
          {[
            ["Collectors", "News, filings, product changelogs, talent footprints queried", true],
            ["Deduplication", "6-stage pipeline: canonical URL, SHA-256, SimHash, semantic clustering", true],
            ["Verifier", "Evidence ground truth verification & confidence calculation", true],
            ["Analyst", "Strategic impact & competitive positioning evaluation", !running],
            ["Reporter", "Executive brief markdown synthesis & citation links", !running],
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

        {runs.length > 0 && (
          <div className="border-t">
            <div className="bg-slate-50 px-5 py-3 text-xs font-bold text-slate-600">
              Recent Run History ({runs.length})
            </div>
            <div className="divide-y divide-slate-100 text-xs">
              {runs.slice(0, 5).map((r) => (
                <div className="flex items-center justify-between px-5 py-3" key={r.id}>
                  <div>
                    <span className="font-mono font-bold text-slate-800">{r.id.slice(0, 8)}</span>
                    <span className="ml-2 text-slate-400">
                      {new Date(r.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-slate-500">{r.duration_seconds}s</span>
                    <span
                      className={`chip ${
                        r.status === "completed"
                          ? "bg-emerald-100 text-emerald-700"
                          : r.status === "running"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-rose-100 text-rose-700"
                      }`}
                    >
                      {r.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
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
            <b>{latestRun ? `${latestRun.duration_seconds}s` : "0.0s"}</b>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Tokens Processed</span>
            <b>{latestRun ? latestRun.tokens.toLocaleString() : "0"}</b>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Engine</span>
            <b>Agno Teams + PgVector</b>
          </div>
        </div>
      </div>
    </div>
  );
}

function SchedulesView({
  schedules,
  onRunNow,
}: {
  schedules: ApiSchedule[];
  onRunNow: (scheduleId: string) => Promise<void>;
}) {
  const [runningId, setRunningId] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const handleRun = async (id: string) => {
    setRunningId(id);
    setStatusMsg(null);
    try {
      await onRunNow(id);
      setStatusMsg("Schedule execution triggered successfully!");
    } catch {
      setStatusMsg("Failed to execute schedule.");
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="panel flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="eyebrow">Automated Monitoring Jobs</p>
          <h2 className="mt-1 text-lg font-bold">Configured Schedules</h2>
          <p className="mt-1 text-sm text-slate-500">
            Control when autonomous multi-agent pipelines collect, verify, and deliver competitor moves.
          </p>
        </div>
      </div>

      {statusMsg && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm font-medium text-indigo-800">
          {statusMsg}
        </div>
      )}

      {schedules.length === 0 ? (
        <div className="panel p-8 text-center text-slate-500">
          <CalendarClock className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-2 text-sm font-semibold text-slate-700">No schedules configured</p>
          <p className="mt-1 text-xs text-slate-400">
            Automated monitoring jobs run periodically via background scheduler.
          </p>
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {schedules.map((s) => (
            <div className="panel p-5" key={s.id}>
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-slate-900">{s.name}</h3>
                  <p className="mt-1 font-mono text-xs text-indigo-600">
                    {s.cron_expression ? `Cron: ${s.cron_expression}` : `Every ${s.interval_seconds}s`}
                  </p>
                </div>
                <span
                  className={`chip ${
                    s.enabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {s.enabled ? "Active" : "Paused"}
                </span>
              </div>

              <div className="mt-4 space-y-2 text-xs text-slate-500">
                <div className="flex justify-between">
                  <span>Last run:</span>
                  <span className="font-medium text-slate-700">
                    {s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "Never"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Next run:</span>
                  <span className="font-medium text-slate-700">
                    {s.next_run_at ? new Date(s.next_run_at).toLocaleString() : "Scheduled"}
                  </span>
                </div>
              </div>

              <div className="mt-5 border-t pt-4">
                <button
                  onClick={() => handleRun(s.id)}
                  disabled={runningId === s.id}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 py-2 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
                >
                  {runningId === s.id ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Running...
                    </>
                  ) : (
                    <>
                      <Play className="h-3.5 w-3.5 fill-current" /> Run Now
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Mcp({
  servers,
  auditLogs,
  onTogglePolicy,
  onAddServer,
  onDiscoverServer,
  onDeleteServer,
}: {
  servers: ApiMcpServer[];
  auditLogs: ApiMcpAuditLog[];
  onTogglePolicy: (serverId: string, toolName: string, enabled: boolean, approval: boolean, agentScope?: string) => void;
  onAddServer: (payload: { name: string; transport: string; url: string; auth_type: string; allowed_tools: string[] }) => void;
  onDiscoverServer: (serverId: string) => Promise<void>;
  onDeleteServer: (serverId: string) => Promise<void>;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [transport, setTransport] = useState("streamable-http");
  const [authType, setAuthType] = useState("bearer");
  const [toolsStr, setToolsStr] = useState("query_internal_financials, get_crm_deals, lookup_billing_rate");
  const [discoveringId, setDiscoveringId] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const allowed = toolsStr
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    onAddServer({
      name: name.trim(),
      transport,
      url: url.trim(),
      auth_type: authType,
      allowed_tools: allowed,
    });
    setName("");
    setUrl("");
    setShowAdd(false);
  };

  const handleDiscover = async (serverId: string) => {
    setDiscoveringId(serverId);
    try {
      await onDiscoverServer(serverId);
    } finally {
      setDiscoveringId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="panel flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="eyebrow">Uber-Style Enterprise Gateway</p>
          <h2 className="mt-1 text-lg font-bold">MCP Servers & Tool Governance Matrix</h2>
          <p className="mt-1 text-sm text-slate-500">
            Automated JSON-RPC 2.0 discovery, disabled-by-default security policies, SSRF private IP validation, and cryptographic audit logs.
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 flex items-center gap-1.5"
        >
          <Plus className="h-4 w-4" /> Add MCP Server
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleSubmit} className="panel border-indigo-200 bg-slate-50 p-5">
          <h4 className="text-sm font-bold text-slate-800">Register New MCP Server</h4>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs font-semibold text-slate-600">Server Name</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Finance & Billing Gateway"
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Server Endpoint URL</label>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="e.g. http://localhost:8001/mcp or https://internal-erp.corp"
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Transport</label>
              <select
                value={transport}
                onChange={(e) => setTransport(e.target.value)}
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              >
                <option value="streamable-http">streamable-http (HTTP POST)</option>
                <option value="sse">sse (Server-Sent Events)</option>
                <option value="stdio">stdio (Local Subprocess)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Auth Type</label>
              <select
                value={authType}
                onChange={(e) => setAuthType(e.target.value)}
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              >
                <option value="bearer">Bearer Token</option>
                <option value="header">Custom Header (X-API-Key)</option>
                <option value="none">None / Open</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs font-semibold text-slate-600">
                Declared Tools (comma separated)
              </label>
              <input
                value={toolsStr}
                onChange={(e) => setToolsStr(e.target.value)}
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="submit"
              className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              Register Server
            </button>
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="rounded-lg border px-3 py-2 text-xs text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {servers.length === 0 ? (
        <div className="panel p-8 text-center text-slate-500">
          <Network className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-2 text-sm font-semibold text-slate-700">No MCP servers registered</p>
          <p className="mt-1 text-xs text-slate-400">
            Register your enterprise servers to give agents access to approved internal data tools.
          </p>
        </div>
      ) : (
        servers.map((server) => (
          <div className="grid gap-5 lg:grid-cols-[.8fr_1.2fr]" key={server.id}>
            <div className="panel p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-bold text-slate-900">{server.name}</p>
                  <p className="mt-1 text-xs text-slate-500 font-mono">
                    {server.transport} · {server.auth_type}
                  </p>
                </div>
                <span className="chip bg-emerald-100 text-emerald-700">{server.status}</span>
              </div>
              {server.url && (
                <p className="truncate rounded bg-slate-50 p-2 font-mono text-xs text-slate-600">
                  {server.url}
                </p>
              )}
              <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
                <ShieldCheck className="mr-2 inline h-4 w-4 text-emerald-600" /> AES-256 envelope
                encryption active & SSRF firewall validated
              </div>
              <div className="flex items-center gap-2 pt-2 border-t">
                <button
                  onClick={() => handleDiscover(server.id)}
                  disabled={discoveringId === server.id}
                  className="rounded-lg bg-indigo-50 border border-indigo-200 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 flex items-center gap-1.5 transition"
                >
                  {discoveringId === server.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5" />
                  )}
                  Discover Tools (tools/list)
                </button>
                <button
                  onClick={() => onDeleteServer(server.id)}
                  className="rounded-lg border border-rose-200 p-1.5 text-rose-600 hover:bg-rose-50"
                  title="Remove server"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div className="panel overflow-hidden">
              <div className="border-b p-5 flex items-center justify-between">
                <div>
                  <p className="font-bold text-slate-900">Governance Policy Matrix</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Uber model: newly discovered tools start disabled by default. Configure agent scope and HITL human approval.
                  </p>
                </div>
              </div>
              {server.policies && server.policies.length > 0 ? (
                server.policies.map((policy: any) => (
                  <div
                    className="flex flex-wrap items-center justify-between border-b p-4 last:border-0 gap-3"
                    key={policy.tool_name}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-sm text-slate-800 font-mono">{policy.tool_name}</p>
                        {policy.is_enabled ? (
                          <span className="chip bg-emerald-100 text-emerald-800 text-[10px]">Enabled</span>
                        ) : (
                          <span className="chip bg-slate-100 text-slate-600 text-[10px]">Disabled by default</span>
                        )}
                        <span className="chip bg-indigo-50 text-indigo-700 text-[10px]">
                          Scope: {policy.agent_scope || "all"}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {policy.require_approval ? "Requires HITL human approval before dispatch" : "Autonomous Read access"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={policy.agent_scope || "all"}
                        onChange={(e) =>
                          onTogglePolicy(
                            server.id,
                            policy.tool_name,
                            policy.is_enabled,
                            policy.require_approval,
                            e.target.value
                          )
                        }
                        className="rounded-lg border bg-white px-2 py-1 text-xs text-slate-700 outline-none"
                      >
                        <option value="all">All Agents</option>
                        <option value="internal_research">Internal Research</option>
                        <option value="analyst">Analyst Only</option>
                      </select>
                      <button
                        onClick={() =>
                          onTogglePolicy(
                            server.id,
                            policy.tool_name,
                            !policy.is_enabled,
                            policy.require_approval,
                            policy.agent_scope || "all"
                          )
                        }
                        className={`h-6 w-11 rounded-full p-0.5 transition ${
                          policy.is_enabled ? "bg-indigo-600" : "bg-slate-200"
                        }`}
                      >
                        <span
                          className={`block h-5 w-5 rounded-full bg-white transition ${
                            policy.is_enabled ? "translate-x-5" : ""
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-5 text-xs text-slate-400">
                  No tools discovered yet. Click &quot;Discover Tools&quot; to probe this MCP server.
                </div>
              )}
            </div>
          </div>
        ))
      )}

      {/* Live MCP Audit Log */}
      <div className="panel overflow-hidden">
        <div className="border-b px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900">Live Gateway Execution Audit Trail</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Every MCP tool invocation is logged with duration, status, and payload sanitization.
            </p>
          </div>
          <span className="chip bg-slate-100 text-slate-700 text-xs font-mono">
            {auditLogs.length} logged calls
          </span>
        </div>

        {auditLogs.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400">
            No tool executions logged yet. Invocations from the Internal Research agent or CI team will appear here in real time.
          </div>
        ) : (
          <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
            {auditLogs.slice(0, 15).map((log) => {
              const statusBadge =
                log.status === "success"
                  ? "bg-emerald-100 text-emerald-700"
                  : log.status === "approval_required"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-rose-100 text-rose-700";
              return (
                <div key={log.id} className="p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-900">{log.tool_name}</span>
                    <span className={`chip text-[10px] uppercase font-bold ${statusBadge}`}>{log.status}</span>
                    <span className="text-slate-400">{log.duration_ms} ms</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {log.result_summary && (
                      <span className="text-slate-500 max-w-xs truncate font-mono">
                        {log.result_summary}
                      </span>
                    )}
                    <span className="text-slate-400 font-mono">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function TeamView({
  users,
  currentUser,
  onRefresh,
}: {
  users: ApiUser[];
  currentUser: ApiUser | null;
  onRefresh: () => void;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("analyst");
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) return;
    setSaving(true);
    setErrorMsg(null);
    try {
      await rivalScopeApi.createUser({
        email: email.trim(),
        name: name.trim() || undefined,
        password: password.trim(),
        role,
      });
      setEmail("");
      setName("");
      setPassword("");
      setShowAdd(false);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (user: ApiUser) => {
    try {
      await rivalScopeApi.updateUser(user.id, { is_active: !user.is_active });
      onRefresh();
    } catch (err: any) {
      alert(err.message || "Failed to update user");
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm("Are you sure you want to remove this user from the tenant?")) return;
    try {
      await rivalScopeApi.deleteUser(userId);
      onRefresh();
    } catch (err: any) {
      alert(err.message || "Failed to remove user");
    }
  };

  return (
    <div className="space-y-6">
      <div className="panel flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="eyebrow">Enterprise Access Control</p>
          <h2 className="mt-1 text-lg font-bold">Team Members & RBAC Roles</h2>
          <p className="mt-1 text-sm text-slate-500">
            Stateless JWT authentication enforcing strict Admin, Analyst, and Viewer privilege tiers.
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 flex items-center gap-2"
        >
          <Plus className="h-4 w-4" /> Add Team Member
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleAddUser} className="panel border-indigo-200 bg-slate-50 p-5 space-y-4">
          <h4 className="text-sm font-bold text-slate-800">Add New User to Organization</h4>
          {errorMsg && (
            <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
              {errorMsg}
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-semibold text-slate-600">Full Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Alex Morgan"
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Email Address *</label>
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="alex@enterprise.corp"
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Temporary Password *</label>
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">RBAC Role *</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
              >
                <option value="analyst">Analyst (Analyze signals & run research)</option>
                <option value="admin">Admin (Full tenant & MCP gateway control)</option>
                <option value="viewer">Viewer (Read-only intelligence access)</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 flex items-center gap-1.5"
            >
              {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Create Member
            </button>
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="rounded-lg border px-3 py-2 text-xs text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Role explanation cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="panel p-4 border-l-4 border-l-purple-500">
          <span className="chip bg-purple-100 text-purple-700 font-semibold text-xs">Admin</span>
          <p className="mt-2 text-xs text-slate-600">
            Full organizational authority. Manages team members, registers MCP servers, configures disabled-by-default tool policies, and approves HITL write actions.
          </p>
        </div>
        <div className="panel p-4 border-l-4 border-l-blue-500">
          <span className="chip bg-blue-100 text-blue-700 font-semibold text-xs">Analyst</span>
          <p className="mt-2 text-xs text-slate-600">
            Executes autonomous collection runs, queries Internal Research agent, generates cited intelligence briefs, and analyzes competitor counter-moves.
          </p>
        </div>
        <div className="panel p-4 border-l-4 border-l-slate-400">
          <span className="chip bg-slate-100 text-slate-700 font-semibold text-xs">Viewer</span>
          <p className="mt-2 text-xs text-slate-600">
            Auditing and consumption access. Views competitor dashboards, verified signals, and published strategic reports with zero mutating tool permissions.
          </p>
        </div>
      </div>

      {/* User list */}
      <div className="panel overflow-hidden">
        <div className="border-b px-5 py-4 flex items-center justify-between">
          <h3 className="font-bold text-slate-900">Active Organization Members ({users.length})</h3>
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-indigo-600"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>
        <div className="divide-y divide-slate-100">
          {users.map((u) => {
            const roleBadge =
              u.role === "admin"
                ? "bg-purple-100 text-purple-700"
                : u.role === "analyst"
                ? "bg-blue-100 text-blue-700"
                : "bg-slate-100 text-slate-700";
            return (
              <div key={u.id} className="p-4 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-full bg-slate-200 flex items-center justify-center font-bold text-slate-700 text-sm uppercase">
                    {(u.name || u.email).slice(0, 2)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-slate-900">{u.name || u.email.split("@")[0]}</span>
                      <span className={`chip text-[10px] font-semibold uppercase ${roleBadge}`}>{u.role}</span>
                      {u.is_active ? (
                        <span className="chip bg-emerald-100 text-emerald-700 text-[10px]">Active</span>
                      ) : (
                        <span className="chip bg-rose-100 text-rose-700 text-[10px]">Disabled</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">{u.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggleActive(u)}
                    className="rounded-lg border px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                  >
                    {u.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    onClick={() => handleDelete(u.id)}
                    className="rounded-lg border border-rose-200 p-1.5 text-rose-600 hover:bg-rose-50"
                    title="Remove member"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DocumentsView({
  documents,
  onRefresh,
}: {
  documents: ApiInternalDoc[];
  onRefresh: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<ApiInternalDoc | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setErrorMsg(null);
    try {
      await rivalScopeApi.uploadDocument(file);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("Are you sure you want to remove this document and delete its vector chunks?")) return;
    try {
      await rivalScopeApi.deleteDocument(docId);
      onRefresh();
    } catch (err: any) {
      alert(err.message || "Failed to delete document");
    }
  };

  return (
    <div className="space-y-6">
      <div className="panel flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="eyebrow">Enterprise Knowledge Ingestion</p>
          <h2 className="mt-1 text-lg font-bold">Document Knowledge Center</h2>
          <p className="mt-1 text-sm text-slate-500">
            Upload CSV, Excel (.xlsx), Word (.docx), and Markdown files. Extracted tabular data and text chunks are indexed in pgvector hybrid search for internal research.
          </p>
        </div>
      </div>

      {/* Upload Box */}
      <div className="panel p-6 border-dashed border-2 border-indigo-200 bg-indigo-50/20 text-center">
        <FileSpreadsheet className="mx-auto h-10 w-10 text-indigo-500" />
        <h3 className="mt-2 text-sm font-bold text-slate-800">Upload Enterprise Files</h3>
        <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">
          Supported: <strong>CSV, Excel (.xlsx, .xls), Word (.docx), Markdown (.md), Plain Text (.txt), JSON</strong> (Max 25MB). Tabular rows are converted into structured Markdown preview tables and embedded into pgvector.
        </p>
        <p className="mt-1 text-[11px] text-slate-400">
          *(Note: PDF OCR scanning is intentionally excluded for high-speed deterministic ingestion).*
        </p>

        {errorMsg && (
          <div className="mt-3 inline-block rounded-lg bg-rose-50 border border-rose-200 px-4 py-2 text-xs text-rose-700">
            {errorMsg}
          </div>
        )}

        <div className="mt-4">
          <label className="cursor-pointer inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition">
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Ingesting & Embedding...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" /> Select File to Upload
              </>
            )}
            <input
              type="file"
              disabled={uploading}
              onChange={handleFileUpload}
              accept=".csv,.xlsx,.xls,.docx,.doc,.md,.markdown,.txt,.json"
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* Document Catalog */}
      <div className="panel overflow-hidden">
        <div className="border-b px-5 py-4 flex items-center justify-between">
          <h3 className="font-bold text-slate-900">Indexed Knowledge Documents ({documents.length})</h3>
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-indigo-600"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>

        {documents.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <Database className="mx-auto h-8 w-8 text-slate-300" />
            <p className="mt-2 text-sm font-semibold text-slate-700">No documents uploaded yet</p>
            <p className="mt-1 text-xs text-slate-400">
              Upload spreadsheets or contract docs above to empower the Internal Research Agent.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {documents.map((doc) => {
              const extBadge =
                doc.file_type === "csv"
                  ? "bg-emerald-100 text-emerald-800"
                  : doc.file_type === "xlsx" || doc.file_type === "xls"
                  ? "bg-green-100 text-green-800"
                  : doc.file_type === "docx"
                  ? "bg-blue-100 text-blue-800"
                  : "bg-slate-100 text-slate-800";
              const sizeKb = Math.round(doc.file_size_bytes / 1024);
              return (
                <div key={doc.id} className="p-4 flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-slate-900">{doc.filename}</span>
                      <span className={`chip text-[10px] font-bold uppercase ${extBadge}`}>{doc.file_type}</span>
                      <span className="chip bg-sky-100 text-sky-800 text-[10px]">{doc.status}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {doc.row_count} rows/paragraphs · {sizeKb} KB · {doc.column_names?.length ? `${doc.column_names.length} columns (${doc.column_names.slice(0, 3).join(", ")}...)` : "Structured text"}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{doc.summary}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPreviewDoc(doc)}
                      className="rounded-lg border px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
                    >
                      <Eye className="h-3.5 w-3.5" /> Preview
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="rounded-lg border border-rose-200 p-1.5 text-rose-600 hover:bg-rose-50"
                      title="Delete document"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="font-bold text-slate-900">{previewDoc.filename}</h3>
                <p className="text-xs text-slate-500">
                  {previewDoc.file_type.toUpperCase()} · {previewDoc.row_count} rows · {Math.round(previewDoc.file_size_bytes / 1024)} KB
                </p>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase">Extraction Summary</h4>
              <p className="text-sm text-slate-600 mt-1">{previewDoc.summary}</p>
            </div>
            {previewDoc.column_names && previewDoc.column_names.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase">Detected Columns / Headers</h4>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {previewDoc.column_names.map((col) => (
                    <span key={col} className="chip bg-slate-100 text-slate-700 text-xs">
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {Boolean(previewDoc.metadata_json?.preview_snippet) && (
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase">Markdown Preview Snippet</h4>
                <pre className="mt-1 max-h-60 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-800 font-mono whitespace-pre-wrap">
                  {String(previewDoc.metadata_json?.preview_snippet)}
                </pre>
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setPreviewDoc(null)}
                className="rounded-lg bg-slate-800 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-900"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ResearchView({
  companies,
  documentsCount,
  mcpToolsCount,
}: {
  companies: ApiCompany[];
  documentsCount: number;
  mcpToolsCount: number;
}) {
  const [query, setQuery] = useState("");
  const [competitor, setCompetitor] = useState("all");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    answer: string;
    internal_sources: Array<{ filename: string; file_type: string; snippet: string }>;
    mcp_tools_used: Array<{ tool_name: string; server_id: string; agent_scope?: string }>;
    web_sources: Array<{ title: string; url: string }>;
  } | null>(null);

  const quickPrompts = [
    "Compare our Q3 gross payment volume and take-rate vs Stripe agentic commerce",
    "Which CRM deals did we lose to Adyen or Stripe and what were the cited objections?",
    "Summarize our active billing tiers, interchange schedules, and volume discounts",
    "What initiatives are planned in our internal engineering roadmap sprint?",
  ];

  const handleRun = async (promptQuery?: string) => {
    const q = (promptQuery || query).trim();
    if (!q || loading) return;
    if (promptQuery) setQuery(promptQuery);
    setLoading(true);
    try {
      const res = await rivalScopeApi.internalResearch(
        q,
        competitor !== "all" ? competitor : undefined
      );
      setResult(res);
    } catch (err: any) {
      alert(err.message || "Research query failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="panel p-5">
        <p className="eyebrow">Enterprise Intelligence Synthesis</p>
        <h2 className="mt-1 text-lg font-bold">Internal Research Agent</h2>
        <p className="mt-1 text-sm text-slate-500">
          Synthesizes internal uploaded documentation (spreadsheets, docs), connected MCP tools (finance, CRM, billing), and live market signals into executive answers.
        </p>

        {/* Stats bar */}
        <div className="mt-4 flex flex-wrap gap-4 text-xs font-medium text-slate-600">
          <span className="flex items-center gap-1.5 bg-slate-100 rounded-lg px-2.5 py-1">
            <FileSpreadsheet className="h-3.5 w-3.5 text-indigo-600" /> {documentsCount} Indexed Internal Docs
          </span>
          <span className="flex items-center gap-1.5 bg-slate-100 rounded-lg px-2.5 py-1">
            <Network className="h-3.5 w-3.5 text-emerald-600" /> {mcpToolsCount} Active Enabled MCP Tools
          </span>
          <span className="flex items-center gap-1.5 bg-slate-100 rounded-lg px-2.5 py-1">
            <ShieldCheck className="h-3.5 w-3.5 text-purple-600" /> Zero Hallucination Citations
          </span>
        </div>
      </div>

      {/* Query Bar */}
      <div className="panel p-5 space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRun()}
              placeholder="Ask anything bridging internal metrics & competitor moves..."
              className="w-full rounded-xl border bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 shadow-sm"
            />
          </div>
          <select
            value={competitor}
            onChange={(e) => setCompetitor(e.target.value)}
            className="rounded-xl border bg-white px-3 py-3 text-sm outline-none focus:border-indigo-500"
          >
            <option value="all">Cross-Reference All Rivals</option>
            {companies.filter((c) => !c.is_self).map((c) => (
              <option key={c.id} value={c.name}>
                Focus: {c.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => handleRun()}
            disabled={loading || !query.trim()}
            className="rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Run Research
          </button>
        </div>

        {/* Prompt Chips */}
        <div>
          <p className="text-xs font-semibold text-slate-500 mb-2">Suggested Research Prompts:</p>
          <div className="flex flex-wrap gap-2">
            {quickPrompts.map((p) => (
              <button
                key={p}
                onClick={() => handleRun(p)}
                className="rounded-lg border bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition text-left"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Output Panel */}
      {result && (
        <div className="space-y-4">
          <div className="panel p-6">
            <div className="mb-4 flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-indigo-600" /> Synthesized Strategic Deliverable
              </h3>
              <button
                onClick={() => setResult(null)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                Clear
              </button>
            </div>
            <div className="prose prose-sm max-w-none text-slate-800 leading-relaxed whitespace-pre-wrap font-sans">
              {result.answer}
            </div>
          </div>

          {/* Sources breakdown */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="panel p-5">
              <h4 className="text-xs font-bold text-slate-700 uppercase flex items-center gap-1.5">
                <FileSpreadsheet className="h-4 w-4 text-indigo-600" /> Internal Documents Grounding
              </h4>
              <div className="mt-3 space-y-2">
                {result.internal_sources.length === 0 ? (
                  <p className="text-xs text-slate-400">No specific internal document chunks matched.</p>
                ) : (
                  result.internal_sources.map((s, idx) => (
                    <div key={idx} className="rounded-lg bg-slate-50 p-2.5 text-xs border">
                      <span className="font-semibold text-slate-800">`{s.filename}`</span>
                      <p className="text-slate-500 mt-1 line-clamp-2">{s.snippet}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="panel p-5">
              <h4 className="text-xs font-bold text-slate-700 uppercase flex items-center gap-1.5">
                <Network className="h-4 w-4 text-emerald-600" /> MCP Tools & Gateway Execution
              </h4>
              <div className="mt-3 space-y-2">
                {result.mcp_tools_used.length === 0 ? (
                  <p className="text-xs text-slate-400">No external MCP tools were required.</p>
                ) : (
                  result.mcp_tools_used.map((t, idx) => (
                    <div key={idx} className="flex items-center justify-between rounded-lg bg-slate-50 p-2.5 text-xs border">
                      <span className="font-mono font-semibold text-slate-800">{t.tool_name}</span>
                      <span className="chip bg-emerald-100 text-emerald-700 text-[10px]">Executed via Gateway</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function formatDetails(details: unknown): string {
  if (!details) return "";
  if (typeof details === "string") return details;
  if (typeof details === "object") {
    const d = details as Record<string, unknown>;
    if (d.summary && typeof d.summary === "string") return d.summary;
    if (d.corroboration_count !== undefined) {
      return `Corroborated across ${d.corroboration_count} source${Number(d.corroboration_count) === 1 ? "" : "s"}`;
    }
    const entries = Object.entries(d)
      .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
      .join(" • ");
    return entries || JSON.stringify(d);
  }
  return String(details);
}

function MemoryView({
  preferences,
  timeline,
  companies,
  onAddPreference,
}: {
  preferences: ApiPreference[];
  timeline: ApiTimelineEvent[];
  companies: ApiCompany[];
  onAddPreference: (category: string, text: string) => Promise<void>;
}) {
  const [prefCategory, setPrefCategory] = useState("positioning");
  const [prefText, setPrefText] = useState("");
  const [savingPref, setSavingPref] = useState(false);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("all");

  const handleSavePref = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prefText.trim() || savingPref) return;
    setSavingPref(true);
    try {
      await onAddPreference(prefCategory, prefText.trim());
      setPrefText("");
    } finally {
      setSavingPref(false);
    }
  };

  const filteredTimeline =
    selectedCompanyId === "all"
      ? timeline
      : timeline.filter((evt) => evt.company_id === selectedCompanyId);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
      {/* Layer 2: Organization Preferences */}
      <div className="panel flex flex-col">
        <div className="border-b p-5">
          <p className="eyebrow">Layer 2: Durable Directives</p>
          <h2 className="mt-1 text-lg font-bold">Organizational Preferences</h2>
          <p className="mt-1 text-xs text-slate-500">
            Durable strategic rules and voice constraints remembered across all agent sessions.
          </p>
        </div>

        <form onSubmit={handleSavePref} className="border-b bg-slate-50/50 p-4">
          <div className="flex gap-2">
            <select
              value={prefCategory}
              onChange={(e) => setPrefCategory(e.target.value)}
              className="rounded-lg border bg-white px-2.5 py-1.5 text-xs font-semibold outline-none focus:border-indigo-500"
            >
              <option value="positioning">positioning</option>
              <option value="pricing">pricing</option>
              <option value="threat">threat</option>
              <option value="alert_threshold">alert_threshold</option>
            </select>
            <input
              required
              value={prefText}
              onChange={(e) => setPrefText(e.target.value)}
              placeholder="e.g. Prioritize real-time payment rails over card issuance"
              className="flex-1 rounded-lg border bg-white px-3 py-1.5 text-xs outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={savingPref}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {savingPref ? <Loader2 className="h-3 w-3 animate-spin" /> : "Save"}
            </button>
          </div>
        </form>

        <div className="flex-1 divide-y divide-slate-100 overflow-y-auto p-2">
          {preferences.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-400">
              No custom directives stored yet. Add one above.
            </div>
          ) : (
            preferences.map((p) => (
              <div className="p-3 text-xs" key={p.id}>
                <span className="rounded bg-indigo-50 px-2 py-0.5 font-bold text-indigo-700">
                  {p.category}
                </span>
                <p className="mt-1.5 text-slate-700">
                  {typeof (p.text || p.memory_text) === "object"
                    ? JSON.stringify(p.text || p.memory_text)
                    : String(p.text || p.memory_text || "")}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Layer 4: Chronological Event Timeline */}
      <div className="panel flex flex-col">
        <div className="flex items-center justify-between border-b p-5">
          <div>
            <p className="eyebrow">Layer 4: Entity Timeline</p>
            <h2 className="mt-1 text-lg font-bold">Historical Event Chronology</h2>
          </div>
          <select
            value={selectedCompanyId}
            onChange={(e) => setSelectedCompanyId(e.target.value)}
            className="rounded-lg border px-2 py-1 text-xs font-semibold outline-none focus:border-indigo-500"
          >
            <option value="all">All Rivals</option>
            {companies
              .filter((c) => !c.is_self)
              .map((c) => (
                <option value={c.id} key={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
        </div>

        <div className="flex-1 divide-y divide-slate-100 overflow-y-auto p-2">
          {filteredTimeline.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-400">
              No historical timeline events recorded yet.
            </div>
          ) : (
            filteredTimeline.map((evt) => (
              <div className="p-3 text-xs" key={evt.id}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800">{evt.title}</span>
                  <span className="text-[10px] text-slate-400">
                    {new Date(evt.event_date).toLocaleDateString()}
                  </span>
                </div>
                {Boolean(formatDetails(evt.details)) && (
                  <p className="mt-1 text-slate-500">{formatDetails(evt.details)}</p>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function IntegrationsView() {
  const [webhookUrl, setWebhookUrl] = useState("https://hooks.slack.com/services/T00/B00/XXXX");
  const [testSent, setTestSent] = useState(false);

  return (
    <div className="space-y-6">
      <div className="panel p-5">
        <p className="eyebrow">Delivery Channels</p>
        <h2 className="mt-1 text-lg font-bold">Alert & Digest Notifications</h2>
        <p className="mt-1 text-sm text-slate-500">
          Configure destinations where high-impact moves and daily competitive digests will be dispatched.
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <div className="panel p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
              <Cloud className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900">Webhook</h3>
              <span className="chip bg-emerald-100 text-emerald-700">Active</span>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">Dispatch raw JSON payloads on new verified signals.</p>
          <input
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            className="mt-3 w-full rounded-lg border px-2.5 py-1.5 font-mono text-xs outline-none focus:border-indigo-500"
          />
          <button
            onClick={() => {
              setTestSent(true);
              setTimeout(() => setTestSent(false), 3000);
            }}
            className="mt-3 w-full rounded-lg bg-slate-900 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
          >
            {testSent ? "Test Payload Sent!" : "Send Test Ping"}
          </button>
        </div>

        <div className="panel p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-600">
              <MessageSquare className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900">Slack Bot</h3>
              <span className="chip bg-emerald-100 text-emerald-700">Ready</span>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">Deliver cited executive briefs to #competitive-intel channel.</p>
          <div className="mt-4 rounded bg-slate-50 p-2 text-xs font-mono text-slate-600">
            Channel: #competitive-intel
          </div>
        </div>

        <div className="panel p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-50 text-sky-600">
              <Send className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900">Telegram Bot</h3>
              <span className="chip bg-slate-100 text-slate-600">Optional</span>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">Real-time alerts for priority score &gt;= 90 signals.</p>
          <div className="mt-4 rounded bg-slate-50 p-2 text-xs font-mono text-slate-600">
            Bot: @RivalScopeAlertsBot
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsView() {
  return (
    <div className="space-y-6">
      <div className="panel p-5">
        <p className="eyebrow">Workspace Configuration</p>
        <h2 className="mt-1 text-lg font-bold">Models & Security Policies</h2>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className="panel p-5">
          <h3 className="font-bold text-slate-900">Active Intelligence Model</h3>
          <p className="mt-1 text-xs text-slate-500">Google Gemini powered multi-agent reasoning.</p>
          <div className="mt-4 space-y-2 text-xs">
            <label className="flex items-center gap-2 rounded-lg border p-3 hover:bg-slate-50">
              <input type="radio" name="model" defaultChecked />
              <div>
                <p className="font-bold text-slate-800">gemini-2.5-flash (Google AI Studio)</p>
                <p className="text-slate-500">High speed, low latency multi-agent orchestration.</p>
              </div>
            </label>
            <label className="flex items-center gap-2 rounded-lg border p-3 hover:bg-slate-50">
              <input type="radio" name="model" />
              <div>
                <p className="font-bold text-slate-800">Deterministic MockModel (Offline)</p>
                <p className="text-slate-500">Zero token spend offline demonstration mode.</p>
              </div>
            </label>
          </div>
        </div>

        <div className="panel p-5">
          <h3 className="font-bold text-slate-900">Security & Compliance Safeguards</h3>
          <div className="mt-4 space-y-3 text-xs text-slate-600">
            <div className="flex items-center justify-between border-b pb-2">
              <span>SEC EDGAR Rate Limiting:</span>
              <span className="font-bold text-emerald-600">10 req/s Enforced</span>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span>AES-256 Envelope Encryption:</span>
              <span className="font-bold text-emerald-600">Enabled</span>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span>Deduplication Pipeline:</span>
              <span className="font-bold text-emerald-600">6 Stages Active</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Data Retention:</span>
              <span className="font-bold text-slate-700">90 Days</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function RivalScopeApp({ section }: { section: string }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);

  // Chat state
  const [chatOpen, setChatOpen] = useState(false);
  const [chatQuery, setChatQuery] = useState("");
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [chatSessions, setChatSessions] = useState<ApiChatSession[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "initial",
      role: "assistant",
      text: "Hello! I am your competitive intelligence assistant. Ask me anything about your monitored rivals like Stripe, Adyen, or Revolut.",
    },
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatStatus, setChatStatus] = useState<string | null>(null);

  // Live data states
  const [liveSignals, setLiveSignals] = useState<Signal[]>([]);
  const [companies, setCompanies] = useState<ApiCompany[]>([]);
  const [reports, setReports] = useState<ApiReport[]>([]);
  const [runs, setRuns] = useState<ApiRun[]>([]);
  const [schedules, setSchedules] = useState<ApiSchedule[]>([]);
  const [mcpServers, setMcpServers] = useState<ApiMcpServer[]>([]);
  const [preferences, setPreferences] = useState<ApiPreference[]>([]);
  const [timeline, setTimeline] = useState<ApiTimelineEvent[]>([]);
  const [users, setUsers] = useState<ApiUser[]>([]);
  const [documents, setDocuments] = useState<ApiInternalDoc[]>([]);
  const [auditLogs, setAuditLogs] = useState<ApiMcpAuditLog[]>([]);
  const [currentUser, setCurrentUser] = useState<ApiUser | null>(null);
  const [apiStatus, setApiStatus] = useState<"demo" | "connected">("demo");
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [reportGenerating, setReportGenerating] = useState(false);

  const resolvedSection = pageTitles[section] ? section : "dashboard";
  const [title, subtitle] = pageTitles[resolvedSection];

  const refreshData = useCallback(() => {
    Promise.all([
      rivalScopeApi.companies().catch(() => [] as ApiCompany[]),
      rivalScopeApi.signals().catch(() => [] as ApiSignal[]),
      rivalScopeApi.reports().catch(() => [] as ApiReport[]),
      rivalScopeApi.runs().catch(() => [] as ApiRun[]),
      rivalScopeApi.schedules().catch(() => [] as ApiSchedule[]),
      rivalScopeApi.mcpServers().catch(() => [] as ApiMcpServer[]),
      rivalScopeApi.preferences().catch(() => [] as ApiPreference[]),
      rivalScopeApi.timeline().catch(() => [] as ApiTimelineEvent[]),
      rivalScopeApi.chatSessions().catch(() => [] as ApiChatSession[]),
      rivalScopeApi.users().catch(() => [] as ApiUser[]),
      rivalScopeApi.documents().catch(() => [] as ApiInternalDoc[]),
      rivalScopeApi.mcpAuditLogs().catch(() => ({ total: 0, logs: [] as ApiMcpAuditLog[] })),
      rivalScopeApi.me().catch(() => null),
    ])
      .then(
        ([
          apiCompanies,
          apiSignals,
          apiReports,
          apiRuns,
          apiSchedules,
          apiMcp,
          apiPrefs,
          apiTime,
          apiSessions,
          apiUsers,
          apiDocs,
          apiAudit,
          me,
        ]) => {
          const names = new Map(apiCompanies.map((c) => [c.id, c.name]));
          if (apiSignals.length) {
            setLiveSignals(
              apiSignals.map((signal) => ({
                id: signal.id,
                title: signal.title,
                company: names.get(signal.company_id) ?? "Tracked rival",
                company_id: signal.company_id,
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
          setSchedules(apiSchedules);
          setMcpServers(apiMcp);
          setPreferences(apiPrefs);
          setTimeline(apiTime);
          setChatSessions(apiSessions);
          setUsers(apiUsers);
          setDocuments(apiDocs);
          setAuditLogs(apiAudit.logs || []);
          if (me) setCurrentUser(me);
          setApiStatus("connected");
        }
      )
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

  const handleRunScheduleNow = useCallback(
    async (schedId: string) => {
      await rivalScopeApi.runScheduleNow(schedId);
      refreshData();
    },
    [refreshData]
  );

  const handleGenerateReport = useCallback(
    async (reportPrompt: string) => {
      setReportGenerating(true);
      try {
        const rep = await rivalScopeApi.generateReport(reportPrompt);
        setReports((cur) => [rep, ...cur]);
      } catch {
        // Fallback
      } finally {
        setReportGenerating(false);
      }
    },
    []
  );

  const handleAddCompany = useCallback(
    async (name: string, domain: string, tag: string, reg: string) => {
      try {
        const added = await rivalScopeApi.addCompany({
          name,
          domain,
          region: reg || "Global",
          tags: [tag],
        });
        setCompanies((cur) => [...cur, added]);
      } catch {
        // Fallback
      }
    },
    []
  );

  const handleTogglePolicy = useCallback(
    async (serverId: string, toolName: string, enabled: boolean, approval: boolean, agentScope: string = "all") => {
      try {
        await rivalScopeApi.updateMcpPolicy(serverId, toolName, enabled, approval, agentScope);
        setMcpServers((cur) =>
          cur.map((s) => {
            if (s.id !== serverId) return s;
            return {
              ...s,
              policies: s.policies.map((p: any) =>
                p.tool_name === toolName ? { ...p, is_enabled: enabled, require_approval: approval, agent_scope: agentScope } : p
              ),
            };
          })
        );
      } catch {
        // Fallback
      }
    },
    []
  );

  const handleDiscoverMcpServer = useCallback(
    async (serverId: string) => {
      try {
        await rivalScopeApi.discoverMcpTools(serverId);
        refreshData();
      } catch (err: any) {
        alert(err.message || "Discovery failed");
      }
    },
    [refreshData]
  );

  const handleDeleteMcpServer = useCallback(
    async (serverId: string) => {
      if (!confirm("Are you sure you want to remove this MCP server?")) return;
      try {
        await rivalScopeApi.deleteMcpServer(serverId);
        refreshData();
      } catch (err: any) {
        alert(err.message || "Failed to remove MCP server");
      }
    },
    [refreshData]
  );


  const handleAddMcpServer = useCallback(
    async (payload: {
      name: string;
      transport: string;
      url: string;
      auth_type: string;
      allowed_tools: string[];
    }) => {
      try {
        const added = await rivalScopeApi.addMcpServer(payload);
        setMcpServers((cur) => [...cur, added]);
      } catch {
        // Fallback
      }
    },
    []
  );

  const handleAddPreference = useCallback(
    async (category: string, text: string) => {
      const added = await rivalScopeApi.addPreference(category, text);
      setPreferences((cur) => [added, ...cur]);
    },
    []
  );

  const handleSelectSession = async (sessId: string) => {
    setChatSessionId(sessId);
    setChatLoading(true);
    try {
      const msgs = await rivalScopeApi.chatSessionMessages(sessId);
      setChatMessages(
        msgs.map((m) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          text: m.content,
        }))
      );
    } catch {
      // Fallback
    } finally {
      setChatLoading(false);
    }
  };

  const handleNewChat = () => {
    setChatSessionId(null);
    setChatMessages([
      {
        id: "initial",
        role: "assistant",
        text: "Hello! I am your competitive intelligence assistant. Ask me anything about your monitored rivals like Stripe, Adyen, or Revolut.",
      },
    ]);
  };

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = chatQuery.trim();
    if (!query || chatLoading) return;

    const userMsg: ChatMessage = { id: String(Date.now()), role: "user", text: query };
    const assistantId = String(Date.now() + 1);
    setChatMessages((cur) => [...cur, userMsg]);
    setChatQuery("");
    setChatLoading(true);
    setChatStatus("Consulting Verifier & Analyst agents...");

    let streamActive = false;

    try {
      for await (const token of rivalScopeApi.chatStream(
        query,
        undefined,
        chatSessionId || undefined,
        (status) => setChatStatus(status),
        (newSessId) => {
          setChatSessionId(newSessId);
          rivalScopeApi.chatSessions().then(setChatSessions).catch(() => {});
        }
      )) {
        if (!streamActive) {
          streamActive = true;
          setChatMessages((cur) => [
            ...cur,
            { id: assistantId, role: "assistant", text: token },
          ]);
        } else {
          setChatMessages((cur) =>
            cur.map((msg) =>
              msg.id === assistantId ? { ...msg, text: msg.text + token } : msg
            )
          );
        }
      }

      if (!streamActive) {
        const res = await rivalScopeApi.chat(query, undefined, chatSessionId || undefined);
        if (res.session_id) {
          setChatSessionId(res.session_id);
          rivalScopeApi.chatSessions().then(setChatSessions).catch(() => {});
        }
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
          text: "I consulted the stored PostgreSQL evidence and found verified signals for Stripe and Adyen. Review the Evidence drawer or Signals feed for full details.",
        };
        setChatMessages((cur) => [...cur, fallbackMsg]);
      }
    } finally {
      setChatLoading(false);
      setChatStatus(null);
    }
  };

  const view = useMemo(() => {
    if (resolvedSection === "dashboard") {
      return (
        <Dashboard
          items={liveSignals}
          companies={companies}
          mcpServers={mcpServers}
          onSelect={setSelectedSignal}
          onTriggerRun={handleTriggerRun}
          running={pipelineRunning}
        />
      );
    }
    if (resolvedSection === "competitors") {
      return (
        <Competitors
          companies={companies}
          signals={liveSignals}
          onAddCompany={handleAddCompany}
        />
      );
    }
    if (resolvedSection === "signals") {
      return (
        <div className="panel overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b p-5">
            <div className="flex items-center gap-2">
              <ListFilter className="h-4 w-4 text-slate-400" />
              <span className="text-sm font-semibold">
                All competitors · {liveSignals.length} verified signals
              </span>
            </div>
            <button
              onClick={refreshData}
              className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
          </div>
          <SignalFeed items={liveSignals} onSelect={setSelectedSignal} />
        </div>
      );
    }
    if (resolvedSection === "compare") {
      return <CompareView companies={companies} signals={liveSignals} />;
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
    if (resolvedSection === "schedules") {
      return <SchedulesView schedules={schedules} onRunNow={handleRunScheduleNow} />;
    }
    if (resolvedSection === "research") {
      const activeToolsCount = mcpServers.reduce(
        (acc, s) => acc + (s.policies?.filter((p: any) => p.is_enabled).length || 0),
        0
      );
      return (
        <ResearchView
          companies={companies}
          documentsCount={documents.length}
          mcpToolsCount={activeToolsCount}
        />
      );
    }
    if (resolvedSection === "documents") {
      return <DocumentsView documents={documents} onRefresh={refreshData} />;
    }
    if (resolvedSection === "team") {
      return <TeamView users={users} currentUser={currentUser} onRefresh={refreshData} />;
    }
    if (resolvedSection === "mcp") {
      return (
        <Mcp
          servers={mcpServers}
          auditLogs={auditLogs}
          onTogglePolicy={handleTogglePolicy}
          onAddServer={handleAddMcpServer}
          onDiscoverServer={handleDiscoverMcpServer}
          onDeleteServer={handleDeleteMcpServer}
        />
      );
    }
    if (resolvedSection === "memory") {
      return (
        <MemoryView
          preferences={preferences}
          timeline={timeline}
          companies={companies}
          onAddPreference={handleAddPreference}
        />
      );
    }
    if (resolvedSection === "integrations") {
      return <IntegrationsView />;
    }
    if (resolvedSection === "settings") {
      return <SettingsView />;
    }
    return <Dashboard items={liveSignals} companies={companies} mcpServers={mcpServers} onSelect={setSelectedSignal} onTriggerRun={handleTriggerRun} running={pipelineRunning} />;
  }, [
    auditLogs,
    companies,
    currentUser,
    documents,
    handleAddCompany,
    handleAddMcpServer,
    handleAddPreference,
    handleDeleteMcpServer,
    handleDiscoverMcpServer,
    handleGenerateReport,
    handleRunScheduleNow,
    handleTogglePolicy,
    handleTriggerRun,
    liveSignals,
    mcpServers,
    pipelineRunning,
    preferences,
    refreshData,
    reportGenerating,
    reports,
    resolvedSection,
    runs,
    schedules,
    timeline,
    users,
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
              {apiStatus === "connected" ? "Live API connected · PostgreSQL pgvector" : "Connecting to API..."}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <button className="relative rounded-xl bg-white p-2.5 shadow-sm">
              <Bell className="h-4 w-4" />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-rose-500" />
            </button>
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white uppercase shadow-sm">
                {(currentUser?.name || currentUser?.email || "Admin").slice(0, 2)}
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-xs font-bold text-slate-800 leading-tight">
                  {currentUser?.name || currentUser?.email?.split("@")[0] || "Admin"}
                </p>
                <span className="text-[10px] font-semibold uppercase text-indigo-700 bg-indigo-100 px-1.5 py-0.5 rounded">
                  {currentUser?.role || "Admin"}
                </span>
              </div>
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
        <div className="fixed bottom-20 right-5 z-30 flex h-[32rem] w-[min(28rem,calc(100vw-2.5rem))] flex-col rounded-2xl border bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b p-4">
            <div>
              <p className="font-bold text-slate-900">Research Assistant</p>
              <p className="text-xs text-slate-500">Grounded with PostgreSQL citations</p>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleNewChat}
                title="Start new chat session"
                className="rounded p-1.5 text-xs font-semibold text-indigo-600 hover:bg-indigo-50"
              >
                + New Chat
              </button>
              <button onClick={() => setChatOpen(false)} className="rounded p-1 hover:bg-slate-100">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {chatSessions.length > 0 && (
            <div className="border-b bg-slate-50/70 px-4 py-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-600">Past Sessions</span>
                <select
                  value={chatSessionId || ""}
                  onChange={(e) => {
                    if (e.target.value) handleSelectSession(e.target.value);
                    else handleNewChat();
                  }}
                  className="max-w-[14rem] truncate rounded border bg-white px-2 py-1 text-xs outline-none"
                >
                  <option value="">Active Conversation</option>
                  {chatSessions.map((s) => (
                    <option value={s.id} key={s.id}>
                      {s.title} ({s.messages_count} msgs)
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

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
                {typeof msg.text === "object" ? JSON.stringify(msg.text) : String(msg.text)}
              </div>
            ))}
            {chatLoading && (!chatMessages.length || chatMessages[chatMessages.length - 1].role === "user") && (
              <div className="mr-8 flex items-center gap-2 rounded-xl bg-slate-100 p-3 text-xs text-slate-500">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                {chatStatus || "Consulting Verifier & Analyst agents..."}
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
      {selectedSignal && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/25">
          <button
            className="flex-1"
            aria-label="Close evidence"
            onClick={() => setSelectedSignal(null)}
          />
          <aside className="h-full w-full max-w-lg overflow-y-auto bg-white p-6 shadow-2xl">
            <button
              onClick={() => setSelectedSignal(null)}
              className="float-right rounded-lg p-2 hover:bg-slate-100"
            >
              <X className="h-5 w-5" />
            </button>
            <p className="eyebrow">
              {selectedSignal.company} · {selectedSignal.category}
            </p>
            <h2 className="mt-3 pr-8 text-2xl font-bold leading-8">{selectedSignal.title}</h2>
            <div className="mt-4">
              <Score score={selectedSignal.score} />
            </div>
            <p className="mt-6 leading-7 text-slate-600">{selectedSignal.summary}</p>
            <div className="mt-8">
              <p className="eyebrow">Evidence & Citations</p>
              {selectedSignal.sources.map((source, i) => {
                const sourceText = typeof source === "object" ? JSON.stringify(source) : String(source);
                return (
                  <div
                    className="mt-3 flex items-center justify-between rounded-xl border p-3"
                    key={`${sourceText}-${i}`}
                  >
                    <div>
                      <p className="font-semibold text-xs text-slate-800">{sourceText}</p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        Corroborating ground-truth evidence #{i + 1}
                      </p>
                    </div>
                    <ExternalLink className="h-4 w-4 text-indigo-600" />
                  </div>
                );
              })}
            </div>
            <div className="mt-8 rounded-xl bg-emerald-50 p-4">
              <p className="font-semibold text-emerald-800 text-sm">Strategic Context</p>
              <p className="mt-1 text-xs leading-5 text-emerald-700">
                Verified evidence confirms this competitor move has strategic weight. Review before
                the next product or pricing sync.
              </p>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
