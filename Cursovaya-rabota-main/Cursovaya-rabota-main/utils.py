from functools import wraps

from flask import abort, flash, g, redirect, request, url_for


def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Сначала войдите в систему.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if g.user["role"] != "admin":
            abort(403)
        return view(**kwargs)
    return wrapped


def safe_next(value):
    return value if value and value.startswith("/") and not value.startswith("//") else None
