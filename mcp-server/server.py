#!/usr/bin/env python3
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from tools.db import init_db
from tools.scraper import scrape_page as _scrape_page
from tools.search import search_proposals as _search_proposals
from tools.search import save_proposal as _save_proposal
from tools.search import get_proposals as _get_proposals

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("proposal-crawler")

DB_PATH = str(Path(__file__).parent.parent / "db" / "proposals.db")


@mcp.tool()
def initialize_database() -> str:
    try:
        init_db(DB_PATH)
        return f"Database initialized at {DB_PATH}"
    except Exception as e:
        return f"Failed to initialize database: {e}"


@mcp.tool()
async def scrape_page(url: str) -> dict:
    return await _scrape_page(url)


@mcp.tool()
def search_proposals(query: str, top_n: int = 5) -> list[dict]:
    return _search_proposals(query, top_n)


@mcp.tool()
def save_proposal(
    title: str,
    url: str,
    source: str,
    source_type: str,
    deadline: str = "",
    eligibility: str = "",
    field: str = "",
    amount: str = "",
    description: str = "",
) -> dict:
    proposal = {
        "title": title,
        "url": url,
        "source": source,
        "source_type": source_type,
        "deadline": deadline or None,
        "eligibility": eligibility or None,
        "field": field or None,
        "amount": amount or None,
        "description": description or None,
    }
    return _save_proposal(proposal)


@mcp.tool()
def get_proposals(source_type: str = "", limit: int = 20) -> list[dict]:
    st = source_type if source_type else None
    return _get_proposals(st, limit)


if __name__ == "__main__":
    mcp.run()
