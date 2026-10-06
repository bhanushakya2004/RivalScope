"""Tenant MCP Client Pool, stdio restrictions, and dynamic callable factory."""

import time
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import PermissionDeniedError
from app.core.logging import get_logger
from app.db.models import McpAuditLog, McpServer
from app.db.session import SessionLocal
from app.mcp_gateway.policy import McpPolicyEngine
from app.mcp_gateway.ssrf import validate_target_url

logger = get_logger("mcp.client")


class McpClientPool:
    """Manages connections to external tenant MCP servers."""

    def __init__(self, db: Session | None = None):
        self.db = db
        self.policy_engine = McpPolicyEngine(db=db)
        self.settings = get_settings()

    def validate_server_transport(self, server: McpServer) -> None:
        """Validate that transport conforms to security constraints."""
        transport = server.transport.lower()
        if transport == "stdio":
            if not self.settings.mcp_enable_stdio:
                raise PermissionDeniedError(
                    "stdio transport is disabled by security policy. Only administrators may enable stdio."
                )
        elif transport in ["streamable-http", "sse", "http"]:
            if server.url:
                validate_target_url(
                    server.url, allow_private_ips=self.settings.mcp_allow_private_ips
                )
        else:
            raise PermissionDeniedError(f"Unsupported MCP transport: {server.transport}")

    def execute_tool(
        self,
        tenant_id: str,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute an external tool with policy enforcement, HITL gating,
        output sanitization, and comprehensive audit logging.
        """
        session = self.db or SessionLocal()
        start_time = time.time()
        status_val = "success"
        error_msg = None
        result_text = ""

        try:
            # 1. Verify policy
            if not self.policy_engine.is_tool_allowed(tenant_id, server_id, tool_name):
                raise PermissionDeniedError(
                    f"Tool '{tool_name}' is disabled or not allowlisted for tenant"
                )

            # 2. Check HITL gating
            if self.policy_engine.requires_hitl_approval(tenant_id, server_id, tool_name):
                logger.info(f"Tool {tool_name} requires HITL approval; returning paused status")
                return {
                    "status": "approval_required",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "message": "Human approval required to execute mutating tool",
                }

            # 3. Simulate tool execution
            result_text = (
                f"Result from {tool_name} for tenant {tenant_id}: "
                f"Successfully processed args: {arguments}"
            )

            # 4. Cap output size to prevent prompt injection / context explosion
            max_chars = self.settings.mcp_max_tool_output_chars
            if len(result_text) > max_chars:
                result_text = result_text[:max_chars] + "\n[OUTPUT TRUNCATED BY SECURITY POLICY]"

            return {"status": "success", "output": result_text}

        except Exception as e:
            status_val = "failed"
            error_msg = str(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000.0
            audit = McpAuditLog(
                tenant_id=tenant_id,
                server_id=server_id,
                tool_name=tool_name,
                user_id=user_id,
                arguments_json=arguments,
                result_summary=result_text[:500] if result_text else None,
                duration_ms=duration_ms,
                status=status_val,
                error=error_msg,
            )
            session.add(audit)
            session.commit()
            if self.db is None:
                session.close()


def get_tenant_mcp_tools(
    tenant_id: str,
    db: Session | None = None,
) -> list[Callable]:
    """
    Dynamic callable tool factory returning tools registered to the authenticated tenant.
    Never accepts tenant_id as a tool argument from the LLM.
    """
    session = db or SessionLocal()
    pool = McpClientPool(db=session)
    tools = []

    try:
        servers = (
            session.query(McpServer)
            .filter(
                McpServer.tenant_id == tenant_id,
                McpServer.status == "healthy",
            )
            .all()
        )

        for srv in servers:
            pool.validate_server_transport(srv)
            allowed = srv.allowed_tools or []

            for t_name in allowed:
                # Create closure binding tenant_id and server.id
                def create_tool_callable(s_id: str, tool_n: str):
                    def mcp_dynamic_tool(**kwargs: Any) -> str:
                        """Dynamically injected tenant MCP tool."""
                        res = pool.execute_tool(
                            tenant_id=tenant_id,
                            server_id=s_id,
                            tool_name=tool_n,
                            arguments=kwargs,
                        )
                        return str(res.get("output", res.get("message", "")))

                    mcp_dynamic_tool.__name__ = f"mcp_{s_id}_{tool_n}"
                    mcp_dynamic_tool.__doc__ = f"Execute external MCP tool {tool_n}"
                    return mcp_dynamic_tool

                tools.append(create_tool_callable(srv.id, t_name))

        return tools
    finally:
        if db is None:
            session.close()
