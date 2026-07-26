# PRD: Proposal Funding Crawler

## Problem
Dosen/peneliti di universitas dan politeknik Indonesia kesulitan menemukan
informasi proposal pendanaan riset yang tersebar di puluhan situs kementerian,
perusahaan nasional, dan lembaga internasional.

## Target Users
- Dosen / peneliti universitas Indonesia
- LPPM (Lembaga Penelitian dan Pengabdian Masyarakat)
- Mahasiswa S2/S3 mencari beasiswa riset

## Functional Requirements

| ID   | Requirement                                         | Priority |
|------|-----------------------------------------------------|----------|
| F-01 | Crawl sumber kementerian (BRIN, LPDP, Kemendikbud)  | P0       |
| F-02 | Crawl sumber nasional (Pertamina, Telkom, Astra)    | P1       |
| F-03 | Crawl sumber multinasional (WB, ADB, EU)            | P2       |
| F-04 | Ekstrak structured data: title, deadline, eligibility, amount, url | P0 |
| F-05 | Deduplikasi proposal berdasarkan title+url          | P0       |
| F-06 | Simpan ke SQLite database                           | P0       |
| F-07 | Notifikasi Telegram untuk proposal baru             | P1       |
| F-08 | Pencarian berbasis keyword/field                    | P2       |
| F-09 | Jadwal crawling otomatis (cron)                     | P1       |

## Non-Functional Requirements
- **Bahasa**: Proposal dalam Bahasa Indonesia maupun Inggris
- **Rate Limiting**: Respect robots.txt, delay 1-3 detik antar request
- **Error Recovery**: Retry 3x dengan exponential backoff
- **Storage**: SQLite, < 10MB untuk 10.000 proposal

## Source Priorities

| Fase | Sumber                              | Interval   |
|------|-------------------------------------|------------|
| 1    | BRIN, LPDP, Kemendikbud             | Harian     |
| 2    | Pertamina, Telkom, Astra, Bank BUMN | Mingguan   |
| 3    | World Bank, ADB, USAID, EU Horizon  | Mingguan   |

## Success Criteria
- Menemukan >=80% proposal yang tersedia publik
- Notifikasi Telegram < 5 menit setelah crawling selesai
- 0 false duplicates dalam database
