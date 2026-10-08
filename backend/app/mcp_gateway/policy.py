"""MCP Policy Engine, Tool Classification, and Versioned Cache Keys."""

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import McpPolicy

logger = get_logger("mcp.policy")

# Mutating or write verbs that require Human-in-the-Loop (HITL) approval
WRITE_VERBS = [
    "create",
    "update",
    "delete",
    "insert",
    "drop",
    "post",
    "send",
    "modify",
    "patch",
    "trigger",
    "refund",
    "transfer",
]


class McpPolicyEngine:
    """Manages per-tool permissions, HITL classifications, and versioned callable keys."""

    def __init__(self, db: Session | None = None):
        self.db = db
        # tenant_id -> current policy version counter
        self._policy_versions: dict[str, int] = {}

    def get_policy_version(self, tenant_id: str) -> int:
        """Return the current policy version counter for the tenant."""
        return self._policy_versions.get(tenant_id, 1)

    def get_cache_key(self, tenant_id: str) -> str:
        """
        Generate callable-factory cache key = f"{tenant_id}:{policy_version}".
        Ensures immediate tool set invalidation when policies change.
        """
        version = self.get_policy_version(tenant_id)
        return f"{tenant_id}:{version}"

    def invalidate_policy(self, tenant_id: str) -> int:
        """Bump policy version counter to invalidate cached tool sets."""
        current = self.get_policy_version(tenant_id)
        new_version = current + 1
        self._policy_versions[tenant_id] = new_version
        logger.info(f"Invalidated tool policy for {tenant_id}; new version: {new_version}")
        return new_version

    def is_write_tool(self, tool_name: str) -> bool:
        """Classify if tool performs side-effects or mutations."""
        t_lower = tool_name.lower()
        return any(verb in t_lower for verb in WRITE_VERBS)

    def is_tool_allowed(
        self,
        tenant_id: str,
        server_id: str,
        tool_name: str,
    ) -> bool:
        """Check if tool is enabled for tenant."""
        if self.db is None:
            return True  # Dev default

        policy = (
            self.db.query(McpPolicy)
            .filter(
                McpPolicy.tenant_id == tenant_id,
                McpPolicy.server_id == server_id,
                McpPolicy.tool_name == tool_name,
            )
            .first()
        )
        if policy is None:
            # Deny by default until approved
            return False
        return policy.is_enabled

    def requires_hitl_approval(
        self,
        tenant_id: str,
        server_id: str,
        tool_name: str,
    ) -> bool:
        """Determine if tool invocation requires human approval before execution."""
        if self.is_write_tool(tool_name):
            return True

        if self.db is not None:
            policy = (
                self.db.query(McpPolicy)
                .filter(
                    McpPolicy.tenant_id == tenant_id,
                    McpPolicy.server_id == server_id,
                    McpPolicy.tool_name == tool_name,
                )
                .first()
            )
            if policy and policy.require_approval:
                return True

        return False

    def is_agent_allowed(
        self,
        tenant_id: str,
        server_id: str,
        tool_name: str,
        agent_name: str,
    ) -> bool:
        """Check if tool is authorized for specific agent system."""
        if self.db is None:
            return True
        policy = (
            self.db.query(McpPolicy)
            .filter(
                McpPolicy.tenant_id == tenant_id,
                McpPolicy.server_id == server_id,
                McpPolicy.tool_name == tool_name,
            )
            .first()
        )
        if policy is None or not policy.is_enabled:
            return False
        scope = getattr(policy, "agent_scope", "all") or "all"
        if scope in ["all", agent_name, "*"]:
            return True
        return False
