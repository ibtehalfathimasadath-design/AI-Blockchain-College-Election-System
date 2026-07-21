"""
College Election System - Main Flask Application
AI-powered voting and nomination system with OCR, Face Recognition, Blockchain simulation

FIXED:
  1. Data sync: update_nomination_status now returns JSON for AJAX calls
  2. API /api/full-stats added for live dashboard stat cards
  3. announce_winner rebuilt: returns JSON, emails winner + admin, marks DB
  4. All async operations properly awaited on frontend via fetch()
  5. Email sent on admin approval (update_nomination_status → approved)
  6. Email sent to winner + admin on result declaration
  7. Frontend polling on admin_nominations page auto-refreshes after approval
"""
print("THIS APP.PY FILE IS RUNNING")
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
import sqlite3
from datetime import datetime

# Import utility modules
from utils.database import init_db, get_db
from utils.ocr_utils import (
    extract_id_card_info, extract_fee_receipt_info, extract_result_sheet_info,
    run_nomination_ocr_checks
)
from utils.face_utils import verify_face, extract_face_from_image
from utils.eligibility import (
    check_nomination_eligibility,
    get_allowed_roles_for_year,
    get_role_requirements
)
from utils.blockchain import Blockchain, get_blockchain, BlockchainClient
from utils.email_utils import (
    send_nomination_result_email,
    send_winner_announcement_email,
    send_nomination_approved_email,   # NEW
    send_result_declared_admin_email, # NEW
)
from utils.user_model import User

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "college_election_secret_key_2024"
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# Auto-create all upload subdirectories on startup
for _sub in ['id_cards', 'fee_receipts', 'result_sheets', 'faces']:
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], _sub), exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize database on startup
with app.app_context():
    init_db()


def allowed_file(filename):
    """Check if uploaded file has an allowed extension (image or PDF)"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def validate_file_upload(file_obj, field_name, max_mb=10):
    """
    Validate a single uploaded file object.
    Returns (valid: bool, error_message: str)
    """
    if not file_obj or file_obj.filename == '':
        return False, f'Please upload your {field_name}.'

    if not allowed_file(file_obj.filename):
        return False, f'{field_name}: only image files (JPG, PNG, GIF) and PDF are allowed.'

    file_obj.seek(0, 2)
    size_bytes = file_obj.tell()
    file_obj.seek(0)
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f'{field_name} file too large. Maximum allowed size is {max_mb}MB.'

    return True, ''


@login_manager.user_loader
def load_user(user_id):
    """Load user from database for Flask-Login"""
    db = get_db()
    user_data = db.execute('SELECT * FROM users WHERE id = ?', [user_id]).fetchone()
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['email'],
                   user_data['role'], user_data['password_hash'])
    return None


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

@app.route('/')
def index():
    """Home page"""
    db = get_db()
    stats = {
        'total_votes': db.execute('SELECT COUNT(*) as c FROM votes').fetchone()['c'],
        'total_nominations': db.execute('SELECT COUNT(*) as c FROM nominations').fetchone()['c'],
        'approved_nominations': db.execute("SELECT COUNT(*) as c FROM nominations WHERE status='approved'").fetchone()['c'],
    }
    return render_template('index.html', stats=stats)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')

        db = get_db()
        user_data = db.execute('SELECT * FROM users WHERE username = ?', [username]).fetchone()

        if user_data and User.check_password(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'], user_data['email'],
                       user_data['role'], user_data['password_hash'])
            login_user(user)
            flash(f'Welcome back, {username}!', 'success')
            if user_data['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('voter_dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        username         = request.form.get('username', '').strip()
        email            = request.form.get('email', '').strip()
        password         = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        role             = request.form.get('role', 'voter')

        errors = []
        if not all([username, email, password, confirm_password]):
            errors.append('All fields are required.')
        if len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html')

        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE username = ? OR email = ?',
                              [username, email]).fetchone()
        if existing:
            flash('Username or email already exists.', 'error')
            return render_template('register.html')

        full_name = request.form.get('full_name', '').strip()
        course    = request.form.get('course', '').strip()
        year      = request.form.get('year', '').strip()
        semester  = request.form.get('semester', '').strip()

        password_hash = User.hash_password(password)
        db.execute(
            'INSERT INTO users (username, email, password_hash, role, full_name, course, year, semester, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [username, email, password_hash, role, full_name, course, year, semester,
             datetime.now().strftime('%Y-%m-%dT%H:%M:%S')]
        )
        db.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ============================================================
# VOTER ROUTES
# ============================================================

@app.route('/voter/dashboard')
@login_required
def voter_dashboard():
    """Voter dashboard showing candidates and voting status"""
    db = get_db()
    candidates = db.execute("""
        SELECT n.*, u.username, u.email
        FROM nominations n
        JOIN users u ON n.user_id = u.id
        WHERE n.status = 'approved'
        ORDER BY n.role
    """).fetchall()

    has_voted = db.execute('SELECT id FROM votes WHERE voter_id = ?',
                          [current_user.id]).fetchone() is not None

    bc = get_blockchain()
    chain_length = bc.get_chain_info().get('blockNumber', 0) or 0

    return render_template('voter_dashboard.html',
                          candidates=candidates,
                          has_voted=has_voted,
                          chain_length=chain_length)


@app.route('/voter/verify-identity', methods=['GET', 'POST'])
@login_required
def verify_identity():
    """Step 1 of voting: Verify voter identity via OCR + Face Recognition"""
    if request.method == 'POST':
        if 'id_card' not in request.files:
            flash('Please upload your ID card.', 'error')
            return render_template('verify_identity.html')

        id_card_file    = request.files['id_card']
        face_photo_file = request.files.get('face_photo')

        if id_card_file.filename == '':
            flash('No ID card file selected.', 'error')
            return render_template('verify_identity.html')

        if not allowed_file(id_card_file.filename):
            flash('Invalid file type. Please upload a JPG or PNG image.', 'error')
            return render_template('verify_identity.html')

        id_filename = secure_filename(f"voter_{current_user.id}_id_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        id_path = os.path.join(app.config['UPLOAD_FOLDER'], 'id_cards', id_filename)
        id_card_file.save(id_path)

        ocr_result = extract_id_card_info(id_path)

        face_matched = False
        if face_photo_file and face_photo_file.filename:
            face_filename = secure_filename(f"voter_{current_user.id}_face_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
            face_path = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', face_filename)
            face_photo_file.save(face_path)
            face_matched = verify_face(id_path, face_path)
        else:
            face_matched = True

        if face_matched:
            session['identity_verified'] = True
            session['voter_name'] = ocr_result.get('name', current_user.username)
            session['voter_id_number'] = ocr_result.get('id_number', 'N/A')
            flash(f'Identity verified successfully! Welcome, {session["voter_name"]}.', 'success')
            return redirect(url_for('cast_vote'))
        else:
            flash('Face verification failed. Your live photo does not match the ID card.', 'error')
            return render_template('verify_identity.html', ocr_result=ocr_result)

    return render_template('verify_identity.html')


@app.route('/voter/cast-vote', methods=['GET', 'POST'])
@login_required
def cast_vote():
    """Step 2 of voting: Cast vote (only if identity verified)"""
    if not session.get('identity_verified'):
        flash('Please verify your identity first.', 'warning')
        return redirect(url_for('verify_identity'))

    db = get_db()
    existing_vote = db.execute('SELECT id FROM votes WHERE voter_id = ?',
                              [current_user.id]).fetchone()
    if existing_vote:
        flash('You have already cast your vote. Duplicate voting is not allowed.', 'error')
        return redirect(url_for('voter_dashboard'))

    candidates = db.execute("""
        SELECT n.*, u.username, u.email
        FROM nominations n
        JOIN users u ON n.user_id = u.id
        WHERE n.status = 'approved'
        ORDER BY n.role
    """).fetchall()

    candidates_by_role = {}
    for c in candidates:
        role = c['role']
        if role not in candidates_by_role:
            candidates_by_role[role] = []
        candidates_by_role[role].append(dict(c))

    if request.method == 'POST':
        selected_votes = {}
        for role in candidates_by_role:
            vote_key = f'vote_{role.lower().replace(" ", "_")}'
            candidate_id = request.form.get(vote_key)
            if candidate_id:
                selected_votes[role] = int(candidate_id)

        if not selected_votes:
            flash('Please select at least one candidate to vote for.', 'error')
            return render_template('cast_vote.html', candidates_by_role=candidates_by_role)

        # ── Get the real blockchain client ───────────────────────────
        bc_client = get_blockchain()   # returns BlockchainClient singleton
        timestamp = datetime.now().isoformat()

        # Insert rows into SQLite first (with 'pending' hash)
        for role, nomination_id in selected_votes.items():
            db.execute("""
                INSERT INTO votes (voter_id, nomination_id, role, timestamp, blockchain_hash)
                VALUES (?, ?, ?, ?, ?)
            """, [current_user.id, nomination_id, role, timestamp, 'pending'])
        db.commit()

        # ── Submit REAL transactions to the Ethereum smart contract ──
        voter_name   = session.get('voter_name', current_user.username)
        all_receipts = []
        tx_hashes    = []

        for role, nomination_id in selected_votes.items():
            receipt = bc_client.cast_vote(
                voter_id      = current_user.id,
                voter_name    = voter_name,
                nomination_id = nomination_id,
                role          = role,
            )
            all_receipts.append(receipt)
            tx_hashes.append(receipt.get('transactionHash', ''))

            # Update the blockchain_hash column with the real tx hash
            db.execute("""
                UPDATE votes
                SET blockchain_hash = ?
                WHERE voter_id = ? AND nomination_id = ? AND timestamp = ?
            """, [receipt.get('transactionHash', ''), current_user.id, nomination_id, timestamp])

        db.commit()

        # Store all tx hashes in session for the confirmation page
        session['last_tx_hashes']  = tx_hashes
        session['last_tx_receipts'] = all_receipts
        session.pop('identity_verified', None)

        # Use the first tx hash as the "block hash" for backward compat
        primary_tx = tx_hashes[0] if tx_hashes else 'unknown'
        flash(f'Vote cast! Transaction: {primary_tx[:20]}...', 'success')
        return redirect(url_for('vote_confirmation', block_hash=primary_tx))

    return render_template('cast_vote.html', candidates_by_role=candidates_by_role)


@app.route('/voter/confirmation/<path:block_hash>')
@login_required
def vote_confirmation(block_hash):
    """Vote confirmation page showing real blockchain transaction receipt"""
    bc_client = get_blockchain()
    chain_info = bc_client.get_chain_info()

    # Pull receipts stored in session during cast_vote
    receipts  = session.pop('last_tx_receipts', [])
    tx_hashes = session.pop('last_tx_hashes', [block_hash])

    # Build a block-like object for the template
    class TxBlock:
        def __init__(self, tx_hash, receipt, chain_info):
            self.hash          = tx_hash
            self.index         = receipt.get('blockNumber', chain_info.get('blockNumber', 0))
            self.previous_hash = '0x' + '0' * 62
            self.timestamp     = datetime.now().isoformat()
            self.nonce         = receipt.get('gasUsed', 21000)
            self.data          = receipt
            self.network       = receipt.get('network', 'ganache')
            self.simulated     = receipt.get('simulated', False)
            self.events        = receipt.get('events', [])

    block = None
    if receipts:
        block = TxBlock(tx_hashes[0], receipts[0], chain_info)
    elif block_hash and block_hash != 'unknown':
        # Reconstruct minimal block from URL hash
        block = TxBlock(block_hash, {
            'blockNumber': chain_info.get('blockNumber', 0),
            'gasUsed': 21000,
            'status': 1,
            'events': [],
            'network': chain_info.get('network', 'ganache'),
            'simulated': False,
        }, chain_info)

    return render_template(
        'vote_confirmation.html',
        block=block,
        block_hash=block_hash,
        all_tx_hashes=tx_hashes,
        chain_info=chain_info,
    )


# ============================================================
# NOMINATION ROUTES
# ============================================================

@app.route('/nomination/apply', methods=['GET', 'POST'])
@login_required
def apply_nomination():
    """
    Nomination application form with document upload.
    Auto-approves/rejects based on OCR eligibility check.
    Sends email notification immediately after result.
    """
    role_requirements = get_role_requirements()

    if request.method == 'POST':
        applicant_name = request.form.get('applicant_name', '').strip()
        department     = request.form.get('department', '').strip()
        desired_role   = request.form.get('desired_role', '').strip()
        manifesto      = request.form.get('manifesto', '').strip()
        motto          = request.form.get('motto', '').strip()
        year           = request.form.get('year', '').strip()
        cgpa_raw       = request.form.get('cgpa', '0').strip()

        errors = []
        if not applicant_name or len(applicant_name) < 2:
            errors.append('Full name must be at least 2 characters.')
        if not department:
            errors.append('Please select your department.')
        if not year:
            errors.append('Please select your year of study.')
        if not desired_role:
            errors.append('Please select the position you are applying for.')

        try:
            cgpa = float(cgpa_raw)
            if cgpa < 0 or cgpa > 10:
                errors.append('CGPA must be between 0.0 and 10.0.')
        except ValueError:
            cgpa = 0.0
            errors.append('Please enter a valid CGPA value.')

        if len(motto) > 150:
            errors.append('Motto must be 150 characters or fewer.')

        if year and desired_role:
            allowed_roles = get_allowed_roles_for_year(year)
            allowed_lower = [r.lower() for r in allowed_roles]
            if desired_role.lower() not in allowed_lower:
                errors.append(
                    f'"{desired_role}" is not available for {year} students. '
                    f'Allowed positions: {", ".join(allowed_roles)}.'
                )

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('apply_nomination.html',
                                   role_requirements=role_requirements)

        file_fields = [
            ('id_card',      'ID Card'),
            ('fee_receipt',  'Fee Receipt'),
            ('result_sheet', 'Semester Mark Card'),
        ]
        file_errors = []
        for field_name, label in file_fields:
            file_obj = request.files.get(field_name)
            valid, msg = validate_file_upload(file_obj, label, max_mb=10)
            if not valid:
                file_errors.append(msg)

        if file_errors:
            for e in file_errors:
                flash(e, 'error')
            return render_template('apply_nomination.html',
                                   role_requirements=role_requirements)

        db = get_db()
        existing = db.execute('SELECT id FROM nominations WHERE user_id = ?',
                             [current_user.id]).fetchone()
        if existing:
            db.execute("DELETE FROM nominations WHERE user_id = ?", [current_user.id])
            db.commit()

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        uid       = current_user.id

        def save_file(file_obj, subfolder, suffix):
            ext = file_obj.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"nom_{uid}_{suffix}_{timestamp}.{ext}")
            path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
            file_obj.save(path)
            return filename, path

        id_filename,     id_path     = save_file(request.files['id_card'],     'id_cards',     'id')
        fee_filename,    fee_path    = save_file(request.files['fee_receipt'],  'fee_receipts', 'fee')
        result_filename, result_path = save_file(request.files['result_sheet'], 'result_sheets','result')

        ocr_checks = run_nomination_ocr_checks(
            input_name  = applicant_name,
            id_path     = id_path,
            fee_path    = fee_path,
            result_path = result_path,
        )

        ocr_data = {
            'id_card'     : ocr_checks['id_info'],
            'fee_receipt' : ocr_checks['fee_info'],
            'result_sheet': ocr_checks['result_info'],
            'name'        : applicant_name,
            'department'  : department,
            'desired_role': desired_role,
            'cgpa'        : cgpa,
            'year'        : year,
            'ocr_checks': {
                'name_match'          : ocr_checks['name_match'],
                'name_match_details'  : ocr_checks['name_match_details'],
                'fail_detected'       : ocr_checks['fail_detected'],
                'fail_details'        : ocr_checks['fail_details'],
                'register_consistent' : ocr_checks['register_consistent'],
                'register_details'    : ocr_checks['register_details'],
            }
        }

        eligibility_result = check_nomination_eligibility(ocr_data, ocr_checks=ocr_checks)
        status = 'approved' if eligibility_result['eligible'] else 'rejected'

        db.execute("""
            INSERT INTO nominations
            (user_id, name, department, role, manifesto, motto, cgpa, year,
             id_card_path, fee_receipt_path, result_sheet_path,
             ocr_data, status, rejection_reasons,
             ocr_name_match, ocr_fail_detected, ocr_register_consistent,
             ocr_extracted_name, ocr_extracted_register,
             created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?)
        """, [
            current_user.id, applicant_name, department, desired_role,
            manifesto, motto, cgpa, year,
            id_filename, fee_filename, result_filename,
            json.dumps(ocr_data), status,
            json.dumps(eligibility_result.get('reasons', [])),
            int(ocr_checks['name_match']),
            int(ocr_checks['fail_detected']),
            int(ocr_checks['register_consistent']),
            ocr_checks.get('extracted_name', ''),
            ocr_checks.get('extracted_register', ''),
            datetime.now().isoformat()
        ])
        db.commit()

        # FIX 4: Send email immediately after save (synchronous, guaranteed)
        send_nomination_result_email(
            current_user.email,
            applicant_name,
            desired_role,
            eligibility_result['eligible'],
            eligibility_result.get('reasons', [])
        )

        if eligibility_result['eligible']:
            flash(
                f'Nomination APPROVED! Your application for {desired_role} has been accepted. '
                'A confirmation email has been sent.',
                'success'
            )
        else:
            reasons_text = '; '.join(
                eligibility_result.get('reasons', ['Did not meet eligibility criteria'])
            )
            flash(
                f'Nomination REJECTED. Reasons: {reasons_text}. '
                'A notification email has been sent.',
                'error'
            )

        return redirect(url_for('nomination_status'))

    return render_template('apply_nomination.html',
                           role_requirements=role_requirements)


@app.route('/nomination/status')
@login_required
def nomination_status():
    """View nomination status for current user"""
    db = get_db()
    nomination = db.execute("""
        SELECT * FROM nominations WHERE user_id = ?
    """, [current_user.id]).fetchone()

    ocr_data          = None
    rejection_reasons = []
    if nomination:
        try:
            ocr_data          = json.loads(nomination['ocr_data']) if nomination['ocr_data'] else {}
            rejection_reasons = json.loads(nomination['rejection_reasons']) if nomination['rejection_reasons'] else []
        except Exception:
            ocr_data, rejection_reasons = {}, []

    return render_template('nomination_status.html',
                          nomination=nomination,
                          ocr_data=ocr_data,
                          rejection_reasons=rejection_reasons)


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/allowed-roles')
def api_allowed_roles():
    """Returns the list of allowed roles for a given year."""
    year_str = request.args.get('year', '').strip()
    if not year_str:
        return jsonify({'error': 'year parameter is required'}), 400

    allowed = get_allowed_roles_for_year(year_str)
    return jsonify({'year': year_str, 'allowed_roles': allowed})


@app.route('/api/live-stats')
def api_live_stats():
    """API endpoint for live vote count updates"""
    db = get_db()
    vote_counts = db.execute("""
        SELECT n.id, n.name, n.role, COUNT(v.id) as vote_count
        FROM nominations n
        LEFT JOIN votes v ON n.id = v.nomination_id
        WHERE n.status = 'approved'
        GROUP BY n.id, n.name, n.role
        ORDER BY n.role, vote_count DESC
    """).fetchall()
    return jsonify([dict(r) for r in vote_counts])


@app.route('/api/full-stats')
def api_full_stats():
    """
    FIX 2: New API endpoint that returns all dashboard stat card values.
    Called by refreshAll() on the admin dashboard so stat cards update
    without a full page reload.
    """
    db = get_db()
    stats = {
        'total_votes'      : db.execute('SELECT COUNT(*) as c FROM votes').fetchone()['c'],
        'total_nominations': db.execute('SELECT COUNT(*) as c FROM nominations').fetchone()['c'],
        'approved'         : db.execute("SELECT COUNT(*) as c FROM nominations WHERE status='approved'").fetchone()['c'],
        'rejected'         : db.execute("SELECT COUNT(*) as c FROM nominations WHERE status='rejected'").fetchone()['c'],
        'pending'          : db.execute("SELECT COUNT(*) as c FROM nominations WHERE status='pending'").fetchone()['c'],
        'total_voters'     : db.execute("SELECT COUNT(*) as c FROM users WHERE role='voter'").fetchone()['c'],
    }
    return jsonify(stats)


@app.route('/api/nomination/<int:nom_id>/status')
@login_required
def api_nomination_status(nom_id):
    """
    FIX 1: Returns current status of a specific nomination as JSON.
    Frontend polls this after an approval action to confirm DB update.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    db = get_db()
    nom = db.execute('SELECT id, status, name, role FROM nominations WHERE id = ?', [nom_id]).fetchone()
    if not nom:
        return jsonify({'error': 'Nomination not found'}), 404
    return jsonify(dict(nom))


@app.route('/api/blockchain-status')
def api_blockchain_status():
    """Real-time blockchain status from Ethereum node"""
    bc_client = get_blockchain()
    info      = bc_client.get_chain_info()
    return jsonify({
        'connected':       info.get('connected', False),
        'network':         info.get('network', 'unknown'),
        'chain_id':        info.get('chainId'),
        'block_number':    info.get('blockNumber'),
        'total_votes':     info.get('totalVotes', 0),
        'voter_count':     info.get('voterCount', 0),
        'contract':        info.get('contractAddress', ''),
        'account':         info.get('account', ''),
        'simulated':       info.get('simulated', True),
    })


@app.route('/api/blockchain-events')
def api_blockchain_events():
    """Fetch all VoteCast events from the smart contract"""
    bc_client = get_blockchain()
    events    = bc_client.get_recent_events()
    return jsonify({'events': events, 'count': len(events)})


@app.route('/api/results/status')
def api_results_status():
    """
    FIX 8: Returns whether results have been declared + winner data.
    Frontend polls this to update election_results page without reload.
    """
    db = get_db()
    announcement = db.execute("SELECT value FROM settings WHERE key='winner_announced'").fetchone()
    if announcement:
        try:
            winners = json.loads(announcement['value'])
        except Exception:
            winners = {}
        return jsonify({'announced': True, 'winners': winners})
    return jsonify({'announced': False, 'winners': {}})


# ============================================================
# ADMIN ROUTES
# ============================================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard with live stats"""
    if current_user.role != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('voter_dashboard'))

    db = get_db()
    stats = {
        'total_votes'      : db.execute('SELECT COUNT(*) as c FROM votes').fetchone()['c'],
        'total_nominations': db.execute('SELECT COUNT(*) as c FROM nominations').fetchone()['c'],
        'approved'         : db.execute("SELECT COUNT(*) as c FROM nominations WHERE status='approved'").fetchone()['c'],
        'rejected'         : db.execute("SELECT COUNT(*) as c FROM nominations WHERE status='rejected'").fetchone()['c'],
        'pending'          : db.execute("SELECT COUNT(*) as c FROM nominations WHERE status='pending'").fetchone()['c'],
        'total_voters'     : db.execute("SELECT COUNT(*) as c FROM users WHERE role='voter'").fetchone()['c'],
    }

    vote_counts = db.execute("""
        SELECT n.id, n.name, n.role, COUNT(v.id) as vote_count
        FROM nominations n
        LEFT JOIN votes v ON n.id = v.nomination_id
        WHERE n.status = 'approved'
        GROUP BY n.id, n.name, n.role
        ORDER BY n.role, vote_count DESC
    """).fetchall()

    recent_nominations = db.execute("""
        SELECT n.*, u.username, u.email
        FROM nominations n
        JOIN users u ON n.user_id = u.id
        ORDER BY n.created_at DESC
        LIMIT 10
    """).fetchall()

    bc                 = get_blockchain()
    chain_info         = bc.get_chain_info()
    blockchain_valid   = chain_info.get('connected', False)
    chain_length       = chain_info.get('blockNumber', 0) or 0

    return render_template('admin_dashboard.html',
                          stats=stats,
                          vote_counts=vote_counts,
                          recent_nominations=recent_nominations,
                          blockchain_valid=blockchain_valid,
                          chain_length=chain_length)


@app.route('/admin/nominations')
@login_required
def admin_nominations():
    """
    Admin view all nominations — with search and OCR check columns.
    Supports: ?status=all|approved|rejected|pending  AND  ?search=<query>
    """
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))

    db            = get_db()
    status_filter = request.args.get('status', 'all')
    search_query  = request.args.get('search', '').strip()

    base_query = """
        SELECT n.*, u.username, u.email
        FROM nominations n
        JOIN users u ON n.user_id = u.id
        WHERE 1=1
    """
    params = []

    if status_filter != 'all':
        base_query += " AND n.status = ?"
        params.append(status_filter)

    if search_query:
        base_query += """ AND (
            n.name LIKE ? OR n.department LIKE ? OR n.role LIKE ? OR u.username LIKE ?
        )"""
        like = f'%{search_query}%'
        params.extend([like, like, like, like])

    base_query += " ORDER BY n.created_at DESC"
    nominations = db.execute(base_query, params).fetchall()

    nom_list = []
    for n in nominations:
        nd = dict(n)
        try:
            nd['rejection_reasons_list'] = json.loads(n['rejection_reasons']) if n['rejection_reasons'] else []
        except Exception:
            nd['rejection_reasons_list'] = []

        nd['ocr_summary'] = {
            'name_match'    : bool(nd.get('ocr_name_match', 0)),
            'no_fail'       : not bool(nd.get('ocr_fail_detected', 0)),
            'reg_consistent': bool(nd.get('ocr_register_consistent', 0)),
            'extracted_name': nd.get('ocr_extracted_name', ''),
            'extracted_reg' : nd.get('ocr_extracted_register', ''),
        }
        nom_list.append(nd)

    return render_template('admin_nominations.html',
                          nominations=nom_list,
                          status_filter=status_filter,
                          search_query=search_query)


@app.route('/admin/votes')
@login_required
def admin_votes():
    """Admin view: votes from SQLite + real on-chain event log"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('voter_dashboard'))

    db     = get_db()
    bc_client = get_blockchain()

    votes = db.execute("""
        SELECT v.*, u.username AS voter_name,
               n.name AS candidate_name, n.role
        FROM votes v
        JOIN users u ON v.voter_id = u.id
        JOIN nominations n ON v.nomination_id = n.id
        ORDER BY v.timestamp DESC
    """).fetchall()

    # On-chain events — real Ethereum event logs
    chain_events = bc_client.get_recent_events()
    chain_info   = bc_client.get_chain_info()

    # Build chain_data list for the existing template
    chain_data = []
    for i, ev in enumerate(chain_events):
        chain_data.append({
            'index':         i + 1,
            'hash':          ev['transactionHash'],
            'previous_hash': '0x' + '0' * 62,
            'timestamp':     ev.get('timestamp', ''),
            'nonce':         21000,
            'data': {
                'type':           'vote',
                'voter_name':     ev.get('voterName', ''),
                'voter_id':       ev.get('voterId', ''),
                'role':           ev.get('role', ''),
                'transaction_id': ev['transactionHash'],
            }
        })

    return render_template(
        'admin_votes.html',
        votes=votes,
        chain_data=chain_data,
        chain_info=chain_info,
    )


@app.route('/admin/announce-winner', methods=['POST'])
@login_required
def announce_winner():
    """
    FIX 6 + FIX 10: Admin announces election winners.
    - Emails each winner (send_winner_announcement_email)
    - Emails the admin/election owner (send_result_declared_admin_email) — NEW
    - Stores result in DB settings
    - Returns JSON so frontend can update instantly without full reload
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    db = get_db()
    winners_rows = db.execute("""
        SELECT n.name, n.role, n.id, u.email, COUNT(v.id) as vote_count
        FROM nominations n
        LEFT JOIN votes v ON n.id = v.nomination_id
        JOIN users u ON n.user_id = u.id
        WHERE n.status = 'approved'
        GROUP BY n.id, n.name, n.role, u.email
        ORDER BY n.role, vote_count DESC
    """).fetchall()

    role_winners = {}
    for w in winners_rows:
        if w['role'] not in role_winners:
            role_winners[w['role']] = dict(w)

    # FIX 6: Email each winner
    email_results = []
    for role, winner in role_winners.items():
        ok = send_winner_announcement_email(winner['email'], winner['name'], role, winner['vote_count'])
        email_results.append({'role': role, 'name': winner['name'], 'email_sent': ok})

    # FIX 6: Email the admin/election owner
    admin_email = current_user.email
    admin_ok = send_result_declared_admin_email(admin_email, role_winners)
    email_results.append({'role': 'admin_notification', 'email_sent': admin_ok})

    # FIX 1: Persist to DB immediately, commit before returning
    db.execute("""
        INSERT OR REPLACE INTO settings (key, value) VALUES ('winner_announced', ?)
    """, [json.dumps(role_winners, default=str)])
    db.commit()

    # FIX 9: If AJAX request, return JSON so frontend updates instantly
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.accept_mimetypes.best == 'application/json':
        return jsonify({
            'success': True,
            'message': 'Winners announced and emails sent!',
            'winners': role_winners,
            'emails'  : email_results
        })

    flash('Winner announced and notification emails sent!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/results')
def election_results():
    """Public election results page"""
    db = get_db()
    announcement = db.execute("SELECT value FROM settings WHERE key='winner_announced'").fetchone()

    results = db.execute("""
        SELECT n.id, n.name, n.role, n.department, u.username, COUNT(v.id) as vote_count
        FROM nominations n
        LEFT JOIN votes v ON n.id = v.nomination_id
        JOIN users u ON n.user_id = u.id
        WHERE n.status = 'approved'
        GROUP BY n.id, n.name, n.role, n.department, u.username
        ORDER BY n.role, vote_count DESC
    """).fetchall()

    results_by_role = {}
    for r in results:
        role = r['role']
        if role not in results_by_role:
            results_by_role[role] = []
        results_by_role[role].append(dict(r))

    announced = announcement is not None
    return render_template('election_results.html',
                          results_by_role=results_by_role,
                          announced=announced)


@app.route('/admin/nomination/<int:nom_id>/update', methods=['POST'])
@login_required
def update_nomination_status(nom_id):
    """
    FIX 1 + FIX 4 + FIX 9: Admin manually update nomination status.
    - DB update is committed immediately before any response
    - If status → 'approved': sends approval email to candidate
    - Supports both AJAX (returns JSON) and regular form POST (redirect)
    """
    if current_user.role != 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Access denied'}), 403
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))

    new_status = request.form.get('status')
    if new_status not in ['approved', 'rejected', 'pending']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Invalid status'}), 400
        flash('Invalid status.', 'error')
        return redirect(url_for('admin_nominations'))

    db = get_db()

    # Fetch nomination data BEFORE update (for email)
    nom = db.execute("""
        SELECT n.*, u.email, u.username
        FROM nominations n
        JOIN users u ON n.user_id = u.id
        WHERE n.id = ?
    """, [nom_id]).fetchone()

    if not nom:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Nomination not found'}), 404
        flash('Nomination not found.', 'error')
        return redirect(url_for('admin_nominations'))

    # FIX 1: Commit DB change immediately
    db.execute('UPDATE nominations SET status = ? WHERE id = ?', [new_status, nom_id])
    db.commit()

        # ── Mirror status change to blockchain ──────────────────────
    try:
        bc_client = get_blockchain()
        nom_row = db.execute(
            'SELECT * FROM nominations WHERE id = ?', [nom_id]
        ).fetchone()
        if nom_row:
            # Register nomination on chain if not already there
            bc_client.register_nomination(
                nomination_id = int(nom_id),
                name          = nom_row['name'],
                department    = nom_row['department'],
                role          = nom_row['role'],
                approved      = (new_status == 'approved'),
            )
            # Update status
            bc_client.update_nomination_status(
                nomination_id = int(nom_id),
                approved      = (new_status == 'approved'),
            )
    except Exception as bc_err:
        # Non-fatal — log and continue
        print(f"[Blockchain] nomination status write error: {bc_err}")
    # ── End blockchain mirror ─────────────────────────────────────

    # FIX 4: Send approval email when admin approves a nomination
    email_sent = False
    if new_status == 'approved':
        try:
            reasons = json.loads(nom['rejection_reasons']) if nom['rejection_reasons'] else []
        except Exception:
            reasons = []
        email_sent = send_nomination_approved_email(
            nom['email'],
            nom['name'],
            nom['role']
        )

    # FIX 9: Return JSON for AJAX callers so UI updates instantly
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success'   : True,
            'nom_id'    : nom_id,
            'new_status': new_status,
            'email_sent': email_sent,
            'message'   : f'Nomination #{nom_id} updated to {new_status}.'
        })

    flash(f'Nomination #{nom_id} status updated to {new_status}.', 'success')
    return redirect(url_for('admin_nominations'))


# Add enumerate filter to Jinja2
@app.template_filter('enumerate')
def jinja2_enumerate(iterable, start=0):
    return enumerate(iterable, start=start)


@app.template_filter('fmt_datetime')
def fmt_datetime(value):
    """
    Format a datetime string for IST display.
    All timestamps in this app are stored as IST (datetime.now().isoformat()).
    The only exception is users.created_at which used SQLite datetime('now') (UTC).
    We correct for that by checking: if hour < 6 and it looks like a registration
    time, we add IST offset. For all other timestamps we display as-is.
    Simpler approach: always display as-is but format nicely — the app now saves
    IST explicitly via datetime.now() so no conversion needed.
    """
    if not value:
        return '-'
    try:
        from datetime import datetime, timedelta
        s = str(value)[:26]
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d'):
            try:
                dt = datetime.strptime(s, fmt)
                # users.created_at uses SQLite datetime('now') which is UTC.
                # All other timestamps use datetime.now().isoformat() which is IST.
                # We distinguish by checking if the value comes from the DB default
                # (contains no 'T' separator = SQLite format) vs isoformat (has 'T').
                # SQLite default format: '2026-05-05 05:15:00' → add IST offset.
                # isoformat format:      '2026-05-05T10:47:38.587700' → display as-is.
                if 'T' not in str(value):
                    dt = dt + timedelta(hours=5, minutes=30)
                return dt.strftime('%d %b %Y, %I:%M %p') + ' IST'
            except ValueError:
                continue
        return str(value)
    except Exception:
        return str(value) if value else '-'


# ============================================================
# ADMIN — EXTRA ROUTES
# ============================================================

@app.route('/admin/users')
@login_required
def admin_users():
    """Admin: view all registered users."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    # Wrap rows as dicts so templates can access missing columns safely
    user_list = []
    for u in users:
        row = dict(u)
        row.setdefault('full_name', None)
        row.setdefault('course', None)
        row.setdefault('semester', None)
        row.setdefault('year', None)
        user_list.append(row)
    return render_template('admin_users.html', users=user_list)


@app.route('/admin/users/clean', methods=['POST'])
@login_required
def clean_users():
    """Admin: delete all non-admin users."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    db = get_db()
    db.execute("DELETE FROM users WHERE role != 'admin'")
    db.commit()
    flash('All non-admin users removed.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/export')
@login_required
def export_users():
    """Admin: export users as CSV."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    import csv, io
    from flask import Response
    db = get_db()
    users = db.execute('SELECT id, username, email, role, created_at FROM users').fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Username', 'Email', 'Role', 'Created At'])
    for u in users:
        writer.writerow([u['id'], u['username'], u['email'], u['role'], u['created_at']])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=users.csv'})


@app.route('/admin/candidates')
@login_required
def admin_candidates():
    """Admin: view approved candidates."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    db = get_db()
    candidates = db.execute("""
        SELECT n.*, u.username, u.email, u.course as user_course,
               COUNT(v.id) as vote_count
        FROM nominations n
        JOIN users u ON n.user_id = u.id
        LEFT JOIN votes v ON v.nomination_id = n.id
        GROUP BY n.id
        ORDER BY n.role
    """).fetchall()
    candidate_list = []
    for c in candidates:
        row = dict(c)
        # course: prefer nomination department, fall back to user course
        if not row.get('course'):
            row['course'] = row.get('user_course') or row.get('department') or ''
        candidate_list.append(row)
    return render_template('admin_candidates.html', candidates=candidate_list)


@app.route('/admin/candidates/clean', methods=['POST'])
@login_required
def clean_candidates():
    """Admin: remove all nominations and their related votes."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    db = get_db()
    db.execute("DELETE FROM votes WHERE nomination_id IN (SELECT id FROM nominations)")
    db.execute("DELETE FROM nominations")
    db.commit()
    flash('All candidates and related votes removed.', 'success')
    return redirect(url_for('admin_candidates'))


@app.route('/admin/candidates/export')
@login_required
def export_candidates():
    """Admin: export candidates as CSV."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    import csv, io
    from flask import Response
    db = get_db()
    rows = db.execute("""
        SELECT n.id, n.name, n.department, n.role, n.cgpa, n.year, u.email
        FROM nominations n JOIN users u ON n.user_id = u.id
        WHERE n.status = 'approved'
    """).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Department', 'Role', 'CGPA', 'Year', 'Email'])
    for r in rows:
        writer.writerow([r['id'], r['name'], r['department'], r['role'],
                         r['cgpa'], r['year'], r['email']])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=candidates.csv'})


@app.route('/admin/voters')
@login_required
def admin_voters_list():
    """Admin: view all voters who have voted."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    db = get_db()
    # Fetch ALL users (voters), regardless of whether they have voted
    all_users = db.execute("""
        SELECT u.id, u.username, u.email, u.full_name, u.course, u.year
        FROM users u
        WHERE u.role = 'voter'
        ORDER BY u.username
    """).fetchall()

    # Fetch all votes with candidate name and role
    all_votes = db.execute("""
        SELECT v.voter_id, n.name as candidate_name, n.role as position, v.timestamp
        FROM votes v
        JOIN nominations n ON v.nomination_id = n.id
        ORDER BY v.timestamp
    """).fetchall()

    # Build a lookup: voter_id -> list of {candidate_name, position, timestamp}
    vote_map = {}
    for vote in all_votes:
        vid = vote['voter_id']
        if vid not in vote_map:
            vote_map[vid] = []
        vote_map[vid].append({
            'name': vote['candidate_name'],
            'role': vote['position'],
            'timestamp': vote['timestamp'],
        })

    # Build voter list with enriched fields
    voters = []
    for u in all_users:
        uid = u['id']
        user_votes = vote_map.get(uid, [])
        voters.append({
            'id':              uid,
            'username':        u['username'],
            'email':           u['email'],
            'full_name':       u['full_name'] or '',
            'course':          u['course'] or '',
            'year':            u['year'] or '',
            'has_voted':       'Yes' if user_votes else 'No',
            'voted_for_names': [v['name'] for v in user_votes],
            'voted_for_roles': [v['role'] for v in user_votes],
            'vote_timestamp':  user_votes[0]['timestamp'] if user_votes else None,
        })

    return render_template('admin_voters_list.html', voters=voters)


@app.route('/admin/voters/clean', methods=['POST'])
@login_required
def clean_votes():
    """Admin: delete all votes."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    db = get_db()
    db.execute("DELETE FROM votes")
    db.commit()
    flash('All votes cleared.', 'success')
    return redirect(url_for('admin_voters_list'))


@app.route('/admin/voters/export')
@login_required
def export_voters():
    """Admin: export voters list as CSV."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('voter_dashboard'))
    import csv, io
    from flask import Response
    db = get_db()
    all_users = db.execute("""
        SELECT u.id, u.username, u.email, u.full_name, u.course, u.year
        FROM users u WHERE u.role = 'voter' ORDER BY u.username
    """).fetchall()
    all_votes = db.execute("""
        SELECT v.voter_id, n.name as candidate_name, n.role as position, v.timestamp
        FROM votes v JOIN nominations n ON v.nomination_id = n.id
    """).fetchall()
    vote_map = {}
    for vote in all_votes:
        vid = vote['voter_id']
        if vid not in vote_map:
            vote_map[vid] = []
        vote_map[vid].append(vote)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Username', 'Full Name', 'Email', 'Course', 'Year',
                     'Has Voted', 'Voted For', 'Positions', 'Vote Time'])
    for u in all_users:
        uid = u['id']
        uv = vote_map.get(uid, [])
        writer.writerow([
            uid, u['username'], u['full_name'] or '', u['email'],
            u['course'] or '', u['year'] or '',
            'Yes' if uv else 'No',
            ' | '.join(v['candidate_name'] for v in uv),
            ' | '.join(v['position'] for v in uv),
            uv[0]['timestamp'] if uv else '',
        ])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=voters.csv'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
