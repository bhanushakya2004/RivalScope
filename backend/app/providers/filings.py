"""Financial and regulatory filings providers: SEC EDGAR and Mock."""

from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.core.ratelimit import limiter
from app.providers.base import BaseFilingsProvider, IngestedItem

logger = get_logger("providers.filings")

# Known CIK lookup for major public fintechs
FINTECH_CIK_MAP: dict[str, str] = {
    "SQ": "0001512673",  # Block, Inc.
    "PYPL": "0001633917",  # PayPal Holdings
    "AFRM": "0001820953",  # Affirm Holdings
    "HOOD": "0001783879",  # Robinhood Markets
    "COIN": "0001679788",  # Coinbase Global
    "MQ": "0001522540",  # Marqeta
    "TOST": "0001650164",  # Toast, Inc.
}


class MockFilingsProvider(BaseFilingsProvider):
    """Deterministic offline filings provider for 10-K, 10-Q, 8-K regulatory analysis."""

    async def get_recent_filings(
        self,
        identifier: str,
        form_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[IngestedItem]:
        logger.info(f"[MockFilings] Retrieving offline filings for: {identifier}")
        now = datetime.now(UTC)
        ident = identifier.upper()

        items: list[IngestedItem] = [
            IngestedItem(
                url=f"https://www.sec.gov/Archives/edgar/data/{ident}/0001512673-26-000012/form8k.htm",
                title=f"{ident} Form 8-K Current Report: Executive Management & Product Organization Restructuring",
                content=(
                    f"Item 5.02: {ident} announced strategic organizational realignment focusing on enterprise "
                    "agentic commerce, embedding credit underwriting capabilities, and accelerating merchant acquisition. "
                    "Operating margins increased by 310 bps year-over-year."
                ),
                provider="mock_filings",
                published_at=now,
                raw_metadata={"form": "8-K", "cik": ident, "items": ["5.02", "8.01"]},
            ),
            IngestedItem(
                url=f"https://www.sec.gov/Archives/edgar/data/{ident}/0001512673-26-000004/form10q.htm",
                title=f"{ident} Form 10-Q Quarterly Report: Gross Payment Volume and Take-Rate Analysis",
                content=(
                    f"Financial Condition: For the quarter ended, {ident} processed $68.4 billion in Gross Payment Volume (GPV), "
                    "representing an 18% YoY growth. Blended net take-rate compressed by 4 bps to 2.82% due to enterprise volume mix. "
                    "Subscription and services-based revenue grew 29%."
                ),
                provider="mock_filings",
                published_at=now,
                raw_metadata={"form": "10-Q", "cik": ident, "gpv_billions": 68.4},
            ),
        ]

        if form_types:
            items = [item for item in items if item.raw_metadata.get("form") in form_types]

        return items[:limit]


class SecEdgarFilingsProvider(BaseFilingsProvider):
    """
    SEC EDGAR regulatory filing provider.
    Strictly complies with SEC EDGAR rules:
    - Declared User-Agent containing name and email contact.
    - Token-bucket rate limiting strictly under 10 req/s.
    """

    def __init__(self, user_agent: str | None = None):
        settings = get_settings()
        self.user_agent = user_agent or settings.sec_edgar_user_agent
        self.rate_limit_per_sec = settings.sec_edgar_rate_limit_per_second

    async def get_recent_filings(
        self,
        identifier: str,
        form_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[IngestedItem]:
        # Resolve ticker to CIK if available
        ident_clean = identifier.upper().strip()
        cik = FINTECH_CIK_MAP.get(ident_clean, ident_clean)

        # Pad CIK to 10 digits as required by SEC EDGAR submissions API
        cik_padded = cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }

        try:
            # Enforce strict rate limit throttle (max 8 req/s to keep safety margin under SEC's 10 req/s)
            await limiter.acquire_or_wait(
                "sec_edgar",
                max_requests=self.rate_limit_per_sec,
                window_seconds=1.0,
                max_wait_seconds=5.0,
            )

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            filings_data = data.get("filings", {}).get("recent", {})
            forms = filings_data.get("form", [])
            accession_numbers = filings_data.get("accessionNumber", [])
            primary_documents = filings_data.get("primaryDocument", [])
            filing_dates = filings_data.get("filingDate", [])
            report_dates = filings_data.get("reportDate", [])

            results: list[IngestedItem] = []
            for i in range(min(len(forms), 25)):
                form = forms[i]
                if form_types and form not in form_types:
                    continue

                accession = accession_numbers[i].replace("-", "")
                primary_doc = primary_documents[i]
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}"

                results.append(
                    IngestedItem(
                        url=doc_url,
                        title=f"{ident_clean} SEC Filing {form} ({filing_dates[i]})",
                        content=(
                            f"Official SEC Filing {form} filed by {ident_clean} on {filing_dates[i]}. "
                            f"Primary document: {primary_doc}. Accession Number: {accession_numbers[i]}."
                        ),
                        provider="sec_edgar",
                        published_at=datetime.now(UTC),
                        raw_metadata={
                            "form": form,
                            "accession_number": accession_numbers[i],
                            "filing_date": filing_dates[i],
                            "report_date": report_dates[i] if i < len(report_dates) else None,
                        },
                    )
                )

                if len(results) >= limit:
                    break

            return results
        except Exception as e:
            logger.error(
                f"SEC EDGAR fetch failed for {identifier}: {e}. Falling back to mock provider."
            )
            return await MockFilingsProvider().get_recent_filings(identifier, form_types, limit)
