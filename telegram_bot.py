#!/usr/bin/env python3
"""Telegram bot for Proposal Funding Crawler — bridges to Hermes Agent for NLU."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from tools.db import init_db
from tools.search import search_proposals, get_proposals

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = str(Path(__file__).parent / "db" / "proposals.db")
TOKEN = "8722850387:AAE_icTw4TyZoXdIvVCglq-zCPJGq9orVgE"
HERMES_TIMEOUT = 120

HELP_TEXT = (
    "/bantuan - List perintah\n"
    "/cari-<keyword> - Cari proposal (BM25)\n"
    "/cari-proposal-<tahun> - Proposal tahun tertentu\n"
    "/cek - Crawl semua sumber\n"
    "/cek-brin, /cek-lpdp, /cek-kemendikbud\n"
    "/proposal-baru - Proposal baru\n"
    "/sumber - Daftar sumber\n\n"
    "Atau tanya natural language, nanti Hermes proses:"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Proposal Funding Crawler siap.\n\n" + HELP_TEXT)


async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def _ask_hermes(prompt: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "hermes", "-z", prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=HERMES_TIMEOUT)
        if proc.returncode != 0:
            return f"Error: {stderr.decode()[:500]}"
        return stdout.decode().strip()
    except asyncio.TimeoutError:
        proc.kill()
        return "Waktu habis. Coba lagi nanti."


async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    await update.message.reply_chat_action("typing")
    logger.info("Sending to Hermes: %s", text[:80])
    response = await _ask_hermes(
        f"Gunakan tool proposal-crawler (MCP server) untuk menjawab. "
        f"Jika perlu, panggil initialize_database dulu. "
        f"Pertanyaan: {text}"
    )
    for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
        await update.message.reply_text(chunk)


async def cari_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.replace("/cari-", "", 1).strip()
    if not keyword:
        await update.message.reply_text("Gunakan: /cari-<kata kunci>")
        return

    await update.message.reply_chat_action("typing")
    try:
        results = search_proposals(keyword, top_n=15)
        if not results:
            await update.message.reply_text(
                f"Tidak ada proposal untuk '{keyword}'. Coba /cek untuk crawling baru."
            )
            return

        grouped = {}
        for r in results:
            grouped.setdefault(r["source"], []).append(r)

        lines = [f"Hasil pencarian: {keyword}"]
        for source, props in grouped.items():
            lines.append(f"\n{source} ({len(props)})")
            for i, p in enumerate(props[:5], 1):
                d_line = f" - Deadline: {p['deadline']}" if p.get("deadline") else ""
                lines.append(f"{i}. {p['title']}{d_line}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cari_proposal_tahun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tahun = update.message.text.replace("/cari-proposal-", "", 1).strip()
    if not tahun.isdigit():
        await update.message.reply_text("Gunakan: /cari-proposal-<tahun>")
        return

    await update.message.reply_chat_action("typing")
    try:
        results = search_proposals(tahun, top_n=15)
        if not results:
            await update.message.reply_text(f"Tidak ada proposal tahun {tahun}. Coba /cek.")
            return

        grouped = {}
        for r in results:
            grouped.setdefault(r["source"], []).append(r)

        lines = [f"Proposal {tahun}"]
        for source, props in grouped.items():
            lines.append(f"\n{source} ({len(props)})")
            for i, p in enumerate(props[:5], 1):
                d_line = f" - {p['deadline']}" if p.get("deadline") else ""
                lines.append(f"{i}. {p['title']}{d_line}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def proposal_baru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_chat_action("typing")
    try:
        results = get_proposals(limit=20)
        if not results:
            await update.message.reply_text("Belum ada proposal. Coba /cek.")
            return

        grouped = {}
        for r in results:
            grouped.setdefault(r["source"], []).append(r)

        lines = [f"Total: {len(results)} proposal"]
        for source, props in grouped.items():
            lines.append(f"\n{source} ({len(props)})")
            for p in props[:7]:
                d_line = f" - {p['deadline']}" if p.get("deadline") else ""
                lines.append(f"  {p['title']}{d_line}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def sumber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["Sumber Pendanaan\n"]
    for s in [
        ("BRIN", "kementerian", "brin.go.id"),
        ("LPDP", "kementerian", "lpdp.kemenkeu.go.id"),
        ("Kemendikbud", "kementerian", "kemdikbud.go.id"),
    ]:
        lines.append(f"- {s[0]} ({s[1]}) — {s[2]}")
    lines.append("\n/cek untuk crawling")
    await update.message.reply_text("\n".join(lines))


async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Crawl dimulai. Saya delegasikan ke Hermes Agent untuk eksekusi..."
    )
    await update.message.reply_chat_action("typing")
    response = await _ask_hermes(
        "Crawl semua sumber pendanaan (BRIN, LPDP, Kemendikbud) "
        "proposal-crawler MCP server. Panggil initialize_database dulu, "
        "lalu scrape setiap sumber. Report hasil."
    )
    for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
        await update.message.reply_text(chunk)


async def cek_brin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Crawl BRIN...")
    await update.message.reply_chat_action("typing")
    response = await _ask_hermes(
        "Gunakan Exa untuk cari proposal BRIN "
        "(query: 'BRIN pendanaan riset proposal 2025 2026 site:brin.go.id'), "
        "scrape tiap URL, extract proposal, save ke DB, report."
    )
    for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
        await update.message.reply_text(chunk)


async def cek_lpdp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Crawl LPDP...")
    await update.message.reply_chat_action("typing")
    response = await _ask_hermes(
        "Gunakan Exa untuk cari proposal LPDP "
        "(query: 'LPDP pendanaan riset 2025 2026 site:lpdp.kemenkeu.go.id'), "
        "scrape tiap URL, extract proposal, save ke DB, report."
    )
    for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
        await update.message.reply_text(chunk)


async def cek_kemendikbud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Crawl Kemendikbud...")
    await update.message.reply_chat_action("typing")
    response = await _ask_hermes(
        "Gunakan Exa untuk cari proposal Kemendikbud "
        "(query: 'Kemendikbud matching fund proposal penelitian 2025 site:kemdikbud.go.id'), "
        "scrape tiap URL, extract proposal, save ke DB, report."
    )
    for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
        await update.message.reply_text(chunk)


def main():
    init_db(DB_PATH)
    logger.info("Database initialized at %s", DB_PATH)

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bantuan", bantuan))
    app.add_handler(CommandHandler("proposal_baru", proposal_baru))
    app.add_handler(CommandHandler("sumber", sumber))
    app.add_handler(CommandHandler("cek", cek))
    app.add_handler(CommandHandler("cek_brin", cek_brin))
    app.add_handler(CommandHandler("cek_lpdp", cek_lpdp))
    app.add_handler(CommandHandler("cek_kemendikbud", cek_kemendikbud))

    app.add_handler(MessageHandler(filters.Regex(r"^/cari-proposal-\d{4}"), cari_proposal_tahun))
    app.add_handler(MessageHandler(filters.Regex(r"^/cari-"), cari_keyword))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_handler))

    logger.info("Bot starting with Hermes NLU bridge...")
    app.run_polling()


if __name__ == "__main__":
    main()
