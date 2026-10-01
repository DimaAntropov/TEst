import sqlite3
from datetime import datetime

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from database import get_db
from utils import login_required

bp = Blueprint("booking", __name__)

@bp.route("/session/<int:session_id>/book", methods=("GET", "POST"))
@login_required
def book(session_id):
    db = get_db()
    show = db.execute("""
        SELECT s.*,m.title,m.duration,h.name AS hall_name,h.rows_count,h.seats_per_row
        FROM sessions s JOIN movies m ON m.id=s.movie_id JOIN halls h ON h.id=s.hall_id
        WHERE s.id=?
    """, (session_id,)).fetchone()
    if show is None:
        abort(404)
    if show["start_time"] <= datetime.now().isoformat(timespec="minutes"):
        flash("Этот сеанс уже начался.", "warning")
        return redirect(url_for("main.index"))
    if request.method == "POST":
        selected = request.form.getlist("seats")
        if not selected or len(selected) > 10:
            flash("Выберите от 1 до 10 мест.", "danger")
        else:
            seats = []
            try:
                for value in selected:
                    row, seat = map(int, value.split("-", 1))
                    if not (1 <= row <= show["rows_count"] and 1 <= seat <= show["seats_per_row"]):
                        raise ValueError
                    seats.append((row, seat))
                if len(seats) != len(set(seats)):
                    raise ValueError
                db.execute("BEGIN IMMEDIATE")
                for row, seat in seats:
                    db.execute(
                        "INSERT INTO tickets(session_id,row_num,seat_num,user_id,status,price) VALUES(?,?,?,?,?,?)",
                        (session_id, row, seat, g.user["id"], "booked", show["price"]),
                    )
                db.commit()
                flash(f"Успешно забронировано мест: {len(seats)}. Сумма: {show['price'] * len(seats):.0f} ₽.", "success")
                return redirect(url_for("booking.profile"))
            except (ValueError, sqlite3.IntegrityError):
                db.rollback()
                flash("Одно из выбранных мест уже занято. Обновите схему и выберите другое.", "danger")
    occupied_rows = db.execute(
        "SELECT row_num,seat_num FROM tickets WHERE session_id=? AND status!='cancelled'", (session_id,)
    ).fetchall()
    occupied = {(x["row_num"], x["seat_num"]) for x in occupied_rows}
    return render_template("book.html", show=show, occupied=occupied)


@bp.route("/profile")
@login_required
def profile():
    tickets = get_db().execute("""
        SELECT t.*,m.title,s.start_time,h.name AS hall_name
        FROM tickets t JOIN sessions s ON s.id=t.session_id
        JOIN movies m ON m.id=s.movie_id JOIN halls h ON h.id=s.hall_id
        WHERE t.user_id=? AND t.status!='cancelled'
        ORDER BY t.booking_date DESC,t.id DESC
    """, (g.user["id"],)).fetchall()
    return render_template("profile.html", tickets=tickets)


@bp.post("/ticket/<int:ticket_id>/cancel")
@login_required
def cancel_ticket(ticket_id):
    db = get_db()
    ticket = db.execute("""
        SELECT t.*,s.start_time FROM tickets t JOIN sessions s ON s.id=t.session_id
        WHERE t.id=? AND t.user_id=?
    """, (ticket_id, g.user["id"])).fetchone()
    if ticket is None:
        abort(404)
    if ticket["status"] != "booked" or ticket["start_time"] <= datetime.now().isoformat(timespec="minutes"):
        flash("Эту бронь нельзя отменить.", "danger")
    else:
        # Сохраняем отмену для аудита, но скрываем её из личного кабинета.
        db.execute(
            "UPDATE tickets SET status='cancelled' WHERE id=? AND user_id=?",
            (ticket_id, g.user["id"]),
        )
        db.commit()
        flash("Бронь отменена.", "success")
    return redirect(url_for("booking.profile"))

