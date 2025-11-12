#!/usr/bin/env python3
"""
Rollback helper to restore the legacy dashboard database (schema v1).
"""

from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parents[1]
OLD_DB = BASE_DIR / "gemini_cli_dashboard.db"
BACKUP_FILE = OLD_DB.with_suffix(".db.backup")


def rollback():
    if not BACKUP_FILE.exists():
        raise SystemExit(f"Backup file not found at {BACKUP_FILE}")

    shutil.copy2(BACKUP_FILE, OLD_DB)
    print(f"Restored {OLD_DB} from {BACKUP_FILE}")


if __name__ == "__main__":
    rollback()
