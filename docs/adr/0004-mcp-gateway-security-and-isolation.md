# ADR 0004: MCP Gateway Security, Tenant Isolation, and Tool Policy Governance

## Status
Accepted

## Context
RivalScope allows enterprise users to connect third-party Model Context Protocol (MCP) servers (e.g. internal CRMs, data warehouses, Jira, Slack) to enrich competitive intelligence with proprietary internal context.

Connecting external MCP servers introduces critical security risks:
1. **Server-Side Request Forgery (SSRF)**: Malicious users or compromised servers targeting internal infrastructure, cloud metadata endpoints (`169.254.169.254`), or private databases.
2. **Cross-Tenant Data Leakage**: Tools or credentials from Tenant A being invoked by Tenant B's agents.
3. **Prompt Injection & Autonomous Actions**: Malicious instructions embedded in competitor web pages tricking an agent into invoking external write/mutation tools on internal systems.
4. **Credential Exposure**: Plaintext storage of MCP bearer tokens or API keys.

## Decision
We enforce a comprehensive security architecture for the MCP Gateway (`app/mcp_gateway/`):

1. **Strict SSRF Firewall & DNS Resolution**:
   - Outbound connections from the gateway must resolve IP addresses before connecting.
   - Block loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`), and private RFC1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) unless explicitly allowed via `MCP_ALLOW_PRIVATE_IPS=true` in development.
   - Restrict transports: `streamable-http` and `sse` enabled by default; `stdio` is disabled by default and restricted to system administrators.

2. **Tenant Scoping & Dynamic Injection**:
   - External MCP connections are keyed strictly by `(tenant_id, server_id)`.
   - Tools are injected into Agno agents at runtime using Agno callable factories:
     `Team(tools=lambda run_context: get_tenant_mcp_tools(run_context.user_id))`
   - Ensures agents only have access to tools registered and approved by their owning organization.

3. **Envelope Encryption for Credentials at Rest**:
   - Credentials (API tokens, OAuth refresh tokens, headers) are encrypted at rest using AES-256-GCM.
   - Key derivation utilizes PBKDF2/HKDF with tenant salt and an application master key configurable via KMS / environment variables.

4. **Granular Per-Tool Policies & Guardrails**:
   - Tool Allowlisting: Discovered tools from an MCP server are disabled by default until an administrator explicitly enables them in the UI.
   - Read vs Write Classification: Any tool tagged as mutating or write-capable requires Human-in-the-Loop (HITL) approval via Agno `continue_run` or is blocked entirely in autonomous cron runs.
   - Output Sanitization & Prompt Injection Shielding: MCP tool outputs are wrapped in untrusted data delimiters and capped at 50,000 characters to prevent context-window exhaustion and prompt injection.

5. **Complete Audit Trail**:
   - Every MCP tool call is recorded in `mcp_audit_logs` with timestamp, tenant_id, user_id, tool_name, parameters, status, duration, and response token count.

## Consequences
- **Positive**: Enterprise-ready security posture, complete tenant isolation, defense against prompt-injection and SSRF.
- **Negative**: Slight connection overhead on initial tool discovery and envelope decryption.
