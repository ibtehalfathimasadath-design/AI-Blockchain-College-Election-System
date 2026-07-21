# College Election System — Complete Fix Guide
## What Was Wrong & What Was Fixed

---

## CRITICAL BUG #1 — Face Verification Was Completely Fake

### Root Cause
`face_utils.py` had a `_simulate_face_verification()` function that was
being used whenever `face_recognition` was not installed. That function
simply returned `True` for **any two files bigger than 100 bytes**.

This is why:
- A palm/hand passed as a face ✗
- Your friend's face passed with your ID ✗
- Any image at all passed verification ✗

### Fixes Applied (`utils/face_utils.py`)

**1. Simulation completely removed**
The fake simulation is gone. If `face_recognition` is not installed,
`verify_face_detailed()` returns `matched=False` with a clear error
message. The system cannot pretend to verify.

**2. Startup guard added (`app.py`)**
```python
from utils.face_utils import FACE_RECOGNITION_AVAILABLE
if not FACE_RECOGNITION_AVAILABLE:
    raise RuntimeError("face_recognition not installed — refusing to start")
```
The Flask app now **refuses to start** if the library is missing,
rather than silently falling back to the insecure simulation.

**3. Threshold tightened: 0.55 → 0.45**
Lower distance = stricter match. The original 0.55 was too lenient and
could allow lookalikes or partial matches.

**4. Multiple faces are now a hard block**
Previously: multiple faces logged a warning but still proceeded with
the first face (so a group photo could pass).
Now: `_encode_image()` returns `status="multiple_faces"` with
`encoding=None`, and the caller immediately rejects the verification.

### Installation (run on your server)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y cmake build-essential libopenblas-dev liblapack-dev

pip install dlib
pip install face_recognition

# Verify
python -c "import face_recognition; print('OK')"
```

---

## BUG #2 — Candidate Documents Accepted Any File Type

### Root Cause
`app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}` was used
for **all** uploads — including nomination documents that should be PDF.
There was no PDF validation at all.

### Fixes Applied (`app.py` + `templates/apply_nomination.html`)

**Backend — extension check + magic byte check**
```python
# NEW: PDF-only allowed set for documents
app.config['ALLOWED_DOC_EXTENSIONS'] = {'pdf'}

def allowed_document(filename):
    return filename.rsplit('.', 1)[1].lower() in {'pdf'}

def validate_pdf_magic(file_storage):
    """Reads first 4 bytes — real PDFs start with %PDF."""
    header = file_storage.read(4)
    file_storage.seek(0)
    return header == b'%PDF'
```

The magic-byte check stops users from renaming a `.jpg` to `.pdf` to
bypass the extension check.

**Frontend — browser-level guard**
```html
<input type="file" name="id_card" accept=".pdf" required>
```
JavaScript also validates before form submission. This is UX convenience
only — the real validation is always on the backend.

---

## BUG #3 — Database Not Centralized (Architecture)

### Root Cause
SQLite stores data in a local file (`election.db`) on one machine. If
you open the app on a second device, it reads its own empty database.

### Fix — How Centralization Works

**The correct architecture (SQLite is fine for a college project):**
```
Student/Admin devices
      │  (browser — no local database)
      ▼
Flask server (ONE machine: college server, Raspberry Pi, or VM)
      │
election.db (single file, on the server only)
```

All devices connect through a browser. There is no database per user.
You just need to run `python app.py` on one shared machine and give
everyone that machine's IP address.

**No code changes needed for this** — just deploy on a single server.

**If you later need MySQL/PostgreSQL (for 200+ concurrent users):**
```bash
pip install pymysql
export DATABASE_URL="mysql+pymysql://user:password@localhost/election_db"
```

The schema in `utils/database.py` is documented with comments showing
exactly which table stores what (users/candidates/votes/settings).

---

## BUG #4 — Voting Race Condition

### Root Cause
The original code checked for a duplicate vote, then inserted. Between
the check and the insert, a second simultaneous request could pass the
check and also insert — resulting in two votes.

### Fix Applied (`app.py` — `cast_vote` route)

```python
# 1. Lock the database for writing before checking
db.execute("BEGIN IMMEDIATE")

# 2. Check for duplicate INSIDE the lock
existing = db.execute(
    'SELECT id FROM votes WHERE voter_id = ?', [current_user.id]
).fetchone()
if existing:
    db.execute("ROLLBACK")
    flash('You have already voted.', 'error')
    return redirect(url_for('voter_dashboard'))

# 3. Insert votes
for role, nomination_id in selected_votes.items():
    db.execute("INSERT INTO votes ...")

# 4. Commit — UNIQUE(voter_id, role) fires as a final safety net
try:
    db.commit()
except sqlite3.IntegrityError:
    db.execute("ROLLBACK")
    flash('Duplicate vote detected.', 'error')
```

Three layers of protection:
- `BEGIN IMMEDIATE` — locks DB so no other request can insert simultaneously
- Check inside the lock — application-level duplicate guard
- `UNIQUE(voter_id, role)` in the schema — database-level final guard

---

## Files Changed

```
election_fixed_v3/
├── app.py                        ← Startup guard, PDF validation,
│                                   allowed_document(), validate_pdf_magic(),
│                                   vote transaction with BEGIN IMMEDIATE
├── utils/
│   ├── face_utils.py             ← Simulation removed, threshold 0.45,
│   │                               multiple-face hard block
│   └── database.py               ← Schema documented, centralization explained
├── templates/
│   └── apply_nomination.html     ← accept=".pdf", JS PDF check
└── requirements.txt              ← Added dlib, face_recognition
```

---

## Priority Order

| Priority | Fix | Time |
|----------|-----|------|
| 🔴 CRITICAL | Install `face_recognition` + remove simulation | 30 min |
| 🔴 CRITICAL | Add startup guard (app refuses without lib) | Done |
| 🟠 HIGH | Threshold → 0.45, hard-block multiple faces | Done |
| 🟠 HIGH | PDF magic-byte validation for nomination docs | Done |
| 🟡 MEDIUM | Deploy on one central server | varies |
| 🟢 LOW | Migrate to MySQL/PostgreSQL for > 200 users | 2–4 hrs |

---

## Quick Start

```bash
# 1. Install dependencies
sudo apt install cmake build-essential libopenblas-dev liblapack-dev
pip install -r requirements.txt

# 2. Run (on your shared server machine)
python app.py

# 3. All users open browser to:
http://<server-ip>:5000

# Default credentials:
# Admin:  admin / admin123
# Voter:  alice_voter / voter123
```

---

## UPDATE — mLAC / UUCMS Document Compatibility (v2.1)

### What was verified against real documents
Real student documents from **Maharani Lakshmi Ammanni College for Women (Autonomous),
Bengaluru** (BCA programme) were cross-checked against the OCR/verification pipeline.
The following improvements were made to ensure these documents are accepted correctly.

### Changes Made

#### `utils/document_verifier.py`

**1. ID card: ADMISSION # / SIDN number patterns added**
`ID_NUMBER_PATTERNS` now matches:
- `ADMISSION # : 2023UG0009` (mLAC ID card format)
- `SIDN : 2023UG0009` (mLAC fee receipt field)

**2. Semester detection: UUCMS Term/Semester field**
`SEMESTER_PATTERNS` now handles:
- `Term/Semester : III` (UUCMS result sheet header format)
- `Term : IV` variants

**3. Year-from-semester inference for UUCMS marks cards**
UUCMS result sheets never print "3rd Year" — they only show semester (I–VI).
`verify_marks_card()` now infers year from the highest semester found:
- Sem I/II → Year 1, Sem III/IV → Year 2, Sem V/VI → Year 3

**4. Course pattern: "Bachelor of Computer Applications"**
`COURSE_PATTERNS` now matches the full UUCMS program name in addition to the
short code "BCA".

**5. Fee receipt: mLAC-specific payment keywords**
Added to `PAID_KEYWORDS`: `debit card`, `hdfc`, `cash`, `total mgmt fee`,
`total fee`, `amount in words`.

Added to `is_receipt_doc` check: `malleswaram`, `18th cross`, `entered by`,
`fees concession`, `swf`, `maintenance` — all present on mLAC receipts.

**6. ID card is_id_doc: added UUCMS/mLAC signals**
`uucms`, `bca`, `mca`, `reg no`, `sidn`, `bachelor of computer`, `malleswaram`
are now recognised as valid college ID signals.

#### `utils/ocr_pipeline.py`

**7. Whitespace tampering check: threshold raised**
UUCMS/mLAC digital PDFs contain normal table whitespace.
The whitespace tampering detector now only flags whitespace blocks that are
substantially longer (64+ spaces) to avoid false positives on official documents.

#### `utils/eligibility.py`

**8. `extract_year_number`: handles plain integer strings**
The marks verifier now passes year as a plain digit (e.g., `"3"`) inferred
from semester number. `extract_year_number("3")` now correctly returns `3`.
