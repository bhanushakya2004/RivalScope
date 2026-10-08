import uuid
import pytest
from app.core.errors import PermissionDeniedError, SSRFSecurityError
from app.db.models import McpAuditLog, McpPolicy, McpServer, Tenant
from app.db.session import SessionLocal
from app.mcp_gateway.client import McpClientPool
from app.mcp_gateway.policy import McpPolicyEngine
from app.mcp_gateway.ssrf import validate_target_url


def test_ssrf_validation():
    # Public URLs should validate safely
    res = validate_target_url("https://api.stripe.com/v1/health", allow_private_ips=False)
    assert "stripe.com" in res

    # Cloud metadata endpoints must be strictly blocked
    with pytest.raises(SSRFSecurityError):
        validate_target_url("http://169.254.169.254/latest/meta-data/", allow_private_ips=False)


def test_mcp_tool_discovery_and_disabled_by_default():
    db = SessionLocal()
    try:
        tenant = Tenant(name="Test MCP Tenant", slug=f"test-mcp-{uuid.uuid4().hex[:8]}")
        db.add(tenant)
        db.commit()


        server = McpServer(
            tenant_id=tenant.id,
            name="Finance MCP Connector",
            transport="streamable-http",
            url="http://mock-finance.internal/mcp",
            auth_type="bearer",
            status="healthy",
        )
        db.add(server)
        db.commit()

        pool = McpClientPool(db=db)
        discovered = pool.discover_server_tools(server=server, tenant_id=tenant.id)

        assert len(discovered) > 0
        tool_names = [t["name"] for t in discovered]
        assert "query_internal_financials" in tool_names

        # Uber-style disabled-by-default verification:
        # All newly discovered tools must have is_enabled=False in policy table
        policies = (
            db.query(McpPolicy)
            .filter(McpPolicy.tenant_id == tenant.id, McpPolicy.server_id == server.id)
            .all()
        )
        assert len(policies) > 0
        for pol in policies:
            assert pol.is_enabled is False, f"Tool {pol.tool_name} should be disabled by default"

        # Policy Engine allows tool only after explicit admin enablement
        engine = McpPolicyEngine(db=db)
        assert engine.is_tool_allowed(tenant.id, server.id, "query_internal_financials") is False

        # Enable the tool
        target_policy = next(p for p in policies if p.tool_name == "query_internal_financials")
        target_policy.is_enabled = True
        db.commit()
        engine.invalidate_policy(tenant.id)

        assert engine.is_tool_allowed(tenant.id, server.id, "query_internal_financials") is True

        # Execute tool and check audit log
        res = pool.execute_tool(
            tenant_id=tenant.id,
            server_id=server.id,
            tool_name="query_internal_financials",
            arguments={"quarter": "Q3-2026"},
        )
        assert res["status"] == "success"

        audit_entry = (
            db.query(McpAuditLog)
            .filter(
                McpAuditLog.tenant_id == tenant.id,
                McpAuditLog.tool_name == "query_internal_financials",
            )
            .first()
        )
        assert audit_entry is not None
        assert audit_entry.status == "success"

        # Cleanup
        db.query(McpAuditLog).filter(McpAuditLog.tenant_id == tenant.id).delete()
        db.query(McpPolicy).filter(McpPolicy.tenant_id == tenant.id).delete()
        db.delete(server)
        db.delete(tenant)
        db.commit()
    finally:
        db.close()
