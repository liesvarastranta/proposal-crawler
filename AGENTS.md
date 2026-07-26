# AGENTS.md — Proposal Funding Crawler

Project ini menggunakan [Superpowers](https://github.com/obra/superpowers) skill
framework. Semua AI agent WAJIB mengikuti workflow di bawah ini.

## Superpowers Workflow (MANDATORY)

```
brainstorming → writing-plans → test-driven-development → requesting-code-review → finishing-a-development-branch
```

| Skill                          | Kapan                                             |
|--------------------------------|---------------------------------------------------|
| `brainstorming`                | Sebelum kode apapun. Tidak ada pengecualian.       |
| `writing-plans`                | Setelah design disetujui. Buat tasks 2-5 menit.    |
| `test-driven-development`      | RED-GREEN-REFACTOR. Test dulu, kode kemudian.      |
| `subagent-driven-development`  | Dispatch subagent per task, review antar task.     |
| `requesting-code-review`       | Setelah setiap task selesai.                       |
| `finishing-a-development-branch` | Merge/PR/cleanup setelah semua task complete.    |

**Hard rule:** Jika skill applies, invoke skill. "Ini simple" bukan alasan skip.
Jika ragu 1% pun — invoke.

## Agent Types

### 1. Agent Pembangun (Coding Agents)
Mereka yang membaca dan patuh ke AGENTS.md ini:
- **Main Agent** (OpenCode) — orchestrator: brainstorming, planning, review
- **Subagent** (`task` tool) — eksekutor task individu, 1 task = 1 subagent fresh
- **Parallel Subagent** — untuk task independen barengan

### 2. Agent Produk (Bukan target AGENTS.md)
- **Hermes Agent** — runtime agent yang melakukan crawling + notifikasi (produk)
- **MCP Crawler Server** — Python process tools: search_grants, scrape_page (produk)

## Code Conventions

- NO COMMENTS unless complex logic demands it
- Fungsi < 20 lines, single purpose
- Type hints everywhere (Python)
- Async/await untuk semua I/O
- snake_case (Python), kebab-case (files)
- `logging` module, bukan `print()`

## Prohibited Actions

- Menulis kode sebelum planning disetujui user
- Skip test writing dengan alasan apapun
- 3+ file changes dalam satu task tanpa izin
- Hardcoded credentials, API keys, secrets
- Emoji dalam kode atau commit message
- Commit langsung ke main/master

## Language

| Context              | Language   |
|----------------------|------------|
| User communication   | Indonesia  |
| Code, commits        | English    |
| Documentation spec   | English    |

## Tool Mapping (OpenCode)

| Action            | Tool        |
|-------------------|-------------|
| Create/edit file  | `write`, `edit` |
| Read file         | `read`      |
| Shell command     | `bash`      |
| Search code       | `grep`, `glob` |
| Todo list         | `todowrite` |
| Dispatch subagent | `task`      |
| Load skill        | `skill`     |
| Fetch URL         | `webfetch`  |

## Project-Specific Rules

| Rule                                  | Reason                                  |
|---------------------------------------|-----------------------------------------|
| Respect robots.txt + rate limiting    | Anti-block, etika crawling              |
| Hash(title+url) untuk deduplikasi     | Mencegah false duplicates               |
| Semua proposal harus accessible publik| Hukum, etika                             |
| Environment variables untuk credentials| Keamanan                               |
| Hermes skills di `skills/<name>/SKILL.md` | Konvensi Hermes                     |
| MCP servers di `opencode.json` `mcp.servers` | Konvensi OpenCode                |
