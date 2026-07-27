CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    deadline TEXT,
    eligibility TEXT,
    field TEXT,
    amount TEXT,
    url TEXT NOT NULL UNIQUE,
    description TEXT,
    discovered_at TEXT DEFAULT (datetime('now', 'localtime')),
    content_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    base_url TEXT NOT NULL,
    last_checked TEXT,
    status TEXT DEFAULT 'active'
);

CREATE VIRTUAL TABLE IF NOT EXISTS proposals_fts USING fts5(
    title,
    description,
    field,
    content='proposals',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS proposals_ai AFTER INSERT ON proposals BEGIN
    INSERT INTO proposals_fts(rowid, title, description, field)
    VALUES (new.id, new.title, new.description, new.field);
END;

CREATE TRIGGER IF NOT EXISTS proposals_ad AFTER DELETE ON proposals BEGIN
    INSERT INTO proposals_fts(proposals_fts, rowid, title, description, field)
    VALUES ('delete', old.id, old.title, old.description, old.field);
END;

CREATE TRIGGER IF NOT EXISTS proposals_au AFTER UPDATE ON proposals BEGIN
    INSERT INTO proposals_fts(proposals_fts, rowid, title, description, field)
    VALUES ('delete', old.id, old.title, old.description, old.field);
    INSERT INTO proposals_fts(rowid, title, description, field)
    VALUES (new.id, new.title, new.description, new.field);
END;

INSERT OR IGNORE INTO sources (name, type, base_url) VALUES
    ('BRIN', 'kementerian', 'https://brin.go.id'),
    ('LPDP', 'kementerian', 'https://lpdp.kemenkeu.go.id'),
    ('Kemendikbud', 'kementerian', 'https://kemdikbud.go.id');
