/**
 * College Election System - Main JavaScript
 * Handles: navigation toggle, password toggle, auto-dismiss alerts,
 *          live vote counter animation, and utility functions
 */

// ===== NAVIGATION TOGGLE (Mobile) =====
function toggleNav() {
    const navLinks = document.getElementById('navLinks');
    if (navLinks) {
        navLinks.classList.toggle('open');
    }
}

// Close nav when clicking outside
document.addEventListener('click', function(e) {
    const navLinks = document.getElementById('navLinks');
    const toggle = document.querySelector('.nav-toggle');
    if (navLinks && toggle && !navLinks.contains(e.target) && !toggle.contains(e.target)) {
        navLinks.classList.remove('open');
    }
});

// ===== PASSWORD TOGGLE =====
function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
    } else {
        input.type = 'password';
        btn.textContent = '👁️';
    }
}

// ===== AUTO-DISMISS FLASH MESSAGES =====
document.addEventListener('DOMContentLoaded', function() {
    const flashMsgs = document.querySelectorAll('.flash-msg');
    flashMsgs.forEach(function(msg) {
        setTimeout(function() {
            msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(function() {
                if (msg.parentNode) {
                    msg.parentNode.removeChild(msg);
                }
            }, 500);
        }, 5000); // Dismiss after 5 seconds
    });
});

// ===== ANIMATED COUNTER (for stats bar) =====
function animateCounter(element, target, duration) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;

    const timer = setInterval(function() {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current);
    }, 16);
}

// Animate stat numbers on page load
document.addEventListener('DOMContentLoaded', function() {
    const statNumbers = document.querySelectorAll('.stat-number[data-target]');
    statNumbers.forEach(function(el) {
        const target = parseInt(el.getAttribute('data-target'));
        if (!isNaN(target) && target > 0) {
            el.textContent = '0';
            setTimeout(function() {
                animateCounter(el, target, 800);
            }, 300);
        }
    });
});

// ===== VOTE BAR ANIMATION =====
document.addEventListener('DOMContentLoaded', function() {
    // Animate vote bars with a slight delay
    const voteBars = document.querySelectorAll('.vote-bar-fill, .rc-bar');
    voteBars.forEach(function(bar) {
        const width = bar.style.width;
        bar.style.width = '0';
        setTimeout(function() {
            bar.style.width = width;
        }, 200);
    });
});

// ===== FILE UPLOAD DRAG & DROP =====
document.addEventListener('DOMContentLoaded', function() {
    const uploadBoxes = document.querySelectorAll('.file-upload-box');
    
    uploadBoxes.forEach(function(box) {
        box.addEventListener('dragover', function(e) {
            e.preventDefault();
            box.style.borderColor = '#1a237e';
            box.style.background = '#eef0fc';
        });
        
        box.addEventListener('dragleave', function() {
            box.style.borderColor = '';
            box.style.background = '';
        });
        
        box.addEventListener('drop', function(e) {
            e.preventDefault();
            box.style.borderColor = '';
            box.style.background = '';
            
            // Find associated file input (sibling or nearby)
            const fileInput = box.parentElement.querySelector('input[type="file"]');
            if (fileInput && e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
    });
});

// ===== BLOCKCHAIN STATUS LIVE REFRESH =====
function updateBlockchainStatus() {
    fetch('/api/blockchain-status')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            // Update chain length displays
            const chainLengthEls = document.querySelectorAll('#chainLength, #chainLengthStat, #adminChainLength');
            chainLengthEls.forEach(function(el) {
                if (el) el.textContent = data.chain_length + (el.id === 'chainLength' ? ' blocks' : '');
            });
        })
        .catch(function(e) { /* Silently fail */ });
}

// ===== FORM LOADING STATE =====
function setFormLoading(formId, btnId, loadingText) {
    const form = document.getElementById(formId);
    const btn = document.getElementById(btnId);
    if (form && btn) {
        form.addEventListener('submit', function() {
            btn.textContent = loadingText || 'Processing...';
            btn.disabled = true;
        });
    }
}

// ===== COPY TO CLIPBOARD =====
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Copied to clipboard!');
        });
    } else {
        // Fallback
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        showToast('Copied!');
    }
}

// ===== TOAST NOTIFICATION =====
function showToast(message, type) {
    type = type || 'info';
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; z-index: 9999;
        background: ${type === 'error' ? '#dc3545' : '#1a237e'};
        color: white; padding: 12px 20px;
        border-radius: 8px; font-size: 0.9rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease;
        max-width: 300px;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s';
        setTimeout(function() {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 500);
    }, 3000);
}

// ===== HASH CLICK TO COPY =====
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.hash-value, .hash-short').forEach(function(el) {
        el.style.cursor = 'pointer';
        el.title = 'Click to copy full hash';
        el.addEventListener('click', function() {
            copyToClipboard(el.textContent.trim());
        });
    });
});

// ===== SMOOTH SCROLL =====
document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// ===== TABLE SEARCH (admin tables) =====
function filterTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;

    input.addEventListener('keyup', function() {
        const filter = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(function(row) {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(filter) ? '' : 'none';
        });
    });
}

// ===== CONFIRM DIALOGS =====
function confirmAction(message, formEl) {
    if (confirm(message)) {
        if (formEl) formEl.submit();
        return true;
    }
    return false;
}

// ===== INITIALIZE =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏛️ College Election System initialized');
    console.log('⛓️ Blockchain: SHA-256 Proof of Work');
    console.log('🤖 AI: EasyOCR + Face Recognition');
    
    // Initialize blockchain status refresh every 60s
    setInterval(updateBlockchainStatus, 60000);
});
