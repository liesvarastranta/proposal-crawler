import hashlib
import logging
import re

from .db import get_db

logger = logging.getLogger(__name__)

STOPWORDS = {"dan", "di", "ke", "dari", "untuk", "yang", "dengan", "ini",
             "itu", "pada", "adalah", "akan", "telah", "sudah", "dalam",
             "oleh", "atau", "sebagai", "tentang", "setelah", "serta",
             "secara", "melalui", "antara", "namun", "juga", "the", "for",
             "and", "of", "to", "in", "is", "on", "at", "by", "with", "a",
             "an"}


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def search_proposals(query: str, top_n: int = 5) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT p.*, bm25(proposals_fts) AS score
        FROM proposals_fts
        JOIN proposals p ON p.id = proposals_fts.rowid
        WHERE proposals_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """,
        (query, top_n),
    ).fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "title": row["title"],
            "source": row["source"],
            "source_type": row["source_type"],
            "deadline": row["deadline"],
            "eligibility": row["eligibility"],
            "field": row["field"],
            "amount": row["amount"],
            "url": row["url"],
            "description": row["description"],
            "discovered_at": row["discovered_at"],
            "_score": row["score"],
        })
    return results


def check_duplicate(title: str, url: str) -> bool:
    db = get_db()

    row = db.execute("SELECT id FROM proposals WHERE url = ?", (url,)).fetchone()
    if row:
        return True

    content_hash = hashlib.sha256(f"{title}{url}".encode()).hexdigest()
    row = db.execute(
        "SELECT id FROM proposals WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    if row:
        return True

    keywords = _extract_keywords(title)
    if not keywords:
        return False

    all_titles = db.execute("SELECT title FROM proposals").fetchall()
    for row in all_titles:
        existing_kw = _extract_keywords(row["title"])
        if not existing_kw:
            continue
        intersection = len(set(keywords) & set(existing_kw))
        union = len(set(keywords) | set(existing_kw))
        jaccard = intersection / union if union > 0 else 0
        if jaccard > 0.7:
            return True

    return False


def save_proposal(proposal: dict) -> dict:
    db = get_db()

    if check_duplicate(proposal["title"], proposal["url"]):
        return {"saved": False, "id": None, "duplicate": True}

    content_hash = hashlib.sha256(
        f"{proposal['title']}{proposal['url']}".encode()
    ).hexdigest()

    cursor = db.execute(
        """
        INSERT INTO proposals (title, source, source_type, deadline,
            eligibility, field, amount, url, description, content_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            proposal["title"],
            proposal["source"],
            proposal["source_type"],
            proposal.get("deadline"),
            proposal.get("eligibility"),
            proposal.get("field"),
            proposal.get("amount"),
            proposal["url"],
            proposal.get("description"),
            content_hash,
        ),
    )
    db.commit()

    return {"saved": True, "id": cursor.lastrowid, "duplicate": False}


def get_proposals(source_type: str | None = None, limit: int = 20) -> list[dict]:
    db = get_db()
    if source_type:
        rows = db.execute(
            "SELECT * FROM proposals WHERE source_type = ? ORDER BY discovered_at DESC LIMIT ?",
            (source_type, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM proposals ORDER BY discovered_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
