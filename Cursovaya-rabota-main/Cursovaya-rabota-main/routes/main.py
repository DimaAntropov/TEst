from datetime import datetime

from flask import Blueprint, render_template, request

from database import get_db

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    date_filter = request.args.get("date", "").strip()
    search = request.args.get("q", "").strip()
    sql = """
        SELECT s.*, m.title, m.genre, m.duration, m.description, h.name AS hall_name,
               h.rows_count * h.seats_per_row AS capacity,
               SUM(CASE WHEN t.status != 'cancelled' THEN 1 ELSE 0 END) AS occupied
        FROM sessions s
        JOIN movies m ON m.id=s.movie_id JOIN halls h ON h.id=s.hall_id
        LEFT JOIN tickets t ON t.session_id=s.id
        WHERE s.start_time >= ?
    """
    params = [datetime.now().isoformat(timespec="minutes")]
    if date_filter:
        sql += " AND date(s.start_time)=date(?)"
        params.append(date_filter)
    if search:
        sql += " AND (m.title LIKE ? OR m.genre LIKE ?)"
        pattern = f"%{search}%"
        params.extend((pattern, pattern))
    sql += " GROUP BY s.id ORDER BY s.start_time"
    shows = get_db().execute(sql, params).fetchall()
    return render_template(
        "index.html", shows=shows, date_filter=date_filter, search=search
    )

