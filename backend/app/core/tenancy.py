"""Tenant context management and request isolation."""

from contextvars import ContextVar

from fastapi import Header, Request

# Context variable preserving tenant_id for the current task/request
current_tenant_var: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)


def set_current_tenant_id(tenant_id: str) -> None:
    """Set tenant ID for current execution context."""
    current_tenant_var.set(tenant_id)


def get_current_tenant_id() -> str | None:
    """Retrieve tenant ID for current execution context."""
    return current_tenant_var.get()


async def tenant_dependency(
    request: Request,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
) -> str:
    """
    Extract tenant_id from JWT state or X-Tenant-ID header.
    Defaults to 'default-tenant' for local dev and demos.
    """
    tenant_id = getattr(request.state, "tenant_id", None) or x_tenant_id or "default-tenant"
    set_current_tenant_id(tenant_id)
    return tenant_id
