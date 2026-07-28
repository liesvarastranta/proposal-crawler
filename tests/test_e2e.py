import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))

from tools.db import init_db, get_db
from tools.search import search_proposals, save_proposal


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
