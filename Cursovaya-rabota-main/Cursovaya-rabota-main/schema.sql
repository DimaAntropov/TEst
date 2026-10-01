PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    phone TEXT,
    role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN ('admin', 'customer')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    genre TEXT NOT NULL,
    duration INTEGER NOT NULL CHECK(duration > 0),
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS halls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    rows_count INTEGER NOT NULL CHECK(rows_count BETWEEN 1 AND 30),
    seats_per_row INTEGER NOT NULL CHECK(seats_per_row BETWEEN 1 AND 40)
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE RESTRICT,
    hall_id INTEGER NOT NULL REFERENCES halls(id) ON DELETE RESTRICT,
    start_time TEXT NOT NULL,
    price REAL NOT NULL CHECK(price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_sessions_hall ON sessions(hall_id, start_time);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE RESTRICT,
    row_num INTEGER NOT NULL CHECK(row_num > 0),
    seat_num INTEGER NOT NULL CHECK(seat_num > 0),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'booked' CHECK(status IN ('booked', 'paid', 'cancelled')),
    price REAL NOT NULL CHECK(price >= 0),
    booking_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_seat
ON tickets(session_id, row_num, seat_num)
WHERE status != 'cancelled';

CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id, booking_date);
CREATE INDEX IF NOT EXISTS idx_tickets_session ON tickets(session_id, status);
