"""MCP Servers and Gateway Policy management router."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.config import get_settings
from app.core.security import encrypt_secret
from app.db.models import McpAuditLog, McpPolicy, McpServer
from app.db.session import get_db
from app.mcp_gateway import McpClientPool, McpPolicyEngine, validate_target_url

router = APIRouter(prefix="/mcp-servers", tags=["MCP Gateway"])


class McpServerRegisterRequest(BaseModel):
    name: str
    transport: str = "streamable-http"  # streamable-http, sse, stdio
    url: str | None = None
    command: str | None = None
    auth_type: str = "bearer"  # bearer, oauth, none
    credentials: str | None = None
    allowed_tools: list[str] = Field(default_factory=list)


class PolicyUpdateRequest(BaseModel):
    tool_name: str
    is_enabled: bool
    require_approval: bool = False
    agent_scope: str = "all"  # all, internal_research, analyst
    description: str | None = None



@router.get("")
def list_mcp_servers(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    servers = db.query(McpServer).filter(McpServer.tenant_id == tenant_id).all()
    results = []
    for s in servers:
        policies = (
            db.query(McpPolicy)
            .filter(
                McpPolicy.tenant_id == tenant_id,
                McpPolicy.server_id == s.id,
            )
            .all()
        )
        results.append(
            {
                "id": s.id,
                "name": s.name,
                "transport": s.transport,
                "url": s.url,
                "auth_type": s.auth_type,
                "status": s.status,
                "allowed_tools": s.allowed_tools or [],
                "policies": [
                    {
                        "tool_name": p.tool_name,
                        "is_enabled": p.is_enabled,
                        "require_approval": p.require_approval,
                    }
                    for p in policies
                ],
                "created_at": s.created_at.isoformat(),
            }
        )
    return results


@router.post("", status_code=status.HTTP_201_CREATED)
def register_mcp_server(
    payload: McpServerRegisterRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    settings = get_settings()

    # 1. Transport & Stdio Validation
    if payload.transport == "stdio" and not settings.mcp_enable_stdio:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="stdio transport is disabled by security policy. Only administrators may enable stdio.",
        )

    # 2. SSRF URL Validation
    if payload.url:
        validate_target_url(payload.url, allow_private_ips=settings.mcp_allow_private_ips)

    # 3. Encrypt credentials at rest using AES-256-GCM
    encrypted_creds = (
        encrypt_secret(payload.credentials, tenant_salt=tenant_id) if payload.credentials else ""
    )

    server = McpServer(
        tenant_id=tenant_id,
        name=payload.name,
        transport=payload.transport,
        url=payload.url,
        command=payload.command,
        auth_type=payload.auth_type,
        encrypted_credentials=encrypted_creds,
        allowed_tools=payload.allowed_tools,
        status="healthy",
    )
    db.add(server)
    db.commit()
    db.refresh(server)

    # Initialize default policies for declared tools
    policy_engine = McpPolicyEngine(db=db)
    for tool_name in payload.allowed_tools:
        is_write = policy_engine.is_write_tool(tool_name)
        policy = McpPolicy(
            tenant_id=tenant_id,
            server_id=server.id,
            tool_name=tool_name,
            is_enabled=True,
            require_approval=is_write,  # Write tools require HITL by default
        )
        db.add(policy)

    policy_engine.invalidate_policy(tenant_id)
    db.commit()

    return {
        "id": server.id,
        "name": server.name,
        "transport": server.transport,
        "url": server.url,
        "status": server.status,
        "allowed_tools": server.allowed_tools,
    }


@router.post("/{server_id}/discover")
def discover_server_tools_endpoint(
    server_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Trigger JSON-RPC tool discovery on an MCP server.
    Newly discovered tools are initialized with 'disabled-by-default' policy.
    """
    _, tenant_id = user_and_tenant
    server = (
        db.query(McpServer)
        .filter(McpServer.tenant_id == tenant_id, McpServer.id == server_id)
        .first()
    )
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found")

    pool = McpClientPool(db=db)
    discovered = pool.discover_server_tools(server=server, tenant_id=tenant_id)

    return {
        "server_id": server.id,
        "server_name": server.name,
        "discovered_tools": discovered,
        "count": len(discovered),
        "status": server.status,
    }


@router.get("/catalog")
def get_mcp_catalog(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Returns full governance matrix of all registered servers and their tools,
    including enabled status, HITL approval gate, and agent scope.
    """
    _, tenant_id = user_and_tenant
    servers = db.query(McpServer).filter(McpServer.tenant_id == tenant_id).all()
    catalog = []

    for s in servers:
        policies = (
            db.query(McpPolicy)
            .filter(McpPolicy.tenant_id == tenant_id, McpPolicy.server_id == s.id)
            .all()
        )
        pol_map = {p.tool_name: p for p in policies}

        # Combine tools from discovered_tools and allowed_tools
        tools_list = s.discovered_tools or []
        known_tool_names = {t.get("name") for t in tools_list if isinstance(t, dict) and t.get("name")}
        for name in (s.allowed_tools or []):
            if name and name not in known_tool_names:
                tools_list.append({"name": name, "description": f"Tool {name}"})

        tool_entries = []
        for t in tools_list:
            t_name = t.get("name", "") if isinstance(t, dict) else str(t)
            pol = pol_map.get(t_name)
            tool_entries.append(
                {
                    "name": t_name,
                    "description": t.get("description", pol.description if pol else "") if isinstance(t, dict) else (pol.description if pol else ""),
                    "is_enabled": pol.is_enabled if pol else False,
                    "require_approval": pol.require_approval if pol else False,
                    "agent_scope": pol.agent_scope if pol else "all",
                }
            )

        catalog.append(
            {
                "server_id": s.id,
                "server_name": s.name,
                "transport": s.transport,
                "url": s.url,
                "status": s.status,
                "tools": tool_entries,
            }
        )

    return catalog


@router.get("/audit-logs")
def get_mcp_audit_logs(
    limit: int = 50,
    offset: int = 0,
    tool_name: str | None = None,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Retrieve tenant MCP execution audit logs."""
    _, tenant_id = user_and_tenant
    query = (
        db.query(McpAuditLog)
        .filter(McpAuditLog.tenant_id == tenant_id)
        .order_by(McpAuditLog.created_at.desc())
    )
    if tool_name:
        query = query.filter(McpAuditLog.tool_name == tool_name)

    total = query.count()
    records = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "logs": [
            {
                "id": r.id,
                "server_id": r.server_id,
                "tool_name": r.tool_name,
                "user_id": r.user_id,
                "arguments_json": r.arguments_json,
                "result_summary": r.result_summary,
                "duration_ms": round(r.duration_ms, 2),
                "status": r.status,
                "error": r.error,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    }


@router.patch("/{server_id}/policies")
def update_tool_policy(
    server_id: str,
    payload: PolicyUpdateRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    policy = (
        db.query(McpPolicy)
        .filter(
            McpPolicy.tenant_id == tenant_id,
            McpPolicy.server_id == server_id,
            McpPolicy.tool_name == payload.tool_name,
        )
        .first()
    )

    if not policy:
        policy = McpPolicy(
            tenant_id=tenant_id,
            server_id=server_id,
            tool_name=payload.tool_name,
            description=payload.description,
            is_enabled=payload.is_enabled,
            require_approval=payload.require_approval,
            agent_scope=payload.agent_scope,
        )
        db.add(policy)
    else:
        policy.is_enabled = payload.is_enabled
        policy.require_approval = payload.require_approval
        policy.agent_scope = payload.agent_scope
        if payload.description:
            policy.description = payload.description

    # Invalidate policy cache for tenant
    engine = McpPolicyEngine(db=db)
    engine.invalidate_policy(tenant_id)
    db.commit()

    return {
        "status": "updated",
        "tool_name": payload.tool_name,
        "is_enabled": policy.is_enabled,
        "require_approval": policy.require_approval,
        "agent_scope": policy.agent_scope,
    }


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mcp_server(
    server_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    server = (
        db.query(McpServer)
        .filter(McpServer.tenant_id == tenant_id, McpServer.id == server_id)
        .first()
    )
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found")

    # Invalidate cached policies
    engine = McpPolicyEngine(db=db)
    engine.invalidate_policy(tenant_id)

    db.delete(server)
    db.commit()
    return None

