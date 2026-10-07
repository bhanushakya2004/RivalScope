export type ApiCompany = {
  id: string;
  name: string;
  domain: string;
  ticker?: string | null;
  region: string;
  is_self: boolean;
  tags: string[];
  feeds: string[];
  created_at: string;
};

export type ApiSignal = {
  id: string;
  company_id: string;
  category: string;
  title: string;
  summary: string;
  event_date: string;
  confidence: number;
  importance_score: number;
  evidence_ids: string[];
  created_at: string;
};

export type ApiReport = {
  id: string;
  title: string;
  report_type: string;
  company_id?: string | null;
  summary: string;
  content: string;
  markdown?: string;
  period?: string;
  status: string;
  created_at: string;
};

export type ApiSchedule = {
  id: string;
  name: string;
  cron_expression?: string | null;
  interval_seconds?: number | null;
  enabled: boolean;
  scope: Record<string, unknown>;
  next_run_at?: string | null;
  last_run_at?: string | null;
};

export type ApiMcpServer = {
  id: string;
  name: string;
  transport: string;
  url?: string | null;
  auth_type: string;
  status: string;
  allowed_tools: string[];
  policies: { tool_name: string; is_enabled: boolean; require_approval: boolean }[];
  created_at: string;
};

export type ApiRun = {
  id: string;
  schedule_id?: string | null;
  run_type: string;
  status: string;
  tokens: number;
  duration_seconds: number;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
};

export type ApiChatMessage = {
  answer: string;
  competitor?: string | null;
  tenant_id: string;
};

export type ApiPreference = {
  id: string;
  category: string;
  text?: string;
  memory_text?: string;
  confidence?: number;
  updated_at?: string;
};

export type ApiTimelineEvent = {
  id: string;
  company_id?: string;
  category: string;
  title: string;
  event_date: string;
  details?: string | Record<string, unknown> | null;
};

export type ApiChatSession = {
  id: string;
  title: string;
  competitor_name?: string;
  created_at: string;
  updated_at: string;
  messages_count: number;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7777";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window === "undefined" ? null : localStorage.getItem("rivalscope_access_token");
  const response = await fetch(`${apiBaseUrl}/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export const rivalScopeApi = {
  companies: () => request<ApiCompany[]>("/companies"),
  addCompany: (payload: { name: string; domain: string; ticker?: string; region?: string; tags?: string[] }) =>
    request<ApiCompany>("/companies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  signals: () => request<ApiSignal[]>("/signals?limit=50"),
  reports: () => request<ApiReport[]>("/reports"),
  generateReport: (title: string, companyId?: string, reportType?: string) =>
    request<ApiReport>("/reports/generate", {
      method: "POST",
      body: JSON.stringify({ title, company_id: companyId, report_type: reportType ?? "daily_brief" }),
    }),
  schedules: () => request<ApiSchedule[]>("/schedules"),
  runScheduleNow: (scheduleId: string) =>
    request<unknown>(`/schedules/${scheduleId}/run-now`, {
      method: "POST",
    }),
  runs: () => request<ApiRun[]>("/runs"),
  triggerRun: (payload?: { company_id?: string; force_notify?: boolean }) =>
    request<ApiRun>("/runs/trigger", {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }),
  resumeRun: (runId: string, action: "approve" | "reject", comment?: string) =>
    request<{ status: string; run_id: string; message: string }>(`/runs/${runId}/resume`, {
      method: "POST",
      body: JSON.stringify({ action, comment }),
    }),
  mcpServers: () => request<ApiMcpServer[]>("/mcp-servers"),
  addMcpServer: (payload: {
    name: string;
    transport?: string;
    url?: string;
    auth_type?: string;
    allowed_tools?: string[];
  }) =>
    request<ApiMcpServer>("/mcp-servers", {
      method: "POST",
      body: JSON.stringify({
        transport: "streamable-http",
        auth_type: "bearer",
        allowed_tools: ["search_knowledge_base", "get_competitor_timeline", "get_company_signals"],
        ...payload,
      }),
    }),
  updateMcpPolicy: (serverId: string, toolName: string, isEnabled: boolean, requireApproval: boolean) =>
    request(`/mcp-servers/${serverId}/policies`, {
      method: "PATCH",
      body: JSON.stringify({ tool_name: toolName, is_enabled: isEnabled, require_approval: requireApproval }),
    }),
  preferences: () => request<ApiPreference[]>("/memory/preferences"),
  addPreference: (category: string, memoryText: string) =>
    request<ApiPreference>("/memory/preferences", {
      method: "POST",
      body: JSON.stringify({ category, memory_text: memoryText }),
    }),
  timeline: (companyId?: string) =>
    request<ApiTimelineEvent[]>(
      `/memory/timeline${companyId ? `?company_id=${companyId}` : ""}`
    ),
  chatSessions: () =>
    request<ApiChatSession[]>("/chat/sessions"),
  chatSessionMessages: (sessionId: string) =>
    request<Array<{ id: string; role: string; content: string; created_at: string }>>(
      `/chat/sessions/${sessionId}/messages`
    ),
  chat: (question: string, competitorName?: string, sessionId?: string) =>
    request<ApiChatMessage & { session_id?: string }>("/chat", {
      method: "POST",
      body: JSON.stringify({ question, competitor_name: competitorName, session_id: sessionId }),
    }),
  chatStream: async function* (
    question: string,
    competitorName?: string,
    sessionId?: string,
    onStatus?: (status: string) => void,
    onSession?: (sessionId: string) => void
  ): AsyncGenerator<string, void, unknown> {
    const token = typeof window === "undefined" ? null : localStorage.getItem("rivalscope_access_token");
    const response = await fetch(`${apiBaseUrl}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question, competitor_name: competitorName, session_id: sessionId }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`Chat stream failed (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      let currentEvent = "message";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.replace("event:", "").trim();
        } else if (trimmed.startsWith("data:")) {
          const dataStr = trimmed.replace("data:", "").trim();
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.session_id && onSession) {
              onSession(parsed.session_id);
            }
            if (currentEvent === "delta" && parsed.token) {
              yield parsed.token;
            } else if (parsed.token) {
              yield parsed.token;
            } else if (parsed.status && onStatus) {
              onStatus(parsed.status);
            }
          } catch {
            if (dataStr) yield dataStr;
          }
        }
      }
    }
  },
};

