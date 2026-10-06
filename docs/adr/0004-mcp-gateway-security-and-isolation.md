# ADR 0004: MCP Gateway Security, Tenant Isolation, and Tool Policy Governance

## Status
Accepted

## Context
RivalScope allows enterprise users to connect third-party Model Context Protocol (MCP) servers (e.g. internal CRMs, data warehouses, Jira, Slack) to enrich competitive intelligence with proprietary internal context.

Connecting external MCP servers introduces critical security risks:
1. **Server-Side Request Forgery (SSRF)**: Malicious users or compromised servers targeting internal infrastructure, cloud metadata endpoints (`169.254.169.254`), or private databases.
2. **Cross-Tenant Data Leakage**: Tools or credentials from Tenant A being invoked by Tenant B's agents, or prompt injection manipulating tool parameters to access another tenant's data.
3. **Prompt Injection & Autonomous Actions**: Malicious instructions embedded in competitor web pages tricking an agent into invoking external write/mutation tools on internal systems.
4. **Credential Exposure**: Plaintext storage of MCP bearer tokens or API keys.

## Decision
We enforce a comprehensive security architecture for the MCP Gateway (`app/mcp_gateway/`):

1. **Strict SSRF Firewall, DNS Resolution & Redirect Controls**:
   - **Outbound IP Blocklist**:
     - IPv4 Loopback & Special: `0.0.0.0/8`, `127.0.0.0/8`
     - Private RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
     - Link-Local / Cloud Metadata: `169.254.0.0/16`
     - Carrier-Grade NAT (CGNAT): `100.64.0.0/10`
     - IPv6 Loopback & Local: `::1/128`, `fc00::/7` (Unique Local), `fe80::/10` (Link-Local), `::ffff:0:0/96` (IPv4-mapped)
   - **DNS Re-resolution at Connect Time**: To defeat DNS rebinding (Time-of-Check to Time-of-Use / TOCTOU attacks), the IP address is re-resolved and validated immediately prior to opening the TCP socket/HTTP request.
   - **No Blind Redirects**: HTTP 3xx redirects do not automatically follow target URLs. Every redirect target is intercepted, parsed, and passed through the SSRF IP validator before a new connection is initiated.
   - **Transport Hardening**: `streamable-http` is supported by default. `stdio` transport is **disabled by default and restricted exclusively to system administrators** via configuration flag (`MCP_ENABLE_STDIO=false`).

2. **Tenant Scoping & Authentication Security**:
   - External MCP connections are keyed strictly by `(tenant_id, server_id)`.
   - **OAuth (`mcp_auth`)**: Hosted connectors authenticate via OAuth 2.0 bearer tokens.
   - **No Tenant Parameter in Tools**: The tenant context is **strictly derived from the authenticated JWT claims / `user_id`**, never from an agent-generated or caller-supplied tool parameter. This prevents prompt injection attacks from attempting cross-tenant parameter spoofing.

3. **Callable Factory Caching & Policy Invalidation**:
   - Dynamic tool injection into Agno agents uses callable factories.
   - To guarantee that tool policy updates, permission revocations, or role changes take effect immediately, the callable cache key is formatted as:
     `f"{tenant_id}:{policy_version}"`
   - Setting `cache_callables=False` is also supported for zero-cache environments.

4. **Envelope Encryption for Credentials at Rest**:
   - Credentials (API tokens, OAuth refresh tokens, headers) are encrypted at rest using AES-256-GCM.
   - Key derivation utilizes PBKDF2/HKDF with tenant salt and an application master key configurable via KMS / environment variables.

5. **Granular Per-Tool Policies & Human-in-the-Loop (HITL)**:
   - Tool Allowlisting: Discovered tools from an MCP server are disabled by default until an administrator explicitly enables them in the UI.
   - Read vs Write Classification: Any tool tagged as mutating or write-capable requires Human-in-the-Loop (HITL) approval via Agno `continue_run` or is blocked entirely in autonomous cron runs.
   - Output Sanitization & Prompt Injection Shielding: MCP tool outputs are wrapped in untrusted data delimiters and capped at 50,000 characters to prevent context-window exhaustion and prompt injection.

6. **Complete Audit Trail**:
   - Every MCP tool call is recorded in `mcp_audit_logs` with timestamp, tenant_id, user_id, tool_name, parameters, status, duration, and response token count.

## Consequences
- **Positive**: Hardened against SSRF, DNS rebinding, and prompt injection parameter manipulation; immediate policy invalidation; strict tenant isolation.
- **Negative**: Adds validation latency on outbound requests and requires managing policy version counters.
