"""
Vinayaka Chavithi Committee Fund Tracker
-----------------------------------------
A small Flask app for a festival organizing team to track:
  - who tipped / contributed how much
  - what the money was spent on (consumptions)
  - running totals & net balance, so nobody has to count cash by hand 3 times

Tables used (MySQL):
  organizers   -> login accounts for committee members
  tips         -> every contribution received
  consumptions -> every expense made
"""

import os
from functools import wraps
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()  # reads variables from a local .env file, if one exists

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g
)
import mysql.connector
from mysql.connector import errorcode

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "change-this-to-a-long-random-secret-in-production"
)

# ---------------------------------------------------------------------------
# Database config
# ---------------------------------------------------------------------------
# Reads from environment variables when they're set (that's how the hosting
# platform will configure it), and falls back to your local MySQL values
# when they're not set (so `python app.py` on your own machine still works
# exactly as before, with nothing extra to configure).
_DB_SSL_DISABLED = os.environ.get("DB_SSL_DISABLED", "true").lower() != "false"

DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_NAME"),
    "port": int(os.environ.get("DB_PORT", "4000")),
    "ssl_disabled": _DB_SSL_DISABLED,
}


# TiDB Cloud (and similar hosts) require a verified TLS connection, not just
# an encrypted one. `certifi` ships the same public CA bundle browsers trust,
# so we point ssl_ca at it instead of asking you to find/download a CA file
# yourself. This only runs when DB_SSL_DISABLED=false is set (i.e. never for
# a normal local MySQL install).
if not _DB_SSL_DISABLED:
    import certifi
    DB_CONFIG["ssl_ca"] = certifi.where()
    DB_CONFIG["ssl_verify_cert"] = True
    DB_CONFIG["ssl_verify_identity"] = True



def get_db():
    """
    Open one connection per request (stored on flask.g) instead of a single
    global connection. A long-lived global connection eventually gets
    dropped by MySQL ('MySQL server has gone away') which is a common
    source of random crashes in small Flask + MySQL apps.
    """
    if "db" not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None and db.is_connected():
        db.close()


def query(sql, params=None, fetch=None, commit=False):
    """Small helper so routes don't repeat cursor boilerplate."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(sql, params or ())
    result = None
    if fetch == "one":
        result = cursor.fetchone()
    elif fetch == "all":
        result = cursor.fetchall()
    if commit:
        db.commit()
        result = cursor.lastrowid
    cursor.close()
    return result


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Totals helper (used on dashboard + collections page)
# ---------------------------------------------------------------------------
def get_totals():
    total_tips = query("SELECT COALESCE(SUM(amount), 0) AS t FROM tips", fetch="one")["t"]
    total_consumed = query("SELECT COALESCE(SUM(amount), 0) AS t FROM consumptions", fetch="one")["t"]
    tip_count = query("SELECT COUNT(*) AS c FROM tips", fetch="one")["c"]
    consumption_count = query("SELECT COUNT(*) AS c FROM consumptions", fetch="one")["c"]
    return {
        "total_tips": float(total_tips),
        "total_consumed": float(total_consumed),
        "net_balance": float(total_tips) - float(total_consumed),
        "tip_count": tip_count,
        "consumption_count": consumption_count,
    }


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = query(
            "SELECT * FROM organizers WHERE username = %s AND password = %s",
            (username, password), fetch="one"
        )

        if user:
            session.clear()
            session["user"] = user["username"]
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")
        return redirect(url_for("login"))

    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard (hub only -- links out to each feature, doesn't dump every form)
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    totals = get_totals()
    recent_tips = query(
        "SELECT * FROM tips ORDER BY timestamp DESC LIMIT 5", fetch="all"
    )
    recent_consumptions = query(
        "SELECT * FROM consumptions ORDER BY timestamp DESC LIMIT 5", fetch="all"
    )
    return render_template(
        "dashboard.html",
        totals=totals,
        recent_tips=recent_tips,
        recent_consumptions=recent_consumptions,
    )


# ---------------------------------------------------------------------------
# Tips (tippers)
# ---------------------------------------------------------------------------
@app.route("/tips", methods=["GET", "POST"])
@login_required
def tips():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        amount = request.form.get("amount", "").strip()

        if not name or not amount:
            flash("Please enter both a name and an amount.", "error")
            return redirect(url_for("tips"))
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "error")
            return redirect(url_for("tips"))

        query(
            "INSERT INTO tips (tipper_name, amount) VALUES (%s, %s)",
            (name, amount_val), commit=True
        )
        flash(f"Added ₹{amount_val:,.2f} from {name}.", "success")
        return redirect(url_for("tips"))

    all_tips = query("SELECT * FROM tips ORDER BY timestamp DESC", fetch="all")
    total = sum(float(t["amount"]) for t in all_tips) if all_tips else 0.0
    return render_template("tips.html", tips=all_tips, total=total)


@app.route("/tips/<int:tip_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tip(tip_id):
    tip = query("SELECT * FROM tips WHERE id = %s", (tip_id,), fetch="one")
    if not tip:
        flash("That tip entry no longer exists.", "error")
        return redirect(url_for("tips"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        amount = request.form.get("amount", "").strip()
        try:
            amount_val = float(amount)
            if not name or amount_val <= 0:
                raise ValueError
        except ValueError:
            flash("Please provide a valid name and a positive amount.", "error")
            return redirect(url_for("edit_tip", tip_id=tip_id))

        query(
            "UPDATE tips SET tipper_name = %s, amount = %s WHERE id = %s",
            (name, amount_val, tip_id), commit=True
        )
        flash("Tip entry updated.", "success")
        return redirect(url_for("tips"))

    return render_template("edit_entry.html", entry=tip, kind="tip")


@app.route("/tips/<int:tip_id>/delete", methods=["POST"])
@login_required
def delete_tip(tip_id):
    query("DELETE FROM tips WHERE id = %s", (tip_id,), commit=True)
    flash("Tip entry deleted.", "success")
    return redirect(url_for("tips"))


# ---------------------------------------------------------------------------
# Consumptions (expenses)
# ---------------------------------------------------------------------------
@app.route("/consumptions", methods=["GET", "POST"])
@login_required
def consumptions():
    if request.method == "POST":
        purpose = request.form.get("purpose", "").strip()
        amount = request.form.get("amount", "").strip()

        if not purpose or not amount:
            flash("Please enter both a purpose and an amount.", "error")
            return redirect(url_for("consumptions"))
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "error")
            return redirect(url_for("consumptions"))

        query(
            "INSERT INTO consumptions (purpose, amount) VALUES (%s, %s)",
            (purpose, amount_val), commit=True
        )
        flash(f"Recorded ₹{amount_val:,.2f} spent on {purpose}.", "success")
        return redirect(url_for("consumptions"))

    all_consumptions = query(
        "SELECT * FROM consumptions ORDER BY timestamp DESC", fetch="all"
    )
    total = sum(float(c["amount"]) for c in all_consumptions) if all_consumptions else 0.0
    return render_template("consumptions.html", consumptions=all_consumptions, total=total)


@app.route("/consumptions/<int:c_id>/edit", methods=["GET", "POST"])
@login_required
def edit_consumption(c_id):
    item = query("SELECT * FROM consumptions WHERE id = %s", (c_id,), fetch="one")
    if not item:
        flash("That expense entry no longer exists.", "error")
        return redirect(url_for("consumptions"))

    if request.method == "POST":
        purpose = request.form.get("purpose", "").strip()
        amount = request.form.get("amount", "").strip()
        try:
            amount_val = float(amount)
            if not purpose or amount_val <= 0:
                raise ValueError
        except ValueError:
            flash("Please provide a valid purpose and a positive amount.", "error")
            return redirect(url_for("edit_consumption", c_id=c_id))

        query(
            "UPDATE consumptions SET purpose = %s, amount = %s WHERE id = %s",
            (purpose, amount_val, c_id), commit=True
        )
        flash("Expense entry updated.", "success")
        return redirect(url_for("consumptions"))

    return render_template("edit_entry.html", entry=item, kind="consumption")


@app.route("/consumptions/<int:c_id>/delete", methods=["POST"])
@login_required
def delete_consumption(c_id):
    query("DELETE FROM consumptions WHERE id = %s", (c_id,), commit=True)
    flash("Expense entry deleted.", "success")
    return redirect(url_for("consumptions"))


# ---------------------------------------------------------------------------
# Collections (the two sub-views the user asked for)
# ---------------------------------------------------------------------------
@app.route("/collections")
@login_required
def collections():
    totals = get_totals()
    view = request.args.get("view", "gross")  # 'gross' or 'net'
    return render_template("collections.html", totals=totals, view=view)


# ---------------------------------------------------------------------------
# History (combined, chronological ledger of everything)
# ---------------------------------------------------------------------------
@app.route("/history")
@login_required
def history():
    tips_rows = query("SELECT * FROM tips", fetch="all")
    consumption_rows = query("SELECT * FROM consumptions", fetch="all")

    ledger = []
    for t in tips_rows:
        ledger.append({
            "type": "tip",
            "label": t["tipper_name"],
            "amount": float(t["amount"]),
            "timestamp": t["timestamp"],
        })
    for c in consumption_rows:
        ledger.append({
            "type": "consumption",
            "label": c["purpose"],
            "amount": float(c["amount"]),
            "timestamp": c["timestamp"],
        })
    ledger.sort(key=lambda row: row["timestamp"], reverse=True)

    return render_template("history.html", ledger=ledger)


if __name__ == "__main__":
    app.run(debug=True)