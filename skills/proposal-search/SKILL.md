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
