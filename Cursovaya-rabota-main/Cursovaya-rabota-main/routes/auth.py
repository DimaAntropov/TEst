import re
import secrets
import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db
from utils import login_required, safe_next

bp = Blueprint("auth", __name__)

@bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        error = None
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9_.-]{3,30}", username):
            error = "Логин: 3–30 букв, цифр или символов . _ -"
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            error = "Введите корректный email."
        elif len(password) < 8:
            error = "Пароль должен содержать не менее 8 символов."
        if error:
            flash(error, "danger")
        else:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO users(username,password_hash,email,phone) VALUES(?,?,?,?)",
                    (username, generate_password_hash(password), email, phone),
                )
                db.commit()
                flash("Регистрация завершена. Теперь войдите.", "success")
                return redirect(url_for("auth.login"))
            except sqlite3.IntegrityError:
                flash("Такой логин или email уже используется.", "danger")
    return render_template("register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Неверный логин или пароль.", "danger")
        elif not user["is_active"]:
            flash("Учётная запись заблокирована. Обратитесь к администратору.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_hex(24)
            flash(f"Добро пожаловать, {user['username']}!", "success")
            return redirect(safe_next(request.form.get("next")) or (url_for("admin.dashboard") if user["role"] == "admin" else url_for("main.index")))
    return render_template("login.html", next_url=request.args.get("next", ""))


@bp.post("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("main.index"))


@bp.post("/account/password")
@login_required
def change_password():
    current = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirmation = request.form.get("password_confirmation", "")

    if not check_password_hash(g.user["password_hash"], current):
        flash("Текущий пароль указан неверно.", "danger")
    elif len(new_password) < 8:
        flash("Новый пароль должен содержать не менее 8 символов.", "danger")
    elif new_password != confirmation:
        flash("Подтверждение нового пароля не совпадает.", "danger")
    elif current == new_password:
        flash("Новый пароль должен отличаться от текущего.", "warning")
    else:
        db = get_db()
        db.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (generate_password_hash(new_password), g.user["id"]),
        )
        db.commit()
        flash("Пароль успешно изменён.", "success")
    return redirect(url_for("booking.profile"))

