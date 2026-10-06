"""FastAPI dependencies for authentication, tenancy, and database sessions."""

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import decode_access_token
from app.core.tenancy import set_current_tenant_id
from app.db.models import User
from app.db.session import get_db

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user_and_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
) -> tuple[User, str]:
    """
    Authenticate user via JWT Bearer token or provide seeded demo user in mock/dev mode.
    Derives tenant strictly from authenticated context.
    """
    settings = get_settings()

    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")

            if not user_id or not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token claims",
                )

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            set_current_tenant_id(tenant_id)
            return user, tenant_id

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}",
            ) from e

    # Fallback to seeded demo user in dev/test/mock mode
    if settings.debug or settings.mock_providers or settings.env in ["development", "test"]:
        demo_user = db.query(User).filter(User.email == "admin@paypulse.io").first()
        if demo_user:
            set_current_tenant_id(demo_user.tenant_id)
            return demo_user, demo_user.tenant_id

        # If database not seeded yet, create ephemeral tenant
        ephemeral_tenant_id = x_tenant_id or "t-paypulse-demo"
        set_current_tenant_id(ephemeral_tenant_id)
        mock_user = User(
            id="u-demo",
            tenant_id=ephemeral_tenant_id,
            email="admin@paypulse.io",
            role="admin",
            is_active=True,
        )
        return mock_user, ephemeral_tenant_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization header required",
    )
