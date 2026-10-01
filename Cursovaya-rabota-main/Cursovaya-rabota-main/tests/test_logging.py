import logging


def test_failed_login_logged(client, app):
    records = []
    handler = logging.Handler()
    handler.emit = lambda r: records.append(r)
    app.logger.addHandler(handler)
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["csrf_token"] = "t"
        c.post("/login", data={"username": "alice", "password": "wrong", "csrf_token": "t"})
    app.logger.removeHandler(handler)
    assert any("login_failed" in r.getMessage() for r in records)


def test_csrf_failure_logged(client, app):
    records = []
    handler = logging.Handler()
    handler.emit = lambda r: records.append(r)
    app.logger.addHandler(handler)
    client.post("/login", data={"username": "a", "password": "b"})  # без csrf
    app.logger.removeHandler(handler)
    assert any("csrf" in r.getMessage().lower() for r in records)