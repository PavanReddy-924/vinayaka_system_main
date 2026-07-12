"""
Run this ONCE to create the database tables and your first organizer login.

    python setup_db.py

It will ask you to type a username and password for the committee account
(since there's no register page, this is how the first -- and any later --
login gets created).
"""

import os
import getpass
import mysql.connector
from werkzeug.security import generate_password_hash

_DB_SSL_DISABLED = os.environ.get("DB_SSL_DISABLED", "true").lower() != "false"

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "22F01A05C6"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "ssl_disabled": _DB_SSL_DISABLED,
}
if not _DB_SSL_DISABLED:
    import certifi
    DB_CONFIG["ssl_ca"] = certifi.where()
    DB_CONFIG["ssl_verify_cert"] = True
    DB_CONFIG["ssl_verify_identity"] = True

DB_NAME = os.environ.get("DB_NAME", "vinayaka_db")

SCHEMA = f"""
CREATE DATABASE IF NOT EXISTS {DB_NAME};
USE {DB_NAME};

CREATE TABLE IF NOT EXISTS organizers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipper_name VARCHAR(100) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS consumptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purpose VARCHAR(200) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    for statement in SCHEMA.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
    conn.commit()
    print(f"Database '{DB_NAME}' and tables are ready.\n")

    cursor.execute(f"USE {DB_NAME}")
    cursor.execute("SELECT COUNT(*) FROM organizers")
    existing = cursor.fetchone()[0]

    if existing:
        print(f"There are already {existing} organizer login(s) in the database.")
        again = input("Add another one anyway? (y/N): ").strip().lower()
        if again != "y":
            cursor.close()
            conn.close()
            return

    username = input("Choose a username for the committee login: ").strip()
    password = getpass.getpass("Choose a password: ").strip()

    if not username or not password:
        print("Username and password cannot be empty. Nothing was created.")
        return

    hashed = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO organizers (username, password) VALUES (%s, %s)",
        (username, hashed),
    )
    conn.commit()
    print(f"\nLogin created for '{username}'. You can now start the app and log in.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
