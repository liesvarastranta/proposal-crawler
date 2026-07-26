# Implementation Plan: Proposal Funding Crawler — Phase 1

> **Branch:** feature/mcp-server  
> **Status:** Not started  
> **Date:** 2025-07-25

## Goal
Build standalone MCP server (Python) with 3 tools: scrape_page, search_proposals, save_proposal. Crawl4AI primary scraper, Firecrawl fallback. SQLite FTS5 for BM25 search + dedup.

## Architecture (3 tools only — YAGNI)

```
┌─────────────────────────────────┐
│       MCP Server (Python)       │
│                                 │
│  Tool 1: scrape_page            │
│    Crawl4AI → fallback Firecrawl│
│                                 │
│  Tool 2: search_proposals       │
│    SQLite FTS5 BM25             │
│                                 │
│  Tool 3: save_proposal          │
│    hash dedup → BM25 dedup      │
│    → INSERT                     │
└─────────────────────────────────┘
```

---

## Task 1: Database Schema

**Files:** `db/schema.sql` (create)

**Verification:**
```bash
cat db/schema.sql | wc -l  # should be > 30 lines
```

### Code

```sql
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    deadline TEXT,
    eligibility TEXT,
    field TEXT,
    amount TEXT,
    url TEXT NOT NULL UNIQUE,
    description TEXT,
    discovered_at TEXT DEFAULT (datetime('now', 'localtime')),
    content_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    base_url TEXT NOT NULL,
    last_checked TEXT,
    status TEXT DEFAULT 'active'
);

CREATE VIRTUAL TABLE IF NOT EXISTS proposals_fts USING fts5(
    title,
    description,
    field,
    content='proposals',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS proposals_ai AFTER INSERT ON proposals BEGIN
    INSERT INTO proposals_fts(rowid, title, description, field)
    VALUES (new.id, new.title, new.description, new.field);
END;

CREATE TRIGGER IF NOT EXISTS proposals_ad AFTER DELETE ON proposals BEGIN
    INSERT INTO proposals_fts(proposals_fts, rowid, title, description, field)
    VALUES ('delete', old.id, old.title, old.description, old.field);
END;

CREATE TRIGGER IF NOT EXISTS proposals_au AFTER UPDATE ON proposals BEGIN
    INSERT INTO proposals_fts(proposals_fts, rowid, title, description, field)
    VALUES ('delete', old.id, old.title, old.description, old.field);
    INSERT INTO proposals_fts(rowid, title, description, field)
    VALUES (new.id, new.title, new.description, new.field);
END;

INSERT OR IGNORE INTO sources (name, type, base_url) VALUES
    ('BRIN', 'kementerian', 'https://brin.go.id'),
    ('LPDP', 'kementerian', 'https://lpdp.kemenkeu.go.id'),
    ('Kemendikbud', 'kementerian', 'https://kemdikbud.go.id');
```

---

## Task 2: Sources Configuration

**Files:** `config/sources.yaml` (create)

**Verification:**
```bash
python3 -c "import yaml; d=yaml.safe_load(open('config/sources.yaml')); print(len(d['sources']), 'sources')"
```
Expected: `3 sources`

### Code

```yaml
sources:
  - name: BRIN
    type: kementerian
    base_url: "https://brin.go.id"
    search_queries:
      - "BRIN pendanaan riset proposal 2025 2026"
      - "BRIN hibah penelitian skema pendanaan"
      - "BRIN call for proposal research grant"
    crawl_policy:
      max_pages: 10
      delay_seconds: 2
      timeout_seconds: 30
      max_retries: 3
      user_agents:
        - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0"
        - "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/148.0.0.0"
    extraction:
      title_selector: "h1, h2.entry-title, .post-title"
      content_selector: "article, .entry-content, .post-content, main"

  - name: LPDP
    type: kementerian
    base_url: "https://lpdp.kemenkeu.go.id"
    search_queries:
      - "LPDP pendanaan riset 2025 2026"
      - "LPDP beasiswa riset proposal penelitian"
    crawl_policy:
      max_pages: 10
      delay_seconds: 2
      timeout_seconds: 30
      max_retries: 3
      user_agents: []
    extraction:
      title_selector: "h1, h2.entry-title, .post-title"
      content_selector: "article, .entry-content, .post-content, main"

  - name: Kemendikbud
    type: kementerian
    base_url: "https://kemdikbud.go.id"
    search_queries:
      - "Kemendikbud matching fund proposal penelitian 2025"
      - "Kemendikbud hibah riset universitas politeknik"
      - "kedaireka pendanaan riset 2025 2026"
    crawl_policy:
      max_pages: 10
      delay_seconds: 2
      timeout_seconds: 30
      max_retries: 3
      user_agents: []
    extraction:
      title_selector: "h1, h2.entry-title, .post-title"
      content_selector: "article, .entry-content, .post-content, main"

default_policy:
  max_pages: 10
  delay_seconds: 2
  timeout_seconds: 30
  max_retries: 3
  user_agents:
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0"
    - "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/148.0.0.0"
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

skip_patterns:
  - "captcha"
  - "login"
  - "signin"
  - "daftar"
  - "register"
```

---

## Task 3: Database Helper

**Files:** `mcp-server/tools/db.py` (create)

**Verification:**
```bash
cd mcp-server && .venv/bin/python -c "
from tools.db import init_db
db = init_db('/tmp/test_proposals.db')
tables = db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
for t in tables: print(t['name'])
"
```
Expected: `proposals`, `sources`, `proposals_fts` listed

### Code

```python
import sqlite3
from pathlib import Path

_connection: sqlite3.Connection | None = None

SCHEMA_PATH = Path(__file__).parent.parent.parent / "db" / "schema.sql"


def init_db(db_path: str) -> sqlite3.Connection:
    global _connection
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)
    conn.commit()
    _connection = conn
    return conn


def get_db() -> sqlite3.Connection:
    if _connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _connection
```

---

## Task 4: Scraper Tool

**Files:** `mcp-server/tools/scraper.py` (create)

**Verification:**
```bash
cd mcp-server && .venv/bin/python -c "from tools import scraper; print('import OK')"
```
Expected: `import OK`

### Code

```python
import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).parent.parent.parent / "config" / "sources.yaml"


def _load_sources_config() -> dict:
    return yaml.safe_load(SOURCES_PATH.read_text())


async def scrape_page(url: str) -> dict:
    config = _load_sources_config()
    policy = config.get("default_policy", {})

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

        async with AsyncWebCrawler() as crawler:
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=policy.get("timeout_seconds", 30000),
                word_count_threshold=10,
            )
            result = await crawler.arun(url=url, config=crawl_config)

            if result.success and result.markdown:
                return {
                    "success": True,
                    "url": url,
                    "markdown": result.markdown[:10000],
                    "error": None,
                    "engine": "crawl4ai",
                }
            raise RuntimeError(result.error_message or "Crawl4AI returned empty content")
    except Exception as e:
        logger.warning("Crawl4AI failed for %s: %s", url, e)

    try:
        from firecrawl import Firecrawl

        fc = Firecrawl()
        result = fc.scrape_url(url, params={"formats": ["markdown"]})

        return {
            "success": True,
            "url": url,
            "markdown": result.get("markdown", "")[:10000],
            "error": None,
            "engine": "firecrawl",
        }
    except Exception as e:
        logger.error("Firecrawl also failed for %s: %s", url, e)
        return {
            "success": False,
            "url": url,
            "markdown": "",
            "error": str(e),
            "engine": None,
        }


def check_robotstxt(url: str) -> bool:
    from urllib.robotparser import RobotFileParser

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp.can_fetch("*", url)
    except Exception:
        return True


def hash_content(title: str, url: str) -> str:
    return hashlib.sha256(f"{title}{url}".encode()).hexdigest()
```

---

## Task 5: Search Tool (BM25)

**Files:** `mcp-server/tools/search.py` (create)

**Verification:**
```bash
cd mcp-server && .venv/bin/python -c "
from tools.db import init_db
from tools.search import save_proposal, search_proposals, check_duplicate
import os, tempfile
f = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = f.name; f.close()
init_db(db_path)
r = save_proposal({'title':'Test Sawit','url':'http://x.com/1','source':'BRIN','source_type':'kementerian'})
print('saved:', r)
results = search_proposals('sawit')
print('found:', len(results))
os.unlink(db_path)
"
```
Expected: `saved: {'saved': True, ...}` and `found: 1`

### Code

```python
import hashlib
import logging

from .db import get_db

logger = logging.getLogger(__name__)

BM25_DEDUP_THRESHOLD = -5.0


def search_proposals(query: str, top_n: int = 5) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT p.*, bm25(proposals_fts) AS score
        FROM proposals_fts
        JOIN proposals p ON p.id = proposals_fts.rowid
        WHERE proposals_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """,
        (query, top_n),
    ).fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "title": row["title"],
            "source": row["source"],
            "source_type": row["source_type"],
            "deadline": row["deadline"],
            "eligibility": row["eligibility"],
            "field": row["field"],
            "amount": row["amount"],
            "url": row["url"],
            "description": row["description"],
            "discovered_at": row["discovered_at"],
            "_score": row["score"],
        })
    return results


def check_duplicate(title: str, url: str) -> bool:
    db = get_db()

    row = db.execute("SELECT id FROM proposals WHERE url = ?", (url,)).fetchone()
    if row:
        return True

    content_hash = hashlib.sha256(f"{title}{url}".encode()).hexdigest()
    row = db.execute(
        "SELECT id FROM proposals WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    if row:
        return True

    rows = db.execute(
        """
        SELECT bm25(proposals_fts) AS score
        FROM proposals_fts
        WHERE proposals_fts MATCH ?
        ORDER BY score
        LIMIT 1
        """,
        (title,),
    ).fetchall()

    if rows and rows[0]["score"] is not None and rows[0]["score"] < BM25_DEDUP_THRESHOLD:
        return True

    return False


def save_proposal(proposal: dict) -> dict:
    db = get_db()

    if check_duplicate(proposal["title"], proposal["url"]):
        return {"saved": False, "id": None, "duplicate": True}

    content_hash = hashlib.sha256(
        f"{proposal['title']}{proposal['url']}".encode()
    ).hexdigest()

    cursor = db.execute(
        """
        INSERT INTO proposals (title, source, source_type, deadline,
            eligibility, field, amount, url, description, content_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            proposal["title"],
            proposal["source"],
            proposal["source_type"],
            proposal.get("deadline"),
            proposal.get("eligibility"),
            proposal.get("field"),
            proposal.get("amount"),
            proposal["url"],
            proposal.get("description"),
            content_hash,
        ),
    )
    db.commit()

    return {"saved": True, "id": cursor.lastrowid, "duplicate": False}


def get_proposals(source_type: str | None = None, limit: int = 20) -> list[dict]:
    db = get_db()
    if source_type:
        rows = db.execute(
            "SELECT * FROM proposals WHERE source_type = ? ORDER BY discovered_at DESC LIMIT ?",
            (source_type, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM proposals ORDER BY discovered_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
```

---

## Task 6: MCP Server Entrypoint

**Files:** `mcp-server/server.py` (create)

**Verification:**
```bash
cd mcp-server && timeout 3 .venv/bin/python server.py 2>&1 || true
```
Expected: MCP server starts without Python errors (may show MCP startup message or timeout)

### Code

```python
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
```

---

## Task 7-9: Scanner Skills

**Files:**
- `skills/brin-scanner/SKILL.md` (create)
- `skills/lpdp-scanner/SKILL.md` (create)
- `skills/kemendikbud-scanner/SKILL.md` (create)

**Verification:**
```bash
ls skills/*/SKILL.md | wc -l
```
Expected: `3`

### skills/brin-scanner/SKILL.md

```markdown
---
name: brin-scanner
description: >
  Use when user says "/cek-brin", "cari proposal BRIN", "pendanaan BRIN",
  or asks about research funding from Badan Riset dan Inovasi Nasional.
---

# BRIN Proposal Scanner

## Pre-flight
1. Call `initialize_database` if not already initialized.

## Search Phase
1. Use Exa `web_search_exa` with queries:
   - "BRIN pendanaan riset proposal 2025 2026 site:brin.go.id"
   - "BRIN hibah penelitian skema pendanaan site:brin.go.id"
2. Collect top 10 URLs from search results.

## Scrape Phase
For each URL found:
1. Call `scrape_page(url)` to get markdown content.
2. If not successful, skip to next URL.
3. Extract proposal details using LLM with instruction:

```
From the following markdown content, extract ALL research funding proposals.
For each proposal found, return JSON with:
- title: The proposal/grant title
- deadline: Submission deadline (YYYY-MM-DD format, or null)
- eligibility: Who can apply (universitas, politeknik, etc.)
- field: Research field (teknologi, sosial, kesehatan, etc.)
- amount: Funding amount (or null if not specified)
- description: Brief description (max 500 chars)

If no proposal found, return empty list.
```

## Save Phase
For each extracted proposal:
1. Call `save_proposal` with source="BRIN", source_type="kementerian"

## Report
Call `get_proposals(source_type="kementerian")` to show new BRIN proposals.
```

### skills/lpdp-scanner/SKILL.md

```markdown
---
name: lpdp-scanner
description: >
  Use when user says "/cek-lpdp", "cari proposal LPDP", "beasiswa LPDP",
  or asks about research funding from Lembaga Pengelola Dana Pendidikan.
---

# LPDP Proposal Scanner

## Pre-flight
1. Call `initialize_database` if not already initialized.

## Search Phase
1. Use Exa `web_search_exa` with queries:
   - "LPDP pendanaan riset 2025 2026 site:lpdp.kemenkeu.go.id"
   - "LPDP beasiswa riset proposal penelitian site:lpdp.kemenkeu.go.id"
2. Collect top 10 URLs from search results.

## Scrape Phase
For each URL found:
1. Call `scrape_page(url)` to get markdown content.
2. If not successful, skip to next URL.
3. Extract proposal details using LLM with instruction:

```
From the following markdown content, extract ALL research funding proposals.
For each proposal found, return JSON with:
- title: The proposal/grant title
- deadline: Submission deadline (YYYY-MM-DD format, or null)
- eligibility: Who can apply (universitas, politeknik, etc.)
- field: Research field (teknologi, sosial, kesehatan, etc.)
- amount: Funding amount (or null if not specified)
- description: Brief description (max 500 chars)

If no proposal found, return empty list.
```

## Save Phase
For each extracted proposal:
1. Call `save_proposal` with source="LPDP", source_type="kementerian"

## Report
Call `get_proposals(source_type="kementerian")` to show new LPDP proposals.
```

### skills/kemendikbud-scanner/SKILL.md

```markdown
---
name: kemendikbud-scanner
description: >
  Use when user says "/cek-kemendikbud", "cari proposal kemendikbud",
  "matching fund", "kedaireka", or asks about Kemendikbud research funding.
---

# Kemendikbud Proposal Scanner

## Pre-flight
1. Call `initialize_database` if not already initialized.

## Search Phase
1. Use Exa `web_search_exa` with queries:
   - "Kemendikbud matching fund proposal penelitian 2025 site:kemdikbud.go.id"
   - "Kemendikbud hibah riset universitas politeknik site:kemdikbud.go.id"
   - "kedaireka pendanaan riset 2025 site:kemdikbud.go.id"
2. Collect top 10 URLs from search results.

## Scrape Phase
For each URL found:
1. Call `scrape_page(url)` to get markdown content.
2. If not successful, skip to next URL.
3. Extract proposal details using LLM with instruction:

```
From the following markdown content, extract ALL research funding proposals.
For each proposal found, return JSON with:
- title: The proposal/grant title
- deadline: Submission deadline (YYYY-MM-DD format, or null)
- eligibility: Who can apply (universitas, politeknik, etc.)
- field: Research field (teknologi, sosial, kesehatan, etc.)
- amount: Funding amount (or null if not specified)
- description: Brief description (max 500 chars)

If no proposal found, return empty list.
```

## Save Phase
For each extracted proposal:
1. Call `save_proposal` with source="Kemendikbud", source_type="kementerian"

## Report
Call `get_proposals(source_type="kementerian")` to show new Kemendikbud proposals.
```

---

## Task 10: Proposal Search Skill

**Files:** `skills/proposal-search/SKILL.md` (create)

**Verification:** file exists with correct frontmatter

### Code

```markdown
---
name: proposal-search
description: >
  Use when user says "/cari-<keyword>", "/cari-proposal-<year>",
  or any search command for existing proposals in the database.
---

# Proposal Search

## Command Routing

### /cari-<keyword>
1. Extract keyword from user input.
2. Call `search_proposals(query="<keyword>", top_n=15)`.
3. Group results by source (BRIN/LPDP/Kemendikbud).
4. Present top 5 per source.

### /cari-proposal-<year>
1. Extract year from command.
2. Call `search_proposals(query="<year>", top_n=15)`.

## Output Format (Telegram MarkdownV2)
```
*Hasil pencarian:* `keyword`

*BRIN* (3 ditemukan)
1. [Judul](url) - Deadline: 30 Juni 2026
...

*LPDP* (2 ditemukan)
1. ...

Total: 9 proposal
```

## Edge Cases
- No results: "Belum ada proposal untuk 'keyword'. Coba /cek."
- DB not initialized: call `initialize_database` first.
```

---

## Task 11: Proposal Report Skill

**Files:** `skills/proposal-report/SKILL.md` (create)

**Verification:** file exists with correct frontmatter

### Code

```markdown
---
name: proposal-report
description: >
  Use when user says "/proposal-baru", "proposal terbaru",
  or requests a report of newly discovered proposals.
---

# Proposal Report

## Steps
1. Call `get_proposals(limit=20)`.
2. Filter to proposals from last 7 days.
3. Group by source_type.
4. Format for Telegram.

## Output Format
```
*Proposal Baru - 7 Hari Terakhir*

*Kementerian* (5 baru)
BRIN: [Judul](url) - Deadline: ...
LPDP: [Judul](url) - Deadline: ...

Total: 5 proposal baru

/cari-<topik> untuk mencari
/cek untuk crawling sekarang
```
```

---

## Task 12: Integration Tests

**Files:** `tests/test_e2e.py` (create)

**Verification:**
```bash
cd mcp-server && .venv/bin/pytest ../tests/test_e2e.py -v
```
Expected: all 5 tests pass

### Code

```python
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))

from tools.db import init_db, get_db
from tools.search import search_proposals, save_proposal, check_duplicate


def test_init_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        db = get_db()
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        assert "proposals" in table_names
        assert "sources" in table_names
        assert "proposals_fts" in table_names
        sources = db.execute("SELECT COUNT(*) as cnt FROM sources").fetchone()
        assert sources["cnt"] == 3
    finally:
        os.unlink(db_path)


def test_save_and_search():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        result = save_proposal({
            "title": "Hibah Penelitian Sawit Berkelanjutan 2026",
            "url": "https://brin.go.id/hibah-sawit-2026",
            "source": "BRIN",
            "source_type": "kementerian",
            "deadline": "2026-12-31",
            "eligibility": "Universitas dan Politeknik",
            "field": "pertanian",
            "amount": "Rp 500.000.000",
            "description": "Pendanaan riset sawit berkelanjutan",
        })
        assert result["saved"] is True
        assert result["duplicate"] is False
        results = search_proposals("sawit", top_n=5)
        assert len(results) == 1
        assert results[0]["title"] == "Hibah Penelitian Sawit Berkelanjutan 2026"
    finally:
        os.unlink(db_path)


def test_dedup_exact_hash():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        save_proposal({
            "title": "Proposal A", "url": "https://example.com/a",
            "source": "BRIN", "source_type": "kementerian",
        })
        result = save_proposal({
            "title": "Proposal A", "url": "https://example.com/a",
            "source": "BRIN", "source_type": "kementerian",
        })
        assert result["duplicate"] is True
    finally:
        os.unlink(db_path)


def test_dedup_bm25_similar():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        save_proposal({
            "title": "Hibah Penelitian Kecerdasan Buatan untuk Universitas Indonesia",
            "url": "https://brin.go.id/ai-grant-1",
            "source": "BRIN", "source_type": "kementerian",
        })
        result = save_proposal({
            "title": "Hibah Riset Kecerdasan Buatan untuk Universitas Indonesia",
            "url": "https://brin.go.id/ai-grant-2",
            "source": "BRIN", "source_type": "kementerian",
        })
        assert result["duplicate"] is True
    finally:
        os.unlink(db_path)


def test_search_multiple():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        for p in [
            {"title": "Riset Energi Terbarukan 2026", "url": "https://a.com/1", "source": "BRIN", "source_type": "kementerian"},
            {"title": "Inovasi Panel Surya", "url": "https://a.com/2", "source": "LPDP", "source_type": "kementerian"},
            {"title": "Studi Sosial Pesisir", "url": "https://a.com/3", "source": "Kemendikbud", "source_type": "kementerian"},
        ]:
            save_proposal(p)
        results = search_proposals("energi OR surya", top_n=5)
        assert len(results) == 2
        results = search_proposals("sosial", top_n=5)
        assert len(results) == 1
        assert results[0]["source"] == "Kemendikbud"
    finally:
        os.unlink(db_path)
```

---

## Execution Order & Dependencies

```
Task 1  (db/schema.sql)          → no dependency
Task 2  (config/sources.yaml)    → no dependency
Task 3  (tools/db.py)            → Task 1
Task 4  (tools/scraper.py)       → Task 2
Task 5  (tools/search.py)        → Task 3
Task 6  (server.py)              → Task 3,4,5
Task 7  (skills/brin-scanner)    → no dependency
Task 8  (skills/lpdp-scanner)    → no dependency
Task 9  (skills/kemendikbud)    → no dependency
Task 10 (skills/proposal-search) → no dependency
Task 11 (skills/proposal-report) → no dependency
Task 12 (tests/test_e2e.py)      → Task 1-6
```

## Tech Stack

| Package      | Version | Purpose                       |
|-------------|---------|-------------------------------|
| crawl4ai    | 0.9.2   | Primary scraper (Playwright)  |
| firecrawl-py| 4.32.1  | Fallback scraper              |
| mcp         | 1.28.1  | MCP server framework (FastMCP)|
| pyyaml      | 6.0.3   | Config parsing                |
| pytest      | 8.x     | Testing                       |

## Git Workflow

```
main                    ← source of truth, protected
  └── feature/mcp-server ← THIS BRANCH for all 12 tasks
       └── PR → review → merge main
```
