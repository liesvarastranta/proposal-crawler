#!/usr/bin/env python3
"""Telegram bot for Proposal Funding Crawler — bridges Telegram to MCP tools."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from tools.db import init_db
from tools.search import search_proposals, save_proposal, get_proposals
from tools.scraper import scrape_page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = str(Path(__file__).parent / "db" / "proposals.db")
TOKEN = "8722850387:AAE_icTw4TyZoXdIvVCglq-zCPJGq9orVgE"
HELP_TEXT = (
    "/bantuan - List semua perintah\n"
    "/cari-<keyword> - Cari proposal (BM25)\n"
    "/cari-proposal-<tahun> - Cari proposal tahun tertentu\n"
    "/cek - Crawl semua sumber\n"
    "/cek-brin - Crawl BRIN\n"
    "/cek-lpdp - Crawl LPDP\n"
    "/cek-kemendikbud - Crawl Kemendikbud\n"
    "/proposal-baru - Proposal baru 7 hari\n"
    "/sumber - Daftar sumber aktif"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Selamat datang! Proposal Funding Crawler siap.\n\n" + HELP_TEXT)


async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def cari_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    keyword = text.replace("/cari-", "", 1).strip()
    if not keyword:
        await update.message.reply_text("Gunakan: /cari-<kata kunci>\nContoh: /cari-sawit")
        return

    await update.message.reply_text(f"Mencari '{keyword}'...")
    try:
        results = search_proposals(keyword, top_n=15)
        if not results:
            await update.message.reply_text(f"Tidak ada proposal untuk '{keyword}'. Coba /cek untuk crawling baru.")
            return

        grouped = {}
        for r in results:
            grouped.setdefault(r["source"], []).append(r)

        lines = [f"🔍 Hasil pencarian: {keyword}"]
        for source, props in grouped.items():
            lines.append(f"\n*{source}* ({len(props)} ditemukan)")
            for i, p in enumerate(props[:5], 1):
                deadline = f" - Deadline: {p['deadline']}" if p.get("deadline") else ""
                lines.append(f"{i}. {p['title']}{deadline}")
                lines.append(f"   {p['url']}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cari_proposal_tahun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tahun = text = update.message.text.replace("/cari-proposal-", "", 1).strip()
    if not tahun.isdigit():
        await update.message.reply_text("Gunakan: /cari-proposal-<tahun>\nContoh: /cari-proposal-2026")
        return

    await update.message.reply_text(f"Mencari proposal tahun {tahun}...")
    try:
        results = search_proposals(tahun, top_n=15)
        if not results:
            await update.message.reply_text(f"Tidak ada proposal tahun {tahun}. Coba /cek untuk crawling baru.")
            return

        grouped = {}
        for r in results:
            grouped.setdefault(r["source"], []).append(r)

        lines = [f"🔍 Proposal {tahun}"]
        for source, props in grouped.items():
            lines.append(f"\n*{source}* ({len(props)} ditemukan)")
            for i, p in enumerate(props[:5], 1):
                deadline = f" - Deadline: {p['deadline']}" if p.get("deadline") else ""
                lines.append(f"{i}. {p['title']}{deadline}")
                lines.append(f"   {p['url']}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def proposal_baru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Mengambil proposal terbaru...")
    try:
        results = get_proposals(limit=20)
        if not results:
            await update.message.reply_text("Belum ada proposal. Coba /cek untuk crawling.")
            return

        grouped = {}
        for r in results:
            grouped.setdefault(r["source"], []).append(r)

        total = len(results)
        lines = [f"📋 Total: {total} proposal"]
        for source, props in grouped.items():
            lines.append(f"\n*{source}* ({len(props)})")
            for p in props[:7]:
                deadline = f" - {p['deadline']}" if p.get("deadline") else ""
                lines.append(f"• {p['title']}{deadline}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def sumber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📡 *Sumber Pendanaan*\n"]
    for s in [
        ("BRIN", "kementerian", "brin.go.id"),
        ("LPDP", "kementerian", "lpdp.kemenkeu.go.id"),
        ("Kemendikbud", "kementerian", "kemdikbud.go.id"),
    ]:
        lines.append(f"• *{s[0]}* ({s[1]}) — {s[2]}")
    lines.append("\n/cek untuk crawling manual")
    await update.message.reply_text("\n".join(lines))


async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Memulai crawling... (simulasi)")
    await update.message.reply_text("Crawl selesai. Gunakan /proposal-baru untuk lihat hasil.")


async def cek_brin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Crawl BRIN... (simulasi — integrasi Exa+Crawl4AI menyusul)")


async def cek_lpdp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Crawl LPDP... (simulasi — integrasi Exa+Crawl4AI menyusul)")


async def cek_kemendikbud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Crawl Kemendikbud... (simulasi — integrasi Exa+Crawl4AI menyusul)")


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

    import re

    async def _cari_proposal_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cari_proposal_tahun(update, context)

    async def _cari_kw(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cari_keyword(update, context)

    app.add_handler(MessageHandler(filters.Regex(r"^/cari-proposal-\d{4}"), _cari_proposal_year))
    app.add_handler(MessageHandler(filters.Regex(r"^/cari-"), _cari_kw))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
