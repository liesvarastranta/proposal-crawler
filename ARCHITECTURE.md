# Architecture: Proposal Funding Crawler

## Overview
4 unit independent dengan interface yang jelas. Hermes Agent sebagai orchestrator,
MCP server (Python + Crawl4AI) untuk crawling, skills pack untuk instruksi per
sumber, SQLite untuk persistence.

## Component Architecture

```
Unit A: Hermes Agent Core
  └─ Brain, Memory, Cron, Telegram Gateway
  └─ Interface: MCP protocol (consumes B's tools)
  └─ Does: orchestrasi crawling, scheduling, notification

Unit B: MCP Crawler Server (Python)
  └─ Tools: search_grants, scrape_page, extract_structured
  └─ Interface: FastMCP stdio/HTTP
  └─ Does: web crawling + structured extraction

Unit C: Skills Pack
  └─ Files: skills/*/SKILL.md
  └─ Interface: Hermes skill system
  └─ Does: source-specific crawling instructions

Unit D: Data Layer
  └─ SQLite db: proposals, sources, crawl_runs
  └─ Interface: SQL via Hermes/agent tools
  └─ Does: persistence + deduplication
```

### Boundary Rules
- Unit B tidak tahu tentang Unit C/D — hanya terima input, return output
- Unit C tidak akses DB langsung — lewat Unit A
- Unit A adalah satu-satunya orchestrator
- Setiap unit bisa di-test secara independent

### Data Flow

```
Cron triggers Unit A
    │
    ▼
Unit A loads Skill (Unit C)
    │
    ▼
Unit A calls MCP tool (Unit B): search_grants(query)
    │
    ▼
Unit B scrapes source → returns structured list
    │
    ▼
Unit A calls MCP tool (Unit B): scrape_page(url, schema)
    │
    ▼
Unit A deduplicates against Unit D
    │
    ▼
Unit A inserts new proposals → Unit D
    │
    ▼
Unit A sends Telegram notification
```

## Component Interfaces

### Unit B: MCP Tools

```
search_grants(query: str, source_type: str, max_results: int = 10)
  → list[{title, url, snippet}]

scrape_page(url: str, schema: dict)
  → {title, deadline, eligibility, amount, description}

extract_structured(content: str, instruction: str)
  → list[dict]
```

### Unit C: Skill Interface

```
Setiap SKILL.md menyediakan:
  - target_urls: list[str]
  - extraction_schema: dict
  - eligibility_filter: str
  - search_queries: list[str]
```

### Unit D: Query Interface

```
insert_proposal(proposal: Proposal) → bool  (false if duplicate)
get_proposals(source_type: str) → list[Proposal]
mark_notified(proposal_ids: list[int]) → void
```

## Data Model

```
proposals
  id            INTEGER PRIMARY KEY
  title         TEXT NOT NULL
  source        TEXT NOT NULL
  source_type   TEXT NOT NULL
  deadline      DATE
  eligibility   TEXT
  field         TEXT
  amount        TEXT
  url           TEXT NOT NULL UNIQUE
  description   TEXT
  discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP
  notified      BOOLEAN DEFAULT 0

sources
  id            INTEGER PRIMARY KEY
  name          TEXT NOT NULL
  type          TEXT NOT NULL
  url           TEXT NOT NULL
  last_checked  DATETIME
  status        TEXT DEFAULT 'active'

crawl_runs
  id            INTEGER PRIMARY KEY
  source_id     INTEGER REFERENCES sources(id)
  started_at    DATETIME
  finished_at   DATETIME
  proposals_found INTEGER DEFAULT 0
```

## Deduplication Strategy

```
New proposal found
        │
        ▼
  Generate hash(title + url)
        │
   ┌────┴────┐
   │ In DB?  │
   └────┬────┘
   yes  │  no
    │   │   │
    ▼   │   ▼
  Skip  │  Insert + notify
```

## Tech Stack

| Decision       | Choice       | Why                                    |
|----------------|-------------|----------------------------------------|
| Agent          | Hermes Agent | Skills, cron, Telegram, MCP built-in   |
| Crawler        | Crawl4AI     | Python, JS rendering, structured extraction |
| LLM            | OpenAI API   | Compatible, tool calling               |
| Web Search     | Exa MCP      | web_search_exa, agent_run              |
| DB             | SQLite       | Zero-setup, Hermes-native              |
| MCP Framework  | FastMCP      | Lightweight Python                     |
| Browser        | Playwright   | JS-heavy gov sites                     |

## File Structure

```
proposal-crawler/
├── opencode.json
├── AGENTS.md
├── PRD.md
├── ARCHITECTURE.md
├── docs/superpowers/specs/
│   └── 2025-07-25-proposal-crawler-design.md
├── mcp-server/
│   ├── pyproject.toml
│   ├── server.py
│   └── tools/
│       ├── __init__.py
│       ├── search.py
│       ├── scraper.py
│       └── sources.py
├── skills/
│   ├── brin-scanner/SKILL.md
│   ├── lpdp-scanner/SKILL.md
│   ├── kemendikbud-scanner/SKILL.md
│   ├── national-scanner/SKILL.md
│   ├── international-scanner/SKILL.md
│   ├── proposal-dedup/SKILL.md
│   └── proposal-report/SKILL.md
├── config/
│   └── sources.yaml
├── db/
│   └── schema.sql
└── tests/
    ├── test_mcp_server.py
    ├── test_scraper.py
    └── test_dedup.py
```
