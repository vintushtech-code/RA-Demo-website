"""
Two-Factor Authentication (2FA / Two-Way Verification) Engine
============================================================

Provides rock-solid 6-digit OTP verification for Admin/Staff authentication.

Key Features:
1. Cryptographically Secure 6-digit OTP code generation via `secrets`.
2. Instant Terminal Output: Every code generated is prominently printed to `sys.stdout` / terminal console.
3. Configurable Recipient Email: Sends to the user's email address or to `settings.ADMIN_2FA_EMAIL`.
4. Expiry & Attempt Limits: Codes expire in 5 minutes (300s); max 5 failed attempts trigger session invalidation.
5. Resend Cooldown Protection: 30-second cooldown timer between resend requests.
"""

import sys
import time
import secrets
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Security & Expiry Constants
OTP_EXPIRY_SECONDS = getattr(settings, 'ADMIN_2FA_CODE_EXPIRY_SECONDS', 300)  # Default: 5 minutes (300s)
MAX_OTP_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 30


def generate_otp_code():
    """
    Generates a cryptographically secure 6-digit numeric OTP string (100000 - 999999).
    """
    return f"{secrets.randbelow(900000) + 100000}"


import hmac
import hashlib

def _generate_session_signature(user_id, otp_code, created_at):
    """
    Generates a cryptographically HMAC signature tying user_id, otp_code, and creation timestamp
    to Django's SECRET_KEY to prevent session tampering or state injection.
    """
    msg = f"{user_id}:{otp_code}:{created_at}".encode('utf-8')
    key = settings.SECRET_KEY.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def send_2fa_otp(user, request, is_resend=False, **kwargs):
    """
    Generates a new 6-digit 2FA OTP code, updates session state,
    prints the verification code directly to the terminal console,
    and sends an email notification.
    """
    code = generate_otp_code()
    now = time.time()
    sig = _generate_session_signature(user.pk, code, now)

    # Store 2FA verification state securely in session
    request.session['pre_2fa_user_id'] = user.pk
    request.session['pre_2fa_otp'] = code
    request.session['pre_2fa_created'] = now
    request.session['pre_2fa_sig'] = sig
    request.session['pre_2fa_attempts'] = 0
    request.session['pre_2fa_last_sent'] = now

    # Determine recipient email address (Settings override or user email)
    configured_admin_email = getattr(settings, 'ADMIN_2FA_EMAIL', '').strip()
    target_email = configured_admin_email if configured_admin_email else user.email

    # ----------------------------------------------------------------------
    # 1. Print Prominently to Terminal Console
    # ----------------------------------------------------------------------
    terminal_banner = f"""
================================================================================
🛡️ ADMIN 2-WAY VERIFICATION OTP CODE GENERATED 🛡️
--------------------------------------------------------------------------------
User Account : {user.username} (ID: {user.pk})
Target Email : {target_email}
Verification Code : >>> {code} <<<
Valid Duration   : {OTP_EXPIRY_SECONDS // 60} Minutes ({OTP_EXPIRY_SECONDS} Seconds)
Trigger Time     : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}
--------------------------------------------------------------------------------
Enter this 6-digit code on the 2FA Verification Page to complete login.
================================================================================
"""
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer.write(terminal_banner.encode('utf-8', errors='replace'))
            sys.stdout.buffer.flush()
        else:
            sys.stdout.write(terminal_banner)
            sys.stdout.flush()
    except Exception:
        ascii_banner = terminal_banner.encode('ascii', errors='replace').decode('ascii')
        sys.stdout.write(ascii_banner)
        sys.stdout.flush()

    logger.info(f"Admin 2FA OTP generated for user '{user.username}' -> Code: {code}")

    # ----------------------------------------------------------------------
    # 2. Send Luxury HTML Email (Terminal Mode in Dev / Real SMTP in Prod)
    # ----------------------------------------------------------------------
    subject = f"[{code}] Admin 2-Way Verification Security Code — Sabin Balan Finance"
    context = {
        'user': user,
        'code': code,
        'expiry_minutes': OTP_EXPIRY_SECONDS // 60,
        'target_email': target_email,
        'is_resend': is_resend,
    }

    try:
        from .emails import send_luxury_email
        send_luxury_email(
            subject=subject,
            template_name='emails/email_2fa_code.html',
            context=context,
            recipient_list=[target_email],
            fail_silently=True,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to dispatch 2FA email to {target_email}: {e}")

    return code


def verify_2fa_otp(request, submitted_code):
    """
    Validates submitted 6-digit OTP code against active session state.
    Uses constant-time comparison (hmac.compare_digest) and HMAC session signature integrity verification.
    Returns: (is_valid: bool, error_message: str or None)
    """
    user_id = request.session.get('pre_2fa_user_id')
    saved_code = request.session.get('pre_2fa_otp')
    created_at = request.session.get('pre_2fa_created', 0)
    saved_sig = request.session.get('pre_2fa_sig')
    attempts = request.session.get('pre_2fa_attempts', 0)

    if not saved_code or not user_id or not saved_sig:
        return False, "Verification session expired or invalid. Please sign in again."

    # Validate session HMAC signature integrity
    expected_sig = _generate_session_signature(user_id, saved_code, created_at)
    if not hmac.compare_digest(str(saved_sig), str(expected_sig)):
        clear_2fa_session(request)
        return False, "Session integrity violation detected. Please sign in again."

    # Enforce Maximum Attempt Limit
    if attempts >= MAX_OTP_ATTEMPTS:
        clear_2fa_session(request)
        return False, "Too many incorrect verification attempts. Security lock triggered. Please sign in again."

    # Enforce Expiration Time
    if time.time() - created_at > OTP_EXPIRY_SECONDS:
        clear_2fa_session(request)
        return False, f"Verification code expired (valid for {OTP_EXPIRY_SECONDS // 60} minutes). Please sign in again."

    clean_code = str(submitted_code).strip()

    # Constant-time string comparison to prevent timing attacks
    if not hmac.compare_digest(clean_code, str(saved_code)):
        attempts += 1
        request.session['pre_2fa_attempts'] = attempts
        remaining = MAX_OTP_ATTEMPTS - attempts
        if remaining > 0:
            return False, f"Invalid 6-digit verification code. {remaining} attempt(s) remaining."
        else:
            clear_2fa_session(request)
            return False, "Too many incorrect verification attempts. Security lock triggered. Please sign in again."

    # Verification successful!
    return True, None


def can_resend_otp(request):
    """
    Checks if enough time has passed (cooldown period) to request a new code.
    Returns: (can_resend: bool, wait_seconds_remaining: int)
    """
    last_sent = request.session.get('pre_2fa_last_sent', 0)
    elapsed = time.time() - last_sent
    if elapsed < RESEND_COOLDOWN_SECONDS:
        return False, int(RESEND_COOLDOWN_SECONDS - elapsed)
    return True, 0


def clear_2fa_session(request):
    """
    Clears all 2FA verification session variables upon completion or failure.
    """
    keys = [
        'pre_2fa_user_id',
        'pre_2fa_otp',
        'pre_2fa_created',
        'pre_2fa_sig',
        'pre_2fa_attempts',
        'pre_2fa_last_sent',
        'pre_2fa_remember_me',
        'pre_2fa_next',
    ]
    for key in keys:
        request.session.pop(key, None)
