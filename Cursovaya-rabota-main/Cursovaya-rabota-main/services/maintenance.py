import logging
import sqlite3
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(app):
    log_dir = Path(app.instance_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "cinema.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def backup_database(database_path, backup_dir):
    source_path = Path(database_path)
    target_dir = Path(backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_path = target_dir / f"cinema_{stamp}.db"
    with sqlite3.connect(source_path) as source, sqlite3.connect(target_path) as target:
        source.backup(target)
    return target_path
