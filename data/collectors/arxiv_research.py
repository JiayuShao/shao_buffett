"""arXiv quantitative finance research paper collector."""

import xml.etree.ElementTree as ET
from typing import Any
import structlog
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter

log = structlog.get_logger(__name__)

BASE_URL = "http://export.arxiv.org/api/query"

# arXiv categories for quantitative finance
QFIN_CATEGORIES = [
    "q-fin.CP",  # Computational Finance
    "q-fin.GN",  # General Finance
    "q-fin.MF",  # Mathematical Finance
    "q-fin.PM",  # Portfolio Management
    "q-fin.PR",  # Pricing of Securities
    "q-fin.RM",  # Risk Management
    "q-fin.ST",  # Statistical Finance
    "q-fin.TR",  # Trading and Market Microstructure
]

# arXiv categories for AI/ML research
AI_CATEGORIES = [
    "cs.AI",   # Artificial Intelligence
    "cs.LG",   # Machine Learning
    "cs.CL",   # Computation and Language (NLP)
    "cs.CV",   # Computer Vision
    "cs.NE",   # Neural and Evolutionary Computing
]


class ArxivCollector(BaseCollector):
    api_name = "arxiv"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)

    async def health_check(self) -> bool:
        try:
            session = await self.get_session()
            await self.rate_limiter.acquire(self.api_name)
            async with session.get(BASE_URL, params={"search_query": "cat:q-fin.GN", "max_results": "1"}) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def search_papers(
        self,
        query: str | None = None,
        categories: list[str] | None = None,
        max_results: int = 10,
        sort_by: str = "submittedDate",
    ) -> list[dict[str, Any]]:
        """Search arXiv for quantitative finance papers."""
        search_parts = []
        if query:
            search_parts.append(f"all:{query}")
        if categories:
            cat_query = " OR ".join(f"cat:{c}" for c in categories)
            search_parts.append(f"({cat_query})")
        else:
            cat_query = " OR ".join(f"cat:{c}" for c in QFIN_CATEGORIES)
            search_parts.append(f"({cat_query})")

        search_query = " AND ".join(search_parts) if search_parts else "cat:q-fin.GN"

        await self.rate_limiter.acquire(self.api_name)
        session = await self.get_session()
        async with session.get(
            BASE_URL,
            params={
                "search_query": search_query,
                "max_results": str(max_results),
                "sortBy": sort_by,
                "sortOrder": "descending",
            },
        ) as resp:
            text = await resp.text()

        return self._parse_atom_feed(text)

    async def get_recent_papers(self, max_results: int = 20) -> list[dict[str, Any]]:
        """Get the most recent q-fin papers."""
        return await self.search_papers(max_results=max_results)

    async def search_ai_finance(self, max_results: int = 10) -> list[dict[str, Any]]:
        """Search for AI/ML in finance papers."""
        return await self.search_papers(
            query="machine learning OR deep learning OR artificial intelligence",
            max_results=max_results,
        )

    async def search_ai_research(
        self, query: str | None = None, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search for AI/ML research papers across core AI categories."""
        return await self.search_papers(
            query=query,
            categories=AI_CATEGORIES,
            max_results=max_results,
        )

    def _parse_atom_feed(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse arXiv Atom feed into structured data."""
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        papers = []

        try:
            root = ET.fromstring(xml_text)
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
                summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
                published = entry.findtext("atom:published", "", ns)
                arxiv_id = entry.findtext("atom:id", "", ns)

                authors = [
                    a.findtext("atom:name", "", ns)
                    for a in entry.findall("atom:author", ns)
                ]

                categories = [
                    c.get("term", "")
                    for c in entry.findall("atom:category", ns)
                ]

                pdf_link = ""
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "pdf":
                        pdf_link = link.get("href", "")
                        break

                papers.append({
                    "title": title,
                    "summary": summary,
                    "authors": authors,
                    "published": published,
                    "arxiv_id": arxiv_id,
                    "pdf_url": pdf_link,
                    "categories": categories,
                })
        except ET.ParseError as e:
            log.error("arxiv_parse_error", error=str(e))

        return papers
