import os
import secrets
from datetime import datetime
from pathlib import Path

import click
from flask import (
    Flask, abort, flash, g, render_template, request, session, current_app,
)

from database import get_db, init_app as init_database, init_db
from routes.admin import bp as admin_bp
from routes.auth import bp as auth_bp
from routes.booking import bp as booking_bp
from routes.main import bp as main_bp
from seed import seed_data
from services.maintenance import backup_database, configure_logging

BASE_DIR = Path(__file__).resolve().parent


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    secret_file = BASE_DIR / ".secret_key"
    if os.environ.get("SECRET_KEY"):
        secret_key = os.environ["SECRET_KEY"]
    elif secret_file.exists():
        secret_key = secret_file.read_text(encoding="utf-8").strip()
    else:
        secret_key = secrets.token_hex(32)
        secret_file.write_text(secret_key, encoding="utf-8")

    app.config.update(
        SECRET_KEY=secret_key,
        DATABASE=str(Path(app.instance_path) / "cinema.db"),
        MAX_CONTENT_LENGTH=1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    )

    init_database(app)
    configure_logging(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    # ─── BEFORE REQUEST: загрузка пользователя + CSRF ────────────────────
    @app.before_request
    def load_user_and_check_csrf():
        # 1. Загрузка пользователя
        user_id = session.get("user_id")
        g.user = (
            get_db().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if user_id else None
        )

        if g.user is not None and not g.user["is_active"]:
            current_app.logger.warning(
                "blocked_user_session user_id=%s ip=%s",
                g.user["id"], request.remote_addr,
            )
            session.clear()
            g.user = None
            flash("Учётная запись заблокирована администратором.", "danger")

        # 2. Гарантируем наличие CSRF-токена в сессии
        if not session.get("csrf_token"):
            session["csrf_token"] = secrets.token_hex(24)

        # 3. Проверка CSRF на POST
        if request.method == "POST":
            token = request.form.get("csrf_token") or ""
            expected = session.get("csrf_token") or ""

            ok = False
            try:
                ok = secrets.compare_digest(str(token), str(expected))
            except TypeError:
                ok = False

            if not ok:
                current_app.logger.warning(
                    "csrf_failed ip=%s path=%s user_id=%s",
                    request.remote_addr, request.path, session.get("user_id"),
                )
                abort(400, "Недействительный CSRF-токен. Обновите страницу.")

    # ─── AFTER REQUEST: заголовки безопасности ──────────────────────────
    @app.after_request
    def set_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'",
        )
        if os.environ.get("FLASK_ENV") == "production":
            resp.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return resp

    # ─── CONTEXT PROCESSOR ─────────────────────────────────────────────
    @app.context_processor
    def template_helpers():
        def format_dt(value, fmt="%d.%m.%Y %H:%M"):
            try:
                return datetime.fromisoformat(value).strftime(fmt)
            except (TypeError, ValueError):
                return value
        return {
            "csrf_token": session.get("csrf_token") or "",
            "format_dt": format_dt,
            "now_iso": datetime.now().isoformat(timespec="minutes"),
        }

    # ─── ERROR HANDLERS ────────────────────────────────────────────────
    def error_page(error):
        code = getattr(error, "code", 500)
        messages = {
            400: "Некорректный запрос",
            403: "Доступ запрещён",
            404: "Страница не найдена",
            413: "Файл слишком большой",
            500: "Ошибка сервера",
        }
        return render_template(
            "error.html", code=code, message=messages.get(code, "Ошибка")
        ), code

    for code in (400, 403, 404, 413, 500):
        app.register_error_handler(code, error_page)

    # ─── HEALTH ────────────────────────────────────────────────────────
    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return {"status": "ok"}

    # ─── CLI: backup-db ────────────────────────────────────────────────
    @app.cli.command("backup-db")
    @click.option("--output", default=None, help="Каталог для резервных копий")
    def backup_db_command(output):
        """Создать согласованную резервную копию SQLite."""
        backup_dir = output or str(Path(app.instance_path) / "backups")
        result = backup_database(app.config["DATABASE"], backup_dir)
        click.echo(f"Резервная копия создана: {result}")

    # ─── Инициализация БД и seed ───────────────────────────────────────
    with app.app_context():
        init_db()
        seed_data()

    return app


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=5600, debug=debug)