# College Election System — Setup Guide

## 🚀 Quick Start (SQLite — Recommended for single-server)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open browser: http://localhost:5000
```

**Default credentials:**
- Admin: `admin` / `admin123`
- Voter: `alice_voter` / `voter123`

---

## 🗄️ Database Setup

### Option A: SQLite (Default — no setup needed)
SQLite is used automatically. All data stored in `election.db` in the project folder.

To centralize: run the Flask server on ONE machine, all others access it via browser at `http://<server-ip>:5000`

### Option B: MySQL

```bash
# Install MySQL driver
pip install pymysql

# Create database
mysql -u root -p
CREATE DATABASE election_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'election_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON election_db.* TO 'election_user'@'%';
FLUSH PRIVILEGES;
EXIT;

# Set environment variable before running
export DATABASE_URL="mysql+pymysql://election_user:your_password@localhost:3306/election_db"
python app.py
```

### Option C: PostgreSQL

```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Create database
psql -U postgres
CREATE DATABASE election_db;
CREATE USER election_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE election_db TO election_user;
\q

# Set environment variable
export DATABASE_URL="postgresql://election_user:your_password@localhost:5432/election_db"
python app.py
```

---

## 🌐 Centralized Access (Multiple Devices)

1. Run Flask server on one central machine (PC/server/Raspberry Pi)
2. Find server IP: `ipconfig` (Windows) or `ip addr` (Linux/Mac)
3. All students/admins access: `http://<server-ip>:5000`
4. No installation needed on client devices — browser only

---

## ✅ Features Fixed

| Feature | Status |
|---------|--------|
| Registration → Login redirect | ✅ Fixed |
| Course / Year / Semester in registration | ✅ Added |
| Camera/face recognition removed | ✅ Removed (ID upload only) |
| Verify & Proceed button | ✅ Working |
| MySQL/PostgreSQL support | ✅ Added via SQLAlchemy |
| Admin: Users Database | ✅ `/admin/users` |
| Admin: Candidates Database | ✅ `/admin/candidates` |
| Admin: Voters Database | ✅ `/admin/voters-list` |
| Export Users to Excel | ✅ `/admin/export/users` |
| Export Candidates to Excel | ✅ `/admin/export/candidates` |
| Export Voters to Excel | ✅ `/admin/export/voters` |
| Clear Users | ✅ POST `/admin/clean/users` |
| Clear Candidates | ✅ POST `/admin/clean/candidates` |
| Clear Votes | ✅ POST `/admin/clean/votes` |
| One vote per user | ✅ DB-level UNIQUE constraint |
| Duplicate vote prevention | ✅ Fixed |
| Password hashing | ✅ werkzeug |
| Route protection | ✅ @login_required + role check |

---

## 🔐 Admin Navigation

After logging in as admin, the navbar shows:
- **Dashboard** — overview + live vote counts
- **Nominations** — manage candidate applications
- **Votes & Blockchain** — all vote records + blockchain explorer
- **Users DB** — view/export/clear all users
- **Candidates DB** — view/export/clear all candidates
- **Voters DB** — view/export/clear voter records

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///election.db` | Database connection string |
| `SECRET_KEY` | `change_me_in_production_2024` | Flask session secret key |
| `ANTHROPIC_API_KEY` | *(not set)* | Enables Claude Vision API for scanned document OCR |

### 🤖 Claude Vision API (Recommended for scanned documents)

The OCR pipeline now uses a **3-strategy approach**:

1. **PyMuPDF direct extraction** — instant, works for digital PDFs (UUCMS, mLAC receipts)
2. **Claude Vision API** ← *new* — AI-powered extraction for scanned/photographed PDFs
3. **EasyOCR / Tesseract** — fully offline fallback

To enable Claude Vision (Strategy 2):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python app.py
```

- Get your API key from: https://console.anthropic.com/
- **No extra pip package needed** — uses Python's built-in `urllib`
- If `ANTHROPIC_API_KEY` is not set, the system automatically falls back to EasyOCR/Tesseract
- Model used: `claude-sonnet-4-20250514`

---

## 📦 Dependencies

Core:
- Flask, Flask-Login, Werkzeug
- SQLAlchemy (database ORM)
- pandas + openpyxl (Excel export)

Optional (for OCR on ID cards):
- easyocr, opencv-python-headless, numpy, Pillow

For MySQL: `pip install pymysql`
For PostgreSQL: `pip install psycopg2-binary`
