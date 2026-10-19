-- Which four dashboard modules a person has chosen, and in what order. One row per account (decision D8):
-- the choice follows the person, not the family profile they are looking at. No row means "use the default four".
-- `modules` is a JSON array of module ids in display order; the API validates it, the database only stores it.
CREATE TABLE dashboard_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    modules TEXT NOT NULL,
    updated TEXT NOT NULL
);
