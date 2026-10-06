"""Unit tests for MCP Gateway: SSRF defense, policy engine, stdio restrictions, and HITL."""

import pytest
from app.core.errors import PermissionDeniedError, SSRFSecurityError
from app.db.models import McpServer
from app.mcp_gateway import (
    McpClientPool,
    McpPolicyEngine,
    validate_target_url,
)


def test_ssrf_blocklist_ipv4_and_cloud_metadata():
    # Loopback & 0.0.0.0
    with pytest.raises(SSRFSecurityError):
        validate_target_url("http://127.0.0.1:8080/mcp")

    with pytest.raises(SSRFSecurityError):
        validate_target_url("http://0.0.0.0/mcp")

    # Cloud metadata (AWS/GCP/Azure)
    with pytest.raises(SSRFSecurityError):
        validate_target_url("http://169.254.169.254/latest/meta-data")

    # RFC 1918 Private Subnets
    with pytest.raises(SSRFSecurityError):
        validate_target_url("http://10.0.0.1/mcp")
    with pytest.raises(SSRFSecurityError):
        validate_target_url("http://192.168.1.50/mcp")
    with pytest.raises(SSRFSecurityError):
        validate_target_url("http://172.16.0.5/mcp")

    # CGNAT
    with pytest.raises(SSRFSecurityError):
        validate_target_url("http://100.64.0.1/mcp")


def test_stdio_disabled_by_default():
    pool = McpClientPool()
    server = McpServer(
        id="srv-stdio-test",
        tenant_id="t-test",
        name="Local Stdio Server",
        transport="stdio",
        command="npx -y @modelcontextprotocol/server-postgres",
    )
    with pytest.raises(PermissionDeniedError):
        pool.validate_server_transport(server)


def test_policy_cache_invalidation_and_versioning():
    engine = McpPolicyEngine()
    tenant_id = "tenant-fintech-1"

    key1 = engine.get_cache_key(tenant_id)
    assert key1 == f"{tenant_id}:1"

    new_version = engine.invalidate_policy(tenant_id)
    assert new_version == 2

    key2 = engine.get_cache_key(tenant_id)
    assert key2 == f"{tenant_id}:2"
    assert key1 != key2


def test_write_tool_hitl_classification():
    engine = McpPolicyEngine()
    assert engine.is_write_tool("create_jira_issue") is True
    assert engine.is_write_tool("refund_transaction") is True
    assert engine.is_write_tool("delete_customer") is True
    assert engine.is_write_tool("lookup_customer_pipeline") is False
    assert engine.is_write_tool("get_competitor_timeline") is False
