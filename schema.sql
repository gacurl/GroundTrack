CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_row_no INTEGER,
    name TEXT NOT NULL,
    rank TEXT,
    nat TEXT,
    visit_request_status TEXT,
    badge_number TEXT,
    in_process_at TEXT,
    out_process_at TEXT,
    organization TEXT,
    thread_initiative TEXT,
    is_walkup INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_participants_badge_number
    ON participants (badge_number);

CREATE INDEX IF NOT EXISTS idx_participants_nat
    ON participants (nat);

CREATE INDEX IF NOT EXISTS idx_participants_thread_initiative
    ON participants (thread_initiative);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER,
    action TEXT NOT NULL,
    badge_number TEXT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants (id)
);

CREATE INDEX IF NOT EXISTS idx_activity_log_participant_id
    ON activity_log (participant_id);

CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp
    ON activity_log (timestamp);
