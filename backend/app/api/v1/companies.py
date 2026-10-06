"""Competitor companies and monitored sources router."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.db.models import Company
from app.db.session import get_db

router = APIRouter(prefix="/companies", tags=["Companies"])


class CompanyCreateRequest(BaseModel):
    name: str
    domain: str
    ticker: str | None = None
    region: str = "US"
    is_self: bool = False
    tags: list[str] = Field(default_factory=list)
    feeds: list[str] = Field(default_factory=list)


class CompanyResponse(BaseModel):
    id: str
    name: str
    domain: str
    ticker: str | None = None
    region: str
    is_self: bool
    tags: list[str]
    feeds: list[str]
    created_at: str


@router.get("", response_model=list[CompanyResponse])
def list_companies(
    is_self: bool | None = None,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    query = db.query(Company).filter(Company.tenant_id == tenant_id)
    if is_self is not None:
        query = query.filter(Company.is_self == is_self)

    companies = query.all()
    return [
        CompanyResponse(
            id=c.id,
            name=c.name,
            domain=c.domain,
            ticker=c.ticker,
            region=c.region,
            is_self=c.is_self,
            tags=c.tags or [],
            feeds=c.feeds or [],
            created_at=c.created_at.isoformat(),
        )
        for c in companies
    ]


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreateRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    company = Company(
        tenant_id=tenant_id,
        name=payload.name,
        domain=payload.domain,
        ticker=payload.ticker,
        region=payload.region,
        is_self=payload.is_self,
        tags=payload.tags,
        feeds=payload.feeds,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    return CompanyResponse(
        id=company.id,
        name=company.name,
        domain=company.domain,
        ticker=company.ticker,
        region=company.region,
        is_self=company.is_self,
        tags=company.tags or [],
        feeds=company.feeds or [],
        created_at=company.created_at.isoformat(),
    )


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    c = db.query(Company).filter(Company.id == company_id, Company.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    return CompanyResponse(
        id=c.id,
        name=c.name,
        domain=c.domain,
        ticker=c.ticker,
        region=c.region,
        is_self=c.is_self,
        tags=c.tags or [],
        feeds=c.feeds or [],
        created_at=c.created_at.isoformat(),
    )


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    _, tenant_id = user_and_tenant
    c = db.query(Company).filter(Company.id == company_id, Company.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    db.delete(c)
    db.commit()
