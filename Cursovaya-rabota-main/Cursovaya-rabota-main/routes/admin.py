import re
import sqlite3
from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from database import get_db
from utils import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.route("")
@admin_required
def dashboard():
    db = get_db()
    counts = {
        "movies": db.execute("SELECT COUNT(*) n FROM movies").fetchone()["n"],
        "halls": db.execute("SELECT COUNT(*) n FROM halls").fetchone()["n"],
        "sessions": db.execute("SELECT COUNT(*) n FROM sessions WHERE start_time>=?", (datetime.now().isoformat(timespec="minutes"),)).fetchone()["n"],
        "tickets": db.execute("SELECT COUNT(*) n FROM tickets WHERE status!='cancelled'").fetchone()["n"],
        "users": db.execute("SELECT COUNT(*) n FROM users").fetchone()["n"],
    }
    return render_template("admin/dashboard.html", counts=counts)


@bp.route("/users")
@admin_required
def users():
    search = request.args.get("q", "").strip()
    role = request.args.get("role", "all")
    state = request.args.get("state", "all")
    conditions = []
    params = []
    if search:
        pattern = f"%{search}%"
        conditions.append("(u.username LIKE ? OR u.email LIKE ? OR u.phone LIKE ?)")
        params.extend((pattern, pattern, pattern))
    if role in {"admin", "customer"}:
        conditions.append("u.role=?")
        params.append(role)
    if state == "active":
        conditions.append("u.is_active=1")
    elif state == "blocked":
        conditions.append("u.is_active=0")
    where = " AND ".join(conditions) or "1=1"
    rows = get_db().execute(
        f"""SELECT u.*,
            SUM(CASE WHEN t.status!='cancelled' THEN 1 ELSE 0 END) active_tickets,
            COUNT(t.id) all_tickets
            FROM users u LEFT JOIN tickets t ON t.user_id=u.id
            WHERE {where} GROUP BY u.id
            ORDER BY CASE WHEN u.role='admin' THEN 0 ELSE 1 END,u.created_at DESC""",
        params,
    ).fetchall()
    return render_template(
        "admin/users.html", users=rows, search=search, role=role, state=state
    )


@bp.route("/user/<int:user_id>/edit", methods=("GET", "POST"))
@admin_required
def user_edit(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        role = request.form.get("role", "customer")
        new_password = request.form.get("new_password", "")
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9_.-]{3,30}", username):
            flash("Проверьте логин пользователя.", "danger")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Введите корректный email.", "danger")
        elif role not in {"admin", "customer"}:
            flash("Указана неизвестная роль.", "danger")
        elif user_id == g.user["id"] and role != "admin":
            flash("Нельзя снять роль администратора у собственной учётной записи.", "danger")
        elif (user["role"] == "admin" and role != "admin" and user["is_active"]
              and db.execute("SELECT COUNT(*) n FROM users WHERE role='admin' AND is_active=1").fetchone()["n"] <= 1):
            flash("Нельзя снять роль у последнего активного администратора.", "danger")
        elif new_password and len(new_password) < 8:
            flash("Новый пароль должен содержать не менее 8 символов.", "danger")
        else:
            try:
                if new_password:
                    db.execute(
                        """UPDATE users SET username=?,email=?,phone=?,role=?,password_hash=?
                           WHERE id=?""",
                        (username, email, phone, role, generate_password_hash(new_password), user_id),
                    )
                else:
                    db.execute(
                        "UPDATE users SET username=?,email=?,phone=?,role=? WHERE id=?",
                        (username, email, phone, role, user_id),
                    )
                db.commit()
                flash("Данные пользователя обновлены.", "success")
                return redirect(url_for("admin.users"))
            except sqlite3.IntegrityError:
                db.rollback()
                flash("Такой логин или email уже занят.", "danger")
    return render_template("admin/user_edit.html", item=user)


@bp.post("/user/<int:user_id>/toggle")
@admin_required
def user_toggle(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    if user_id == g.user["id"]:
        flash("Нельзя заблокировать собственную учётную запись.", "danger")
    elif user["role"] == "admin" and user["is_active"]:
        active_admins = db.execute(
            "SELECT COUNT(*) n FROM users WHERE role='admin' AND is_active=1"
        ).fetchone()["n"]
        if active_admins <= 1:
            flash("Нельзя заблокировать последнего активного администратора.", "danger")
            return redirect(url_for("admin.users"))
        db.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
        db.commit()
        flash("Пользователь заблокирован.", "success")
    else:
        new_state = 0 if user["is_active"] else 1
        db.execute("UPDATE users SET is_active=? WHERE id=?", (new_state, user_id))
        db.commit()
        flash("Пользователь разблокирован." if new_state else "Пользователь заблокирован.", "success")
    return redirect(request.referrer or url_for("admin.users"))


@bp.post("/user/<int:user_id>/delete")
@admin_required
def user_delete(user_id):
    db = get_db()
    if user_id == g.user["id"]:
        flash("Нельзя удалить собственную учётную запись.", "danger")
        return redirect(url_for("admin.users"))
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    tickets_count = db.execute(
        "SELECT COUNT(*) n FROM tickets WHERE user_id=?", (user_id,)
    ).fetchone()["n"]
    if tickets_count:
        flash("Пользователя с историей билетов нельзя удалить — его можно заблокировать.", "danger")
    else:
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()
        flash("Пользователь удалён.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/movies", methods=("GET", "POST"))
@admin_required
def movies():
    db = get_db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        genre = request.form.get("genre", "").strip()
        description = request.form.get("description", "").strip()
        try:
            duration = int(request.form.get("duration", "0"))
            if not title or not genre or not 1 <= duration <= 600:
                raise ValueError
            db.execute("INSERT INTO movies(title,genre,duration,description) VALUES(?,?,?,?)", (title, genre, duration, description))
            db.commit(); flash("Фильм добавлен.", "success")
            return redirect(url_for("admin.movies"))
        except ValueError:
            flash("Проверьте название, жанр и длительность.", "danger")
    movies = db.execute("SELECT * FROM movies ORDER BY title").fetchall()
    return render_template("admin/movies.html", movies=movies)


@bp.route("/movie/<int:item_id>/edit", methods=("GET", "POST"))
@admin_required
def movie_edit(item_id):
    db = get_db(); item = db.execute("SELECT * FROM movies WHERE id=?", (item_id,)).fetchone()
    if not item: abort(404)
    if request.method == "POST":
        try:
            title=request.form.get("title","").strip(); genre=request.form.get("genre","").strip()
            duration=int(request.form.get("duration","0")); description=request.form.get("description","").strip()
            if not title or not genre or duration < 1: raise ValueError
            db.execute("UPDATE movies SET title=?,genre=?,duration=?,description=? WHERE id=?", (title,genre,duration,description,item_id))
            db.commit(); flash("Фильм обновлён.", "success"); return redirect(url_for("admin.movies"))
        except ValueError: flash("Проверьте данные.", "danger")
    return render_template("admin/movie_edit.html", item=item)


@bp.post("/movie/<int:item_id>/delete")
@admin_required
def admin_movie_delete(item_id):
    db=get_db()
    try:
        db.execute("DELETE FROM movies WHERE id=?",(item_id,)); db.commit(); flash("Фильм удалён.","success")
    except sqlite3.IntegrityError:
        db.rollback(); flash("Нельзя удалить фильм, пока для него существуют сеансы.","danger")
    return redirect(url_for("admin.movies"))


@bp.route("/halls", methods=("GET", "POST"))
@admin_required
def halls():
    db=get_db()
    if request.method == "POST":
        try:
            name=request.form.get("name","").strip(); rows=int(request.form.get("rows_count","0")); seats=int(request.form.get("seats_per_row","0"))
            if not name or not 1<=rows<=30 or not 1<=seats<=40: raise ValueError
            db.execute("INSERT INTO halls(name,rows_count,seats_per_row) VALUES(?,?,?)",(name,rows,seats)); db.commit()
            flash("Зал добавлен.","success"); return redirect(url_for("admin.halls"))
        except ValueError: flash("Проверьте параметры зала.","danger")
        except sqlite3.IntegrityError: flash("Зал с таким названием уже существует.","danger")
    halls=db.execute("SELECT * FROM halls ORDER BY name").fetchall()
    return render_template("admin/halls.html",halls=halls)


@bp.route("/hall/<int:item_id>/edit", methods=("GET","POST"))
@admin_required
def hall_edit(item_id):
    db=get_db(); item=db.execute("SELECT * FROM halls WHERE id=?",(item_id,)).fetchone()
    if not item: abort(404)
    if request.method == "POST":
        try:
            name=request.form.get("name","").strip(); rows=int(request.form.get("rows_count","0")); seats=int(request.form.get("seats_per_row","0"))
            if not name or not 1<=rows<=30 or not 1<=seats<=40: raise ValueError
            max_used=db.execute("SELECT MAX(row_num) r,MAX(seat_num) s FROM tickets t JOIN sessions x ON x.id=t.session_id WHERE x.hall_id=? AND t.status!='cancelled'",(item_id,)).fetchone()
            if (max_used["r"] or 0)>rows or (max_used["s"] or 0)>seats:
                flash("Нельзя уменьшить зал: имеются брони на удаляемые места.","danger")
            else:
                db.execute("UPDATE halls SET name=?,rows_count=?,seats_per_row=? WHERE id=?",(name,rows,seats,item_id)); db.commit()
                flash("Зал обновлён.","success"); return redirect(url_for("admin.halls"))
        except (ValueError,sqlite3.IntegrityError): flash("Проверьте данные и уникальность названия.","danger")
    return render_template("admin/hall_edit.html",item=item)


@bp.post("/hall/<int:item_id>/delete")
@admin_required
def hall_delete(item_id):
    db = get_db()
    try:
        db.execute("DELETE FROM halls WHERE id=?", (item_id,))
        db.commit()
        flash("Зал удалён.", "success")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("Нельзя удалить зал, пока для него существуют сеансы.", "danger")
    return redirect(url_for("admin.halls"))


def has_overlap(db, hall_id, start_time, duration, exclude=None):
    new_start=datetime.fromisoformat(start_time); new_end=new_start+timedelta(minutes=duration)
    rows=db.execute("""SELECT s.id,s.start_time,m.duration FROM sessions s JOIN movies m ON m.id=s.movie_id
                       WHERE s.hall_id=? AND (? IS NULL OR s.id!=?)""",(hall_id,exclude,exclude)).fetchall()
    for row in rows:
        old_start=datetime.fromisoformat(row["start_time"]); old_end=old_start+timedelta(minutes=row["duration"])
        if new_start < old_end and old_start < new_end: return True
    return False


@bp.route("/sessions", methods=("GET","POST"))
@admin_required
def sessions():
    db=get_db()
    if request.method == "POST":
        try:
            movie_id=int(request.form.get("movie_id","0")); hall_id=int(request.form.get("hall_id","0")); price=float(request.form.get("price","-1")); start=request.form.get("start_time","")
            movie=db.execute("SELECT * FROM movies WHERE id=?",(movie_id,)).fetchone(); hall=db.execute("SELECT * FROM halls WHERE id=?",(hall_id,)).fetchone()
            datetime.fromisoformat(start)
            if not movie or not hall or price<0: raise ValueError
            if has_overlap(db,hall_id,start,movie["duration"]):
                flash("В это время зал занят другим сеансом.","danger")
            else:
                db.execute("INSERT INTO sessions(movie_id,hall_id,start_time,price) VALUES(?,?,?,?)",(movie_id,hall_id,start,price)); db.commit()
                flash("Сеанс добавлен.","success"); return redirect(url_for("admin.sessions"))
        except ValueError: flash("Проверьте дату, фильм, зал и цену.","danger")
    shows=db.execute("""SELECT s.*,m.title,m.duration,h.name hall_name,(SELECT COUNT(*) FROM tickets t WHERE t.session_id=s.id AND t.status!='cancelled') occupied
                         FROM sessions s JOIN movies m ON m.id=s.movie_id JOIN halls h ON h.id=s.hall_id ORDER BY s.start_time DESC""").fetchall()
    return render_template("admin/sessions.html",shows=shows,movies=db.execute("SELECT * FROM movies ORDER BY title").fetchall(),halls=db.execute("SELECT * FROM halls ORDER BY name").fetchall())


@bp.route("/session/<int:item_id>/edit", methods=("GET", "POST"))
@admin_required
def session_edit(item_id):
    db = get_db()
    item = db.execute("SELECT * FROM sessions WHERE id=?", (item_id,)).fetchone()
    if item is None:
        abort(404)
    if request.method == "POST":
        try:
            movie_id = int(request.form.get("movie_id", "0"))
            hall_id = int(request.form.get("hall_id", "0"))
            price = float(request.form.get("price", "-1"))
            start = request.form.get("start_time", "")
            movie = db.execute("SELECT * FROM movies WHERE id=?", (movie_id,)).fetchone()
            hall = db.execute("SELECT * FROM halls WHERE id=?", (hall_id,)).fetchone()
            datetime.fromisoformat(start)
            if not movie or not hall or price < 0:
                raise ValueError
            if has_overlap(db, hall_id, start, movie["duration"], exclude=item_id):
                flash("В это время зал занят другим сеансом.", "danger")
            else:
                db.execute(
                    "UPDATE sessions SET movie_id=?,hall_id=?,start_time=?,price=? WHERE id=?",
                    (movie_id, hall_id, start, price, item_id),
                )
                db.commit()
                flash("Сеанс обновлён.", "success")
                return redirect(url_for("admin.sessions"))
        except ValueError:
            flash("Проверьте дату, фильм, зал и цену.", "danger")
    return render_template(
        "admin/session_edit.html",
        item=item,
        movies=db.execute("SELECT * FROM movies ORDER BY title").fetchall(),
        halls=db.execute("SELECT * FROM halls ORDER BY name").fetchall(),
    )


@bp.post("/session/<int:item_id>/delete")
@admin_required
def admin_session_delete(item_id):
    db=get_db()
    active=db.execute("SELECT COUNT(*) n FROM tickets WHERE session_id=? AND status!='cancelled'",(item_id,)).fetchone()["n"]
    if active: flash("Нельзя удалить сеанс с действующими бронями.","danger")
    else:
        db.execute("DELETE FROM sessions WHERE id=?",(item_id,));db.commit();flash("Сеанс удалён.","success")
    return redirect(url_for("admin.sessions"))


@bp.route("/reports")
@admin_required
def reports():
    db = get_db()
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    date_conditions = []
    params = []
    if start:
        date_conditions.append("date(s.start_time)>=date(?)")
        params.append(start)
    if end:
        date_conditions.append("date(s.start_time)<=date(?)")
        params.append(end)
    date_where = " AND ".join(date_conditions) or "1=1"

    summary = db.execute(
        f"""SELECT
                SUM(CASE WHEN t.status!='cancelled' THEN 1 ELSE 0 END) tickets,
                COALESCE(SUM(CASE WHEN t.status='paid' THEN t.price ELSE 0 END),0) paid_revenue,
                COALESCE(SUM(CASE WHEN t.status='booked' THEN t.price ELSE 0 END),0) expected_revenue
            FROM tickets t JOIN sessions s ON s.id=t.session_id
            WHERE {date_where}""",
        params,
    ).fetchone()
    rows = db.execute(
        f"""SELECT s.id,m.title,s.start_time,h.name hall_name,
                h.rows_count*h.seats_per_row capacity,
                SUM(CASE WHEN t.status!='cancelled' THEN 1 ELSE 0 END) occupied,
                COALESCE(SUM(CASE WHEN t.status='paid' THEN t.price ELSE 0 END),0) paid_revenue
            FROM sessions s JOIN movies m ON m.id=s.movie_id
            JOIN halls h ON h.id=s.hall_id
            LEFT JOIN tickets t ON t.session_id=s.id
            WHERE {date_where}
            GROUP BY s.id ORDER BY s.start_time DESC""",
        params,
    ).fetchall()
    return render_template(
        "admin/reports.html", summary=summary, rows=rows, start=start, end=end
    )


@bp.route("/tickets")
@admin_required
def tickets():
    status = request.args.get("status", "active")
    query = request.args.get("q", "").strip()
    conditions = []
    params = []
    if status == "active":
        conditions.append("t.status!='cancelled'")
    elif status in {"booked", "paid", "cancelled"}:
        conditions.append("t.status=?")
        params.append(status)
    if query:
        conditions.append("(u.username LIKE ? OR m.title LIKE ?)")
        pattern = f"%{query}%"
        params.extend((pattern, pattern))
    where = " AND ".join(conditions) or "1=1"
    rows = get_db().execute(
        f"""SELECT t.*,u.username,m.title,s.start_time,h.name hall_name
            FROM tickets t JOIN users u ON u.id=t.user_id
            JOIN sessions s ON s.id=t.session_id
            JOIN movies m ON m.id=s.movie_id JOIN halls h ON h.id=s.hall_id
            WHERE {where} ORDER BY t.booking_date DESC,t.id DESC""",
        params,
    ).fetchall()
    return render_template(
        "admin/tickets.html", tickets=rows, status=status, search=query
    )


@bp.post("/ticket/<int:ticket_id>/cancel")
@admin_required
def cancel_ticket(ticket_id):
    db = get_db()
    db.execute(
        "UPDATE tickets SET status='cancelled' WHERE id=? AND status='booked'",
        (ticket_id,),
    )
    db.commit()
    flash("Бронь отменена администратором.", "success")
    return redirect(request.referrer or url_for("admin.tickets"))


@bp.post("/ticket/<int:ticket_id>/paid")
@admin_required
def mark_paid(ticket_id):
    db=get_db();db.execute("UPDATE tickets SET status='paid' WHERE id=? AND status='booked'",(ticket_id,));db.commit()
    flash("Билет отмечен как оплаченный.","success");return redirect(request.referrer or url_for("admin.reports"))

