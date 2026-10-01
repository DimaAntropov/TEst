import threading
from database import get_db


def test_concurrent_booking_same_seat(app, seeded_db):
    """Два потока одновременно бронируют место 1-1."""
    results = []
    barrier = threading.Barrier(2)

    def worker():
        with app.test_client() as c:
            with c.session_transaction() as s:
                s["user_id"] = 2
                s["csrf_token"] = "fixed-token"
            barrier.wait()
            r = c.post(
                "/session/1/book",
                data={"seats": ["1-1"], "csrf_token": "fixed-token"},
            )
            results.append(r.status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert 500 not in results

    with app.app_context():
        row = get_db().execute(
            "SELECT COUNT(*) c FROM tickets WHERE session_id=1 "
            "AND row_num=1 AND seat_num=1 AND status!='cancelled'"
        ).fetchone()
        assert row["c"] == 1