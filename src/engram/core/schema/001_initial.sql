-- 001_initial.sql
-- Initial Engram schema. Creates the core nodes/edges/aliases/provenance tables
-- and the FTS5 virtual table used for keyword recall.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS nodes (
    id            TEXT PRIMARY KEY,
    path          TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    body          TEXT NOT NULL,
    node_type     TEXT NOT NULL CHECK (node_type IN ('fact','pattern','decision','reference')),
    tags          TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    verified_on   DATETIME,
    ttl_days      INTEGER NOT NULL,
    superseded_by TEXT REFERENCES nodes(id),
    degree        INTEGER DEFAULT 0,
    cluster_id    INTEGER,
    pagerank      REAL DEFAULT 0,
    quarantined   INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    body, title, tags,
    tokenize = 'porter unicode61',
    content = 'nodes',
    content_rowid = 'rowid'
);

CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
    INSERT INTO nodes_fts(rowid, body, title, tags)
    VALUES (new.rowid, new.body, new.title, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, body, title, tags)
    VALUES ('delete', old.rowid, old.body, old.title, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, body, title, tags)
    VALUES ('delete', old.rowid, old.body, old.title, old.tags);
    INSERT INTO nodes_fts(rowid, body, title, tags)
    VALUES (new.rowid, new.body, new.title, new.tags);
END;

CREATE TABLE IF NOT EXISTS edges (
    id          INTEGER PRIMARY KEY,
    source_id   TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id   TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    edge_type   TEXT NOT NULL CHECK (edge_type IN ('wiki-link','co-recall','shared-tag','manual')),
    weight      REAL DEFAULT 1.0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id, edge_type)
);

CREATE TABLE IF NOT EXISTS aliases (
    canonical TEXT NOT NULL,
    alias     TEXT NOT NULL,
    UNIQUE(canonical, alias)
);

CREATE TABLE IF NOT EXISTS provenance (
    id           INTEGER PRIMARY KEY,
    node_id      TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    entry_type   TEXT NOT NULL CHECK (entry_type IN ('fact-asserted','fact-corrected','pattern-observed','verified')),
    session_id   TEXT,
    jira_ticket  TEXT,
    evidence     TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS co_recall_log (
    session_id  TEXT,
    node_id     TEXT REFERENCES nodes(id) ON DELETE CASCADE,
    query       TEXT,
    recalled_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id      INTEGER PRIMARY KEY,
    ts      DATETIME DEFAULT CURRENT_TIMESTAMP,
    op      TEXT NOT NULL,
    payload TEXT
);

CREATE INDEX IF NOT EXISTS idx_edges_source     ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target     ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_provenance_node  ON provenance(node_id);
CREATE INDEX IF NOT EXISTS idx_nodes_type       ON nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_nodes_quarantine ON nodes(quarantined);
