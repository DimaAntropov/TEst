from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from database import get_db

def seed_data():
    db = get_db()
    if not db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        db.execute(
            "INSERT INTO users(username,password_hash,email,phone,role) VALUES(?,?,?,?,?)",
            ("admin", generate_password_hash("Admin123!"), "admin@cinema.local", "", "admin"),
        )
    if not db.execute("SELECT 1 FROM halls LIMIT 1").fetchone():
        db.executemany(
            "INSERT INTO halls(name,rows_count,seats_per_row) VALUES(?,?,?)",
            [("Красный зал", 6, 10), ("Синий зал", 5, 8)],
        )
    if not db.execute("SELECT 1 FROM movies LIMIT 1").fetchone():
        db.executemany(
            "INSERT INTO movies(title,genre,duration,description) VALUES(?,?,?,?)",
            [
                ("Путь к звёздам", "Фантастика", 118, "Космическое путешествие и история о смелости."),
                ("Последний билет", "Комедия", 96, "Лёгкая комедия о случайной встрече в кинотеатре."),
                ("Тайна старого дома", "Детектив", 110, "Запутанное расследование с неожиданной развязкой."),
            ],
        )
    # Старые демонстрационные сеансы остаются в базе, однако главная страница
    # показывает только будущие. Поэтому новое расписание создаётся не только
    # для пустой таблицы, но и в случае, когда все существующие сеансы прошли.
    now_iso = datetime.now().isoformat(timespec="minutes")
    has_future_sessions = db.execute(
        "SELECT 1 FROM sessions WHERE start_time >= ? LIMIT 1", (now_iso,)
    ).fetchone()
    if not has_future_sessions:
        movies = db.execute("SELECT id FROM movies ORDER BY id LIMIT 3").fetchall()
        halls = db.execute("SELECT id FROM halls ORDER BY id LIMIT 2").fetchall()
        base = (datetime.now() + timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        rows = []
        for day in range(3):
            rows.extend([
                (movies[0]["id"], halls[0]["id"], (base + timedelta(days=day)).isoformat(timespec="minutes"), 450),
                (movies[1]["id"], halls[1]["id"], (base + timedelta(days=day, hours=2)).isoformat(timespec="minutes"), 350),
                (movies[2]["id"], halls[0]["id"], (base + timedelta(days=day, hours=3)).isoformat(timespec="minutes"), 400),
            ])
        db.executemany(
            "INSERT INTO sessions(movie_id,hall_id,start_time,price) VALUES(?,?,?,?)",
            rows,
        )
    db.commit()
