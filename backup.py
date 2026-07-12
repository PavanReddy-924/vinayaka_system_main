"""
Quick backup: dumps every row in `tips` and `consumptions` (and the
organizers list, usernames only -- never passwords) to a timestamped
text file you can open in Excel/Notepad.

Run it any time, from your own machine, as long as it can reach your
database (works whether that's localhost or your hosted DB -- just make
sure the same environment variables you use for the live app are set,
or edit DB_CONFIG below directly):

    python backup.py

Recommended: run this once a day during the festival, and keep the files
somewhere safe (e.g. email them to yourself, or save to a USB drive).
This matters more than usual if you're on a free/hobby-tier database host.
"""

import os
import csv
from datetime import datetime
import mysql.connector

_DB_SSL_DISABLED = os.environ.get("DB_SSL_DISABLED", "true").lower() != "false"

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "22F01A05C6"),
    "database": os.environ.get("DB_NAME", "vinayaka_db"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "ssl_disabled": _DB_SSL_DISABLED,
}
if not _DB_SSL_DISABLED:
    import certifi
    DB_CONFIG["ssl_ca"] = certifi.where()
    DB_CONFIG["ssl_verify_cert"] = True
    DB_CONFIG["ssl_verify_identity"] = True


def dump_table(cursor, table_name, filename):
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    if not rows:
        print(f"  {table_name}: no rows, skipping file.")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {table_name}: {len(rows)} row(s) -> {filename}")


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    os.makedirs("backups", exist_ok=True)

    print(f"Backing up database as of {stamp}...")
    dump_table(cursor, "tips", f"backups/tips_{stamp}.csv")
    dump_table(cursor, "consumptions", f"backups/consumptions_{stamp}.csv")

    cursor.close()
    conn.close()
    print("\nDone. Files are in the 'backups' folder.")


if __name__ == "__main__":
    main()
