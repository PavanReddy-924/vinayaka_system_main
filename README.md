# Vinayaka Chavithi Committee Fund Tracker

A small Flask + MySQL app for tracking festival contributions ("tips") and
expenses ("consumptions"), so the committee never has to hand-count cash
two or three times to catch a mistake.

## What's inside

```
vinayaka_system/
├── app.py                 Flask app (routes, DB access)
├── setup_db.py             Run once: creates tables + your first login
├── requirements.txt
├── static/
│   ├── style.css
│   └── vinayakalogo.jpeg   <- put your festival photo here (see below)
└── templates/
    ├── base.html           Shared header / nav / flash messages
    ├── login.html
    ├── dashboard.html      Summary + navigation hub (no forms dumped here)
    ├── tips.html           Add + view tippers
    ├── consumptions.html   Add + view expenses
    ├── edit_entry.html     Shared edit form for a tip or expense
    ├── collections.html    Gross total vs. net balance (2 tabs)
    └── history.html        Combined chronological ledger
```

## 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Add your festival image

Drop your `vinayakalogo.jpeg` into `static/`. It's used as a soft, darkened
background across every page (via `static/style.css`), so any reasonably
high-resolution photo works well — it doesn't need to be square or a logo
specifically. If the file is missing, the app still looks intentional: it
falls back to a plain deep-maroon background.

If you have more festival photos, you're welcome to reuse the same pattern —
just add them to `static/` and reference them in `style.css` or in a
template with `{{ url_for('static', filename='your-image.jpg') }}`.

## 3. Create the database

Edit the `DB_CONFIG` dictionary at the top of `setup_db.py` and `app.py` to
match your MySQL username/password, then run:

```bash
python setup_db.py
```

This creates the database, the three tables, and asks you to type a
username + password for your first committee login (passwords are stored
**hashed**, never in plain text — this fixes a real security issue in the
original version of the app). Run it again any time you need to add another
committee member's login.

## 4. Run it locally

```bash
python app.py
```

Visit `http://127.0.0.1:5000` and log in with the username/password you
just created.

## What changed from your original version

- **Dashboard is now a hub, not a form dump.** It shows live totals (total
  tips, total spent, net balance) plus recent activity, and links out to
  each feature. The "Add Tip" form no longer opens automatically — it lives
  on the Tippers page.
- **Passwords are hashed** with Werkzeug's `generate_password_hash` /
  `check_password_hash` instead of stored and compared as plain text.
- **One DB connection per request** instead of a single global connection
  that MySQL eventually drops ("MySQL server has gone away") after being
  idle — a common crash cause in small Flask+MySQL apps.
- **Edit, not just delete.** Since your original pain point was miscounts,
  you can now fix a wrong name/amount in place instead of deleting and
  re-adding (which loses the original timestamp).
- **Collections page has both sub-views you asked for** — gross total and
  net balance — as two tabs on one page.
- **Fully responsive**: the top nav collapses into a hamburger menu, and
  tables collapse into stacked cards, on phone-sized screens.
- **Client-side search** on the Tippers and Expenses tables, so you can
  quickly find a specific name/purpose during the rush of the festival.

## 5. Deploy for free on PythonAnywhere

PythonAnywhere's free tier supports Flask + MySQL and is enough for
10–20 users.

1. Sign up at **pythonanywhere.com** (free "Beginner" account).
2. Go to the **Files** tab and upload this whole folder (or use a Bash
   console and `git clone` if you push this to GitHub first).
3. Go to the **Databases** tab, set a MySQL password, and create a database
   — PythonAnywhere will give you a host like
   `yourusername.mysql.pythonanywhere-services.com`. Update `DB_CONFIG` in
   both `app.py` and `setup_db.py` with that host, your PythonAnywhere
   MySQL username, and that password.
4. Open a **Bash console** on PythonAnywhere and run:
   ```bash
   cd vinayaka_system
   pip install --user -r requirements.txt
   python setup_db.py
   ```
5. Go to the **Web** tab → **Add a new web app** → choose **Flask** → point
   it at `app.py` in your uploaded folder.
6. In the **Web** tab, edit the **WSGI configuration file** so it imports
   your app, e.g.:
   ```python
   import sys
   path = '/home/yourusername/vinayaka_system'
   if path not in sys.path:
       sys.path.append(path)
   from app import app as application
   ```
7. Make sure the **Static files** mapping points `/static/` to your
   `vinayaka_system/static/` folder, so `style.css` and the background
   image load correctly.
8. Hit **Reload** on the Web tab. Your app is now live at
   `yourusername.pythonanywhere.com`.

For a real festival with more concurrent users than the free tier's request
limits allow, the same steps work on Render, Railway, or a small VPS —
just swap the MySQL host details.
