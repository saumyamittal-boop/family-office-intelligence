-- Holdings imported from statements (ADR-0020). An import is one confirmed file; its lines are what the person confirmed in the preview.
-- Both tables cascade from the profile and from the account, so deleting either removes its holdings. Every query also carries the
-- account id taken from the session, so a profile id from another account finds nothing.
CREATE TABLE holding_imports (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_kind TEXT NOT NULL CHECK (file_kind IN ('csv', 'xlsx')),
    unit TEXT NOT NULL CHECK (unit IN ('cr', 'lakh', 'inr')),
    content_sha256 TEXT NOT NULL,
    row_count INTEGER NOT NULL CHECK (row_count > 0),
    total_cr REAL NOT NULL CHECK (total_cr > 0),
    created TEXT NOT NULL,
    UNIQUE (profile_id, content_sha256)
);
CREATE INDEX idx_holding_imports_profile ON holding_imports(profile_id);

CREATE TABLE holdings (
    id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES holding_imports(id) ON DELETE CASCADE,
    row_no INTEGER NOT NULL,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    account TEXT NOT NULL DEFAULT '',
    value_cr REAL NOT NULL CHECK (value_cr > 0)
);
CREATE INDEX idx_holdings_import ON holdings(import_id);
