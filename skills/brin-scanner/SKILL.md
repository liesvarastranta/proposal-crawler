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
