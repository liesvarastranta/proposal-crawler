---
name: proposal-report
description: >
  Use when user says "/proposal-baru", "proposal terbaru",
  or requests a report of newly discovered proposals in the database.
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
