"""Stage 5: Event-Level Clustering and Corroboration Engine."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ClusterCitation(BaseModel):
    """Citation record for an evidence source in a cluster."""

    url: str
    title: str
    provider: str
    published_at: datetime


class CorroboratedCluster(BaseModel):
    """Event-level cluster agglomerating multi-source evidence."""

    id: str
    tenant_id: str
    company_id: str
    company_name: str
    title: str
    summary: str
    category: str
    corroboration_count: int = 1
    confidence: float = 0.85
    citations: list[ClusterCitation] = Field(default_factory=list)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventClusterEngine:
    """Manages event-level cluster formation and corroboration scoring."""

    def __init__(self):
        # In-memory cluster store: tenant_id -> Dict of cluster_id -> CorroboratedCluster
        self._clusters: dict[str, dict[str, CorroboratedCluster]] = {}

    def add_to_cluster(
        self,
        cluster_id: str,
        citation: ClusterCitation,
    ) -> CorroboratedCluster:
        """Add corroborating evidence citation to an existing cluster."""
        for tenant_clusters in self._clusters.values():
            if cluster_id in tenant_clusters:
                cl = tenant_clusters[cluster_id]
                cl.corroboration_count += 1
                cl.citations.append(citation)
                cl.last_seen_at = citation.published_at
                # Increase confidence with additional distinct corroborating sources
                cl.confidence = min(0.99, 0.85 + (cl.corroboration_count - 1) * 0.06)
                return cl
        raise KeyError(f"Cluster with ID {cluster_id} not found")

    def create_cluster(
        self,
        cluster_id: str,
        tenant_id: str,
        company_id: str,
        company_name: str,
        title: str,
        summary: str,
        category: str,
        citation: ClusterCitation,
    ) -> CorroboratedCluster:
        """Create new event cluster for unique signal."""
        if tenant_id not in self._clusters:
            self._clusters[tenant_id] = {}

        cluster = CorroboratedCluster(
            id=cluster_id,
            tenant_id=tenant_id,
            company_id=company_id,
            company_name=company_name,
            title=title,
            summary=summary,
            category=category,
            corroboration_count=1,
            confidence=0.88,
            citations=[citation],
            first_seen_at=citation.published_at,
            last_seen_at=citation.published_at,
        )
        self._clusters[tenant_id][cluster_id] = cluster
        return cluster

    def get_cluster(self, tenant_id: str, cluster_id: str) -> CorroboratedCluster | None:
        """Retrieve cluster by ID."""
        return self._clusters.get(tenant_id, {}).get(cluster_id)
