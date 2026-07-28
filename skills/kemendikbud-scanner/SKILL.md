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
