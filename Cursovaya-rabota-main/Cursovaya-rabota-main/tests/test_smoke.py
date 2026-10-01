"""Smoke-тесты: минимальная проверка, что приложение поднимается."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# ─── Корень проекта в sys.path (обязательно для запуска из tests/) ────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("FLASK_ENV", "testing")


class CinemaSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "smoke.db"

        # Передаём БД через env до создания приложения
        os.environ["DATABASE"] = str(cls._db_path)

        from app import create_app
        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()
        os.environ.pop("DATABASE", None)

    def setUp(self):
        self.client = self.app.test_client()

    def test_public_pages_return_200(self):
        for path in ("/", "/login", "/register", "/health"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_admin_requires_login(self):
        r = self.client.get("/admin")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_profile_requires_login(self):
        r = self.client.get("/profile")
        self.assertEqual(r.status_code, 302)

    def test_missing_page_returns_404(self):
        self.assertEqual(self.client.get("/missing-page").status_code, 404)

    def test_health_endpoint(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok"})

    def test_security_headers_present(self):
        r = self.client.get("/")
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("Content-Security-Policy", r.headers)

    def test_csrf_required_for_post(self):
        r = self.client.post("/login", data={"username": "a", "password": "b"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()